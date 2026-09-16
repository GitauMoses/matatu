"""
Step 1 of the data pipeline: turn the Digital Matatus source feed into the
network files the app loads.

    data/sources/digital_matatus_2015.zip  ->  data/network/*.csv

Every route in the source is extracted; none are dropped.

The source is a transit-schedule feed, but what we write is not: matatus have
no timetable, so service calendars, agencies and headways are dropped rather
than carried as files nothing reads. See app/feed.py for the shape.

Corridors are a column, not a folder. Splitting the network into per-corridor
directories put 118 of 134 routes in one called "nairobi", which organised
nothing. The label survives as a development marker on routes that sit along
a checked trunk (see corridors.py); it is blank otherwise and never reaches
the API.

Run: python3 tools/extract.py      (from the backend/ directory)
"""
import collections
import csv
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.feed import INBOUND, OUTBOUND                 # noqa: E402
from app.paths import DIGITAL_MATATUS_ZIP, NETWORK_DIR  # noqa: E402
from tools.corridors import assign_corridors           # noqa: E402
from tools import corrections                          # noqa: E402

# The source marks direction with direction_id: 1 runs away from town.
SOURCE_DIRECTION = {"1": OUTBOUND, "0": INBOUND}


def read_source(zf):
    def rows(name):
        with zf.open(name) as f:
            return list(csv.DictReader(f.read().decode("utf-8-sig").splitlines()))

    return {
        "routes": rows("routes.txt"),
        "trips": rows("trips.txt"),
        "stops": rows("stops.txt"),
        "stop_times": rows("stop_times.txt"),
        "shapes": rows("shapes.txt"),
    }


def write_csv(name, header, rows):
    with open(os.path.join(NETWORK_DIR, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def main():
    with zipfile.ZipFile(DIGITAL_MATATUS_ZIP) as zf:
        src = read_source(zf)

    stops = {s["stop_id"]: (float(s["stop_lat"]), float(s["stop_lon"]))
             for s in src["stops"]}

    order = collections.defaultdict(list)
    for r in src["stop_times"]:
        order[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"]))

    shape_points = collections.defaultdict(list)
    for r in src["shapes"]:
        shape_points[r["shape_id"]].append(
            (int(r["shape_pt_sequence"]), float(r["shape_pt_lat"]), float(r["shape_pt_lon"]))
        )
    shape_points = {k: [(lat, lon) for _, lat, lon in sorted(v)]
                    for k, v in shape_points.items()}

    numbers = {r["route_id"]: (r["route_short_name"] or r["route_id"]).strip()
               for r in src["routes"]}

    # route_id -> direction -> (ordered stage ids, headsign, shape_id)
    per_route: dict[str, dict[str, tuple]] = collections.defaultdict(dict)
    for t in src["trips"]:
        direction = SOURCE_DIRECTION.get(t["direction_id"])
        if not direction:
            continue
        stage_ids = [sid for _, sid in sorted(order.get(t["trip_id"], []))]
        if not stage_ids:
            continue
        # Keep the better-surveyed one if a direction somehow appears twice.
        existing = per_route[t["route_id"]].get(direction)
        if existing and len(existing[0]) >= len(stage_ids):
            continue
        per_route[t["route_id"]][direction] = (
            stage_ids, t["trip_headsign"].strip(), t["shape_id"],
        )

    stages_of_route = {}
    for rid, dirs in per_route.items():
        number = numbers.get(rid)
        if not number:
            continue
        stage_ids = (dirs.get(OUTBOUND) or next(iter(dirs.values())))[0]
        pts = [stops[s] for s in stage_ids if s in stops]
        if pts:
            stages_of_route[number] = pts

    print("assigning corridor labels from route geometry…")
    corridor_of = assign_corridors({numbers[r]: r for r in per_route},
                                   stages_of_route, default="")

    if os.path.isdir(NETWORK_DIR):
        shutil.rmtree(NETWORK_DIR)
    os.makedirs(NETWORK_DIR, exist_ok=True)

    used_stages = {sid for dirs in per_route.values()
                   for stage_ids, _, _ in dirs.values() for sid in stage_ids}
    stage_rows = [[s["stop_id"], s["stop_name"].strip(), s["stop_lat"], s["stop_lon"]]
                  for s in src["stops"] if s["stop_id"] in used_stages]

    route_rows, path_rows, shape_rows = [], [], []
    for route in src["routes"]:
        rid = route["route_id"]
        if rid not in per_route:
            continue
        dirs = per_route[rid]
        route_rows.append([
            rid, numbers[rid],
            route["route_long_name"] or route["route_desc"],
            dirs.get(OUTBOUND, ([], "", ""))[1],
            dirs.get(INBOUND, ([], "", ""))[1],
            corridor_of.get(rid, ""),
        ])
        for direction, (stage_ids, _, shape_id) in dirs.items():
            for i, sid in enumerate(stage_ids):
                path_rows.append([rid, direction, i, sid])
            for i, (lat, lon) in enumerate(shape_points.get(shape_id, [])):
                shape_rows.append([rid, direction, i, lat, lon])

    # Hand corrections go on last so they survive this rebuild - see
    # tools/corrections.py for why they cannot live in data/network/.
    stage_rows, path_rows, shape_rows, notes = corrections.apply(
        stage_rows, route_rows, path_rows, shape_rows, numbers)

    # A route's advertised terminus changes when it gets extended.
    stage_name = {r[0]: r[1] for r in stage_rows}
    last_of = {}
    for route_id, direction, seq, sid in path_rows:
        key = (route_id, direction)
        if key not in last_of or seq > last_of[key][0]:
            last_of[key] = (seq, sid)
    for row in route_rows:
        for idx, direction in ((3, "out"), (4, "in")):
            end = last_of.get((row[0], direction))
            if end:
                row[idx] = stage_name.get(end[1], row[idx])

    counts = {}
    counts["stages"] = write_csv("stages.csv",
        ["stage_id", "name", "lat", "lon"], stage_rows)
    counts["routes"] = write_csv("routes.csv",
        ["route_id", "number", "description", "outbound_to", "inbound_to", "corridor"],
        route_rows)
    counts["paths"] = write_csv("paths.csv",
        ["route_id", "direction", "sequence", "stage_id"], path_rows)
    counts["shape_points"] = write_csv("shapes.csv",
        ["route_id", "direction", "sequence", "lat", "lon"], shape_rows)

    terminal_rows = []
    for number, entries in corrections.load_terminals().items():
        route_id = {numbers[r]: r for r in numbers}.get(number)
        if not route_id:
            notes.append(f"  ! terminals skipped: no route numbered {number}")
            continue
        for t in entries:
            terminal_rows.append([route_id, number, t["name"],
                                  f"{t['lat']:.6f}", f"{t['lon']:.6f}",
                                  "|".join(t["saccos"])])
    counts["terminals"] = write_csv("terminals.csv",
        ["route_id", "number", "name", "lat", "lon", "saccos"], terminal_rows)

    operator_rows = []
    for number, saccos in corrections.load_route_operators().items():
        route_id = {numbers[r]: r for r in numbers}.get(number)
        if not route_id:
            continue
        operator_rows.append([route_id, number, "|".join(saccos)])
    counts["route_operators"] = write_csv("route_operators.csv",
        ["route_id", "number", "saccos"], operator_rows)

    print("  " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    for n in notes:
        print(n)
    labelled = collections.Counter(c for c in corridor_of.values() if c)
    for corridor, n in sorted(labelled.items()):
        listed = sorted((numbers[r] for r, c in corridor_of.items() if c == corridor),
                        key=lambda x: (len(x), x))
        print(f"  {corridor}: {n} routes — {' '.join(listed)}")
    print(f"  unlabelled: {len(route_rows) - sum(labelled.values())} routes")


if __name__ == "__main__":
    main()
