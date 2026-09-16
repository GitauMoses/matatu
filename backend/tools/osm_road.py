"""
Fetches a named road's geometry from OpenStreetMap and writes it as a
polyline that extensions can borrow.

Why this exists: extending a route in corrections/extensions.csv adds stages
past the surveyed terminus, but the route's recorded shape still stops where
the 2015 survey stopped. That leaves the map drawing a line that ends early,
the leg distance under-counted, and - because reachability is decided by
whether a route's path passes near a point - everything past the old terminus
unreachable on request.

So an extension needs road geometry as well as stages. The road is public
OSM data, unlike stop records, which along Kangundo Road past Kamulu simply
do not exist in any dataset.

    python3 tools/osm_road.py "Kangundo Road" -1.33 36.97 -1.24 37.15

Writes data/sources/road_<slug>.csv as an ordered lat,lon polyline.

Data (c) OpenStreetMap contributors, ODbL.
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

from app.paths import SOURCES_DIR  # noqa: E402

OVERPASS_HOSTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def overpass(query, tries=3):
    for _ in range(tries):
        for host in OVERPASS_HOSTS:
            try:
                req = urllib.request.Request(
                    host, data=urllib.parse.urlencode({"data": query}).encode(),
                    headers={"User-Agent": "matatu-app/0.1 (+github.com/GitauMoses)"})
                with urllib.request.urlopen(req, timeout=200) as r:
                    return json.loads(r.read().decode())
            except Exception as exc:
                print(f"  ({host.split('/')[2]}: {str(exc)[:50]})")
                time.sleep(3)
    return None


# Collapse points into buckets this wide when building a centreline.
BUCKET_DEG = 0.0004  # ~45 m


def centreline(ways, axis="lon"):
    """Collapse a road's ways into a single ordered centreline.

    Greedy end-to-end stitching does not work here. Major roads are mapped as
    one way per carriageway, so walking nearest-endpoint runs out along one
    side and straight back down the other - on Kangundo Road that produced a
    10 km line for a 5 km road that ended where it started.

    Instead, bucket every point along the road's dominant axis and take the
    median of each bucket. Two carriageways collapse into the line between
    them, which is what we want to hang stages off. This assumes the road does
    not double back on itself along that axis; true for the arterial
    corridors out of Nairobi, and worth re-checking for anything winding.
    """
    pts = [p for w in ways for p in w if len(w) >= 2]
    if not pts:
        return []
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    if axis == "auto":
        axis = "lon" if (max(lons) - min(lons)) >= (max(lats) - min(lats)) else "lat"

    key = (lambda p: p[1]) if axis == "lon" else (lambda p: p[0])
    buckets: dict[int, list] = {}
    for p in pts:
        buckets.setdefault(int(key(p) / BUCKET_DEG), []).append(p)

    line = []
    for b in sorted(buckets):
        group = sorted(buckets[b], key=lambda p: p[0] if axis == "lon" else p[1])
        line.append(group[len(group) // 2])
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("south", type=float)
    ap.add_argument("west", type=float)
    ap.add_argument("north", type=float)
    ap.add_argument("east", type=float)
    args = ap.parse_args()

    bbox = f"{args.south},{args.west},{args.north},{args.east}"
    query = f"""
    [out:json][timeout:180];
    way["highway"~"trunk|primary|secondary|tertiary"]["name"~"{args.name}",i]({bbox});
    out geom;
    """
    print(f"fetching '{args.name}' geometry…")
    data = overpass(query)
    if not data:
        raise SystemExit("Overpass unreachable; try again later")

    ways = [[(p["lat"], p["lon"]) for p in w.get("geometry") or []]
            for w in data.get("elements", [])]
    line = centreline(ways, axis="auto")
    if len(line) < 2:
        raise SystemExit(f"no usable geometry for '{args.name}' in that box")

    slug = "".join(c.lower() if c.isalnum() else "_" for c in args.name).strip("_")
    out = os.path.join(SOURCES_DIR, f"road_{slug}.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sequence", "lat", "lon"])
        for i, (lat, lon) in enumerate(line):
            w.writerow([i, f"{lat:.6f}", f"{lon:.6f}"])

    span = sum(haversine_km(*a, *b) for a, b in zip(line, line[1:]))
    print(f"  {len(line)} points, {span:.1f} km -> data/sources/road_{slug}.csv")


if __name__ == "__main__":
    main()
