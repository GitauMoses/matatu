"""
Step 5: match Nairobi's most recognizable saccos by name (the ones a rider
actually looks for on the windscreen) to routes, and flag the ones that
aren't in the NTSA registry under any name we can find.

The registry uses legal/registered names, not street names — "Super Metro"
is "SUPER METRO LIMITED" in the data, but several well-known brands don't
appear under any recognizable name at all (same pattern already found for
Lopha in step 2/4 — likely registered under a different legal entity).
That's real information, not a gap in the script: it means don't assume a
brand you don't find here is unserved, it means the registry doesn't expose
its legal name.

Output: datacleaning/out/prominent_sacco_routes.csv, one row per
(sacco, route) match, plus a printed list of brands not found at all.
"""
import csv
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).parent
ROUTES_CSV = ROOT.parent / "backend" / "data" / "views" / "routes.csv"
PERMITS_CSV = ROOT / "out" / "permits.csv"
OUT_CSV = ROOT / "out" / "prominent_sacco_routes.csv"

# display name -> registered PTO name(s) found by hand in out/permits.csv.
# None means: searched, not found under any recognizable name.
PROMINENT_SACCOS: dict[str, list[str] | None] = {
    "KBS": ["KENYA BUS SERVICE MANAGEMENT LIMITED"],
    "City Shuttle": None,  # "seven city shuttle limited" exists but runs Athi River/Kitengela/Machakos, not Westlands/Upper Hill/Ngong — different company
    "Super Metro": ["SUPER METRO LIMITED"],
    "Forward Travellers": ["FORWARD TRAVELLERS SACCO LTD"],
    # "ZURI GENESIS CO. LIMITED" exists but runs Thika Rd/Kahawa West/Ruiru,
    # not Rongai/Lang'ata/Kiserian — a different company with the same name.
    "Zuri": None,
    "Ongata Line": ["ONGATA LINE TRANSPORTERS LIMITED"],
    "Embassava": ["EMBASSAVA COOPERATIVE SAVINGS AND CREDIT SOCIETY LTD"],
    "Citi Hoppa": None,
    "Kikuyu Travellers": None,
    "Eastleigh Commuters": ["EASTLEIGH COMMUTER SERVICES LIMITED"],
    "Nicco Movers": ["NICCO MOVERS LIMITED"],
    "MSL (Mwiki Sacco)": ["MWIKI PSV SACCO SOCIETY LIMITED"],
    "Thika Road Travellers": None,
    "Nyakach": None,
    "Umoja One": None,
}

MIN_HITS = 2
MIN_COVERAGE = 0.5
FUZZY_CUTOFF = 78
TOP_N_PER_SACCO = 6


def load_routes():
    routes = []
    with ROUTES_CSV.open() as f:
        for row in csv.DictReader(f):
            stage_names = [s.strip().lower() for s in row["stages_in_order"].split(">")]
            routes.append(
                {
                    "route": row["route"], "corridor": row["corridor"],
                    "from_terminus": row["from_terminus"], "to_terminus": row["to_terminus"],
                    "stage_names": stage_names,
                }
            )
    return routes


def load_permits_by_sacco():
    by_sacco = defaultdict(list)
    with PERMITS_CSV.open() as f:
        for row in csv.DictReader(f):
            via_points = [v for v in row["via_points"].split("|") if len(v) >= 3]
            by_sacco[row["sacco"]].append({**row, "via_points": via_points})
    return by_sacco


def best_fuzzy_match(via_point: str, stage_names: list[str]) -> float:
    return max((fuzz.partial_ratio(via_point, n) for n in stage_names), default=0.0)


def main():
    routes = load_routes()
    by_sacco = load_permits_by_sacco()

    rows = []
    not_found = []

    for display_name, registry_names in PROMINENT_SACCOS.items():
        if not registry_names:
            not_found.append(display_name)
            continue

        permits = [p for name in registry_names for p in by_sacco.get(name, [])]
        if not permits:
            not_found.append(display_name)
            continue

        matches = []  # (coverage, hits, total, route, permit)
        for permit in permits:
            total = len(permit["via_points"])
            if total == 0:
                continue
            for route in routes:
                hits = sum(
                    1 for vp in permit["via_points"]
                    if best_fuzzy_match(vp, route["stage_names"]) >= FUZZY_CUTOFF
                )
                if hits < MIN_HITS:
                    continue
                coverage = hits / total
                if coverage < MIN_COVERAGE:
                    continue
                matches.append((coverage, hits, total, route, permit))

        matches.sort(key=lambda m: (-m[0], -m[1]))
        seen_routes = set()
        for coverage, hits, total, route, permit in matches:
            if route["route"] in seen_routes:
                continue
            seen_routes.add(route["route"])
            if len(seen_routes) > TOP_N_PER_SACCO:
                break
            confidence = "high" if coverage >= 0.8 and hits >= 3 else "medium" if coverage >= 0.65 else "low"
            rows.append(
                {
                    "sacco": display_name, "registry_name": permit["sacco"],
                    "route": route["route"], "corridor": route["corridor"],
                    "from_terminus": route["from_terminus"], "to_terminus": route["to_terminus"],
                    "coverage": f"{coverage:.2f}", "hits_of_total": f"{hits}/{total}",
                    "via_raw": permit["via_raw"], "confidence": confidence, "VERDICT": "",
                }
            )

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "sacco", "registry_name", "route", "corridor", "from_terminus", "to_terminus",
                "coverage", "hits_of_total", "via_raw", "confidence", "VERDICT",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    matched_saccos = {r["sacco"] for r in rows}
    print(f"wrote {len(rows)} (sacco, route) matches -> {OUT_CSV}")
    print(f"matched routes for: {sorted(matched_saccos)}")
    print(f"NOT found in the NTSA registry under any recognizable name: {not_found}")


if __name__ == "__main__":
    main()
