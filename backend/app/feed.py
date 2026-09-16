"""
Loads the matatu network from data/network/ into memory.

The model is deliberately not a transit-schedule format. Those are built
around departure times, service calendars and headways, and matatus have
none of that - they leave when full and run around the clock. Carrying that
shape meant writing agency, calendar and frequency files nothing ever read,
and a "stop times" file holding no times, only the order of stages.

What a matatu route actually is: a numbered service with an ordered list of
stages between two termini, ridden in either direction. Four files:

    stages.csv    stage_id, name, lat, lon
    routes.csv    route_id, number, description, outbound_to, inbound_to, corridor
    paths.csv     route_id, direction, sequence, stage_id
    shapes.csv    route_id, direction, sequence, lat, lon
    terminals.csv route_id, number, name, lat, lon, saccos

`direction` is "out" (away from town) or "in" (towards town). Both are kept
because they genuinely differ - 131 of 134 routes list different stages each
way, mostly because CBD streets are one-way.

`corridor` is a development label, not a user-facing idea: it marks routes
that have been checked along a known trunk so work can proceed in phases.
It is blank for routes not on one, and never reaches the API.
"""
import csv
import os
from dataclasses import dataclass, field

from .paths import NETWORK_DIR

OUTBOUND = "out"
INBOUND = "in"


@dataclass
class Stage:
    id: str
    name: str
    lat: float
    lon: float


@dataclass
class RoutePath:
    """One direction of a route: the stages in the order you pass them."""
    route_id: str
    direction: str
    headsign: str
    stage_ids: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.route_id}:{self.direction}"


@dataclass
class Terminal:
    """A place in town where a route boards, and the saccos running it there.

    A route can have more than one: 38/39 loads at Bus Station (Super Metro,
    City Shuttle) and at Temple Road (Obamana, EBTI and others). Which one you
    walk to decides which sacco you ride, so this is real information to a
    passenger, not bookkeeping.
    """
    name: str
    lat: float
    lon: float
    saccos: list[str] = field(default_factory=list)


@dataclass
class Route:
    id: str
    number: str
    description: str
    corridor: str  # dev label, may be empty
    path_ids: list[str] = field(default_factory=list)
    terminals: list[Terminal] = field(default_factory=list)
    # Saccos likely to run this route, matched from NTSA's registry rather
    # than confirmed by a rider — see datacleaning/README.md. Only ever a
    # fallback when `terminals` has nothing confirmed; never shown as fact.
    likely_saccos: list[str] = field(default_factory=list)


class Network:
    def __init__(self):
        self.stages: dict[str, Stage] = {}
        self.routes: dict[str, Route] = {}
        self.paths: dict[str, RoutePath] = {}
        self.shapes: dict[str, list[list[float]]] = {}  # path id -> [[lon, lat], ...]
        # stage id -> path ids calling there. Without it every candidate pair
        # rescans all 268 paths, which is what made a wider shortlist slow.
        self.paths_by_stage: dict[str, list[str]] = {}

    def all_stages(self):
        return list(self.stages.values())

    def all_routes(self):
        return list(self.routes.values())

    def all_paths(self):
        return list(self.paths.values())


def _read(name: str):
    path = os.path.join(NETWORK_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_all() -> Network:
    net = Network()

    for row in _read("stages.csv"):
        net.stages[row["stage_id"]] = Stage(
            id=row["stage_id"], name=row["name"].strip(),
            lat=float(row["lat"]), lon=float(row["lon"]),
        )

    for row in _read("routes.csv"):
        route = Route(
            id=row["route_id"], number=row["number"],
            description=row["description"], corridor=row.get("corridor", ""),
        )
        net.routes[route.id] = route
        for direction, headsign in ((OUTBOUND, row.get("outbound_to", "")),
                                    (INBOUND, row.get("inbound_to", ""))):
            path = RoutePath(route_id=route.id, direction=direction,
                             headsign=(headsign or "").strip())
            net.paths[path.id] = path
            route.path_ids.append(path.id)

    ordered: dict[str, list[tuple[int, str]]] = {}
    for row in _read("paths.csv"):
        key = f"{row['route_id']}:{row['direction']}"
        ordered.setdefault(key, []).append((int(row["sequence"]), row["stage_id"]))
    for key, pairs in ordered.items():
        if key in net.paths:
            net.paths[key].stage_ids = [sid for _, sid in sorted(pairs)]

    for row in _read("terminals.csv"):
        route = net.routes.get(row["route_id"])
        if route:
            route.terminals.append(Terminal(
                name=row["name"].strip(),
                lat=float(row["lat"]), lon=float(row["lon"]),
                saccos=[s for s in row["saccos"].split("|") if s],
            ))

    for row in _read("route_operators.csv"):
        route = net.routes.get(row["route_id"])
        if route:
            route.likely_saccos = [s for s in row["saccos"].split("|") if s]

    points: dict[str, list[tuple[int, float, float]]] = {}
    for row in _read("shapes.csv"):
        key = f"{row['route_id']}:{row['direction']}"
        points.setdefault(key, []).append(
            (int(row["sequence"]), float(row["lon"]), float(row["lat"]))
        )
    for key, triples in points.items():
        net.shapes[key] = [[lon, lat] for _, lon, lat in sorted(triples)]

    for path in net.paths.values():
        for sid in path.stage_ids:
            net.paths_by_stage.setdefault(sid, []).append(path.id)

    # A route with no stages either way carries no information; drop it so
    # nothing downstream has to keep checking for empty paths.
    for route in list(net.routes.values()):
        if not any(net.paths[p].stage_ids for p in route.path_ids):
            for p in route.path_ids:
                net.paths.pop(p, None)
            net.routes.pop(route.id, None)

    return net
