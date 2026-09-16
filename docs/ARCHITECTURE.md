# Matatu App — codebase walkthrough

A presenter's guide. Each section is roughly one slide: what the part does,
and the one decision in it worth defending.

---

## 1. The problem, in one slide

Nairobi's matatu network has no reliable public dataset. The best open one —
**Digital Matatus, 2015** — was collected by University of Nairobi students
riding every route with GPS phones. It is also what powers **Google Maps'**
Nairobi transit directions, ingested in 2015.

So Google and this app start from the same decade-old survey. The difference
has to come from somewhere else. That framing drives every decision below.

---

## 2. Shape of the system

```
   phone (React Native)  ──HTTP──▶  backend (Flask)  ──reads──▶  data/network/*.csv
        Mapbox draws                 plans the trip              2,481 stages
        the map                      searches places             134 routes
                                          │
                                          └──▶ Photon (OpenStreetMap) for place search
```

No database. The whole network loads into memory at startup in ~0.1 s and
plans a trip in ~200 ms. At 2,481 stages that is not a compromise, and a
database would buy nothing yet.

---

## 3. `backend/` — three directories, three jobs

```
app/     the running service    — never writes data
tools/   the data pipeline      — never imported by the app
data/    the data itself
```

**The decision worth defending:** the pipeline is not part of the
application. `tools/` builds `data/network/`; `app/` only ever reads it.
They share nothing but the file format, so the data can be rebuilt, replaced,
or hand-corrected without touching a line of service code.

---

## 4. `app/` — four files

| File | Job |
|---|---|
| `main.py` | Flask endpoints: `/search`, `/plan`, `/routes`, `/health` |
| `feed.py` | Loads the network into memory |
| `routing.py` | Plans the trip |
| `geocoding.py` | Place search via Photon |

---

## 5. The data model, and why it isn't GTFS

GTFS is the transit standard, and the source feed is GTFS. What we store is
not, because **GTFS assumes a timetable** — departure times, service
calendars, headways — and matatus have none. They leave when full and run
around the clock.

Carrying GTFS meant writing `agency.txt`, `calendar.txt` and
`frequencies.txt` that nothing ever read, plus a `stop_times.txt` holding no
times at all — only the order of stages. The filenames promised a schedule
that does not exist.

What a matatu route actually is:

```
stages.csv      stage_id, name, lat, lon
routes.csv      route_id, number, description, outbound_to, inbound_to, corridor
paths.csv       route_id, direction, sequence, stage_id
shapes.csv      route_id, direction, sequence, lat, lon
terminals.csv   route_id, number, name, lat, lon, saccos
```

Eight files became five, all of them read. `direction` is `out` or `in`, kept
separate because **131 of 134 routes list different stages each way** — mostly
one-way CBD streets.

---

## 6. How a trip gets planned

Two coordinates in, an itinerary out. Four steps, all in `routing.py`:

1. **Nearest stages** at each end — but *grouped*, not deduplicated
2. **Matatus serving both**, in the right direction — plus one-change options
3. **Score** every option in estimated minutes
4. **Return** the itinerary, with the road path sliced from `shapes.csv`

### The scoring formula

```
minutes = walking_km × 13  +  ride_km × 3  +  changes × 7
```

Every term is there because leaving it out produced a specific wrong answer.
These are the good stories for a technical audience — each is a real bug with
a real journey attached:

**Ride time is per kilometre, not per stage.** Costing it per stage punished
being carried closer: alighting three closely-spaced stages further on scored
7.5 minutes of extra riding, which lost to a 530 m walk. The planner kept
telling people to get off early and walk.

**Nearby stages are grouped, never dropped.** The survey stores one record per
route through a place. Ungrouped, the shortlist fills with repeats — near
Ruiru the eight closest records were four places listed twice, all on one
feeder route, hiding the trunk stages 237 and 145 use. But the records at a
place are *not* interchangeable: at Juja, `Juja Stage` and `Jkuat` sit 80 m
apart and only `Jkuat` is on the inbound trip. Keeping only the closest left
a passenger heading to town walking 1.4 km to the next usable stage.

**Changes are always evaluated, never a fallback.** A direct matatu that
drops you 3 km from the door is worse than changing once.

**There is no fare in the formula.** An earlier version ranked partly on a
"fare proxy" — the number of stages on the whole route, standing in for the
terminus a matatu is priced to. It was an inference presented as a number, so
it was removed. Nothing in this app claims to know what a trip costs.

---

## 7. Alighting on request

The survey recorded far fewer stages than exist. Kahawa Wendani has no stage
record, yet route 237 drives straight through it.

Matatus stop on request — you tell the conductor the place. So the planner
asks *"does a route pass here"*, not *"is there a stage record here"*. If a
route's path comes within 250 m, a stop is spliced into that route's stage
order at the right position and everything downstream treats it normally.

Kahawa Wendani went from *"alight at Kahawa, walk 530 m"* to *"alight at
Kahawa Wendani"* — and the app labels it **tell the conductor**.

---

## 8. `tools/` — the data pipeline

```
python3 tools/build.py            # offline, seconds
python3 tools/build.py --network  # also refresh from OpenStreetMap
```

| Script | Does |
|---|---|
| `extract.py` | source survey → `data/network/` |
| `corridors.py` | assigns corridor labels from geometry |
| `corrections.py` | applies hand corrections on top |
| `osm_geometry.py` | swaps route lines for current OpenStreetMap ones |
| `osm_road.py` | pulls a named road's centreline |
| `osm_stages.py` | pulls OSM's own stage list |
| `export.py` | human-readable CSVs for checking |

### Corridors are derived, not listed

A corridor is defined by a **trunk route** — 237 for Thika Road, 120 for
Kiambu Road, 38/39 for Kangundo Road. A route joins if ≥5 of its stages sit
within 400 m of that trunk.

This replaced a hand-typed list of route ids, written from a printed map
before the survey was available and never revisited. It had quietly dropped
routes 25 (Baba Dogo), 25A (Lucky Summer), 29/30 and 43 into a leftover
bucket despite all four running up Thika Road.

Adding a corridor is now one line naming its trunk. You never enumerate
members.

---

## 9. Where the geometry comes from

Stage names, order and direction: **Digital Matatus, 2015**.
Route lines: **OpenStreetMap, 2026** — actively maintained, most of the
network edited this year.

The two are combined because OSM's Nairobi route relations contain **only
ways and zero stop members** — 1,521 members across our corridor, not one of
them a stop. So OSM has the better line and the survey has the only stages.

246 of 268 route directions now use OSM geometry. Route 237 went from 129
points to 1,144.

**Why not just ask a directions API?** Because it invents detours no matatu
takes. Mapbox has no transit profile at all, and a driving route between two
stages weaves off the highway into estates and back — a Nairobi→Juja trip
appeared to detour through Kiambu.

---

## 10. `data/corrections/` — the actual asset

Everything above is public data anyone can download. This directory is not.

```
stages.csv      stages the survey never recorded
extensions.csv  stages past a route's surveyed terminus
terminals.csv   where a route boards in town, and the saccos there
routes.csv      the number actually painted on the matatu
```

`extract.py` rebuilds `data/network/` from scratch every run, so hand edits
there vanish. Corrections are applied *after* the survey loads, so they
survive.

**Worked example — route 38/39, Kangundo Road.** From one rider:

- It runs to **Joska**, 11 km past where the survey stopped. Twelve stages
  added, geometry extended along the real road.
- It boards from **two** town terminals — Bus Station (Super Metro, City
  Shuttle) and Temple Road (Obamana, EBTI, Forward Travellers, Kubamba, KMO).

That second fact fixed a **bug**, not just a label. The survey records 38/39
starting at Muthurwa, 864 m from where passengers actually board — far enough
to fall outside the planner's shortlist, so it invented a pointless hop on
another matatu just to reach the route. With the real terminals it is
directly boardable.

---

## 11. `mobile/` — React Native

```
src/theme.ts                    colour, type, spacing, per-route colours
src/api.ts                      the only place that talks to the backend
src/MapScreen.tsx               orchestrates
src/components/SearchPanel.tsx  origin + destination
src/components/BottomSheet.tsx  draggable sheet
src/components/Itinerary.tsx    the journey
```

**The sacco is the headline, not the route number.** Riders identify a matatu
by the sacco painted on it — most people could not tell you the number of a
matatu they take daily. So "Super Metro · City Shuttle" is set at 19px and
`38/39` is a small chip beside it. Where no sacco is known it falls back to
*"Matatu towards Joska"*.

**Detail is folded away.** A 43-stage journey with eight saccos is all true
and all available, but showing it at once buries the one sentence the rider
needs. The sheet's three heights are the disclosure mechanism: collapsed
shows the answer, half shows the steps, full shows everything.

**The sheet uses core `Animated` + `PanResponder`**, not `reanimated` or
`gesture-handler`, because both are native modules and either would force a
fresh `expo prebuild`. This screen needed a sheet, not a gesture framework.

---

## 12. Honest limitations

Worth saying out loud before someone asks:

- **The survey is from 2015.** Nairobi County's December 2024 gazette revoked
  the 2017 route network and introduced 89 new routes. Every route should be
  treated as provisional until ground-checked.
- **One change maximum.** Journeys needing two changes (Karen → Westlands)
  don't resolve. That needs a real graph search — RAPTOR or OpenTripPlanner —
  which would change one file, because the data underneath stays valid.
- **8 route numbers on Kangundo Road are survey-internal** (`04SK`, `1961Kd`)
  and would send someone looking for a matatu that doesn't exist. Listed in
  `data/corrections/README.md`, deliberately not guessed at.
- **1 of 134 routes has saccos.** The redesign makes that gap visible rather
  than hiding it behind a route number.
- **No fares.** Not modelled, not estimated, not claimed.

---

## 13. The argument

Google has the same 2015 data. What it does not have, and cannot get, is a
rider who knows route 44 goes to Kahawa West rather than Kenyatta University,
that 17B and 49 now run as one service, and that 38/39 loads at Temple Road
under six different saccos.

The corrections layer is the product. Everything else is plumbing built so
that knowledge has somewhere to live and survives every rebuild.
