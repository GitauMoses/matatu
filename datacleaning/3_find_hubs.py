"""
Step 3: find place names in the NTSA permits that aren't in our stage network
at all, and flag the ones most likely to be a real missing hub rather than
noise — specifically, ones mentioned alongside stages from two or more
different corridors that don't otherwise connect in our data.

This is how "Ruai" and "Kariobangi Roundabout" would have surfaced before a
rider ever reported them: a permit lists a via-point we don't recognize,
sitting in the same route description as stages we do recognize on two
different trunk roads. That pattern is exactly what a missing cross-corridor
link looks like from the outside.

Fuzzy string matching (rapidfuzz) is used instead of exact string equality
because the permit data is riddled with typos and spelling variants
("dagoreti" / "dagoretti", "kikuyu" / "kikuyu west") that would otherwise
flood the "unknown" bucket with places we actually already know.

Output: datacleaning/out/hub_candidates.csv, for you to check against the
map — not written to backend/data/corrections/.
"""
import csv
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz, process

ROOT = Path(__file__).parent
STAGES_CSV = ROOT.parent / "backend" / "data" / "views" / "stages.csv"
PERMITS_CSV = ROOT / "out" / "permits.csv"
OUT_CSV = ROOT / "out" / "hub_candidates.csv"

FUZZY_CUTOFF = 82   # rapidfuzz token_sort_ratio, 0-100
MIN_MENTIONS = 2    # ignore one-off spelling flukes
MIN_PHRASE_LEN = 4  # drop very short/near-empty via-points


def load_known_stages():
    """normalized name/alias -> set of corridors it belongs to."""
    known: dict[str, set[str]] = {}
    with STAGES_CSV.open() as f:
        for row in csv.DictReader(f):
            corridors = {c for c in row["corridor"].split() if c}
            names = [row["name"]] + [a.strip() for a in row.get("aliases", "").split("|")]
            for name in names:
                name = name.strip().lower()
                if not name:
                    continue
                known.setdefault(name, set()).update(corridors)
    return known


def load_permits():
    permits = []
    with PERMITS_CSV.open() as f:
        for row in csv.DictReader(f):
            via_points = [v for v in row["via_points"].split("|") if len(v) >= MIN_PHRASE_LEN]
            permits.append({**row, "via_points": via_points})
    return permits


def classify(via_point: str, known_names: list[str], known: dict[str, set[str]]):
    match = process.extractOne(via_point, known_names, scorer=fuzz.token_sort_ratio, score_cutoff=FUZZY_CUTOFF)
    if match is None:
        return None
    name, score, _ = match
    return known[name]


def main():
    known = load_known_stages()
    known_names = list(known.keys())
    permits = load_permits()
    print(f"{len(known_names)} known stage names/aliases, {len(permits)} permits")

    # unknown via-point -> aggregated evidence
    evidence: dict[str, dict] = defaultdict(
        lambda: {"mentions": 0, "saccos": set(), "corridors": set(), "examples": []}
    )

    for permit in permits:
        corridors_in_this_permit: set[str] = set()
        unknowns_in_this_permit: list[str] = []
        for vp in permit["via_points"]:
            corridors = classify(vp, known_names, known)
            if corridors:
                corridors_in_this_permit |= corridors
            else:
                unknowns_in_this_permit.append(vp)

        for vp in unknowns_in_this_permit:
            e = evidence[vp]
            e["mentions"] += 1
            e["saccos"].add(permit["sacco"])
            e["corridors"] |= corridors_in_this_permit
            if len(e["examples"]) < 3:
                e["examples"].append((permit["sacco"], permit["permit_no"], permit["via_raw"]))

    rows = []
    for vp, e in evidence.items():
        if e["mentions"] < MIN_MENTIONS:
            continue
        rows.append(
            {
                "via_point": vp,
                "mentions": e["mentions"],
                "sacco_count": len(e["saccos"]),
                "corridors_touched": " ".join(sorted(e["corridors"])) or "(none known)",
                "num_corridors": len(e["corridors"]),
                "sample_saccos": " | ".join(list(e["saccos"])[:3]),
                "example_via_raw": e["examples"][0][2] if e["examples"] else "",
                "example_permit": f"{e['examples'][0][0]} / {e['examples'][0][1]}" if e["examples"] else "",
                "VERDICT": "",
            }
        )

    # strongest signal first: touches multiple known corridors, then just mention count
    rows.sort(key=lambda r: (-r["num_corridors"], -r["mentions"]))

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "via_point", "mentions", "sacco_count", "num_corridors",
                "corridors_touched", "sample_saccos", "example_via_raw",
                "example_permit", "VERDICT",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    bridges = sum(1 for r in rows if r["num_corridors"] >= 2)
    print(f"wrote {len(rows)} candidate unknown places -> {OUT_CSV}")
    print(f"{bridges} of those are mentioned alongside 2+ different corridors — check these first")


if __name__ == "__main__":
    main()
