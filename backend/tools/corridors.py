"""
Which corridor a route belongs to, derived from where it actually runs.

This replaces a hand-typed list of route ids. That list was written from
reading the printed route map before the surveyed feed was available, and it
was both incomplete and silently wrong - routes 25 (Baba Dogo), 25A (Lucky
Summer), 29/30 (Mathare North) and 43 (Ngumba) all run up Thika Road and all
ended up in the leftover bucket, because nobody went back to retype the list.

A corridor is defined by a trunk route that everyone agrees runs its length.
Any route sharing enough of that trunk's path belongs to the corridor. So
adding a corridor means naming its trunk, not enumerating its members, and
the membership can't drift out of date with the data.
"""
import math

# corridor -> route number of the route that defines its trunk
TRUNK_ROUTES = {
    "thika_road": "237",     # Townterminal - Roasters - Githurai - Ruiru - Juja - Thika
    "kiambu_road": "120",    # Kaka - Muthaiga - Kiambu Road - Kiambu - Githunguri
    "kangundo_road": "38/39",  # Bus Station/Temple Rd - Kayole - Ruai - Kamulu - Joska
    "mombasa_road": "110",     # Railways - Mombasa Rd - Mlolongo - Kitengela
    "langata_road": "126",     # Railways - Langata Rd - Ongata Rongai - Kiserian
    "ngong_road": "111",       # Railways - Ngong Rd - Karen - Ngong
}

# A stage counts as "on the trunk" within this distance of its path.
ON_TRUNK_KM = 0.4

# Share of a route's stages that must sit on the trunk for it to belong.
# Deliberately low: feeder routes run a few kilometres up the trunk and then
# branch off into an estate, and to a passenger standing on the trunk they
# are still that corridor's routes. Route 25 (Baba Dogo) and 25A (Lucky
# Summer) sit at 0.29 and 0.27.
MIN_SHARE = 0.25

# The real discriminator is how many stages a route actually runs along the
# trunk, because share alone can't separate a short feeder from a route that
# merely crosses. At five, routes 25 and 25A (5 and 7 stages on Thika Road)
# are in, while 145B, 53 and 17B_2 (3, 1 and 0) correctly stay out despite
# comparable shares.
MIN_STAGES_ON_TRUNK = 5


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _grid(points, cell_km):
    """Bucket trunk points so proximity tests don't scan the whole line."""
    cell = cell_km / 110.0
    buckets = {}
    for lat, lon in points:
        buckets.setdefault((int(lat / cell), int(lon / cell)), []).append((lat, lon))
    return buckets, cell


def _near_trunk(lat, lon, buckets, cell, limit_km):
    cy, cx = int(lat / cell), int(lon / cell)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for tlat, tlon in buckets.get((cy + dy, cx + dx), ()):
                if haversine_km(lat, lon, tlat, tlon) <= limit_km:
                    return True
    return False


def assign_corridors(routes, stages_of_route, default="nairobi"):
    """routes: {route_number: route_id}
    stages_of_route: route_number -> [(lat, lon), ...]
    Returns {route_id: corridor_name}."""
    trunks = {}
    for corridor, trunk_number in TRUNK_ROUTES.items():
        pts = stages_of_route.get(trunk_number)
        if pts:
            trunks[corridor] = _grid(pts, ON_TRUNK_KM)

    assignment = {}
    for number, route_id in routes.items():
        pts = stages_of_route.get(number) or []
        best, best_share = default, 0.0
        for corridor, (buckets, cell) in trunks.items():
            if not pts:
                continue
            on = sum(1 for lat, lon in pts
                     if _near_trunk(lat, lon, buckets, cell, ON_TRUNK_KM))
            share = on / len(pts)
            if on >= MIN_STAGES_ON_TRUNK and share >= MIN_SHARE and share > best_share:
                best, best_share = corridor, share
        assignment[route_id] = best
    return assignment
