"""
Applies hand-maintained corrections on top of the surveyed network.

The survey is from 2015 and stops short of reality in places: routes have
been extended, stages exist that were never recorded, and a route can board
from more than one terminal in town. None of that could be captured before,
because extract.py rebuilds data/network/ from scratch on every run, so any
hand edit there was silently undone.

Corrections live in data/corrections/ and are applied after the survey is
loaded, so they survive a rebuild. This is where knowledge that is *not* in
any public dataset goes - it is the part of this project that is actually
ours rather than a copy of a decade-old feed.

    stages.csv      stages the survey never recorded
    extensions.csv  stages appended past a route's surveyed terminus
    terminals.csv   town terminals a route boards from, and the saccos there
    routes.csv      the number actually painted on the matatu

An extension also needs geometry. Without it the map line stops at the old
terminus, leg distances are under-counted, and - since reachability is
decided by whether a route's path passes near a point - nothing past the old
terminus can be reached on request. Name a road in the extension's `road`
column and its centreline (see tools/osm_road.py) is used for the new
stretch.

Extensions apply to both directions: appended to the outbound order and
prepended in reverse to the inbound, because the matatu comes back the
same way.
"""
import csv
import math
import os
import re

from app.paths import DATA_DIR, SOURCES_DIR

CORRECTIONS_DIR = os.path.join(DATA_DIR, "corrections")


def _read(name):
    path = os.path.join(CORRECTIONS_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return [r for r in csv.DictReader(f) if any(v.strip() for v in r.values())]


def load_stages():
    """stage_id -> (name, lat, lon)."""
    return {r["stage_id"]: (r["name"].strip(), float(r["lat"]), float(r["lon"]))
            for r in _read("stages.csv")}


def load_extensions():
    """route number -> [(after_stage_name, [stage_id, ...], road_slug), ...]"""
    out = {}
    for r in _read("extensions.csv"):
        ids = r["stage_ids"].split()
        if ids:
            out.setdefault(r["route"].strip(), []).append(
                (r["after_stage"].strip(), ids, (r.get("road") or "").strip()))
    return out


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_road(slug: str):
    """Ordered [(lat, lon), ...] centreline written by tools/osm_road.py."""
    path = os.path.join(SOURCES_DIR, f"road_{slug}.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["sequence"]))
    return [(float(r["lat"]), float(r["lon"])) for r in rows]


def road_between(road, start, end):
    """The slice of `road` running from the point nearest start to nearest end."""
    if len(road) < 2:
        return []
    i = min(range(len(road)), key=lambda k: _haversine_km(*start, *road[k]))
    j = min(range(len(road)), key=lambda k: _haversine_km(*end, *road[k]))
    if i == j:
        return []
    return road[i:j + 1] if i < j else road[j:i + 1][::-1]


def load_terminals():
    """route number -> [{name, lat, lon, saccos[]}, ...]"""
    out = {}
    for r in _read("terminals.csv"):
        out.setdefault(r["route"].strip(), []).append({
            "name": r["terminal"].strip(),
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "saccos": [s.strip() for s in r["saccos"].split("|") if s.strip()],
        })
    return out


def load_route_operators():
    """route number -> [sacco, ...], unverified — see data/corrections/README
    or datacleaning/README.md for where this comes from. Never a substitute
    for a rider-confirmed terminals.csv row; the app treats it as a guess.
    """
    out = {}
    for r in _read("route_operators.csv"):
        saccos = [s.strip() for s in r["saccos"].split("|") if s.strip()]
        if saccos:
            out[r["route"].strip()] = saccos
    return out


def load_route_numbers():
    """surveyed number -> number a passenger would look for."""
    return {r["number"].strip(): r["display_as"].strip()
            for r in _read("routes.csv") if r.get("display_as", "").strip()}


def tidy_number(number: str) -> str:
    """Drop a surveyor's variant suffix from a route number.

    The survey distinguished variants of one service by appending a code:
    19C became 19Cdc, 19Cjk and 19C2 for its Donholm, Jacaranda and second
    variants. None of that is painted on the matatu, so telling someone to
    board "19Cdc" sends them looking for a vehicle that does not exist.

    Only lowercase suffixes are stripped, because matatu numbers are never
    lowercase, so that transformation is safe. Uppercase codes like 04SK or
    33GTB are genuinely ambiguous - the letter may be part of the real number
    - and are left alone for a human to resolve in routes.csv.
    """
    m = re.match(r"^(\d{1,3}[A-Z]?)[a-z]+\d*$", number)
    return m.group(1) if m else number


def _terminal_stage_id(number: str, name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")
    return f"term_{number.replace('/', '_')}_{slug}"


def apply(stage_rows, route_rows, path_rows, shape_rows, numbers_by_route_id):
    """Fold corrections into the rows extract.py is about to write.

    Returns (stage_rows, path_rows, shape_rows, notes). Rows are the same
    shape extract.py builds.
    """
    extra_stages = load_stages()
    extensions = load_extensions()
    terminals = load_terminals()
    overrides = load_route_numbers()
    notes = []

    # Give every route a number a passenger could actually look for.
    renamed = []
    for row in route_rows:
        surveyed = row[1]
        display = overrides.get(surveyed) or tidy_number(surveyed)
        if display != surveyed:
            renamed.append(f"{surveyed}->{display}")
            row[1] = display
    if renamed:
        notes.append(f"  + route numbers tidied: {', '.join(sorted(renamed))}")

    known = {r[0] for r in stage_rows}
    for sid, (name, lat, lon) in extra_stages.items():
        if sid not in known:
            stage_rows.append([sid, name, f"{lat:.6f}", f"{lon:.6f}"])
            known.add(sid)

    # Terminals are boarding points, not labels. The survey often records a
    # route as starting somewhere other than where it actually loads - 38/39
    # is recorded from Muthurwa, 864 m from where passengers really board -
    # and a terminus that far out falls outside the planner's shortlist, so
    # it invents a pointless hop to reach the route at all. Adding them as
    # stages at the town end makes boarding there work.
    for number, entries in terminals.items():
        for t in entries:
            sid = _terminal_stage_id(number, t["name"])
            if sid not in known:
                stage_rows.append([sid, t["name"], f"{t['lat']:.6f}", f"{t['lon']:.6f}"])
                known.add(sid)

    name_of = {r[0]: r[1] for r in stage_rows}
    route_id_of_number = {numbers_by_route_id[rid]: rid for rid in numbers_by_route_id}

    # regroup paths so we can rewrite a whole direction at a time
    by_path: dict[tuple[str, str], list[str]] = {}
    for route_id, direction, _seq, stage_id in path_rows:
        by_path.setdefault((route_id, direction), []).append(stage_id)

    coords = {r[0]: (float(r[2]), float(r[3])) for r in stage_rows}
    shape_by_path: dict[tuple[str, str], list] = {}
    for route_id, direction, _seq, lat, lon in shape_rows:
        shape_by_path.setdefault((route_id, direction), []).append((float(lat), float(lon)))

    for number, items in extensions.items():
        route_id = route_id_of_number.get(number)
        if not route_id:
            notes.append(f"  ! extension skipped: no route numbered {number}")
            continue
        for after_name, new_ids, road_slug in items:
            missing = [i for i in new_ids if i not in name_of]
            if missing:
                notes.append(f"  ! {number}: unknown stage ids {missing}")
                continue

            out_ids = by_path.get((route_id, "out"))
            if out_ids is None:
                notes.append(f"  ! {number}: no outbound direction to extend")
                continue
            tail = [name_of.get(s, "") for s in out_ids]
            if after_name and after_name not in tail:
                notes.append(f"  ! {number}: '{after_name}' not on the outbound route")
                continue
            cut = tail.index(after_name) + 1 if after_name else len(out_ids)
            by_path[(route_id, "out")] = out_ids[:cut] + new_ids

            # The matatu returns the same way, so the inbound order is the
            # extension reversed, in front of whatever it already had.
            in_ids = by_path.get((route_id, "in"))
            if in_ids is not None:
                in_names = [name_of.get(s, "") for s in in_ids]
                start = in_names.index(after_name) if after_name in in_names else 0
                by_path[(route_id, "in")] = list(reversed(new_ids)) + in_ids[start:]

            # Carry the drawn line out to the new terminus too, or the map
            # stops early and nothing past it is reachable on request.
            geom_note = ""
            road = load_road(road_slug) if road_slug else []
            out_shape = shape_by_path.get((route_id, "out"))
            if out_shape:
                anchor = coords.get(out_ids[cut - 1]) if cut else out_shape[-1]
                tail = []
                cursor = anchor
                for sid in new_ids:
                    target = coords[sid]
                    seg = road_between(road, cursor, target) if road else []
                    tail.extend(seg or [target])
                    cursor = target
                shape_by_path[(route_id, "out")] = out_shape + tail
                in_shape = shape_by_path.get((route_id, "in"))
                if in_shape is not None:
                    shape_by_path[(route_id, "in")] = list(reversed(tail)) + in_shape
                geom_note = (f", geometry +{len(tail)} pts via {road_slug}"
                             if road else f", geometry +{len(tail)} pts (straight)")

            notes.append(f"  + {number}: extended past {after_name or 'terminus'} "
                         f"to {name_of[new_ids[-1]]} (+{len(new_ids)} stages{geom_note})")

    for number, entries in terminals.items():
        route_id = route_id_of_number.get(number)
        if not route_id:
            notes.append(f"  ! terminals skipped: no route numbered {number}")
            continue
        ids = [_terminal_stage_id(number, t["name"]) for t in entries]
        out_ids = by_path.get((route_id, "out"))
        if out_ids is not None:
            by_path[(route_id, "out")] = [i for i in ids if i not in out_ids] + out_ids
        in_ids = by_path.get((route_id, "in"))
        if in_ids is not None:
            by_path[(route_id, "in")] = in_ids + [i for i in reversed(ids) if i not in in_ids]
        notes.append(f"  + {number}: boards from "
                     + ", ".join(t["name"] for t in entries))

    rebuilt = []
    for (route_id, direction), ids in by_path.items():
        for i, sid in enumerate(ids):
            rebuilt.append([route_id, direction, i, sid])

    rebuilt_shapes = []
    for (route_id, direction), pts in shape_by_path.items():
        for i, (lat, lon) in enumerate(pts):
            rebuilt_shapes.append([route_id, direction, i, lat, lon])

    used = {sid for _, _, _, sid in rebuilt}
    stage_rows = [r for r in stage_rows if r[0] in used]
    return stage_rows, rebuilt, rebuilt_shapes, notes
