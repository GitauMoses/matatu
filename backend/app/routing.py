"""
Trip planning over the loaded matatu network.

Works on route *paths* (one per direction) rather than routes, so a plan
always reflects a matatu actually travelling the way the passenger wants to
go. There are no departure times anywhere in here: matatus leave when full,
so the only time-like thing is an estimate used to rank options.

Route geometry comes from the source feed's recorded shapes - the GPS trace
of someone riding the matatu - sliced between the boarding and alighting
stages. We deliberately do NOT ask a directions API to infer the path:
matatus follow their own route, and a driving-directions call between stops
will happily invent detours through estates that no matatu takes.

This is still not a general-purpose transit router. It handles a direct trip
and a single transfer at a shared stage. Multi-transfer journeys across many
corridors will need a real graph search (RAPTOR / OpenTripPlanner), which
only changes this file - the network data underneath stays valid.
"""
import math
from .feed import Network, RoutePath, Stage


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# Beyond this, "walk to the stage" stops being a real answer - it means the
# place sits outside the area we hold stage data for, and we should say so
# rather than return a plan nobody would follow.
MAX_REASONABLE_WALK_KM = 2.5


def nearest_stage(net: Network, lat: float, lon: float) -> tuple[Stage, float]:
    best, best_dist = None, float("inf")
    for stop in net.all_stages():
        d = haversine_km(lat, lon, stop.lat, stop.lon)
        if d < best_dist:
            best, best_dist = stop, d
    return best, best_dist


def _nearest_stops(net: Network, lat: float, lon: float, limit: int) -> list[tuple[Stage, float]]:
    scored = [(s, haversine_km(lat, lon, s.lat, s.lon)) for s in net.all_stages()]
    scored.sort(key=lambda p: p[1])
    return scored[:limit]


# Two stops this close with the same name are the same kerbside place,
# recorded once per route that was surveyed through it.
SAME_PLACE_KM = 0.25


# In town, stages are dense enough that the nearest handful of places all sit
# within a few hundred metres, which pushed real termini out of the shortlist:
# Railways is 700 m from the centre, and every route starting there - 2, 8,
# 102, 111, 125, 126, covering Ngong Road, Langata Road and Mombasa Road -
# became unreachable directly. So always consider everything inside this
# radius, however many places that is.
ALWAYS_CONSIDER_KM = 1.2

# Ceiling on that expansion, so a dense centre cannot blow up the pairing
# search that runs over these candidates.
MAX_PLACES = 20


def _nearest_places(net: Network, lat: float, lon: float,
                    limit: int) -> list[tuple[list[Stage], float]]:
    """Nearest distinct places, each as the full group of stop records there.

    Grouping (rather than dropping duplicates) matters twice over. The feed
    holds one stop record per route surveyed through a place, so an
    ungrouped shortlist fills with repeats - near Ruiru the eight closest
    records were four places listed twice, all on one feeder route, hiding
    the trunk stages 237 and 145 use.

    But the records at a place are not interchangeable, so we must keep all
    of them: at Juja, "Juja Stage" and "Jkuat" sit 80 m apart and only
    "Jkuat" appears on the inbound trip. Keeping just the closer record left
    a passenger heading to town with no usable boarding point for a
    kilometre and a half.
    """
    scored = [(s, haversine_km(lat, lon, s.lat, s.lon)) for s in net.all_stages()]
    scored.sort(key=lambda p: p[1])

    groups: list[tuple[list[Stage], float]] = []
    for stop, km in scored:
        for members, _ in groups:
            if _same_place(stop, members[0]):
                members.append(stop)
                break
        else:
            keep = len(groups) < limit or km <= ALWAYS_CONSIDER_KM
            if not keep or len(groups) >= MAX_PLACES:
                continue
            groups.append(([stop], km))
    return groups


def _same_place(a: Stage, b: Stage) -> bool:
    d = haversine_km(a.lat, a.lon, b.lat, b.lon)
    if d > SAME_PLACE_KM:
        return False
    # Within a few dozen metres it's the same kerb whatever the label says -
    # which also absorbs survey typos like "Super Higway" / "Super Highway".
    if d <= 0.12:
        return True
    na, nb = _norm_name(a.name), _norm_name(b.name)
    return na == nb or na in nb or nb in na


def _norm_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


# How far a passenger will walk to change matatus. Transfers can't rely on
# two trips sharing a stop_id: each source route was surveyed separately, so
# the same physical place has different ids per route (Thika Road's "Ngara"
# sits 29 m from Kiambu Road's "Ngara Bus Terminals"). Matching on proximity
# also models the real thing - crossing the road to the other stage.
#
# Set to match how people actually change in town. Terminals are spread
# across the centre - Railways to Archives is 650 m, to Townterminal 692 m -
# and walking between them is the ordinary way to cross the city: you ride in
# on one route, walk to where the other route loads, and ride out. At 350 m
# none of those connections existed, so Rongai to Thika and Ngong to Githurai
# returned nothing at all.
TRANSFER_WALK_KM = 0.75

_transfer_index: dict[int, dict[str, list[tuple[str, float]]]] = {}


def _nearby_stops(net: Network) -> dict[str, list[tuple[str, float]]]:
    """stop_id -> [(other_stop_id, km), ...] within TRANSFER_WALK_KM, cached
    per feed instance.

    Across the full city feed this is ~2,500 stops, so building it costs a
    few seconds. Call build_transfer_index() at startup rather than paying
    that on whichever request happens to arrive first.
    """
    key = id(net)
    cached = _transfer_index.get(key)
    if cached is not None:
        return cached

    stops = net.all_stages()
    index: dict[str, list[tuple[str, float]]] = {s.id: [(s.id, 0.0)] for s in stops}
    # Bucket by a coarse grid so we compare each stop only against its own
    # neighbourhood instead of all 2,500 - the full pairwise sweep is ~3M
    # haversines and dominates startup.
    cell = TRANSFER_WALK_KM / 110.0  # degrees, roughly
    buckets: dict[tuple[int, int], list[Stage]] = {}
    for s in stops:
        buckets.setdefault((int(s.lat / cell), int(s.lon / cell)), []).append(s)

    for (cy, cx), members in buckets.items():
        neighbours = [
            n for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            for n in buckets.get((cy + dy, cx + dx), ())
        ]
        for a in members:
            for b in neighbours:
                if a.id >= b.id:
                    continue
                d = haversine_km(a.lat, a.lon, b.lat, b.lon)
                if d <= TRANSFER_WALK_KM:
                    index[a.id].append((b.id, d))
                    index[b.id].append((a.id, d))
    _transfer_index[key] = index
    return index


def build_transfer_index(net: Network) -> int:
    """Warm the interchange index. Returns the number of stops indexed."""
    _nearby_stops(net)
    return len(net.stages)


# How close a route's recorded path must come to a point for the matatu to be
# able to drop you there. Matatus stop on request anywhere along their route -
# you tell the conductor the place and get off at it - so a surveyed stage
# record is not required for somewhere to be reachable.
ON_ROUTE_KM = 0.25


class _Overlay:
    """Per-request view of the network with request stops spliced in.

    The survey recorded far fewer stages than exist. Kahawa Wendani has no
    stage record, yet route 237 drives straight through it, so "alight at
    Kahawa and walk 530 m" is a worse answer than "tell the conductor
    Wendani". This inserts a stop at the point where a route actually passes
    the place, at the right position in that route's stage order, so the rest
    of the planner treats it like any other stage.

    The Network itself is loaded once and shared, so nothing here mutates it.
    """

    def __init__(self, net: Network):
        self.net = net
        self.stages: dict[str, Stage] = {}
        self.path_stage_ids: dict[str, list[str]] = {}
        self.extra_paths_by_stage: dict[str, list[str]] = {}

    def stage(self, stage_id: str) -> Stage:
        return self.stages.get(stage_id) or self.net.stages[stage_id]

    def stage_ids(self, path: RoutePath) -> list[str]:
        return self.path_stage_ids.get(path.id, path.stage_ids)

    def paths_at(self, stage_id: str) -> list[RoutePath]:
        """Route directions calling at a stage, via the prebuilt index."""
        ids = self.net.paths_by_stage.get(stage_id, ())
        extra = self.extra_paths_by_stage.get(stage_id, ())
        return [self.net.paths[i] for i in (*ids, *extra) if i in self.net.paths]

    def add_request_stop(self, path: RoutePath, lat: float, lon: float,
                         name: str) -> Stage | None:
        """Splice a stop into `path` where it passes closest to (lat, lon)."""
        shape = self.net.shapes.get(path.id) or []
        if len(shape) < 2:
            return None
        k = min(range(len(shape)),
                key=lambda i: haversine_km(lat, lon, shape[i][1], shape[i][0]))
        snapped_lon, snapped_lat = shape[k]
        if haversine_km(lat, lon, snapped_lat, snapped_lon) > ON_ROUTE_KM:
            return None

        ids = self.stage_ids(path)
        # Where along the route does this fall? Compare against each stage's
        # own position on the shape, so ordering follows the road, not
        # straight-line distance.
        def shape_index(stage_id: str) -> int:
            s = self.stage(stage_id)
            return min(range(len(shape)),
                       key=lambda i: haversine_km(s.lat, s.lon, shape[i][1], shape[i][0]))

        insert_at = len(ids)
        for pos, sid in enumerate(ids):
            if shape_index(sid) > k:
                insert_at = pos
                break
        if insert_at == 0:
            return None  # before the terminus; boarding there isn't a thing

        stage_id = f"req:{path.id}:{k}"
        stage = Stage(id=stage_id, name=name, lat=snapped_lat, lon=snapped_lon)
        self.stages[stage_id] = stage
        self.path_stage_ids[path.id] = ids[:insert_at] + [stage_id] + ids[insert_at:]
        self.extra_paths_by_stage.setdefault(stage_id, []).append(path.id)
        return stage


def _paths_near(net: Network, lat: float, lon: float,
                radius_km: float = ON_ROUTE_KM) -> list[tuple[RoutePath, float]]:
    """Route directions whose recorded path passes within radius_km."""
    out = []
    for path in net.all_paths():
        shape = net.shapes.get(path.id) or []
        if len(shape) < 2:
            continue
        best = min((haversine_km(lat, lon, p[1], p[0]) for p in shape), default=None)
        if best is not None and best <= radius_km:
            out.append((path, best))
    out.sort(key=lambda p: p[1])
    return out


def _shape_slice(net: Network, path: RoutePath, from_stop: Stage, to_stop: Stage) -> list[list[float]]:
    """The recorded road path between two stages on this route direction."""
    shape = net.shapes.get(path.id) or []
    if len(shape) < 2:
        return [[from_stop.lon, from_stop.lat], [to_stop.lon, to_stop.lat]]

    def nearest_idx(stop: Stage) -> int:
        return min(range(len(shape)),
                   key=lambda i: haversine_km(stop.lat, stop.lon, shape[i][1], shape[i][0]))

    i, j = nearest_idx(from_stop), nearest_idx(to_stop)
    if i == j:
        return [[from_stop.lon, from_stop.lat], [to_stop.lon, to_stop.lat]]
    segment = shape[i:j + 1] if i < j else shape[j:i + 1][::-1]
    # Anchor the ends on the actual stages so the line starts and finishes
    # at the stage markers rather than at whichever GPS ping was closest.
    return [[from_stop.lon, from_stop.lat]] + segment + [[to_stop.lon, to_stop.lat]]


def _line_km(points: list[list[float]]) -> float:
    """Length of a [[lon, lat], ...] polyline."""
    return sum(haversine_km(a[1], a[0], b[1], b[0])
               for a, b in zip(points, points[1:]))


def _leg(ov: _Overlay, path: RoutePath, board: Stage, alight: Stage) -> dict:
    net = ov.net
    route = net.routes[path.route_id]
    stage_ids = ov.stage_ids(path)
    i, j = stage_ids.index(board.id), stage_ids.index(alight.id)
    between = stage_ids[i:j + 1]
    geometry = _shape_slice(net, path, board, alight)
    return {
        "route_id": route.id,
        "route_number": route.number,
        "route_description": route.description,
        "path_id": path.id,
        "headsign": path.headsign,
        "terminals": [
            {"name": t.name, "lat": t.lat, "lon": t.lon, "saccos": t.saccos}
            for t in route.terminals
        ],
        # Only meaningful when terminals has nothing confirmed - see Route.likely_saccos.
        "likely_saccos": route.likely_saccos if not route.terminals else [],
        "board_stop": _stop_out(board),
        "alight_stop": _stop_out(alight),
        "stops": [_stop_out(ov.stage(s)) for s in between],
        "alight_on_request": alight.id.startswith("req:"),
        "num_stages": len(between) - 1,
        "distance_km": round(_line_km(geometry), 2),
        "geometry": geometry,
    }


def _paths_serving(ov: _Overlay, from_id: str, to_id: str) -> list[RoutePath]:
    """Route directions visiting from_id then to_id in that order."""
    out = []
    for path in ov.paths_at(from_id):
        ids = ov.stage_ids(path)
        if to_id in ids and ids.index(from_id) < ids.index(to_id):
            out.append(path)
    return out


# Ranking is in estimated minutes: pick the fastest journey, and prefer the
# one that walks you least.
#
# There is no fare data in this project. An earlier version ranked partly on
# a "fare proxy" - the number of stages on the whole route, standing in for
# the terminus a matatu is priced to. It was an inference presented as a
# number, so it's gone. Nothing here claims to know what a trip costs.
#
# These constants are rough but honest about being rough: they exist to
# order options against each other, not to promise an arrival time. Matatus
# leave when full and Nairobi traffic is what it is, so no total is shown to
# the passenger - only walking distance and stage counts, which are facts.
WALK_MIN_PER_KM = 13.0     # ~4.6 km/h, allowing for terrain and crossings
RIDE_MIN_PER_KM = 3.0      # ~20 km/h door to door, including stopping
TRANSFER_MIN = 7.0         # finding the next matatu and waiting for it


# Walking is worse than the clock says. A minute on foot carrying shopping,
# in sun or rain, is not a minute sitting in a matatu, and riders will accept
# a noticeably longer trip to avoid a long walk. Standard practice in transit
# routing is to weight walking above in-vehicle time; without it the planner
# sent someone 1.7 km on foot from Kayole Junction to save six minutes, when
# a matatu left from the stage they were already standing at.
#
# Applied only to ranking, never to the figure shown to the passenger - the
# displayed estimate stays an honest guess at elapsed time.
WALK_AVERSION = 1.9


def estimated_minutes(option: dict) -> float:
    """Rough journey time, used to order options - never shown as an ETA.

    Riding is costed by distance, not by number of stages. Counting stages
    punished being carried closer: alighting at a request stop three closely
    spaced stages further on scored as 7.5 minutes of extra riding, which lost
    to a 530 m walk, so the planner kept telling people to get off early and
    walk. Distance does not have that failure - three stages over half a
    kilometre costs what half a kilometre costs.
    """
    walk_km = (option["walk_to_board_km"] + option["walk_from_alight_km"]
               + option.get("transfer_walk_km", 0.0))
    ride_km = sum(leg.get("distance_km", 0.0) for leg in option["legs"])
    return (walk_km * WALK_MIN_PER_KM
            + ride_km * RIDE_MIN_PER_KM
            + option["transfers"] * TRANSFER_MIN)


def _walk_km(option: dict) -> float:
    return (option["walk_to_board_km"] + option["walk_from_alight_km"]
            + option.get("transfer_walk_km", 0.0))


def _score(option: dict) -> tuple[float, float]:
    """Ranking cost: elapsed time, with walking weighted above riding."""
    extra = _walk_km(option) * WALK_MIN_PER_KM * (WALK_AVERSION - 1)
    return (estimated_minutes(option) + extra, _walk_km(option))


# Below this, taking a matatu is not worth it. In and around town people
# walk: boarding, paying and alighting costs more time than the walk saves,
# and short hops across the CBD are not a thing anyone actually does.
WALK_INSTEAD_KM = 1.6


def plan_trip(net: Network, origin_lat: float, origin_lon: float,
              dest_lat: float, dest_lon: float, candidates: int = 8,
              origin_name: str = "your starting point",
              dest_name: str = "your destination") -> dict:
    direct_km = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    if direct_km <= WALK_INSTEAD_KM:
        return {
            "options": [],
            "walk_only": {
                "distance_km": round(direct_km, 2),
                "minutes": max(1, round(direct_km * WALK_MIN_PER_KM)),
            },
            "note": "This is a short trip - walking is quicker than finding a matatu.",
        }

    ov = _Overlay(net)

    # Before falling back to "walk to the nearest recorded stage", check
    # whether a route simply drives past. Matatus stop on request, so a place
    # a route passes is reachable even with no stage recorded there - which
    # is most places, since the survey is far sparser than reality.
    request_origin = [
        st for st in (ov.add_request_stop(p, origin_lat, origin_lon, origin_name)
                      for p, _ in _paths_near(net, origin_lat, origin_lon)) if st
    ]
    request_dest = [
        st for st in (ov.add_request_stop(p, dest_lat, dest_lon, dest_name)
                      for p, _ in _paths_near(net, dest_lat, dest_lon)) if st
    ]

    origin_opts = _nearest_places(net, origin_lat, origin_lon, candidates)
    dest_opts = _nearest_places(net, dest_lat, dest_lon, candidates)
    if not origin_opts or not dest_opts:
        return {"error": "no stages loaded"}

    # Say plainly when a point is out of range of any stage we hold, instead
    # of routing someone from a stage they'd never realistically walk to.
    for opts, which, on_route in ((origin_opts, "starting point", request_origin),
                                  (dest_opts, "destination", request_dest)):
        members, km = opts[0]
        if km > MAX_REASONABLE_WALK_KM and not on_route:
            return {"error": (
                f"Your {which} is {km:.1f} km from the nearest matatu stage we have "
                f"({members[0].name}).")}

    # Flatten place groups back to individual stops; every record at a place
    # is a candidate, since different records there serve different trips.
    # Request stops come first: being dropped at the door beats walking.
    origin_stops = [(s, 0.0) for s in request_origin] + \
                   [(s, km) for members, km in origin_opts for s in members]
    dest_stops = [(s, 0.0) for s in request_dest] + \
                 [(s, km) for members, km in dest_opts for s in members]

    options: list[dict] = []
    seen: set[tuple] = set()

    # Direct trips, considering several nearby stages at each end rather than
    # only the single closest - the nearest stage often isn't served by any
    # matatu going where the passenger wants.
    for board, board_km in origin_stops:
        for alight, alight_km in dest_stops:
            if board.id == alight.id:
                continue
            for path in _paths_serving(ov, board.id, alight.id):
                key = (path.route_id, board.id, alight.id)
                if key in seen:
                    continue
                seen.add(key)
                options.append({
                    "legs": [_leg(ov, path, board, alight)],
                    "transfers": 0,
                    "walk_to_board_km": round(board_km, 2),
                    "walk_from_alight_km": round(alight_km, 2),
                })

    # Transfers are always considered, not just when nothing direct exists.
    # A direct matatu that leaves you a 3 km walk is worse than changing once
    # and being dropped at the door, so the two have to compete on score
    # rather than one pre-empting the other.
    nearby = _nearby_stops(net)
    best_by_routes: dict[tuple[str, str], tuple] = {}
    for board, board_km in origin_stops:
        first_legs = ov.paths_at(board.id)
        for alight, alight_km in dest_stops:
            second_legs = ov.paths_at(alight.id)
            for t1 in first_legs:
                ids1 = ov.stage_ids(t1)
                i1 = ids1.index(board.id)
                onward = ids1[i1 + 1:]
                for t2 in second_legs:
                    if t2.route_id == t1.route_id:
                        continue
                    ids2 = ov.stage_ids(t2)
                    j2 = ids2.index(alight.id)
                    inbound = set(ids2[:j2])
                    sig = (t1.route_id, t2.route_id)
                    for offset, x1 in enumerate(onward, start=1):
                        for x2, walk_km in nearby.get(x1, ()):
                            if x2 not in inbound:
                                continue
                            # Stages actually ridden, so an interchange 20
                            # stops further down the road is scored as the
                            # detour it is rather than tying with the near one.
                            # Score this interchange the same way the final
                            # ranking will, using straight-line distance as a
                            # cheap stand-in for ride distance. It has to be
                            # comparable: only the best interchange per route
                            # pair survives, so a proxy that disagrees with
                            # estimated_minutes locks in a worse one before
                            # ranking ever sees the alternatives.
                            x1s, x2s = ov.stage(x1), ov.stage(x2)
                            ride_km = (haversine_km(board.lat, board.lon, x1s.lat, x1s.lon)
                                       + haversine_km(x2s.lat, x2s.lon, alight.lat, alight.lon))
                            total = (TRANSFER_MIN
                                     + (board_km + alight_km + walk_km) * WALK_MIN_PER_KM
                                     + ride_km * RIDE_MIN_PER_KM)
                            prev = best_by_routes.get(sig)
                            if prev is None or total < prev[0]:
                                best_by_routes[sig] = (
                                    total, t1, t2, board, alight, x1, x2,
                                    board_km, alight_km, walk_km,
                                )
                            break  # nearest usable interchange for this stage

    for total, t1, t2, board, alight, x1, x2, board_km, alight_km, walk_km in \
            sorted(best_by_routes.values(), key=lambda v: v[0])[:6]:
        s1, s2 = ov.stage(x1), ov.stage(x2)
        options.append({
            "legs": [_leg(ov, t1, board, s1), _leg(ov, t2, s2, alight)],
            "transfers": 1,
            "transfer_stop": _stop_out(s1),
            "transfer_to_stop": _stop_out(s2),
            "transfer_walk_km": round(walk_km, 2),
            "walk_to_board_km": round(board_km, 2),
            "walk_from_alight_km": round(alight_km, 2),
        })

    if not options:
        return {"error": (
            "No matatu route found between these points. This planner handles a "
            "direct trip or one change, so a journey needing two changes won't "
            "resolve yet.")}

    options.sort(key=_score)

    # One entry per set of matatus. Without this the list is the same route
    # repeated with slightly different boarding stages, which reads as four
    # choices when it's really one.
    deduped: list[dict] = []
    seen_routes: set[tuple[str, ...]] = set()
    for o in options:
        sig = tuple(l["route_number"] for l in o["legs"])
        if sig in seen_routes:
            continue
        seen_routes.add(sig)
        deduped.append(o)

    for o in deduped:
        o["estimated_minutes"] = round(estimated_minutes(o))

    return {
        "options": deduped[:4],
        "note": ("Options are ordered cheapest-first: matatu fares are priced to the "
                 "route's terminus, not the distance you actually ride, so a matatu "
                 "ending sooner usually costs less for the same journey. Fare amounts "
                 "and sacco names are not in this data yet."),
    }


def _stop_out(stop: Stage) -> dict:
    return {"id": stop.id, "name": stop.name, "lat": stop.lat, "lon": stop.lon}
