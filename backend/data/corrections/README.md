# Corrections

Knowledge that is **not** in any public dataset. This is the part of the
project that is ours rather than a copy of a decade-old survey — Google has
the same 2015 feed, it does not have this.

`tools/extract.py` wipes and rebuilds `data/network/` on every run, so hand
edits there are silently undone. These files are applied *after* the survey is
loaded, so they survive.

## Files

**`stages.csv`** — stages the survey never recorded.
```
stage_id,name,lat,lon,source
kr_kamulu,Kamulu,-1.28262,37.06448,osm
```

**`extensions.csv`** — stages beyond a route's surveyed terminus. Applied to
the outbound order and mirrored in reverse onto the inbound, since the matatu
returns the same way. The route's advertised terminus updates automatically.
```
route,after_stage,stage_ids,note
38/39,Quickmart,kr_ruai kr_block10 ... kr_kamulu,Runs to Kamulu; survey stopped at Ruai
```

**`terminals.csv`** — where a route boards in town, and which saccos run it
there. These become real stages at the town end of the route, not labels:
the survey often records a route starting somewhere other than where it
actually loads, and a terminus too far from the centre falls outside the
planner's candidate shortlist, which made it invent a hop just to reach the
route.
```
route,terminal,lat,lon,saccos
38/39,Temple Road,-1.2862321,36.8296266,Obamana|EBTI|Kubamba Ltd
```

## Recorded so far

All from a rider, Aug 2026.

**38/39 (Kangundo Road)** — extended past Ruai to Joska at the edge of the
metro area (12 stages, geometry followed along the real road), plus its two
town terminals: Bus Station (Super Metro, City Shuttle) and Temple Road
(Obamana, EBTI, Forward Travellers, Kubamba, KMO).

**237 (Thika Road, serving Juja and Thika)** — three separate town terminals,
which matters because which one you walk to decides which sacco you ride:

| Terminal | Saccos |
|---|---|
| Kenya National Archives | Super Metro, Latema, Enabled |
| Odeon Cinema | Lopha |
| Mfangano / Ronald Ngala | Nicco |

**145 (Ruiru)** — Kenya National Archives (Lopha). Lopha runs both this and
237, but from different terminals, so the same sacco appears twice with
different coordinates. That is correct, not a duplicate.

**Route numbers** — `19Cdc`/`19Cjk` → 19C and `17Aky` → 17A are fixed
automatically, because lowercase suffixes are never painted on a matatu.

## Waiting on rider data

### Kangundo Road route numbers
These carry survey-internal identifiers. Guesses in the last column are
**not** applied — a wrong number sends someone looking for a matatu that does
not exist. Fill `display_as` in `routes.csv` when known.

| Survey number | Route | Possibly |
|---|---|---|
| `04SK` | Ronald Ngala – Jogoo Rd – Kangundo Rd – Saika – Kayole Jct | ? |
| `1960` | OTC – Donholm – Kayole | 19/60 |
| `1961K` | Landhies Rd – Jogoo Rd – Jacaranda – Kayole | 19/61 |
| `19C2` | Donholm – Caltex – Komarocks | 19C |
| `33DP` | Muthurwa – Donholm – Pipeline | 33 |
| `33GTB` | Accra Rd – Jogoo Rd – Donholm – Fedha – Gate B | 33 |
| `3560_2` | Donholm – Mutindwa – Umoja 2 | 35/60 |
| `3738` | Rounda – Saika – Ruai | 37/38 |

### Terminals and saccos
Only 38/39 has them. The other 18 Kangundo Road routes have none — rider to
supply, same format as `terminals.csv`.

## Still unrecorded

These came from the same rider and have no correction file yet, because they
need a change/remove operation that isn't implemented:

- **44** goes to Kahawa West, not Kenyatta University as the survey and OSM both claim.
- **17B and 49** now run as one service (Kasarani → Sunton → Mwiki), not two.
- **Seasons** has a stage on Thika Road; the survey records only the two on Kasarani–Mwiki road.
