"""
Step 2: match NTSA permits (datacleaning/out/permits.csv) against our route
stage lists (backend/data/views/routes.csv) to propose a sacco per route.

This is a candidate generator, not a source of truth. It writes
datacleaning/out/route_sacco_candidates.csv for manual review. Nothing here
is loaded by the app and nothing writes to backend/data/corrections/.

Method: normalize every stage name in a route into a bag of words. For each
permit's via-points, check what fraction of each via-point's words appear in
that bag. A via-point "hits" if most of its words are present. Score a
(route, permit) pair by how many of the permit's via-points hit, out of how
many the permit has — this rewards a permit whose described corridor is
well covered by the route, and penalizes generic one-word coincidences.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
ROUTES_CSV = ROOT.parent / "backend" / "data" / "views" / "routes.csv"
PERMITS_CSV = ROOT / "out" / "permits.csv"
OUT_CSV = ROOT / "out" / "route_sacco_candidates.csv"

# words too generic to count as a match on their own (drop before comparing)
STOPWORDS = {
    "road", "rd", "stage", "terminal", "terminus", "junction", "market",
    "the", "via", "and", "of", "at", "mwisho", "area", "estate", "centre",
    "center", "bus", "station", "school", "girls", "boys", "primary",
    "secondary", "church", "hospital", "a", "b", "c",
}

MIN_HITS = 2          # a permit needs at least this many via-points confirmed
MIN_COVERAGE = 0.5    # ...covering at least this fraction of its via-points
TOP_N_PER_ROUTE = 5


def words(s: str) -> set[str]:
    s = s.lower()
    s = re.sub(r"[^\w\s/]", " ", s)
    return {w for w in re.split(r"[\s/]+", s) if w and w not in STOPWORDS}


def load_routes():
    routes = []
    with ROUTES_CSV.open() as f:
        for row in csv.DictReader(f):
            stage_names = [s.strip() for s in row["stages_in_order"].split(">")]
            bag = set()
            for name in stage_names:
                bag |= words(name)
            routes.append(
                {
                    "route": row["route"],
                    "corridor": row["corridor"],
                    "from_terminus": row["from_terminus"],
                    "to_terminus": row["to_terminus"],
                    "bag": bag,
                }
            )
    return routes


def load_permits():
    permits = []
    with PERMITS_CSV.open() as f:
        for row in csv.DictReader(f):
            via_points = [v for v in row["via_points"].split("|") if v]
            via_word_sets = [words(v) for v in via_points]
            via_word_sets = [ws for ws in via_word_sets if ws]  # drop empty (pure stopwords)
            permits.append(
                {
                    "sacco": row["sacco"],
                    "permit_no": row["permit_no"],
                    "via_raw": row["via_raw"],
                    "via_word_sets": via_word_sets,
                }
            )
    return permits


def hit(via_words: set[str], bag: set[str]) -> bool:
    if not via_words:
        return False
    overlap = len(via_words & bag)
    return overlap / len(via_words) >= 0.6


def main():
    routes = load_routes()
    permits = load_permits()
    print(f"{len(routes)} routes x {len(permits)} permits")

    candidates = defaultdict(list)  # route -> list of (score, hits, total, permit)

    for permit in permits:
        total = len(permit["via_word_sets"])
        if total == 0:
            continue
        for route in routes:
            hits = sum(1 for vw in permit["via_word_sets"] if hit(vw, route["bag"]))
            if hits < MIN_HITS:
                continue
            coverage = hits / total
            if coverage < MIN_COVERAGE:
                continue
            candidates[route["route"]].append((coverage, hits, total, permit))

    rows = []
    for route in routes:
        matches = sorted(candidates.get(route["route"], []), key=lambda x: (-x[0], -x[1]))[:TOP_N_PER_ROUTE]
        if not matches:
            rows.append(
                {
                    "route": route["route"],
                    "corridor": route["corridor"],
                    "from_terminus": route["from_terminus"],
                    "to_terminus": route["to_terminus"],
                    "sacco": "",
                    "permit_no": "",
                    "coverage": "",
                    "hits_of_total": "",
                    "via_raw": "",
                    "confidence": "unknown",
                    "VERDICT": "",
                }
            )
            continue
        for coverage, hits, total, permit in matches:
            confidence = "high" if coverage >= 0.8 and hits >= 3 else "medium" if coverage >= 0.65 else "low"
            rows.append(
                {
                    "route": route["route"],
                    "corridor": route["corridor"],
                    "from_terminus": route["from_terminus"],
                    "to_terminus": route["to_terminus"],
                    "sacco": permit["sacco"],
                    "permit_no": permit["permit_no"],
                    "coverage": f"{coverage:.2f}",
                    "hits_of_total": f"{hits}/{total}",
                    "via_raw": permit["via_raw"],
                    "confidence": confidence,
                    "VERDICT": "",
                }
            )

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "route", "corridor", "from_terminus", "to_terminus",
                "sacco", "permit_no", "coverage", "hits_of_total", "via_raw",
                "confidence", "VERDICT",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    no_match = sum(1 for route in routes if not candidates.get(route["route"]))
    print(f"wrote {len(rows)} candidate rows -> {OUT_CSV}")
    print(f"{no_match} of {len(routes)} routes have zero candidate match")


if __name__ == "__main__":
    main()
