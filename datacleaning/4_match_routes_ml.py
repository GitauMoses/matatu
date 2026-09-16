"""
Step 4: match NTSA permits to routes with fuzzy string matching, as a second,
independent method from step 2's exact-word-overlap matcher.

A first attempt at this used whole-document TF-IDF + cosine similarity
(permit text vs. route text, scored as two long blobs). That scored
everything low and missed matches step 2 had already found (route 38/39's
Forward Travellers, confirmed against your own verified data) — whole-
document similarity gets diluted once both sides are long strings of mostly
unrelated stage names. Per-via-point fuzzy matching keeps the structure that
made step 2 work (does this specific via-point appear on this specific
route?) but replaces exact word equality with edit-distance similarity, so
"dagoreti" and "dagoretti" — spelling drift this hand-typed data is full of
— count as a match instead of two unrelated words.

Still a candidate generator. Nothing here is loaded by the app or written
to backend/data/corrections/. Where this file and step 2's file agree on a
route/sacco pairing, that agreement is the strongest signal in the pipeline.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).parent
ROUTES_CSV = ROOT.parent / "backend" / "data" / "views" / "routes.csv"
PERMITS_CSV = ROOT / "out" / "permits.csv"
OUT_CSV = ROOT / "out" / "route_sacco_candidates_ml.csv"

MIN_HITS = 2
MIN_COVERAGE = 0.5
TOP_N_PER_ROUTE = 5
FUZZY_CUTOFF = 78  # rapidfuzz partial_ratio, 0-100


def load_routes():
    routes = []
    with ROUTES_CSV.open() as f:
        for row in csv.DictReader(f):
            stage_names = [s.strip().lower() for s in row["stages_in_order"].split(">")]
            routes.append(
                {
                    "route": row["route"],
                    "corridor": row["corridor"],
                    "from_terminus": row["from_terminus"],
                    "to_terminus": row["to_terminus"],
                    "stage_names": stage_names,
                }
            )
    return routes


def load_permits():
    permits = []
    with PERMITS_CSV.open() as f:
        for row in csv.DictReader(f):
            via_points = [v for v in row["via_points"].split("|") if len(v) >= 3]
            permits.append(
                {
                    "sacco": row["sacco"],
                    "permit_no": row["permit_no"],
                    "via_raw": row["via_raw"],
                    "via_points": via_points,
                }
            )
    return permits


def best_fuzzy_match(via_point: str, stage_names: list[str]) -> float:
    best = 0.0
    for name in stage_names:
        score = fuzz.partial_ratio(via_point, name)
        if score > best:
            best = score
    return best


def main():
    routes = load_routes()
    permits = load_permits()
    print(f"{len(routes)} routes x {len(permits)} permits")

    candidates = defaultdict(list)  # route -> list of (coverage, hits, total, permit)

    for permit in permits:
        total = len(permit["via_points"])
        if total == 0:
            continue
        for route in routes:
            hits = sum(
                1
                for vp in permit["via_points"]
                if best_fuzzy_match(vp, route["stage_names"]) >= FUZZY_CUTOFF
            )
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
                    "route": route["route"], "corridor": route["corridor"],
                    "from_terminus": route["from_terminus"], "to_terminus": route["to_terminus"],
                    "sacco": "", "permit_no": "", "coverage": "", "hits_of_total": "",
                    "via_raw": "", "confidence": "unknown", "VERDICT": "",
                }
            )
            continue
        for coverage, hits, total, permit in matches:
            confidence = "high" if coverage >= 0.8 and hits >= 3 else "medium" if coverage >= 0.65 else "low"
            rows.append(
                {
                    "route": route["route"], "corridor": route["corridor"],
                    "from_terminus": route["from_terminus"], "to_terminus": route["to_terminus"],
                    "sacco": permit["sacco"], "permit_no": permit["permit_no"],
                    "coverage": f"{coverage:.2f}", "hits_of_total": f"{hits}/{total}",
                    "via_raw": permit["via_raw"], "confidence": confidence, "VERDICT": "",
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
