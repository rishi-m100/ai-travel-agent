TOOL_SCHEMAS = [
    {
        "name": "search_flights",
        "description": "Search for available flights between two cities on a specific date. Returns flights sorted by price cheapest first. Accepts city names like 'New York' or IATA codes like 'JFK'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Departure city name or IATA code"},
                "destination": {"type": "string", "description": "Arrival city name or IATA code"},
                "date": {"type": "string", "description": "Departure date in YYYY-MM-DD format"},
                "max_price": {"type": "number", "description": "Optional maximum price in USD"},
                "cabin": {"type": "string", "enum": ["economy", "business", "first"]},
                "nonstop_only": {"type": "boolean", "description": "If true, only return nonstop flights"},
                "max_results": {"type": "integer", "description": "Max results to return, default 10"},
            },
            "required": ["origin", "destination", "date"],
        },
    },
    {
        "name": "get_flight_details",
        "description": "Get complete details for a specific flight by its flight_id. Use to confirm price and times before finalizing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_id": {"type": "string", "description": "Flight ID from search_flights, e.g. 'FL0000001'"},
            },
            "required": ["flight_id"],
        },
    },
    {
        "name": "search_hotels",
        "description": "Search for hotels in a specific city. Returns hotels sorted by price cheapest first. Pass check_in/check_out dates to filter by availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name or airport IATA code"},
                "check_in": {"type": "string", "description": "Check-in date in YYYY-MM-DD format (filters to available hotels)"},
                "check_out": {"type": "string", "description": "Check-out date in YYYY-MM-DD format (filters to available hotels)"},
                "max_price": {"type": "number", "description": "Optional maximum price per night in USD"},
                "tier": {"type": "string", "description": "Optional hotel tier (e.g. 'budget', 'luxury')"},
                "min_rating": {"type": "number", "description": "Optional minimum rating (e.g. 4.0)"},
                "pet_friendly": {"type": "boolean", "description": "If true, only return pet-friendly hotels"},
                "max_results": {"type": "integer", "description": "Max results to return, default 10"},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_hotel_details",
        "description": "Get complete details for a specific hotel by its hotel_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hotel_id": {"type": "string", "description": "Hotel ID from search_hotels"},
            },
            "required": ["hotel_id"],
        },
    },
    {
        "name": "search_activities",
        "description": "Search for activities/attractions in a city. Returns activities sorted by cost cheapest first. Pass day_of_week to filter by open days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name or airport IATA code"},
                "category": {"type": "string", "description": "Optional category (e.g. 'Museum', 'Outdoors')"},
                "day_of_week": {"type": "string", "description": "Optional day of week to filter by (e.g. 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')"},
                "max_price": {"type": "number", "description": "Optional maximum cost in USD"},
                "min_rating": {"type": "number", "description": "Optional minimum rating (e.g. 4.5)"},
                "accessible_only": {"type": "boolean", "description": "If true, only return wheelchair-accessible activities"},
                "max_results": {"type": "integer", "description": "Max results to return, default 10"},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_activity_details",
        "description": "Get complete details for a specific activity by its activity_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "string", "description": "Activity ID from search_activities"},
            },
            "required": ["activity_id"],
        },
    },
    {
        "name": "calculate_total_cost",
        "description": "Calculate total cost for a tentative itinerary including flights, hotel, and activities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of flight IDs",
                },
                "hotel_id": {"type": "string", "description": "Hotel ID"},
                "hotel_nights": {"type": "integer", "description": "Number of nights at hotel (default 0)"},
                "activity_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of activity IDs",
                },
            },
        },
    },
    {
        "name": "submit_itinerary",
        "description": "Submit the final itinerary or ask a clarifying question to the user. This MUST be the final tool call. Each selected item must include a brief reason explaining why it was chosen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Flight ID (e.g. 'FL00000001')"},
                            "reason": {"type": "string", "description": "Brief reason this flight was chosen (e.g. 'Cheapest nonstop option departing in the morning')"}
                        },
                        "required": ["id", "reason"]
                    },
                    "description": "Selected flights with reasons"
                },
                "hotels": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Hotel ID (e.g. 'HT00001')"},
                            "reason": {"type": "string", "description": "Brief reason this hotel was chosen (e.g. 'Best rated luxury hotel under $300/night')"}
                        },
                        "required": ["id", "reason"]
                    },
                    "description": "Selected hotels with reasons"
                },
                "activities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Activity ID (e.g. 'AC000001')"},
                            "reason": {"type": "string", "description": "Brief reason this activity was chosen (e.g. 'Highly rated outdoor adventure matching user interests')"}
                        },
                        "required": ["id", "reason"]
                    },
                    "description": "Selected activities with reasons"
                },
                "check_in": {
                    "type": "string",
                    "description": "Hotel check-in date in YYYY-MM-DD format"
                },
                "check_out": {
                    "type": "string",
                    "description": "Hotel check-out date in YYYY-MM-DD format"
                },
                "hotel_nights": {
                    "type": "integer",
                    "description": "Number of nights at hotel"
                },
                "total_cost": {
                    "type": "number",
                    "description": "Total cost of the itinerary. Pass 0 if none."
                },
                "message": {
                    "type": "string",
                    "description": "Message to the user explaining the itinerary, clarifying questions, or why nothing was found."
                }
            },
            "required": ["flights", "hotels", "activities", "total_cost", "message"]
        }
    }
]

CONSTRAINT_PARSER_TOOL = {
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