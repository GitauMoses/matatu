"""
Pulls every bus stop / stage OpenStreetMap knows about in the Nairobi metro
area and writes them to data/sources/osm_stages.csv.

This is a *source*, not an export: export.py reads it to tag each surveyed
stage with the nearest OpenStreetMap place name.

Why this exists: the surveyed feed has ~2,500 stop records but they collapse
to far fewer distinct places, and whole neighbourhoods have none. OSM has
its own, independently mapped set.

IMPORTANT - these stops are NOT attached to routes. OSM's Nairobi route
relations contain only ways, with zero stop members, so a stop node here
tells you a stage exists but not which matatu serves it or in what order.
Treat this file as a palette of known stages to build routes from, not as
something that can be loaded and routed on directly.

Run: python3 osm_stops.py
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.paths import OSM_STAGES_CSV as OUT

OVERPASS_HOSTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Nairobi metro: Limuru/Kiambu north, Athi River south, Ngong west, past Thika east.
BBOX = "-1.50,36.55,-0.95,37.25"

QUERY = f"""
[out:json][timeout:180];
(
  node["highway"="bus_stop"]({BBOX});
  node["public_transport"="platform"]({BBOX});
  node["public_transport"="station"]({BBOX});
  node["amenity"="bus_station"]({BBOX});
);
out tags center;
"""


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
                print(f"  ({host.split('/')[2]}: {str(exc)[:60]})")
                time.sleep(3)
    return None


def main():
    print("querying Overpass for Nairobi metro stops…")
    data = overpass(QUERY)
    if not data:
        raise SystemExit("Overpass unreachable; try again later")

    rows, unnamed = [], 0
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name") or "").strip()
        lat, lon = el.get("lat"), el.get("lon")
        if lat is None or lon is None:
            continue
        if not name:
            unnamed += 1
            continue
        kind = (tags.get("amenity") or tags.get("public_transport")
                or tags.get("highway") or "stop")
        rows.append([f"osm:{el['id']}", name, f"{lat:.6f}", f"{lon:.6f}", kind])

    rows.sort(key=lambda r: r[1].lower())
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stage_id", "name", "lat", "lon", "kind"])
        w.writerows(rows)

    print(f"  {len(rows)} named stops written to {os.path.basename(OUT)}")
    print(f"  ({unnamed} unnamed nodes skipped)")


if __name__ == "__main__":
    main()
