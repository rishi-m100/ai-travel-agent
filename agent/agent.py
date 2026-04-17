from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
import anthropic
from pathlib import Path
from agent.tool_schemas import TOOL_SCHEMAS
from agent.tools import execute_tool
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

DB_PATH = Path(__file__).parent.parent / "data" / "mindy_dataset.db"

MAX_AGENT_TURNS = 10
MAX_REVISION_COUNT = 10

# ---------------------------------------------------------------------------
# Constraint parser (pre-loop step)
# ---------------------------------------------------------------------------

_CONSTRAINT_PARSER_TOOL = {
    "name": "extract_constraints",
    "description": (
        "Extract structured travel constraints from the user's message. "
        "Categorise every requirement into hard, soft, or assumptions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hard": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Non-negotiable requirements (dates, origin, destination, "
                    "budget ceiling, number of travellers, etc.)"
                ),
            },
            "soft": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Preferences that are nice-to-have but not deal-breakers "
                    "(amenities, activity types, airline preference, hotel "
                    "tier, etc.)"
                ),
            },
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Things inferred but not explicitly stated by the user "
                    "(e.g. 'assumed year is 2025', 'assuming round-trip', "
                    "'assuming 1 traveller')."
                ),
            },
        },
        "required": ["hard", "soft", "assumptions"],
    },
}

_CONSTRAINT_PARSER_SYSTEM = (
    "You are a constraint extraction assistant. Given a user travel request, "
    "call the extract_constraints tool to return every requirement broken into "
    "three categories: hard (non-negotiable), soft (preferences), and "
    "assumptions (inferred but not stated). Be thorough."
)


def parse_constraints(user_message: str) -> dict:
    """Make a forced-tool-use LLM call to extract structured constraints.

    Returns a dict with keys: hard, soft, assumptions (each a list of str).
    """
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        temperature=0,
        system=_CONSTRAINT_PARSER_SYSTEM,
        tools=[_CONSTRAINT_PARSER_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    # The response will contain a single tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_constraints":
            return block.input

    # Fallback — should not happen with tool_choice="any"
    return {"hard": [], "soft": [], "assumptions": []}

SYSTEM_PROMPT = """You are Mindy, a travel agent. You have tools to search for flights, hotels, and activities. Only use IDs returned by the tools — do not ever invent or create one that doesn't exist.

DATABASE COVERAGE: Flight and hotel data exists from 2021-04-11 through 2026-04-11. When a user gives a date without a year (for example "June 12-15"), infer the most recent past year where data exists - so "June 12-15" means 2025-06-12 to 2025-06-15. Don't assume a future year outside the data range. If the user says "next month" or "this summer" relative to today (2026-04-11), use the closest matching dates that fall within the data range (default to 2025 for summer months).

OUTPUT RULE - STRICT: Your very last action in every response MUST be a `submit_itinerary` tool call. You are not allowed to end your turn with a text message. This applies even when:
- The user only asked for flights (pass empty hotels/activities arrays)
- You want to ask a clarifying question (put it in the 'message' field, pass empty arrays)
- You found nothing (explain in 'message', pass empty arrays and total_cost 0)
- You want to show multiple options (pick the best one for the structured fields, mention others in 'message')
Never stop with end_turn text. Always finish with submit_itinerary.

REASONING RULE: For every flight, hotel, and activity you select in submit_itinerary, you MUST include a brief 'reason' explaining why you chose it — e.g. price, timing, rating, proximity, user preference match. This helps the user understand your recommendations."""

# ---------------------------------------------------------------------------
# Constraint verification layer
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def verify_constraints(itinerary: dict) -> list[str]:
    """Validate all IDs exist in the DB, check hotel availability windows,
    verify activity days_open, and ensure cost is consistent."""
    violations = []

    raw_flights    = itinerary.get("flights", [])
    raw_hotels     = itinerary.get("hotels", [])
    raw_activities = itinerary.get("activities", [])
    reported_cost  = itinerary.get("total_cost", 0)
    check_in       = itinerary.get("check_in")
    check_out      = itinerary.get("check_out")
    hotel_nights   = itinerary.get("hotel_nights", 1)

    # Extract IDs — handle both {id, reason} objects and plain strings
    def _extract_ids(items):
        return [
            (item["id"] if isinstance(item, dict) else item)
            for item in items
        ]

    flight_ids   = _extract_ids(raw_flights)
    hotel_ids    = _extract_ids(raw_hotels)
    activity_ids = _extract_ids(raw_activities)

    computed_cost = 0.0

    with _get_conn() as conn:
        # --- Validate flight IDs ---
        for fid in flight_ids:
            row = conn.execute(
                "SELECT price, seats_available FROM flights WHERE flight_id = ?",
                (fid,),
            ).fetchone()
            if row is None:
                violations.append(f"Flight ID '{fid}' does not exist in the database.")
            else:
                if row["seats_available"] is not None and row["seats_available"] <= 0:
                    violations.append(
                        f"Flight '{fid}' has no available seats."
                    )
                computed_cost += row["price"]

        # --- Validate hotel IDs + availability windows ---
        for hid in hotel_ids:
            row = conn.execute(
                "SELECT price_per_night FROM hotels WHERE hotel_id = ?",
                (hid,),
            ).fetchone()
            if row is None:
                violations.append(f"Hotel ID '{hid}' does not exist in the database.")
            else:
                # Fix #2: multiply by hotel_nights for multi-night stays
                nights = hotel_nights if hotel_nights and hotel_nights > 0 else 1
                computed_cost += row["price_per_night"] * nights

                # Fix #1: check hotel_availability for the requested dates
                if check_in and check_out:
                    avail = conn.execute(
                        """SELECT 1 FROM hotel_availability
                           WHERE hotel_id = ?
                             AND check_in <= ? AND check_out >= ?
                             AND rooms_left > 0""",
                        (hid, check_in, check_out),
                    ).fetchone()
                    if avail is None:
                        violations.append(
                            f"Hotel '{hid}' has no availability for "
                            f"{check_in} to {check_out}."
                        )

        # --- Validate activity IDs + days_open ---
        # Build set of day-of-week abbreviations for the trip dates
        trip_days: set[str] = set()
        if check_in and check_out:
            try:
                ci = datetime.strptime(check_in, "%Y-%m-%d")
                co = datetime.strptime(check_out, "%Y-%m-%d")
                d = ci
                while d < co:
                    trip_days.add(d.strftime("%a"))  # 'Mon', 'Tue', etc.
                    d += timedelta(days=1)
            except ValueError:
                pass  # if dates can't be parsed, skip days_open check

        for aid in activity_ids:
            row = conn.execute(
                "SELECT cost, days_open FROM activities WHERE activity_id = ?",
                (aid,),
            ).fetchone()
            if row is None:
                violations.append(
                    f"Activity ID '{aid}' does not exist in the database."
                )
            else:
                computed_cost += row["cost"]

                # Fix #5: check days_open against trip dates
                if trip_days and row["days_open"]:
                    try:
                        open_days = set(json.loads(row["days_open"]))
                        if not trip_days & open_days:
                            violations.append(
                                f"Activity '{aid}' is not open on any of "
                                f"the trip days ({', '.join(sorted(trip_days))})."
                            )
                    except (json.JSONDecodeError, TypeError):
                        pass  # malformed days_open, skip

    # --- Cost sanity check (allow small float tolerance) ---
    if (flight_ids or hotel_ids or activity_ids) and reported_cost > 0:
        if abs(computed_cost - reported_cost) > 1.0:
            violations.append(
                f"Reported total_cost (${reported_cost:.2f}) does not match "
                f"computed cost (${computed_cost:.2f}). Please recalculate."
            )

    return violations


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_OUTPUT_FIELDS = ("flights", "hotels", "activities", "total_cost",
                  "check_in", "check_out", "hotel_nights")


def _build_response(itinerary: dict, *, trace: list[dict],
                    message: str | None = None,
                    error: str | None = None) -> str:
    """Build the final JSON response with eval fields nested under 'output'."""
    output = {k: itinerary.get(k) for k in _OUTPUT_FIELDS
              if itinerary.get(k) is not None}
    # Ensure arrays default to [] and cost defaults to 0
    for arr_key in ("flights", "hotels", "activities"):
        output.setdefault(arr_key, [])
    output.setdefault("total_cost", 0)

    resp: dict = {"output": output}
    if message or itinerary.get("message"):
        resp["message"] = message or itinerary.get("message", "")
    if error:
        resp["error"] = error
    resp["trace"] = trace
    return json.dumps(resp, indent=2)


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(user_message: str, verbose: bool = False) -> str:
    """Run the agentic loop. Returns JSON string of the final itinerary."""

    # --- Pre-loop: parse constraints ---
    constraints = parse_constraints(user_message)
    if verbose:
        print(f"[constraints] {json.dumps(constraints, indent=2)}")

    constraints_block = (
        "\n\nPARSED CONSTRAINTS (use these to guide your search):\n"
        f"Hard (non-negotiable): {json.dumps(constraints.get('hard', []))}\n"
        f"Soft (preferences):    {json.dumps(constraints.get('soft', []))}\n"
        f"Assumptions:           {json.dumps(constraints.get('assumptions', []))}\n"
    )
    augmented_system = SYSTEM_PROMPT + constraints_block

    messages = [{"role": "user", "content": user_message}]
    trace: list[dict] = [{"step": "parse_constraints", "output": constraints}]
    turn = 0
    revision_count = 0

    while True:
        turn += 1
        if turn > MAX_AGENT_TURNS:
            if verbose:
                print(f"[agent] Max turns ({MAX_AGENT_TURNS}) exceeded")
            return _build_response(
                {}, trace=trace,
                message="I ran out of planning steps. Please try a simpler query.",
                error="max turns exceeded",
            )

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            temperature=0,
            system=augmented_system,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Record token usage for this turn
        token_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        messages.append({"role": "assistant", "content": response.content})

        # --- end_turn fallback (fragile-safe) ---
        if response.stop_reason == "end_turn":
            text_block = next(
                (b.text for b in response.content if hasattr(b, "text")), None
            )
            if text_block is None:
                return _build_response(
                    {}, trace=trace,
                    error="agent ended without text or tool call",
                )

            text_response = text_block.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            elif text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            return text_response.strip()

        # --- tool_use handling ---
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                # ---------- submit_itinerary with constraint check ----------
                if block.name == "submit_itinerary":
                    itinerary = block.input
                    violations = verify_constraints(itinerary)

                    trace.append({
                        "turn": turn,
                        "tool": block.name,
                        "input": itinerary,
                        "output": (
                            "PASS" if not violations else violations
                        ),
                        "tokens": token_usage,
                    })

                    if violations:
                        revision_count += 1
                        if verbose:
                            print(
                                f"[constraint] Violations found "
                                f"(revision {revision_count}/{MAX_REVISION_COUNT}): "
                                f"{violations}"
                            )
                        if revision_count > MAX_REVISION_COUNT:
                            return _build_response(
                                itinerary, trace=trace,
                                message=(
                                    "The agent could not produce a "
                                    "constraint-satisfying itinerary within "
                                    f"the revision limit ({MAX_REVISION_COUNT}). "
                                    "Please simplify your request or relax "
                                    "some constraints."
                                ),
                                error="revision limit exceeded",
                            )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                f"Constraint violations found: {json.dumps(violations)}. "
                                "Please fix and resubmit."
                            ),
                        })
                        # Don't return — continue the loop so the agent can fix
                    else:
                        if verbose:
                            print("[constraint] All constraints passed ✓")
                        return _build_response(itinerary, trace=trace)
                    continue

                # ---------- normal tool calls ----------
                if verbose:
                    print(f"[tool] {block.name}({json.dumps(block.input)})")
                result = execute_tool(block.name, block.input)
                if verbose:
                    print(f"[result] {result[:200]}")

                trace.append({
                    "turn": turn,
                    "tool": block.name,
                    "input": block.input,
                    "output": json.loads(result) if result else None,
                    "tokens": token_usage,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    response = run_agent(
        "NYC → LA, June 12–15",
        verbose=True
    )
    print("\n=== RESPONSE ===")
    print(response)