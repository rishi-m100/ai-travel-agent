# Mindy Bench - Benchmarking Script


1. **Constraint Satisfaction (CS)** - How well constraints are met
2. **Budget Efficiency (BE)** - How close to optimal cost
3. **Logistics Score (LS)** - Logical consistency

## The 3 Tasks

| Task ID | Task Name | What It Tests |
|---------|-----------|---------------|
| easy_01 | Find Cheapest Flight in Time Period | Price optimization |
| easy_02 | Find Hotel with 1 Amenity Requirement | Preference matching |
| easy_03 | Find Flight within Specific Time Constraint | Temporal reasoning |

## How to Run

## Generate the Database

```bash
python scripts/generate_world_data_v2.py
```

##  Run Mindy Bench 
```bash
python benchmark/mindy_bench.py
```

## Output JSON

Results are saved to `benchmark/benchmark_results.json`:

## Understanding Scores

All scores range from 0.0 to 1.0:

- **1.0** = Perfect
- **0.9** = Excellent
- **0.8** = Good
- **<= 0.7** = Needs improvement

### Constraint Satisfaction
- Measures how many requirements were met
- Example: 5 out of 5 constraints met = 1.0

### Budget Efficiency
- Measures proximity to optimal (cheapest) cost
- Formula: `1.0 - ((agent_cost - optimal_cost) / budget)`
- Perfect match to cheapest option = 1.0

### Logistics Score
- Starts at 1.0
- Deducts points for logical errors. -0.3 every time. 
- No errors = 1.0


### Database not found
Make sure you ran the data generation script first:
```bash
python scripts/generate_world_data_v3.py
```

#

Each task checks the following things: 

**Task 1: Cheapest Flight**
- Has flight?
- Correct route (ORD to SEA)?
- Correct date (July 1, 2025)?
- Is it the cheapest option?
- Seats available?

**Task 2: Hotel with Gym**
- Has hotel?
- Correct city (New York)?
- Correct date (Oct 5, 2025)?
- Has gym amenity?
- Room available?

**Task 3: Flight Arriving Before 2PM**
- Has flight?
- Correct route (JFK to LAX)?
- Correct date (Sept 15, 2025)?
- Arrives before 2:00 PM?
- Seats available?
