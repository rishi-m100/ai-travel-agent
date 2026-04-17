import argparse, csv, json, math, os, random
from datetime import date, datetime, time, timedelta
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--seed",    type=int, default=42)
parser.add_argument("--csv-dir", default="data/csvs")
parser.add_argument("--days",    type=int, default=10, help="Number of days of data to generate")
parser.add_argument("--per-day", type=int, default=2,  help="Flights per route per day")
args = parser.parse_args()
random.seed(args.seed)
Path(args.csv_dir).mkdir(parents=True, exist_ok=True)

DATE_START = date(2025, 6, 10)
ALL_DATES  = [DATE_START + timedelta(days=i) for i in range(args.days)]

AIRPORTS = [
    ("JFK","New York","NY",-5,40.64,-73.78),
    ("LAX","Los Angeles","CA",-8,33.94,-118.41),
    ("ORD","Chicago","IL",-6,41.98,-87.91),
    ("DFW","Dallas","TX",-6,32.90,-97.04),
    ("ATL","Atlanta","GA",-5,33.64,-84.43),
    ("SFO","San Francisco","CA",-8,37.62,-122.38),
    ("SEA","Seattle","WA",-8,47.45,-122.31),
    ("MIA","Miami","FL",-5,25.80,-80.29),
    ("BOS","Boston","MA",-5,42.36,-71.01),
    ("DEN","Denver","CO",-7,39.86,-104.67),
    ("LAS","Las Vegas","NV",-8,36.08,-115.15),
    ("PHX","Phoenix","AZ",-7,33.44,-112.01),
    ("MSP","Minneapolis","MN",-6,44.88,-93.22),
    ("DTW","Detroit","MI",-5,42.21,-83.35),
    ("PDX","Portland","OR",-8,45.59,-122.60),
    ("SAN","San Diego","CA",-8,32.73,-117.19),
    ("AUS","Austin","TX",-6,30.20,-97.67),
    ("BNA","Nashville","TN",-6,36.12,-86.68),
    ("CLE","Cleveland","OH",-5,41.41,-81.85),
    ("MSY","New Orleans","LA",-6,29.99,-90.26),
    ("SLC","Salt Lake City","UT",-7,40.79,-111.98),
    ("IAH","Houston","TX",-6,29.99,-95.34),
    ("PHL","Philadelphia","PA",-5,39.87,-75.24),
    ("BWI","Baltimore","MD",-5,39.18,-76.67),
    ("DCA","Washington DC","VA",-5,38.85,-77.04),
    ("RDU","Raleigh","NC",-5,35.88,-78.79),
    ("TPA","Tampa","FL",-5,27.98,-82.53),
    ("MCO","Orlando","FL",-5,28.43,-81.31),
    ("STL","St. Louis","MO",-6,38.75,-90.37),
    ("MCI","Kansas City","MO",-6,39.30,-94.71),
    ("IND","Indianapolis","IN",-5,39.72,-86.29),
    ("CMH","Columbus","OH",-5,39.99,-82.89),
    ("PIT","Pittsburgh","PA",-5,40.49,-80.23),
    ("MKE","Milwaukee","WI",-6,42.95,-87.90),
    ("OMA","Omaha","NE",-6,41.30,-95.89),
    ("ABQ","Albuquerque","NM",-7,35.04,-106.61),
    ("TUL","Tulsa","OK",-6,36.20,-95.89),
    ("OKC","Oklahoma City","OK",-6,35.39,-97.60),
    ("ELP","El Paso","TX",-7,31.81,-106.38),
    ("LIT","Little Rock","AR",-6,34.73,-92.22),
    ("MEM","Memphis","TN",-6,35.04,-89.98),
    ("BHM","Birmingham","AL",-6,33.56,-86.75),
    ("JAX","Jacksonville","FL",-5,30.49,-81.69),
    ("SAV","Savannah","GA",-5,32.13,-81.20),
    ("CHS","Charleston","SC",-5,32.90,-80.04),
    ("BOI","Boise","ID",-7,43.56,-116.22),
    ("GEG","Spokane","WA",-8,47.62,-117.53),
    ("FAT","Fresno","CA",-8,36.78,-119.72),
    ("SMF","Sacramento","CA",-8,38.70,-121.59),
    ("ONT","Ontario","CA",-8,34.06,-117.60),
]

AIRPORT_LOOKUP = {r[0]: r for r in AIRPORTS}

AIRPORT_MARKET_MULT = {
    "JFK":1.45, "SFO":1.40, "LAX":1.35, "BOS":1.30, "MIA":1.25,
    "SEA":1.20, "ORD":1.18, "DCA":1.18, "BWI":1.12, "DEN":1.15,
    "SAN":1.20, "AUS":1.18, "PDX":1.15, "BNA":1.12, "LAS":1.10,
    "ATL":1.10, "DFW":1.08, "IAH":1.08, "PHX":1.05, "MCO":1.12,
    "TPA":1.05, "MSP":1.05, "PHL":1.08, "DTW":1.05, "SLC":1.08,
    "MSY":1.10, "RDU":1.08, "STL":1.00, "MCI":1.00, "IND":0.97,
    "CMH":0.97, "PIT":1.00, "MKE":0.97, "CLE":0.97, "JAX":1.00,
    "TUL":0.90, "OKC":0.90, "OMA":0.90, "ABQ":0.92, "ELP":0.90,
    "LIT":0.88, "MEM":0.92, "BHM":0.90, "SAV":0.95, "CHS":0.97,
    "BOI":0.93, "GEG":0.88, "FAT":0.88, "SMF":1.00, "ONT":0.92,
}

AIRLINES_EXT = [
    ("AA", "American Airlines",   0.82, 0.015, "premium",    0.12, 0.18, 3.5, 5.0),
    ("DL", "Delta Air Lines",     0.87, 0.010, "premium",    0.13, 0.19, 3.5, 5.5),
    ("UA", "United Airlines",     0.80, 0.018, "premium",    0.11, 0.17, 3.2, 5.0),
    ("WN", "Southwest Airlines",  0.78, 0.020, "mainstream", 0.09, 0.14, 2.5, 3.5),
    ("B6", "JetBlue Airways",     0.75, 0.022, "mainstream", 0.09, 0.13, 2.8, 3.8),
    ("AS", "Alaska Airlines",     0.85, 0.012, "mainstream", 0.10, 0.15, 3.0, 4.2),
    ("F9", "Frontier Airlines",   0.72, 0.025, "budget",     0.06, 0.09, 2.0, 2.8),
    ("NK", "Spirit Airlines",     0.68, 0.030, "budget",     0.05, 0.08, 1.8, 2.5),
    ("G4", "Allegiant Air",       0.70, 0.028, "budget",     0.06, 0.09, 2.0, 2.8),
    ("SY", "Sun Country",         0.76, 0.021, "budget",     0.07, 0.10, 2.2, 3.0),
]
AIRLINE_LOOKUP = {r[0]: r for r in AIRLINES_EXT}

MAJOR_HUBS = {
    "JFK", "LAX", "ORD", "DFW", "ATL", "SFO", "SEA",
    "MIA", "BOS", "DEN", "LAS", "IAH", "PHX",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def haversine_miles(iata1, iata2):
    r1 = AIRPORT_LOOKUP[iata1]; r2 = AIRPORT_LOOKUP[iata2]
    lat1, lon1 = math.radians(r1[4]), math.radians(r1[5])
    lat2, lon2 = math.radians(r2[4]), math.radians(r2[5])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 3958.8 * 2 * math.asin(math.sqrt(a))

def flight_hours(miles):
    return max(0.75, miles / 500 + 0.5 + random.uniform(-0.1, 0.3))

def time_add(t, hours):
    dt = datetime.combine(date.today(), t) + timedelta(hours=hours)
    return dt.time()

def fmt(t):
    return t.strftime("%H:%M")

def is_holiday(d):
    if d.month == 11 and d.day >= 22: return True
    if d.month == 12 and d.day >= 20: return True
    if d.month ==  1 and d.day <=  4: return True
    if d.month ==  3 and 10 <= d.day <= 31: return True
    if d.month ==  5 and d.day >= 24: return True
    if d.month ==  9 and d.day <=  7: return True
    return False

def season_mult(d):
    if is_holiday(d):              return random.uniform(1.35, 1.65)
    if d.month in (6, 7, 8):       return random.uniform(1.20, 1.40)
    if d.month in (1, 2):          return random.uniform(0.82, 0.93)
    return random.uniform(0.92, 1.12)

def dow_mult(d):
    dow = d.weekday()
    if dow in (0, 4):    return random.uniform(1.08, 1.18)
    if dow in (1, 2, 3): return random.uniform(0.90, 0.98)
    return random.uniform(0.95, 1.05)

def calc_price(miles, al_iata, cabin, fl_date, origin, dest):
    al  = AIRLINE_LOOKUP[al_iata]
    cpm = random.uniform(al[5], al[6])
    mkt = math.sqrt(
        AIRPORT_MARKET_MULT.get(origin, 1.0) * AIRPORT_MARKET_MULT.get(dest, 1.0)
    )
    base = miles * cpm * mkt * season_mult(fl_date) * dow_mult(fl_date)
    if cabin == "business":
        base *= random.uniform(al[7], al[8])
    if miles < 400:
        floor = 39 if al[4] == "budget" else 59
    elif miles < 1000:
        floor = 79 if al[4] == "budget" else 99
    else:
        floor = 120 if al[4] == "budget" else 149
    return round(max(floor, base + random.uniform(-15, 25)), 2)

def airline_pool(o_hub, d_hub):
    if o_hub and d_hub:
        return (["AA","DL","UA","WN","B6","AS","F9","NK"],
                [20,  20,  18,  14,  10,  10,   5,   3])
    elif o_hub or d_hub:
        return (["AA","DL","UA","WN","B6","AS","F9","NK","G4","SY"],
                [15,  15,  13,  15,  10,  10,   8,   7,   4,   3])
    else:
        return (["WN","F9","NK","G4","SY","B6","AS","AA","DL","UA"],
                [20,  16,  14,  12,  10,   9,   8,   5,   4,   2])

# ─── Build routes (same logic as v2) ────────────────────────────────────────

iatas  = [a[0] for a in AIRPORTS]
others = {a: [b for b in iatas if b != a] for a in iatas}

routes = []
for origin in iatas:
    for dest in iatas:
        if origin == dest:
            continue
        o_hub = origin in MAJOR_HUBS
        d_hub = dest   in MAJOR_HUBS
        if o_hub and d_hub:
            routes.append((origin, dest, 1.00))
        elif o_hub or d_hub:
            routes.append((origin, dest, 1.00))
        else:
            if random.random() < 0.55:
                routes.append((origin, dest, 0.72))

print(f"Generating flights: {len(routes)} routes × {args.days} days × {args.per_day}/day ...")

# ─── Generate flights ────────────────────────────────────────────────────────

COLUMNS = [
    "flight_id", "airline_iata", "flight_number",
    "origin", "destination", "depart_date", "depart_time", "arrive_time",
    "duration_hours", "price", "seats_available",
    "stops", "layover_airport", "layover_minutes", "cabin",
]

rows = []
fid  = 1

for origin, dest, svc_pct in routes:
    miles  = haversine_miles(origin, dest)
    o_hub  = origin in MAJOR_HUBS
    d_hub  = dest   in MAJOR_HUBS
    al_pool, al_wts = airline_pool(o_hub, d_hub)
    other_ap = [a for a in others[origin] if a != dest]

    for fl_date in ALL_DATES:
        if random.random() > svc_pct:
            continue

        n = args.per_day
        dep_hours = sorted(random.sample(range(5, 23), min(n, 18)))

        for dep_h in dep_hours:
            al    = random.choices(al_pool, weights=al_wts)[0]
            dur   = round(flight_hours(miles) + random.uniform(-0.05, 0.1), 2)
            cabin = random.choices(["economy", "business"], [0.88, 0.12])[0]
            price = calc_price(miles, al, cabin, fl_date, origin, dest)
            dep   = time(dep_h, random.choice([0,5,10,15,20,25,30,35,40,45,50,55]))
            arr   = time_add(dep, dur)
            stops = random.choices([0, 1], [0.65, 0.35])[0]
            lay   = random.choice(other_ap) if stops and other_ap else None
            lay_m = random.randint(45, 180) if stops else None

            rows.append((
                f"FL{fid:08d}", al, f"{al}{random.randint(100,9999)}",
                origin, dest, fl_date.isoformat(), fmt(dep), fmt(arr),
                dur, price, random.randint(1, 150),
                stops, lay, lay_m, cabin
            ))
            fid += 1

# ─── Write CSV ───────────────────────────────────────────────────────────────

out_path = os.path.join(args.csv_dir, "flights_v2.csv")
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(COLUMNS)
    w.writerows(rows)

print(f"\n✅ Done!")
print(f"   {len(rows):,} flight records written to {out_path}")
print(f"   Date range: {ALL_DATES[0].isoformat()} → {ALL_DATES[-1].isoformat()}")
