# Data pipeline

Scripts that **build** the data. Nothing here is imported by the running app —
`app/` only reads what these produce. Run them from `backend/`.

```
python3 tools/build.py            # extract + export (offline, seconds)
python3 tools/build.py --network  # also refresh from OpenStreetMap (slow)
```

| Script | Reads | Writes | Network |
|---|---|---|---|
| `extract.py` | `data/sources/digital_matatus_2015.zip` | `data/network/*.csv` | no |
| `osm_stages.py` | Overpass | `data/sources/osm_stages.csv` | yes |
| `osm_geometry.py` | Overpass + `data/network/` | `data/network/shapes.csv` | yes |
| `export.py` | `data/network/` | `data/views/routes.csv`, `stages.csv` | no |
| `corridors.py` | — | — | library, not a script |

## Corridors are a label, not a layout

A corridor is a **development marker** — it says "these routes have been
checked along a known trunk", so the data can be built out in phases. It is
not a user-facing idea and never reaches the API.

It used to be a folder split. That put 118 of 134 routes in a directory called
`nairobi`, which organised nothing while making every reader walk a corridor
loop. Now it is one column in `routes.csv`, blank for the 118.

`corridors.py` assigns the label by checking how much of a route's path runs
along that corridor's **trunk route** — 237 for Thika Road, 120 for Kiambu
Road. A route qualifies if at least 5 of its stages sit within 400 m of the
trunk and that's at least a quarter of its stages.

This replaced a hand-typed list of route ids, which was written from the printed
route map before the surveyed feed existed and then never revisited. It had
quietly dropped routes 25 (Baba Dogo), 25A (Lucky Summer), 29/30 (Mathare North)
and 43 (Ngumba) into the leftover bucket despite all four running up Thika Road.

The thresholds are tuned against measured overlap, and the absolute stage count
is doing most of the work — share alone can't tell a short feeder from a route
that merely crosses the corridor:

| | stages on Thika Rd trunk | share | in? |
|---|---|---|---|
| 237 | 36 | 1.00 | yes |
| 45K | 18 | 0.86 | yes |
| 25A (Lucky Summer) | 7 | 0.27 | yes |
| 25 (Baba Dogo) | 5 | 0.29 | yes |
| 145B | 3 | 0.27 | no — Ruiru feeder |
| 53 | 1 | 0.12 | no — branches at Roasters |
| 17B_2 | 0 | 0.00 | no — Kasarani–Mwiki road |

**Adding a corridor** means adding one line to `TRUNK_ROUTES` naming its trunk
route number, then re-running. You never enumerate members.

## Views

Generated for reading, not read back. See `data/README.md` for how the three
data directories differ.

`data/views/routes.csv` — one row per route: both termini, stage count, and
every stage in order, e.g.

```
25A  thika_road  25A Terminal -> Lucky Summer Terminal  26 stages
     25A Terminal > Koja > Ngara > Pangani > Muthaiga > ... > Lucky Summer Terminal
```

`data/views/stages.csv` — one row per distinct stage (1,258 of them): where it
is, which routes serve it, other names recorded at the same spot, and the
nearest OSM place name.

That last column matters. Surveyed stages are named after landmarks —
`Stadium`, `Naivas`, `Seasons` — not neighbourhoods, so searching "Kasarani"
matches no stage even though seventeen sit within 1.5 km of it.

## No timetable anywhere

The source is a transit-schedule feed; what `extract.py` writes is not.
Those formats are built around departure times, service calendars and
headways, and matatus have none — they leave when full and run around the
clock. Carrying that shape meant writing agency, calendar and frequency files
nothing read, and a "stop times" file holding no times, only the order of
stages. The names promised a timetable that does not exist.

What a matatu route actually is: a numbered service with an ordered list of
stages between two termini, ridden either way. Four files, all of them read:

```
stages.csv   stage_id, name, lat, lon
routes.csv   route_id, number, description, outbound_to, inbound_to, corridor
paths.csv    route_id, direction, sequence, stage_id
shapes.csv   route_id, direction, sequence, lat, lon
```

`direction` is `out` (away from town) or `in`. Both are stored because they
genuinely differ — 131 of 134 routes list different stages each way, mostly
because CBD streets are one-way.

Nothing time-based is stored or shown. The planner does estimate minutes to
rank options against each other, but that estimate is never presented as an
arrival time.
