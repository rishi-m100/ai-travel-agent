import argparse, csv, os, random, sqlite3
from datetime import date, timedelta
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--seed",    type=int, default=42)
parser.add_argument("--db",      default="data/mindy_dataset_v3.db")
parser.add_argument("--csv-dir", default="data/csvs")
parser.add_argument("--days",    type=int, default=10, help="Number of days of data to generate")
args = parser.parse_args()
random.seed(args.seed)
Path(args.csv_dir).mkdir(parents=True, exist_ok=True)

DATE_START = date(2025, 6, 10)
DATE_END   = DATE_START + timedelta(days=args.days)

# Read existing hotel IDs from the DB
conn = sqlite3.connect(args.db)
hotel_ids = [r[0] for r in conn.execute("SELECT hotel_id FROM hotels ORDER BY hotel_id").fetchall()]
conn.close()

if not hotel_ids:
    print("ERROR: No hotels found in the database. Run generate_world_data_v2.py first.")
    exit(1)

print(f"Generating hotel availability: {len(hotel_ids)} hotels × {args.days} days ...")

COLUMNS = ["avail_id", "hotel_id", "check_in", "check_out", "rooms_left"]

rows = []
avail_id = 1

for hid in hotel_ids:
    d = DATE_START
    while d < DATE_END:
        nights = random.randint(1, 7)
        cout   = min(d + timedelta(days=nights), DATE_END)
        rooms  = random.choices(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 10],
            [4, 5, 10, 15, 20, 16, 11, 10, 5, 4],
        )[0]
        rows.append((avail_id, hid, d.isoformat(), cout.isoformat(), rooms))
        avail_id += 1
        d = cout

out_path = os.path.join(args.csv_dir, "hotel_availability_v2.csv")
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(COLUMNS)
    w.writerows(rows)

print(f"\n✅ Done!")
print(f"   {len(rows):,} availability windows written to {out_path}")
print(f"   Date range: {DATE_START.isoformat()} → {(DATE_END - timedelta(days=1)).isoformat()}")
