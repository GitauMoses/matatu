"""
Step 6: merge the prominent-sacco matches and the general ML candidate file
into one route -> likely-operators table, ready to load into the app as an
*unconfirmed* suggestion (never shown as fact — that distinction is made in
the app, not here).

Priority order per route:
  1. A prominent, name-verified sacco (step 5) — these were checked by hand
     against a real description of where that sacco runs, so they're worth
     more than an automated string match alone.
  2. The general fuzzy matcher (step 4), medium/high confidence only.

Output: backend/data/corrections/route_operators.csv — NOT terminals.csv.
This is deliberately a separate, lower-trust file: it has no terminal
coordinates (the NTSA data doesn't give any), so it can't say *where* to
board, only *who* probably runs the route. The app treats it accordingly.
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
PROMINENT_CSV = ROOT / "out" / "prominent_sacco_routes.csv"
ML_CANDIDATES_CSV = ROOT / "out" / "route_sacco_candidates_ml.csv"
OUT_CSV = ROOT.parent / "backend" / "data" / "corrections" / "route_operators.csv"

MAX_SACCOS_PER_ROUTE = 3
CONF_RANK = {"high": 3, "medium": 2, "low": 1, "unknown": 0}


def main():
    by_route: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    # (sacco, source, priority) — priority: prominent=2, ml=1

    with PROMINENT_CSV.open() as f:
        for row in csv.DictReader(f):
            if CONF_RANK.get(row["confidence"], 0) < CONF_RANK["medium"]:
                continue
            by_route[row["route"]].append((row["sacco"], "prominent", 2))

    with ML_CANDIDATES_CSV.open() as f:
        for row in csv.DictReader(f):
            if not row["sacco"] or CONF_RANK.get(row["confidence"], 0) < CONF_RANK["medium"]:
                continue
            # Title-case the registry name so it doesn't shout at the rider.
            name = row["sacco"].title()
            by_route[row["route"]].append((name, "ml", 1))

    rows = []
    for route, entries in sorted(by_route.items()):
        entries.sort(key=lambda e: -e[2])  # prominent first
        seen = set()
        picked = []
        for sacco, source, _ in entries:
            key = sacco.lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(sacco)
            if len(picked) >= MAX_SACCOS_PER_ROUTE:
                break
        rows.append({"route": route, "saccos": "|".join(picked)})

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["route", "saccos"])
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {len(rows)} routes -> {OUT_CSV}")


if __name__ == "__main__":
    main()
