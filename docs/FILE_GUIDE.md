# File guide

What each part does. One statement per file.

---

## The two halves

**`backend/`** — holds the matatu data and answers two questions: *what place
do you mean?* and *which matatu do I take?*

**`mobile/`** — the phone app. Draws the map, takes the two locations, shows
the answer.

They communicate over HTTP. The phone holds no matatu data.

---

# backend/

## backend/app/ — the service

Runs continuously. Loads all the data into memory at startup and answers
requests.

**`main.py`** — the API. Defines four endpoints:
- `/search` — text in, matching places out
- `/plan` — two coordinates in, an itinerary out
- `/routes` — lists every route
- `/health` — confirms the service is up and how much data it loaded

**`routing.py`** — plans the journey. Takes a start and an end coordinate and
returns which matatu to board, where to board it, where to get off, and how
long it takes. Ranks the options by estimated minutes.

**`feed.py`** — loads the data. Reads the five CSVs in `data/network/` into
memory when the service starts.

**`geocoding.py`** — turns typed text into coordinates. Asks Photon
(OpenStreetMap) for places matching what the user typed.

**`paths.py`** — holds the file locations every other file uses.

---

## backend/tools/ — the data pipeline

Run by hand when data changes. Builds the files the service reads.

```
python3 tools/build.py
```

**`build.py`** — runs the whole pipeline in order.

**`extract.py`** — reads the 2015 survey and writes `data/network/`. This is
what produces the data the service loads.

**`corrections.py`** — applies the hand-written corrections in
`data/corrections/` on top of the survey.

**`corridors.py`** — labels each route with the corridor it runs along, by
measuring how much of its path follows a trunk route.

**`osm_geometry.py`** — fetches current route lines from OpenStreetMap and
writes them into `shapes.csv`.

**`osm_road.py`** — fetches a named road's centreline, used when a route is
extended past where the survey ended.

**`osm_stages.py`** — fetches OpenStreetMap's own list of stage names.

**`export.py`** — writes `data/views/`, human-readable CSVs for checking the
data by eye.

---

## backend/data/ — the data

**`sources/`** — the raw inputs.
- `digital_matatus_2015.zip` — the survey: students rode every route with GPS phones
- `osm_stages.csv` — 494 stage names from OpenStreetMap
- `road_kangundo_road.csv` — Kangundo Road centreline

**`corrections/`** — rider knowledge, written by hand.
- `stages.csv` — stages that exist but the survey missed
- `extensions.csv` — stages past where a route was surveyed to
- `terminals.csv` — where a route boards in town, and the saccos there
- `routes.csv` — the number painted on the matatu

**`network/`** — what the service loads. Five files:

| File | Holds | Rows |
|---|---|---|
| `stages.csv` | every stage and its coordinates | 2,485 |
| `routes.csv` | every route, its number and termini | 134 |
| `paths.csv` | the stages each route passes, in order | 6,265 |
| `shapes.csv` | the line each route draws on the map | 23,349 |
| `terminals.csv` | town terminals and their saccos | 6 |

**`views/`** — the same data flattened for reading in a spreadsheet.

---

# mobile/

**`App.tsx`** — entry point. Renders the map screen.

**`src/api.ts`** — talks to the backend. Two functions: `searchPlaces` and
`planTrip`.

**`src/theme.ts`** — the colours, text sizes and spacing every component uses.

**`src/MapScreen.tsx`** — the screen. Holds the state, draws the Mapbox map,
and connects the three components below.

**`src/components/SearchPanel.tsx`** — the two location fields and the
suggestion list beneath them.

**`src/components/BottomSheet.tsx`** — the draggable panel over the map. Three
heights: collapsed, half, full.

**`src/components/Itinerary.tsx`** — the journey, step by step: walk, board,
ride, get off.

---

## How one trip flows through

1. User types in **`SearchPanel`**
2. **`api.ts`** calls `/search`
3. **`main.py`** asks **`geocoding.py`** for places and checks its own stage list
4. User picks one — now there are coordinates
5. **`api.ts`** calls `/plan`
6. **`routing.py`** reads the network loaded by **`feed.py`** and builds the itinerary
7. **`MapScreen`** draws the line, **`Itinerary`** lists the steps

---

## Four sentences

**`app/`** answers requests.
**`tools/`** builds the data.
**`data/network/`** is what gets answered from.
**`data/corrections/`** is the knowledge that isn't in any public dataset.
