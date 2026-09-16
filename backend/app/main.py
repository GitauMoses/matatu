from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

from .geocoding import search_places
from .feed import load_all
from .routing import plan_trip, nearest_stage, build_transfer_index, MAX_REASONABLE_WALK_KM

app = Flask(__name__)
CORS(app)  # tighten origins before real deployment

net = load_all()
build_transfer_index(net)  # pay the interchange scan here, not on first request

# stop_id -> route numbers stopping there, so search can tell a passenger
# which matatus a stage is good for.
ROUTES_AT_STAGE: dict[str, list[str]] = {}
for _path in net.all_paths():
    _route = net.routes.get(_path.route_id)
    if not _route:
        continue
    for _sid in _path.stage_ids:
        bucket = ROUTES_AT_STAGE.setdefault(_sid, [])
        if _route.number not in bucket:
            bucket.append(_route.number)


def error(status_code, message):
    return jsonify({"detail": message}), status_code


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "stages_loaded": len(net.stages),
        "routes_loaded": len(net.routes),
        "paths_loaded": len(net.paths),
    })


@app.get("/stops")
def list_stops():
    return jsonify([
        {"id": s.id, "name": s.name, "lat": s.lat, "lon": s.lon,
         "routes": ROUTES_AT_STAGE.get(s.id, [])}
        for s in net.all_stages()
    ])


@app.get("/routes")
def list_routes():
    out = []
    for r in net.all_routes():
        out.append({
            "id": r.id,
            "number": r.number,
            "description": r.description,
            "directions": [
                {
                    "direction": net.paths[p].direction,
                    "towards": net.paths[p].headsign,
                    "num_stages": len(net.paths[p].stage_ids),
                }
                for p in r.path_ids
            ],
        })
    return jsonify(out)


@app.get("/routes/<route_id>/shape")
def route_shape(route_id):
    """Full recorded path for each direction of a route, for drawing a whole
    route line rather than just the slice used by one plan."""
    route = net.routes.get(route_id)
    if not route:
        return error(404, "unknown route")
    return jsonify({
        "route_id": route.id,
        "number": route.number,
        "directions": [
            {
                "direction": net.paths[p].direction,
                "towards": net.paths[p].headsign,
                "geometry": net.shapes.get(p, []),
                "stages": [
                    {"id": s, "name": net.stages[s].name,
                     "lat": net.stages[s].lat, "lon": net.stages[s].lon}
                    for s in net.paths[p].stage_ids if s in net.stages
                ],
            }
            for p in route.path_ids
        ],
    })


@app.get("/search")
def search():
    """Place search for the origin/destination boxes.

    Returns matching matatu stages first (they're what we can actually route
    to), then OSM places. Every result carries the nearest stage and the walk
    to it, so the app can tell someone standing in an estate which stage to
    head for - and can say plainly when nothing is within walking distance.
    """
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])

    near = None
    try:
        near = (float(request.args["lat"]), float(request.args["lon"]))
    except (KeyError, ValueError, TypeError):
        pass

    ql = q.lower()

    # The same physical stage appears once per route that was surveyed
    # through it, so collapse by name and keep one entry per place.
    #
    # The subtitle lists the matatus that stop there. It used to name the
    # corridor ("Matatu stage · thika road"), which is a development concept
    # for building the data out in phases - meaningless to someone standing
    # at the stage. Which routes serve it is the thing they can act on.
    by_name: dict[str, dict] = {}
    for s in net.all_stages():
        if ql not in s.name.lower():
            continue
        key = s.name.lower()
        if key in by_name:
            by_name[key]["routes"].update(ROUTES_AT_STAGE.get(s.id, ()))
            continue
        by_name[key] = {
            "id": f"stage:{s.id}", "name": s.name,
            "lat": s.lat, "lon": s.lon, "source": "stage",
            "nearest_stage": {"id": s.id, "name": s.name, "walk_km": 0.0},
            "reachable": True,
            "routes": set(ROUTES_AT_STAGE.get(s.id, ())),
        }
    for r in by_name.values():
        routes = sorted(r.pop("routes"), key=lambda x: (len(x), x))
        shown, extra = routes[:5], len(routes) - 5
        r["routes"] = routes
        r["context"] = (
            "Matatu stage · " + ", ".join(shown) + (f" +{extra} more" if extra > 0 else "")
            if shown else "Matatu stage"
        )
    results = sorted(by_name.values(),
                     key=lambda r: (not r["name"].lower().startswith(ql), len(r["name"])))[:5]

    stage_names = {r["name"].lower() for r in results}
    for place in search_places(q, near=near):
        if place["name"].lower() in stage_names:
            continue
        stage, km = nearest_stage(net, place["lat"], place["lon"])
        place["nearest_stage"] = (
            {"id": stage.id, "name": stage.name, "walk_km": round(km, 2),
             "routes": ROUTES_AT_STAGE.get(stage.id, [])} if stage else None
        )
        place["reachable"] = bool(stage) and km <= MAX_REASONABLE_WALK_KM
        results.append(place)

    return jsonify(results[:12])


@app.get("/plan")
def plan():
    try:
        origin_lat = float(request.args["origin_lat"])
        origin_lon = float(request.args["origin_lon"])
        dest_lat = float(request.args["dest_lat"])
        dest_lon = float(request.args["dest_lon"])
    except (KeyError, ValueError):
        return error(400, "origin_lat, origin_lon, dest_lat, dest_lon are required numeric query params")

    result = plan_trip(
        net, origin_lat, origin_lon, dest_lat, dest_lon,
        origin_name=(request.args.get("origin_name") or "your starting point").strip(),
        dest_name=(request.args.get("dest_name") or "your destination").strip(),
    )
    if "error" in result:
        return error(404, result["error"])
    return jsonify(result)


if __name__ == "__main__":
    # Run with: python3 -m app.main   (from the backend/ directory)
    app.run(host="0.0.0.0", port=8123, debug=True)
