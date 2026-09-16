"""
Replaces each corridor route's shape with current OpenStreetMap geometry.

The Digital Matatus feed supplies the structure we depend on - stage names,
their order, direction, CBD termini - because OSM has none of it: its Nairobi
route relations carry only ways, with zero stop members. What OSM does have
is a live road trace. Those relations are actively maintained (most of our
corridor was edited in 2026, against a 2015 survey), so the *line* is better
there while the *stages* are better here.

So this only swaps `shapes.txt`. stops/trips/stop_times are untouched.

Run: python3 osm_shapes.py            (from this directory)
     python3 osm_shapes.py --dry-run  (report coverage, write nothing)

Data © OpenStreetMap contributors, ODbL.
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.paths import NETWORK_DIR

OVERPASS_HOSTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

BBOX = "-1.45,36.65,-1.05,37.15"

def refs_for(short_name: str) -> list[str]:
    """OSM relation `ref` values that could describe our route.

    Matching is on the route number as printed on the matatu, which is what
    both datasets key on. Our feed appends a suffix for surveyed variants of
    the same number ("17B_2"), and OSM has no equivalent, so we fall back to
    the base number - the variant then either matches on endpoints or keeps
    its own trace.
    """
    short = (short_name or "").strip()
    if not short:
        return []
    candidates = [short]
    if "_" in short:
        candidates.append(short.split("_", 1)[0])
    return candidates

# Endpoints must land within this of the trip's own first/last stage for the
# OSM line to be accepted as that direction's path.
ENDPOINT_TOLERANCE_KM = 3.0


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def overpass(query: str, tries: int = 3):
    for _ in range(tries):
        for host in OVERPASS_HOSTS:
            try:
                req = urllib.request.Request(
                    host, data=urllib.parse.urlencode({"data": query}).encode(),
                    headers={"User-Agent": "matatu-app/0.1 (+https://github.com/GitauMoses)"},
                )
                with urllib.request.urlopen(req, timeout=240) as r:
                    return json.loads(r.read().decode())
            except Exception as exc:
                print(f"    ({host.split('/')[2]}: {str(exc)[:60]})")
                time.sleep(3)
    return None


def stitch(ways: list[list[tuple[float, float]]]) -> list[list[float]]:
    """Join member ways into one polyline.

    Relation members are unordered and individually can run either way, so we
    walk greedily from the first way, each time taking whichever remaining way
    starts or ends nearest the current tip and flipping it if needed. Gaps are
    tolerated (Nairobi relations aren't all perfectly connected) but a jump of
    more than ~1 km ends the line rather than drawing a false shortcut.
    """
    remaining = [w for w in ways if len(w) >= 2]
    if not remaining:
        return []

    line = list(remaining.pop(0))
    while remaining:
        tip = line[-1]
        best_i, best_flip, best_d = None, False, float("inf")
        for i, w in enumerate(remaining):
            d_start = haversine_km(tip[0], tip[1], w[0][0], w[0][1])
            d_end = haversine_km(tip[0], tip[1], w[-1][0], w[-1][1])
            if d_start < best_d:
                best_i, best_flip, best_d = i, False, d_start
            if d_end < best_d:
                best_i, best_flip, best_d = i, True, d_end
        if best_i is None or best_d > 1.0:
            break
        w = remaining.pop(best_i)
        line.extend(reversed(w) if best_flip else w)

    return [[lon, lat] for lat, lon in line]


def _wanted_refs() -> set[str]:
    """Every route number in the network."""
    refs: set[str] = set()
    with open(os.path.join(NETWORK_DIR, "routes.csv"), newline="") as f:
        for row in csv.DictReader(f):
            refs.update(refs_for(row["number"]))
    return refs


def fetch_osm_routes() -> dict[str, list[list[list[float]]]]:
    """ref -> [polyline, ...] (one per relation carrying that ref)."""
    query = f"""
    [out:json][timeout:240];
    relation["type"="route"]["route"="bus"]({BBOX});
    out geom;
    """
    print("  querying Overpass…")
    data = overpass(query)
    if not data:
        raise SystemExit("Overpass unreachable; try again later")

    wanted = _wanted_refs()
    out: dict[str, list[list[list[float]]]] = {}
    for el in data.get("elements", []):
        ref = (el.get("tags", {}).get("ref") or "").strip()
        if ref not in wanted:
            continue
        ways = []
        for m in el.get("members", []):
            geom = m.get("geometry")
            if m.get("type") == "way" and geom:
                ways.append([(p["lat"], p["lon"]) for p in geom])
        line = stitch(ways)
        if len(line) >= 2:
            out.setdefault(ref, []).append(line)
    return out


def load_paths():
    def read(name):
        p = os.path.join(NETWORK_DIR, name)
        with open(p, newline="") as f:
            return list(csv.DictReader(f))

    stages = {s["stage_id"]: (float(s["lat"]), float(s["lon"]))
              for s in read("stages.csv")}
    numbers = {r["route_id"]: r["number"] for r in read("routes.csv")}
    seq = {}
    for r in read("paths.csv"):
        seq.setdefault((r["route_id"], r["direction"]), []).append(
            (int(r["sequence"]), r["stage_id"]))
    paths = []
    for (route_id, direction), pairs in seq.items():
        ordered = [sid for _, sid in sorted(pairs) if sid in stages]
        if ordered:
            paths.append({
                "route_id": route_id, "direction": direction,
                "number": numbers.get(route_id, ""),
                "first": stages[ordered[0]], "last": stages[ordered[-1]],
            })
    return paths


def best_line_for_path(path, candidates):
    """Pick and orient the OSM line that matches this route direction."""
    best, best_score = None, float("inf")
    for line in candidates:
        start = (line[0][1], line[0][0])
        end = (line[-1][1], line[-1][0])
        fwd = (haversine_km(*path["first"], *start) + haversine_km(*path["last"], *end))
        rev = (haversine_km(*path["first"], *end) + haversine_km(*path["last"], *start))
        if fwd <= rev and fwd < best_score:
            best, best_score = line, fwd
        elif rev < fwd and rev < best_score:
            best, best_score = list(reversed(line)), rev
    if best is None or best_score > ENDPOINT_TOLERANCE_KM:
        return None, best_score
    return best, best_score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    osm = fetch_osm_routes()
    print(f"  OSM relations stitched for {len(osm)} refs\n")

    paths = load_paths()

    rows, swapped, kept = [], 0, 0
    existing = {}
    with open(os.path.join(NETWORK_DIR, "shapes.csv"), newline="") as f:
        for r in csv.DictReader(f):
            existing.setdefault((r["route_id"], r["direction"]), []).append(
                (int(r["sequence"]), r["lat"], r["lon"])
            )

    if True:
        for path in paths:
            key = (path["route_id"], path["direction"])
            refs = refs_for(path["number"])
            cands = [ln for ref in refs for ln in osm.get(ref, [])]
            line, score = best_line_for_path(path, cands) if cands else (None, None)

            if line:
                swapped += 1
                src = "osm"
                pts = [(i, f"{lat:.6f}", f"{lon:.6f}") for i, (lon, lat) in enumerate(line)]
                note = f"{len(line):>5} pts  endpoints off by {score:.2f} km"
            else:
                kept += 1
                src = "dm"
                pts = sorted(existing.get(key, []))
                why = "no OSM ref" if not cands else f"endpoints off by {score:.1f} km"
                note = f"{len(pts):>5} pts  kept 2015 trace ({why})"
            print(f"  {path['number']:<7} {path['direction']:<4} {src:<4} {note}")
            for i, lat, lon in pts:
                rows.append([path["route_id"], path["direction"], i, lat, lon])

        if not args.dry_run:
            with open(os.path.join(NETWORK_DIR, "shapes.csv"), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["route_id", "direction", "sequence", "lat", "lon"])
                w.writerows(rows)
        print(f"\n-> {swapped} directions from OSM, {kept} kept from the 2015 trace"
              f"{' (dry run, nothing written)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
