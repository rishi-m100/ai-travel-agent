#!/usr/bin/env python3
"""
Mindy Bench - Benchmarking script for Mindy AI Travel Agent
3 metrics are covered
- Constraint Satisfaction (CS): 0.0 - 1.0
- Budget Efficiency (BE): 0.0 - 1.0
- Logistics Score (LS): 0.0 - 1.0
"""

from __future__ import annotations

import json
import sqlite3
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict
import sys

# Set the database path for benchmarking BEFORE importing agent modules
# This ensures the agent only queries the benchmark database
BENCHMARK_DB_PATH = Path(__file__).parent.parent / "data" / "mindy_dataset_v3.db"
os.environ["MINDY_DB_PATH"] = str(BENCHMARK_DB_PATH)

# Add parent directory to path to import agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent import run_agent
from agent.tools import DB_PATH


@dataclass
class BenchmarkTask:
    """Defines a benchmark task with expected criteria."""
    task_id: str
    name: str
    user_prompt: str
    constraints: dict[str, Any]
    ground_truth: dict[str, Any]
    success_criteria: dict[str, Any]


@dataclass
class TaskScore:
    """Scores for a single task evaluation."""
    task_id: str
    task_name: str
    constraint_satisfaction: float  # 0.0 - 1.0
    budget_efficiency: float        # 0.0 - 1.0
    logistics_score: float          # 0.0 - 1.0
    evaluation_score: float         # Composite weighted score
    passed: bool                    # Binary pass/fail based on threshold
    details: dict[str, Any]
    agent_response: dict[str, Any] | None = None  # Full agent JSON response



# EASY BENCHMARK TASKS (3 tasks)


EASY_TASKS = [
    BenchmarkTask(
        task_id="easy_01",
        name="Find Cheapest Flight in Time Period",
        user_prompt="Find the cheapest flight from Chicago (ORD) to Seattle (SEA) on June 10th, 2025.",
        constraints={},
        ground_truth={
            "type": "flight",
            "origin_city": "Chicago",
            "destination_city": "Seattle",
            "date": "2025-06-10",
            "origin": "ORD",
            "destination": "SEA"
        },
        success_criteria={
            "must_have_flight": True,
            "correct_route": True,
            "correct_date": True,
            "is_cheapest": True,
            "has_availability": True
        }
    ),

    BenchmarkTask(
        task_id="easy_02",
        name="Find Hotel with 1 Amenity Requirement",
        user_prompt="I need a hotel in New York for June 10th, 2025 that has a gym",
        constraints={},
        ground_truth={
            "type": "hotel",
            "city": "New York",
            "check_in": "2025-06-10",
            "required_amenity": "gym"
        },
        success_criteria={
            "must_have_hotel": True,
            "correct_city": True,
            "correct_date": True,
            "has_gym": True,
            "has_availability": True
        }
    ),

    BenchmarkTask(
        task_id="easy_03",
        name="Find Flight within Specific Time Constraint",
        user_prompt="Find a flight from New York (JFK) to Los Angeles (LAX) on June 11th, 2025 that arrives before 4:00 PM.",
        constraints={},
        ground_truth={
            "type": "flight",
            "origin_city": "New York",
            "destination_city": "Los Angeles",
            "date": "2025-06-11",
            "max_arrival_time": "16:00",
            "origin": "JFK",
            "destination": "LAX"
        },
        success_criteria={
            "must_have_flight": True,
            "correct_route": True,
            "correct_date": True,
            "arrives_on_time": True,
            "has_availability": True
        }
    ),

    BenchmarkTask(
        task_id="easy_04",
        name="Find Non-Stop Flight",
        user_prompt="I need a non-stop flight from San Francisco (SFO) to Boston (BOS) on June 10th, 2025.",
        constraints={},
        ground_truth={
            "type": "flight",
            "origin_city": "San Francisco",
            "destination_city": "Boston",
            "date": "2025-06-10",
            "origin": "SFO",
            "destination": "BOS",
            "max_stops": 0
        },
        success_criteria={
            "must_have_flight": True,
            "correct_route": True,
            "correct_date": True,
            "is_nonstop": True,
            "has_availability": True
        }
    ),
]

# MEDIUM BENCHMARK TASKS (4 tasks)

MEDIUM_TASKS = [
    BenchmarkTask(
        task_id="medium_01",
        name="Weekend Trip with Budget - Flight and Hotel",
        user_prompt="I'm in Chicago and need a flight to Miami plus a hotel for a weekend trip (June 10-12, 2025). My total budget is $800.",
        constraints={"max_budget": 800},
        ground_truth={
            "type": "multi",
            "origin_city": "Chicago",
            "origin": "ORD",
            "destination_city": "Miami",
            "destination": "MIA",
            "date": "2025-06-10",
            "check_in": "2025-06-10",
            "check_out": "2025-06-12",
            "hotel_nights": 2
        },
        success_criteria={
            "must_have_flight": True,
            "must_have_hotel": True,
            "correct_destination": True,
            "correct_dates": True,
            "within_budget": True,
            "has_availability": True
        }
    ),

    BenchmarkTask(
        task_id="medium_02",
        name="Multi-Constraint Trip - Hotel Amenity and Activities",
        user_prompt="I'm in Los Angeles and want to plan a 2-day relaxing trip to Denver (June 10-12, 2025). I need a flight, a hotel with a pool, and some wellness activities. Budget is $1,000.",
        constraints={"max_budget": 1000},
        ground_truth={
            "type": "multi",
            "origin_city": "Los Angeles",
            "origin": "LAX",
            "destination_city": "Denver",
            "destination": "DEN",
            "date": "2025-06-10",
            "city": "Denver",
            "check_in": "2025-06-10",
            "check_out": "2025-06-12",
            "hotel_nights": 2,
            "required_amenity": "pool",
            "activity_category": "wellness"
        },
        success_criteria={
            "must_have_flight": True,
            "must_have_hotel": True,
            "correct_destination": True,
            "correct_dates": True,
            "has_required_amenity": True,
            "has_activities": True,
            "within_budget": True,
            "has_availability": True
        }
    ),

    BenchmarkTask(
        task_id="medium_03",
        name="Business Trip with Time Constraint",
        user_prompt="I'm in Philadelphia and have a meeting in Boston at 2 PM on June 10th, 2025. I need a flight from Philadelphia (PHL) that gets me there by noon and a hotel near the airport.",
        constraints={},
        ground_truth={
            "type": "multi",
            "origin_city": "Philadelphia",
            "origin": "PHL",
            "destination_city": "Boston",
            "destination": "BOS",
            "date": "2025-06-10",
            "max_arrival_time": "12:00"
        },
        success_criteria={
            "must_have_flight": True,
            "must_have_hotel": True,
            "correct_destination": True,
            "correct_date": True,
            "arrives_on_time": True,
            "has_availability": True
        }
    ),

    BenchmarkTask(
        task_id="medium_04",
        name="Family Trip with Multiple Activities",
        user_prompt="We're in Boston and want to plan a 3-day family trip to Orlando (June 10-13, 2025). We need a flight, hotel, and 2 fun activities for kids. Our budget is $2,500.",
        constraints={"max_budget": 2500},
        ground_truth={
            "type": "multi",
            "origin_city": "Boston",
            "origin": "BOS",
            "destination_city": "Orlando",
            "destination": "MCO",
            "date": "2025-06-10",
            "city": "Orlando",
            "check_in": "2025-06-10",
            "check_out": "2025-06-13",
            "hotel_nights": 3,
            "min_activities": 2
        },
        success_criteria={
            "must_have_flight": True,
            "must_have_hotel": True,
            "correct_destination": True,
            "correct_dates": True,
            "has_min_activities": True,
            "within_budget": True,
            "has_availability": True
        }
    ),
]

# HARD BENCHMARK TASKS (2 tasks)

HARD_TASKS = [
    BenchmarkTask(
        task_id="hard_01",
        name="Multi-Turn Clarification Test - Ambiguous Request",
        user_prompt="I need a trip to Miami.",
        constraints={},
        ground_truth={
            "type": "clarification",
            "destination_city": "Miami",
            "destination": "MIA",
            # Agent should ASK for: origin, dates, budget, preferences
            "requires_clarification": True
        },
        success_criteria={
            "asks_for_clarification": True,
            "mentions_missing_info": True,
            "minimal_assumptions": True
        }
    ),

    BenchmarkTask(
        task_id="hard_02",
        name="Long Horizon Planning - 2 Week Trip",
        user_prompt="I'm planning a 2-week trip to Florida (Miami) from Chicago. My budget is $5,000. I want to arrive on June 10th, 2025.",
        constraints={"max_budget": 5000},
        ground_truth={
            "type": "multi",
            "origin_city": "Chicago",
            "origin": "ORD",
            "destination_city": "Miami",
            "destination": "MIA",
            "date": "2025-06-10",
            "city": "Miami",
            "check_in": "2025-06-10",
            "check_out": "2025-06-23",
            "hotel_nights": 13,
            "min_activities": 5,
            "trip_duration_days": 14
        },
        success_criteria={
            "must_have_flight": True,
            "must_have_hotel": True,
            "correct_destination": True,
            "correct_dates": True,
            "long_hotel_stay": True,
            "has_multiple_activities": True,
            "within_budget": True,
            "has_availability": True
        }
    ),
]

# SCORING FUNCTIONS
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_constraint_satisfaction(
    task: BenchmarkTask,
    agent_output: dict
) -> tuple[float, dict]:
    """
    Calculate Constraint Satisfaction score (0.0 - 1.0).
    Returns (score, details_dict).
    """
    output = agent_output.get("output", {})
    criteria = task.success_criteria
    details = {}

    total_constraints = len(criteria)
    met_constraints = 0

    with _get_conn() as conn:
        if task.ground_truth["type"] == "flight":
            flights = output.get("flights", [])

            # Must have flight
            if criteria.get("must_have_flight"):
                if flights:
                    met_constraints += 1
                    details["has_flight"] = True
                else:
                    details["has_flight"] = False

            if flights:
                flight_id = flights[0]["id"] if isinstance(flights[0], dict) else flights[0]
                flight_row = conn.execute(
                    """SELECT f.*, ao.city as origin_city, ad.city as destination_city
                       FROM flights f
                       JOIN airports ao ON f.origin = ao.iata
                       JOIN airports ad ON f.destination = ad.iata
                       WHERE f.flight_id = ?""",
                    (flight_id,)
                ).fetchone()

                if flight_row:
                    # Correct route
                    if criteria.get("correct_route"):
                        origin_match = (
                            flight_row["origin_city"] == task.ground_truth.get("origin_city") or
                            flight_row["origin"] == task.ground_truth.get("origin")
                        )
                        dest_match = (
                            flight_row["destination_city"] == task.ground_truth.get("destination_city") or
                            flight_row["destination"] == task.ground_truth.get("destination")
                        )
                        if origin_match and dest_match:
                            met_constraints += 1
                            details["correct_route"] = True
                        else:
                            details["correct_route"] = False

                    # Correct date
                    if criteria.get("correct_date"):
                        if flight_row["depart_date"] == task.ground_truth.get("date"):
                            met_constraints += 1
                            details["correct_date"] = True
                        else:
                            details["correct_date"] = False

                    # Cheapest check
                    if criteria.get("is_cheapest"):
                        cheapest = conn.execute(
                            """SELECT MIN(price) as min_price FROM flights f
                               JOIN airports ao ON f.origin = ao.iata
                               JOIN airports ad ON f.destination = ad.iata
                               WHERE (LOWER(ao.city) = LOWER(?) OR f.origin = ?)
                                 AND (LOWER(ad.city) = LOWER(?) OR f.destination = ?)
                                 AND f.depart_date = ?
                                 AND f.seats_available > 0""",
                            (
                                task.ground_truth.get("origin_city"),
                                task.ground_truth.get("origin"),
                                task.ground_truth.get("destination_city"),
                                task.ground_truth.get("destination"),
                                task.ground_truth.get("date")
                            )
                        ).fetchone()

                        if cheapest and cheapest["min_price"] is not None and abs(flight_row["price"] - cheapest["min_price"]) < 1.0:
                            met_constraints += 1
                            details["is_cheapest"] = True
                            details["optimal_price"] = cheapest["min_price"]
                        else:
                            details["is_cheapest"] = False
                            details["optimal_price"] = cheapest["min_price"] if cheapest and cheapest["min_price"] is not None else None

                    # Time constraint check
                    if criteria.get("arrives_on_time"):
                        max_time = task.ground_truth.get("max_arrival_time")
                        if flight_row["arrive_time"] <= max_time:
                            met_constraints += 1
                            details["arrives_on_time"] = True
                        else:
                            details["arrives_on_time"] = False

                    # Non-stop check
                    if criteria.get("is_nonstop"):
                        max_stops = task.ground_truth.get("max_stops", 0)
                        if flight_row["stops"] <= max_stops:
                            met_constraints += 1
                            details["is_nonstop"] = True
                        else:
                            details["is_nonstop"] = False
                            details["actual_stops"] = flight_row["stops"]

                    # Availability
                    if criteria.get("has_availability"):
                        if flight_row["seats_available"] > 0:
                            met_constraints += 1
                            details["has_availability"] = True
                        else:
                            details["has_availability"] = False

        elif task.ground_truth["type"] == "hotel":
            hotels = output.get("hotels", [])

            # Must have hotel
            if criteria.get("must_have_hotel"):
                if hotels:
                    met_constraints += 1
                    details["has_hotel"] = True
                else:
                    details["has_hotel"] = False

            if hotels:
                hotel_id = hotels[0]["id"] if isinstance(hotels[0], dict) else hotels[0]
                hotel_row = conn.execute(
                    "SELECT * FROM hotels WHERE hotel_id = ?",
                    (hotel_id,)
                ).fetchone()

                if hotel_row:
                    # Correct city
                    if criteria.get("correct_city"):
                        if hotel_row["city"] == task.ground_truth.get("city"):
                            met_constraints += 1
                            details["correct_city"] = True
                        else:
                            details["correct_city"] = False

                    # Has required amenity (gym)
                    if criteria.get("has_gym"):
                        amenities_str = hotel_row["amenities"] or ""
                        if "gym" in amenities_str.lower():
                            met_constraints += 1
                            details["has_gym"] = True
                        else:
                            details["has_gym"] = False

                    # Availability AND date check (combined - no double counting)
                    if criteria.get("has_availability") or criteria.get("correct_date"):
                        check_in = task.ground_truth.get("check_in")
                        avail = conn.execute(
                            """SELECT 1 FROM hotel_availability
                               WHERE hotel_id = ?
                                 AND check_in <= ?
                                 AND check_out > ?
                                 AND rooms_left > 0""",
                            (hotel_id, check_in, check_in)
                        ).fetchone()

                        if avail:
                            # Award one point for the combined availability+date check
                            met_constraints += 1
                            details["has_availability"] = True
                            details["correct_date"] = True
                        else:
                            details["has_availability"] = False
                            details["correct_date"] = False

        elif task.ground_truth["type"] == "multi":
            # Multi-type tasks (flight + hotel + activities)
            flights = output.get("flights", [])
            hotels = output.get("hotels", [])
            activities = output.get("activities", [])

            # Track which constraints have been checked to avoid double-counting
            checked_constraints = set()

            # Check if required items exist
            if criteria.get("must_have_flight"):
                if flights:
                    met_constraints += 1
                    details["has_flight"] = True
                else:
                    details["has_flight"] = False
                checked_constraints.add("must_have_flight")

            if criteria.get("must_have_hotel"):
                if hotels:
                    met_constraints += 1
                    details["has_hotel"] = True
                else:
                    details["has_hotel"] = False
                checked_constraints.add("must_have_hotel")

            # Check hotel for multi-tasks
            if hotels:
                hotel_id = hotels[0]["id"] if isinstance(hotels[0], dict) else hotels[0]
                hotel_row = conn.execute(
                    "SELECT * FROM hotels WHERE hotel_id = ?",
                    (hotel_id,)
                ).fetchone()

                if hotel_row:
                    # Correct city
                    if criteria.get("correct_city") and "correct_city" not in checked_constraints:
                        if hotel_row["city"] == task.ground_truth.get("city"):
                            met_constraints += 1
                            details["correct_city"] = True
                        else:
                            details["correct_city"] = False
                        checked_constraints.add("correct_city")

                    # Has required amenity (pool, etc.)
                    if criteria.get("has_required_amenity") and "has_required_amenity" not in checked_constraints:
                        required_amenity = task.ground_truth.get("required_amenity", "")
                        amenities_str = hotel_row["amenities"] or ""
                        if required_amenity.lower() in amenities_str.lower():
                            met_constraints += 1
                            details["has_required_amenity"] = True
                        else:
                            details["has_required_amenity"] = False
                        checked_constraints.add("has_required_amenity")

                    # Date check for hotels
                    if criteria.get("correct_dates") and "correct_dates" not in checked_constraints:
                        check_in = task.ground_truth.get("check_in")
                        check_out = task.ground_truth.get("check_out")
                        avail = conn.execute(
                            """SELECT 1 FROM hotel_availability
                               WHERE hotel_id = ?
                                 AND check_in <= ?
                                 AND check_out >= ?
                                 AND rooms_left > 0""",
                            (hotel_id, check_in, check_out)
                        ).fetchone()

                        if avail:
                            met_constraints += 1
                            details["correct_dates"] = True
                        else:
                            details["correct_dates"] = False
                        checked_constraints.add("correct_dates")

            # Check flight for multi-tasks
            if flights:
                flight_id = flights[0]["id"] if isinstance(flights[0], dict) else flights[0]
                flight_row = conn.execute(
                    """SELECT f.*, ao.city as origin_city, ad.city as destination_city
                       FROM flights f
                       JOIN airports ao ON f.origin = ao.iata
                       JOIN airports ad ON f.destination = ad.iata
                       WHERE f.flight_id = ?""",
                    (flight_id,)
                ).fetchone()

                if flight_row:
                    # Correct destination (includes route check)
                    # Only check once even if both flight and hotel have destination criteria
                    if criteria.get("correct_destination") and "correct_destination" not in checked_constraints:
                        dest_city = task.ground_truth.get("destination_city")
                        origin_city = task.ground_truth.get("origin_city")

                        # Check destination matches
                        dest_match = (flight_row["destination_city"] == dest_city or
                                     flight_row["destination"] == task.ground_truth.get("destination"))

                        # Check origin matches if specified
                        origin_match = True
                        if origin_city:
                            origin_match = (flight_row["origin_city"] == origin_city or
                                          flight_row["origin"] == task.ground_truth.get("origin"))

                        # Also verify hotel is in correct destination city if hotel exists
                        hotel_dest_match = True
                        if hotels and hotel_row:
                            hotel_dest_match = hotel_row["city"] == dest_city

                        if dest_match and origin_match and hotel_dest_match:
                            met_constraints += 1
                            details["correct_destination"] = True
                        else:
                            details["correct_destination"] = False
                            if not origin_match:
                                details["wrong_origin"] = f"Expected {origin_city}, got {flight_row['origin_city']}"
                            if not dest_match:
                                details["wrong_destination"] = f"Expected {dest_city}, got {flight_row['destination_city']}"
                            if not hotel_dest_match:
                                details["hotel_wrong_city"] = f"Hotel in {hotel_row['city']}, expected {dest_city}"
                        checked_constraints.add("correct_destination")

                    # Correct date
                    if criteria.get("correct_date") and "correct_date" not in checked_constraints:
                        if flight_row["depart_date"] == task.ground_truth.get("date"):
                            met_constraints += 1
                            details["correct_date"] = True
                        else:
                            details["correct_date"] = False
                        checked_constraints.add("correct_date")

                    # Time constraint
                    if criteria.get("arrives_on_time") and "arrives_on_time" not in checked_constraints:
                        max_time = task.ground_truth.get("max_arrival_time")
                        if flight_row["arrive_time"] <= max_time:
                            met_constraints += 1
                            details["arrives_on_time"] = True
                        else:
                            details["arrives_on_time"] = False
                        checked_constraints.add("arrives_on_time")

            # Check activities
            if criteria.get("has_activities") and "has_activities" not in checked_constraints:
                if activities:
                    met_constraints += 1
                    details["has_activities"] = True
                else:
                    details["has_activities"] = False
                checked_constraints.add("has_activities")

            if criteria.get("has_min_activities") and "has_min_activities" not in checked_constraints:
                min_activities = task.ground_truth.get("min_activities", 1)
                if len(activities) >= min_activities:
                    met_constraints += 1
                    details["has_min_activities"] = True
                    details["actual_activities"] = len(activities)
                else:
                    details["has_min_activities"] = False
                    details["actual_activities"] = len(activities)
                checked_constraints.add("has_min_activities")

            # Availability check for multi
            if criteria.get("has_availability") and "has_availability" not in checked_constraints:
                # This is already checked in hotel/flight sections above
                # Just mark as true if we got this far
                if (not criteria.get("must_have_hotel") or hotels) and (not criteria.get("must_have_flight") or flights):
                    met_constraints += 1
                    details["has_availability"] = True
                else:
                    details["has_availability"] = False
                checked_constraints.add("has_availability")

            # Budget check for multi-type tasks
            if criteria.get("within_budget") and "within_budget" not in checked_constraints:
                total_cost = output.get("total_cost", 0)
                max_budget = task.constraints.get("max_budget", float('inf'))
                if total_cost <= max_budget:
                    met_constraints += 1
                    details["within_budget"] = True
                    details["budget_used"] = total_cost
                    details["budget_limit"] = max_budget
                else:
                    details["within_budget"] = False
                    details["budget_used"] = total_cost
                    details["budget_limit"] = max_budget
                checked_constraints.add("within_budget")

            # Long hotel stay check (for 2-week trips, etc.)
            if criteria.get("long_hotel_stay") and "long_hotel_stay" not in checked_constraints:
                expected_nights = task.ground_truth.get("hotel_nights", 0)
                actual_nights = output.get("hotel_nights", 0)
                # Allow some flexibility (within 1 night)
                if abs(actual_nights - expected_nights) <= 1:
                    met_constraints += 1
                    details["long_hotel_stay"] = True
                    details["expected_nights"] = expected_nights
                    details["actual_nights"] = actual_nights
                else:
                    details["long_hotel_stay"] = False
                    details["expected_nights"] = expected_nights
                    details["actual_nights"] = actual_nights
                checked_constraints.add("long_hotel_stay")

            # Multiple activities check (for long trips)
            if criteria.get("has_multiple_activities") and "has_multiple_activities" not in checked_constraints:
                min_activities = task.ground_truth.get("min_activities", 5)
                actual_activities = len(activities)
                if actual_activities >= min_activities:
                    met_constraints += 1
                    details["has_multiple_activities"] = True
                    details["min_activities"] = min_activities
                    details["actual_activities"] = actual_activities
                else:
                    details["has_multiple_activities"] = False
                    details["min_activities"] = min_activities
                    details["actual_activities"] = actual_activities
                checked_constraints.add("has_multiple_activities")

        elif task.ground_truth["type"] == "clarification":
            # Clarification task - agent should ASK for more info, not make assumptions
            message = agent_output.get("message", "")

            # Check if agent asks for clarification
            if criteria.get("asks_for_clarification"):
                # Look for question marks or clarifying phrases
                clarifying_phrases = [
                    "?", "when", "where", "what", "which", "how many",
                    "could you", "can you", "please provide", "need to know",
                    "clarify", "specify", "tell me more", "more information"
                ]
                asks_questions = any(phrase in message.lower() for phrase in clarifying_phrases)

                if asks_questions:
                    met_constraints += 1
                    details["asks_for_clarification"] = True
                    details["message_snippet"] = message[:200]
                else:
                    details["asks_for_clarification"] = False
                    details["message_snippet"] = message[:200]

            # Check if agent mentions missing information
            if criteria.get("mentions_missing_info"):
                missing_info_phrases = [
                    "missing", "need", "require", "don't have", "haven't specified",
                    "date", "budget", "origin", "depart", "return", "when are you"
                ]
                mentions_missing = any(phrase in message.lower() for phrase in missing_info_phrases)

                if mentions_missing:
                    met_constraints += 1
                    details["mentions_missing_info"] = True
                else:
                    details["mentions_missing_info"] = False

            # Check if agent made minimal assumptions (few bookings without info)
            if criteria.get("minimal_assumptions"):
                flights = output.get("flights", [])
                hotels = output.get("hotels", [])
                activities = output.get("activities", [])

                # Good: Agent returns 0-1 items (not making assumptions)
                # Bad: Agent returns multiple items (making assumptions about dates, origin, etc.)
                total_items = len(flights) + len(hotels) + len(activities)

                if total_items <= 1:
                    met_constraints += 1
                    details["minimal_assumptions"] = True
                    details["items_returned"] = total_items
                else:
                    details["minimal_assumptions"] = False
                    details["items_returned"] = total_items

    score = met_constraints / total_constraints if total_constraints > 0 else 0.0

    # CRITICAL: Cap score at 1.0 to prevent scoring bugs from breaking the 0-1 scale
    score = min(1.0, max(0.0, score))

    details["met_constraints"] = met_constraints
    details["total_constraints"] = total_constraints

    # Add warning if score would have exceeded 1.0 (indicates a bug)
    if met_constraints > total_constraints:
        details["warning"] = f"Bug detected: {met_constraints} constraints met but only {total_constraints} defined"

    return score, details


def calculate_budget_efficiency(
    agent_output: dict,
    constraint_details: dict,
    task: BenchmarkTask = None
) -> tuple[float, dict]:
    """
    Calculate Budget Efficiency score (0.0 - 1.0).
    Formula: 1.0 - ((agent_cost - optimal_cost) / budget)
    Uses task.constraints["max_budget"] if specified, otherwise uses default generous budget.
    """
    output = agent_output.get("output", {})
    details = {}

    agent_cost = output.get("total_cost", 0)
    details["agent_cost"] = agent_cost

    optimal_price = constraint_details.get("optimal_price")
    optimal_cost = optimal_price if optimal_price is not None else agent_cost
    details["optimal_cost"] = optimal_cost

    # Use task's budget constraint if specified, otherwise use generous default
    if task and task.constraints.get("max_budget"):
        budget = task.constraints.get("max_budget")
        details["budget_source"] = "task_constraint"
    else:
        budget = max(optimal_cost * 10, 5000) if optimal_cost is not None and optimal_cost > 0 else 5000
        details["budget_source"] = "default_generous"
    details["budget"] = budget

    if agent_cost > budget:
        score = 0.0
        details["over_budget"] = True
    else:
        if budget > 0:
            score = 1.0 - ((agent_cost - optimal_cost) / budget)
            score = max(0.0, min(1.0, score))
        else:
            score = 1.0 if agent_cost == optimal_cost else 0.0
        details["over_budget"] = False

    return score, details


def calculate_logistics_score(agent_output: dict) -> tuple[float, dict]:
    """
    Calculate Logistics Score (0.0 - 1.0).
    Starts at 1.0, deducts 0.1 for each logical inconsistency.
    """
    output = agent_output.get("output", {})
    score = 1.0
    violations = []

    # Check for errors
    if agent_output.get("error"):
        score -= 0.3
        violations.append(f"Agent error: {agent_output['error']}")

    # Check date consistency
    check_in = output.get("check_in")
    check_out = output.get("check_out")

    if check_in and check_out:
        if check_out <= check_in:
            score -= 0.2
            violations.append("Check-out date not after check-in date")

    # Check hotel nights
    hotel_nights = output.get("hotel_nights", 0)
    if check_in and check_out and hotel_nights > 0:
        from datetime import datetime
        try:
            ci = datetime.strptime(check_in, "%Y-%m-%d")
            co = datetime.strptime(check_out, "%Y-%m-%d")
            expected_nights = (co - ci).days
            if abs(hotel_nights - expected_nights) > 0:
                score -= 0.1
                violations.append(f"Hotel nights mismatch")
        except ValueError:
            score -= 0.1
            violations.append("Invalid date format")

    score = max(0.0, score)

    details = {
        "violations": violations,
        "violation_count": len(violations)
    }

    return score, details


def calculate_evaluation_score(cs: float, be: float, ls: float) -> float:
    """
    Calculate composite Evaluation Score as defined in paper.
    S = (0.5 * CS) + (0.3 * BE) + (0.2 * LS)
    All inputs should be in range [0.0, 1.0].
    Output is capped at 1.0 to prevent scoring bugs.
    """
    # Cap all inputs at 1.0 as safety measure
    cs = min(1.0, max(0.0, cs))
    be = min(1.0, max(0.0, be))
    ls = min(1.0, max(0.0, ls))

    score = (0.5 * cs) + (0.3 * be) + (0.2 * ls)

    # Cap final score at 1.0
    return min(1.0, max(0.0, score))


def evaluate_task(task: BenchmarkTask, agent_output: dict, success_threshold: float = 0.75) -> TaskScore:
    """Evaluate a single task and return scores."""

    cs_score, cs_details = calculate_constraint_satisfaction(task, agent_output)
    be_score, be_details = calculate_budget_efficiency(agent_output, cs_details, task)
    ls_score, ls_details = calculate_logistics_score(agent_output)

    # Calculate composite evaluation score (paper's headline metric)
    eval_score = calculate_evaluation_score(cs_score, be_score, ls_score)

    # Binary pass/fail based on threshold
    passed = eval_score >= success_threshold

    all_details = {
        "constraint_satisfaction": cs_details,
        "budget_efficiency": be_details,
        "logistics": ls_details
    }

    return TaskScore(
        task_id=task.task_id,
        task_name=task.name,
        constraint_satisfaction=cs_score,
        budget_efficiency=be_score,
        logistics_score=ls_score,
        evaluation_score=eval_score,
        passed=passed,
        details=all_details,
        agent_response=agent_output  # Save full agent response
    )


# run benchmark
def run_benchmark(tasks: list[BenchmarkTask] = None, verbose: bool = True, num_runs: int = 3) -> dict:
    """Run benchmark on all tasks and return results."""
    if tasks is None:
        tasks = EASY_TASKS + MEDIUM_TASKS + HARD_TASKS

    # Verify agent is using the correct database
    if verbose:
        print(f"Benchmark Database: {BENCHMARK_DB_PATH}")
        print(f"Agent Database:     {DB_PATH}")
        if str(DB_PATH) != str(BENCHMARK_DB_PATH):
            print("WARNING: Agent is using a different database than benchmark!")
        else:
            print("different database\n")

    results = []

    for i, task in enumerate(tasks, 1):
        if verbose:
            print(f"\n{'='*70}")
            print(f"Task {i}/{len(tasks)}: {task.name}")
            print(f"{'='*70}")
            print(f"Prompt: {task.user_prompt}")
            print(f"\nRunning agent {num_runs} times...")

        # Run the task multiple times
        run_scores = []
        run_details = []  # Store detailed info for each run
        for run_num in range(1, num_runs + 1):
            if verbose:
                print(f"\n  Run {run_num}/{num_runs}...")

            try:
                agent_response = run_agent(task.user_prompt, verbose=False)
                agent_output = json.loads(agent_response)
            except Exception as e:
                if verbose:
                    print(f"  ERROR: Agent failed - {e}")
                agent_output = {
                    "output": {},
                    "error": str(e),
                    "trace": []
                }

            score = evaluate_task(task, agent_output)
            run_scores.append(score)

            # Extract constraints from trace (first step should be parse_constraints)
            constraints = {}
            trace = agent_output.get("trace", [])
            if trace and trace[0].get("step") == "parse_constraints":
                constraints = trace[0].get("output", {})

            # Save detailed run information
            run_details.append({
                "run_number": run_num,
                "constraints": constraints,
                "trace": trace,
                "output": agent_output.get("output", {}),
                "message": agent_output.get("message"),
                "error": agent_output.get("error"),
                "scores": {
                    "constraint_satisfaction": score.constraint_satisfaction,
                    "budget_efficiency": score.budget_efficiency,
                    "logistics_score": score.logistics_score,
                    "evaluation_score": score.evaluation_score,
                    "passed": score.passed
                },
                "score_details": score.details
            })

            if verbose:
                print(f"  CS: {score.constraint_satisfaction:.3f} | BE: {score.budget_efficiency:.3f} | LS: {score.logistics_score:.3f} | Eval: {score.evaluation_score:.3f} | Pass: {score.passed}")

        # Calculate average scores across all runs
        avg_cs = sum(s.constraint_satisfaction for s in run_scores) / len(run_scores)
        avg_be = sum(s.budget_efficiency for s in run_scores) / len(run_scores)
        avg_ls = sum(s.logistics_score for s in run_scores) / len(run_scores)
        avg_eval = sum(s.evaluation_score for s in run_scores) / len(run_scores)

        # Task passes if average evaluation score meets threshold
        task_passed = avg_eval >= 0.75

        # Create averaged task score with detailed run information
        avg_score = TaskScore(
            task_id=task.task_id,
            task_name=task.name,
            constraint_satisfaction=avg_cs,
            budget_efficiency=avg_be,
            logistics_score=avg_ls,
            evaluation_score=avg_eval,
            passed=task_passed,
            details={
                "average_of_runs": num_runs,
                "task_info": {
                    "prompt": task.user_prompt,
                    "constraints": task.constraints,
                    "ground_truth": task.ground_truth,
                    "success_criteria": task.success_criteria
                },
                "runs": run_details,  # Full detailed run information
                "individual_runs": [
                    {
                        "run": idx + 1,
                        "cs": s.constraint_satisfaction,
                        "be": s.budget_efficiency,
                        "ls": s.logistics_score,
                        "eval": s.evaluation_score,
                        "passed": s.passed,
                        "details": s.details
                    }
                    for idx, s in enumerate(run_scores)
                ],
                "last_run_details": run_scores[-1].details if run_scores else {}
            },
            agent_response=run_scores[-1].agent_response if run_scores else None
        )

        results.append(avg_score)

        if verbose:
            print(f"\n--- AVERAGE SCORES (across {num_runs} runs) ---")
            print(f"Constraint Satisfaction: {avg_cs:.3f}")
            print(f"Budget Efficiency:       {avg_be:.3f}")
            print(f"Logistics Score:         {avg_ls:.3f}")
            print(f"Evaluation Score:        {avg_eval:.3f}")
            print(f"Task Passed (≥0.75):     {task_passed}")

    # Calculate overall averages across all tasks
    if verbose:
        print(f"\n{'='*70}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*70}")

    avg_cs = sum(s.constraint_satisfaction for s in results) / len(results)
    avg_be = sum(s.budget_efficiency for s in results) / len(results)
    avg_ls = sum(s.logistics_score for s in results) / len(results)

    summary = {
        "total_tasks": len(results),
        "runs_per_task": num_runs,
        "overall_average_scores": {
            "constraint_satisfaction": avg_cs,
            "budget_efficiency": avg_be,
            "logistics_score": avg_ls
        },
        "task_results": [asdict(s) for s in results]
    }

    if verbose:
        print(f"\nEach task was run {num_runs} times.")
        print(f"\nOverall Average Constraint Satisfaction: {avg_cs:.3f}")
        print(f"Overall Average Budget Efficiency:       {avg_be:.3f}")
        print(f"Overall Average Logistics Score:         {avg_ls:.3f}")
        print(f"\n{'='*70}\n")

    return summary


def save_results(results: dict, output_path: str = None):
    """Save benchmark results to JSON file."""
    if output_path is None:
        output_path = Path(__file__).parent / "benchmark_results.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mindy Bench - AI Travel Agent Benchmark")
    parser.add_argument("--output", "-o", type=str, help="Output path for results JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose output")
    parser.add_argument("--runs", "-r", type=int, default=3, help="Number of times to run each task (default: 3)")

    args = parser.parse_args()


    print("MINDY BENCH - AI Travel Agent Benchmarking System")


    results = run_benchmark(verbose=not args.quiet, num_runs=args.runs)
    save_results(results, args.output)
