# Matatu App (Nairobi transit) — MVP

Helps a commuter answer: **which stage do I go to, which matatu do I board, where do I get off.**

Routing and transit data come from **Google Maps Directions API** in transit
mode. Place search comes from **Photon** (OpenStreetMap).

## Why Google for routing

The hand-rolled planner that preceded this produced wrong answers repeatedly —
riding past a destination and doubling back, preferring a 3 km walk over a
change, hiding the only usable boarding stage. Google's transit engine handles
multi-change journeys, walking networks and route choice properly.

Worth knowing: **Google's Nairobi transit data is the Digital Matatus 2015
survey**, which Google ingested in 2015. So the underlying data is the same
vintage as the feed still vendored at
`backend/app/data/sources/digital_matatus_2015.zip` — what Google adds is the
routing, not fresher data.

### Two constraints from Google's terms

These shape the architecture and are not optional:

- **Results may not be cached or stored.** `google_directions.py` proxies live
  on every request and writes nothing. Don't add a cache there.
- **Results may not be shown on a non-Google map.** This is why the app uses
  `react-native-maps` on the Google provider rather than Mapbox, and why plans
  can't be merged with our own route data and re-displayed.

That second one matters for the roadmap: layering your own surveyed matatu data
on top of Google's results is not permitted. When that becomes the point of the
product, routing has to move back in-house — see "Own data" below.

## Setup

### Backend (Python / Flask)
```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add GOOGLE_MAPS_API_KEY
python3 -m app.main
```
Serves on `0.0.0.0:8123`. Endpoints: `/health`, `/search?q=`,
`/plan?origin_lat=&origin_lon=&dest_lat=&dest_lon=`

The Directions key stays server-side so it never ships in the app bundle.

### Mobile (React Native / Expo)
```
cd mobile
cp .env.example .env        # EXPO_PUBLIC_API_URL = laptop LAN IP, not localhost
npm install
export GOOGLE_MAPS_ANDROID_KEY=<android sdk key>
npx expo prebuild
npx expo run:android
```
Won't run in Expo Go — `react-native-maps` has native code.

Build environment notes (wiped by `expo prebuild --clean`):
`android/local.properties` needs `sdk.dir`, and Gradle needs JDK 21 via
`org.gradle.java.home` — the system default JDK 25 fails the native/CMake step.

## Google Cloud keys

Two separate keys, both from the same project:

| Key | Where | Enable |
|---|---|---|
| `GOOGLE_MAPS_API_KEY` | `backend/.env` | Directions API |
| `GOOGLE_MAPS_ANDROID_KEY` | shell env at build time | Maps SDK for Android |

Billing must be enabled on the Cloud project — the free tier covers MVP
traffic, but the APIs return `REQUEST_DENIED` without a billing account.

## Place search
`/search` uses Photon (OpenStreetMap), not Google Places. OSM has dense Nairobi
POI coverage — Sarit Centre, Thika Road Mall, Garden City all resolve, where
Mapbox returned nothing usable. It is also free, and unlike Google Places
results these can be stored and displayed anywhere.

## Own data (retained, not currently used for routing)

`backend/app/data/` still holds the full pipeline built before the switch:

- `sources/digital_matatus_2015.zip` — the original survey (134 routes, 2,481
  GPS-recorded stages)
- `extract_corridor.py` — slices it into per-corridor GTFS feeds
- `osm_shapes.py` — overwrites route geometry with current OpenStreetMap traces
  (OSM's Nairobi bus relations are actively maintained; most were edited in 2026)

This is the basis for moving routing back in-house once there is proprietary
route data worth routing on. Rider corrections gathered so far, unresolved
against the 2015 data:

| Route | 2015 feed says | Rider says |
|---|---|---|
| 44G / 44K | Githurai → KU | no Githurai–KU route; 44 goes to Kahawa West |
| 17B, 49 | separate routes | run combined as one (Kasarani → Sunton → Mwiki) |
| 45P | Githurai → Proggie | agrees |

Also recorded: there is **no Seasons stage on Thika Road** in the survey, though
one exists in reality — both surveyed Seasons stops sit on Kasarani–Mwiki road.

Data © OpenStreetMap contributors, ODbL, for anything derived from OSM.
