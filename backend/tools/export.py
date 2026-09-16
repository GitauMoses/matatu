"""
Final step of the pipeline: human-readable exports for inspecting and
correcting the data by hand.

    data/views/routes.csv  - one row per route: termini + stages in order
    data/views/stages.csv  - one row per distinct stage: where, which routes

Run: python3 tools/export.py     (from the backend/ directory)
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.feed import OUTBOUND, load_all                       # noqa: E402
from app.paths import OSM_STAGES_CSV, VIEWS_DIR      # noqa: E402
from app.routing import _same_place, haversine_km    # noqa: E402

ROUTES_CSV = os.path.join(VIEWS_DIR, "routes.csv")
STAGES_CSV = os.path.join(VIEWS_DIR, "stages.csv")


def outbound_path(net, route):
    """The direction running away from town, preferred for listing a route.

    Falls back to whichever direction lists more stages, since a few routes
    only have one recorded properly.
    """
    paths = [net.paths[p] for p in route.path_ids if p in net.paths]
    paths = [p for p in paths if p.stage_ids]
    if not paths:
        return None
    out = [p for p in paths if p.direction == OUTBOUND]
    return max(out or paths, key=lambda p: len(p.stage_ids))


def export_routes(net):
    rows = []
    for route in net.all_routes():
        path = outbound_path(net, route)
        if not path:
            continue
        stages = [net.stages[s].name for s in path.stage_ids if s in net.stages]
        if not stages:
            continue

        other = next((net.paths[p] for p in route.path_ids
                      if p in net.paths and net.paths[p].id != path.id), None)
        return_towards = other.headsign if other else ""

        rows.append([
            route.number,
            route.corridor,
            stages[0],
            stages[-1],
            len(stages),
            return_towards,
            " > ".join(stages),
            route.description,
            route.id,
        ])

    rows.sort(key=lambda r: (r[1], len(r[0]), r[0]))
    os.makedirs(VIEWS_DIR, exist_ok=True)
    with open(ROUTES_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["route", "corridor", "from_terminus", "to_terminus",
                    "num_stages", "return_towards", "stages_in_order",
                    "surveyed_description", "source_route_id"])
        w.writerows(rows)
    return len(rows)


def load_osm_places():
    if not os.path.exists(OSM_STAGES_CSV):
        return []
    with open(OSM_STAGES_CSV, newline="") as f:
        return [(r["name"], float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)]


def export_stages(net):
    osm = load_osm_places()

    routes_at_stage: dict[str, set[str]] = {}
    corridors_at_stage: dict[str, set[str]] = {}
    for path in net.all_paths():
        route = net.routes.get(path.route_id)
        if not route:
            continue
        for sid in path.stage_ids:
            routes_at_stage.setdefault(sid, set()).add(route.number)
            if route.corridor:
                corridors_at_stage.setdefault(sid, set()).add(route.corridor)

    groups: list[list] = []
    for stage in sorted(net.all_stages(), key=lambda s: s.name):
        for g in groups:
            if _same_place(stage, g[0]):
                g.append(stage)
                break
        else:
            groups.append([stage])

    rows = []
    for g in groups:
        head = g[0]
        names = []
        for s in g:
            if s.name not in names:
                names.append(s.name)
        routes = sorted({r for s in g for r in routes_at_stage.get(s.id, ())},
                        key=lambda x: (len(x), x))
        area = ""
        if osm:
            best, best_d = "", 1.0
            for oname, olat, olon in osm:
                d = haversine_km(head.lat, head.lon, olat, olon)
                if d < best_d:
                    best, best_d = oname, d
            area = best
        # A stage has no corridor of its own; it inherits the labels of the
        # routes calling there, and most have none.
        corridors = sorted({c for s in g for c in corridors_at_stage.get(s.id, ())})
        rows.append([head.id, names[0], f"{head.lat:.6f}", f"{head.lon:.6f}",
                     " ".join(corridors), " ".join(routes),
                     " | ".join(names[1:]), area])

    rows.sort(key=lambda r: r[1].lower())
    with open(STAGES_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stage_id", "name", "lat", "lon", "corridor",
                    "routes", "aliases", "nearby_osm_name"])
        w.writerows(rows)
    return len(rows)


def main():
    net = load_all()
    n_routes = export_routes(net)
    n_stages = export_stages(net)
    print(f"{n_routes} routes -> data/views/routes.csv")
    print(f"{n_stages} stages -> data/views/stages.csv")


if __name__ == "__main__":
    main()
