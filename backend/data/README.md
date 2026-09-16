# Data

Three directories, three jobs. Only one of them is ever edited by hand.

```
sources/      external inputs      hand-managed, never generated
corrections/  our own knowledge    hand-managed, applied on top of sources
network/      what the app loads   generated — rebuilt from scratch each run
views/        readable flattenings generated — nothing reads them back
```

## sources/

| File | What it is |
|---|---|
| `digital_matatus_2015.zip` | The surveyed feed — students rode every route with GPS phones. Stage names, order, direction and termini all come from here. |
| `osm_stages.csv` | Stage names fetched from OpenStreetMap (`tools/osm_stages.py`). Used to tag each surveyed stage with a nearby place name. |

Both are inputs. `osm_stages.csv` lived in the outputs folder for a while, which
was wrong — it is read by `export.py`, not written by it.

## network/

What `app/feed.py` loads. Four files, all of them read:

```
stages.csv   stage_id, name, lat, lon
routes.csv   route_id, number, description, outbound_to, inbound_to, corridor
paths.csv    route_id, direction, sequence, stage_id
shapes.csv   route_id, direction, sequence, lat, lon
```

**`tools/extract.py` deletes and rewrites this whole directory.** Editing a file
here is silently undone on the next build. See below.

## views/

`routes.csv` and `stages.csv`, the same network flattened into one row per thing
so it can be read in a spreadsheet — a route's whole stage list in a single
cell, a stage's serving routes in a single cell.

These are **derived**, not a second copy: they're a join of `routes.csv` and
`paths.csv` that no code reads back. Delete them and nothing breaks; run
`python3 tools/export.py` to bring them back.

## corrections/

Rider knowledge that contradicts or extends the 2015 survey — see
`corrections/README.md`. Applied by `extract.py` after the survey loads, so it
survives the rebuild that wipes `network/`.
