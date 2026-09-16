# datacleaning

Turns the NTSA PTO registry (`~/Downloads/Registered NMA PTOS and their Routes
of Operation .xlsx`) into sacco candidates per route number, and surfaces
place names the registry mentions that aren't in our stage network at all —
possible missing hubs like a corridor connection we haven't mapped. Nothing
in this folder is loaded by the app.

## Pipeline

```
python3 1_flatten_xlsx.py      # xlsx -> out/permits.csv (one row per permit)
python3 2_match_routes.py      # word-overlap match: permits -> route/sacco candidates
python3 3_find_hubs.py         # fuzzy-match every via-point against known stages; unmatched ones are hub candidates
python3 4_match_routes_ml.py   # fuzzy-match match: permits -> route/sacco candidates (independent of step 2)
```

Needs `rapidfuzz` (steps 3 & 4). Both live in `backend/.venv`.

### out/permits.csv

Every permit split out of the sacco's cell: `sacco, permit_no, via_raw,
via_points`. 1,574 of ~1,669 listed permits parsed cleanly (94%); the rest
had formatting the regex didn't catch (multiple permits run together on one
numbered line, mostly).

### out/route_sacco_candidates.csv and out/route_sacco_candidates_ml.csv

Two independent guesses at which sacco runs each of our 134 routes, same
output shape: `route, corridor, from_terminus, to_terminus, sacco,
permit_no, coverage, hits_of_total, via_raw, confidence, VERDICT`.

- **step 2** requires an exact word to match between a permit's via-points
  and the route's stage names. Found candidates for 90/134 routes.
- **step 4** does the same via-point-against-route check but with fuzzy
  string matching (edit distance) instead of exact words, so hand-typed
  spelling drift ("dagoreti" vs "dagoretti") doesn't break a real match.
  Found candidates for 130/134 routes.

  A first version of step 4 used TF-IDF + cosine similarity over whole
  route/permit text blobs — the more standard "ML" approach — but it scored
  everything low and missed matches step 2 had already confirmed. Whole-
  document similarity dilutes once both sides are long strings of mostly
  unrelated place names. Per-via-point fuzzy matching kept the structure
  that made step 2 work and fixed the spelling-drift blind spot instead.

**Where both files agree on a route/sacco pairing, that's the strongest
signal in the pipeline** — two different methods landing on the same
answer. `VERDICT` is blank in both for you to fill in (`OK`, `WRONG`, or a
correction), same pattern as `backend/data/research/`.

Confidence tiers (both files): **high** = coverage ≥ 0.80 and ≥ 3
via-points confirmed · **medium** ≥ 0.65 · **low** ≥ 0.50 (the cutoff).

### out/hub_candidates.csv

Every via-point across all 1,574 permits that doesn't fuzzy-match any known
stage name or alias, ranked by how many different corridors it shows up
alongside (a place mentioned in the same permit as stages from two
unconnected corridors is exactly what a missing cross-corridor link looks
like from the outside) and how many separate permits mention it.

Columns: `via_point, mentions, sacco_count, num_corridors,
corridors_touched, sample_saccos, example_via_raw, example_permit, VERDICT`.

**This worked on the first run.** It independently rediscovered both gaps
you reported by riding, weeks before this pipeline existed:

| via_point | mentions | saccos |
|---|---|---|
| `ruai` | 46 | 20+ |
| `kariobangi` / `kariobangi round about` | 37 / 5 | many |

It also turned up others in the same area worth checking: `eastern bypass`
(21 mentions), `joska` (31), `malaa` (25), `kenol` (22) — these read like
the Kangundo Road / Eastern Bypass corridor extends further than we have
mapped, past Ruai.

**Caveat:** the top of the file is dominated by generic town names —
`nairobi`, `kikuyu`, `thika`, `kiserian` — that don't fuzzy-match because
our stages are specific locations ("Thika Makongeni Terminal"), not bare
town names. That's a matcher limitation, not a real gap; skip anything that's
just a town you already know we serve and look for specific landmarks/
junctions instead.

## Sanity checks

Route 38/39 already has verified data (`Forward Travellers` at Temple Road).
Both step 2 and step 4 independently surfaced `FORWARD TRAVELLERS SACCO
LTD` for route 38/39. Step 4 also found it for route 145.

**Known miss:** `Lopha` (verified for routes 237 and 145) does not appear
anywhere in the NTSA registry under that name — likely registered under a
different legal/PTO name than its street brand. Don't assume "not in the
registry" means "not real" — cross-check against `backend/data/research/`
and rider reports too.

## When a row is verified

Same as `backend/data/research/`: move it into
`backend/data/corrections/terminals.csv` (saccos) or wherever a new stage
belongs (`backend/data/corrections/stages.csv` / `extensions.csv` for a new
hub), then rebuild with `python3 tools/extract.py` from `backend/`. Nothing
in `datacleaning/` or `backend/data/research/` is read by the app.
