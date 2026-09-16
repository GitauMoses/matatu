# Research — for verification, not for use

**Nothing in this folder is loaded by the app.** These are candidates gathered
from public sources so they can be checked against reality before anything is
written into `data/corrections/`.

Every previous sacco and terminal in this project came from a rider. Web
sources for this are thin, inconsistent, and mostly do not link a sacco to a
route to a terminal — which is exactly the trio you need. So treat the whole
file as a starting point for questions, not as answers.

## saccos_to_verify.csv

| Column | Meaning |
|---|---|
| `route`, `corridor`, `destination` | which service this row is about |
| `proposed_terminal` + coords | where a source claims it boards in town |
| `proposed_saccos` | operators a source claims run it, `\|` separated |
| `confidence` | see below |
| `source` | where the claim came from |
| `VERDICT` | **you fill this in** — `OK`, `WRONG`, or a correction |
| `your_notes` | anything else |

### Confidence

- **CONFIRMED** (6 rows) — from you, already live in the app. Left in as a reference for what a good row looks like.
- **medium** (8) — a source names the sacco *and* the corridor, but not always the exact terminal.
- **low** (10) — one weak source, or the sacco is inferred from a corridor list rather than stated for that route.
- **unknown** (4) — nothing found. Listed so the gap is visible.

## What the sources actually support

**Railways Terminus is the hub for the whole southern and western side** —
Ngong, Karen, Rongai, Kiserian, Kitengela, Kikuyu, Kawangware, Kibera. That
matches the survey, which starts routes 2, 8, 102, 111, 125 and 126 there.
Sources also mention Kencom and Afya Centre as additional boarding points for
some of these, which the app does not know about.

**Sacco-to-corridor claims found:**

| Sacco | Claimed to serve |
|---|---|
| Super Metro | Kikuyu, Rongai, Ngong, Kitengela, Limuru, Wangige, Kinoo |
| Metro Trans | Kitengela, Kiserian, Rongai, Ngong, Athi River |
| Zuri | Rongai, Langata, Kiserian |
| MOA | Ngong Road corridor — Ngong, Kiserian, Karen, Dagoretti |
| Embassava | Umoja, Kayole, Donholm, Ruai, Njiru — Tea Room and OTC |
| Forward Travellers | Thika, Juja, Ruiru, Githurai |
| Double M | Thika Road — Ruiru, Juja, Githurai |

None of these sources give a sacco-plus-terminal pairing for a specific route
number, which is the level the app needs.

## Worth knowing: Green Park Terminus

Green Park was built at Uhuru Park specifically to replace Railways for the
Ngong Road and Langata Road routes — Ngong, Karen, Rongai, Kikuyu, Dagoretti,
Kawangware, Kibra, Langata, Nairobi West, Kiserian.

**It has not taken over.** Reporting from August 2026 describes it as deserted,
with those matatus still operating from Railways. So the app's current data is
right — but this is the single change most likely to invalidate every southern
route at once, and worth asking about when you verify.

## When a row is verified

Move it into `data/corrections/terminals.csv` in that file's format, then
rebuild:

```
python3 tools/extract.py
```

Delete or mark the row here so it is clear what has been through verification.

## Sources

- [pulse.co.ke — matatu stages after the CBD ban](https://www.pulse.co.ke/story/location-of-the-new-matatu-stages-after-nairobi-cbd-ban-2024081618115963437)
- [nai254 — SACCOs and their routes](https://nai254.com/2026/04/24/list-of-saccos-in-kenya-and-their-routes/)
- [nairobipostalcodes.org — Nairobi matatu routes](https://nairobipostalcodes.org/nairobi-matatu-routes/)
- [nairobileo — Super Metro Rongai route](https://nairobileo.co.ke/news/article/26585/super-metro-announces-new-route-to-rongai)
- [Nation — Green Park opens](https://nation.africa/kenya/counties/nairobi/no-more-railways-stage-as-nairobi-green-park-terminus-open-its-gates-to-matatus-3819264)
- [Nation — the Sh250m stage no one wants](https://nation.africa/kenya/counties/nairobi/green-park-the-sh250-million-matatu-stage-no-one-wants-4155986)

---

# Reported by rider, Sep 2026 — needs detail before it can be added

Both came from a real journey (Kayole Junction → Juja) where the app gave a
poor answer. Neither exists in any dataset we hold.

## 1. Lopha has a Thika stage at Kariobangi Roundabout

Rider: *"take a number 38 at Junction to Kariobangi Rounda stage, then take a
Lopha at Rounda — they have a stage there that goes to Thika, so I alight at
Juja."*

We hold Lopha at Odeon (route 237) and Archives (route 145). A third Lopha
terminal at Kariobangi Roundabout serving Thika is not recorded anywhere.

Checked: the stages within 1 km of Kariobangi Roundabout serve only local
routes — 26, 36, 42, 16/62, 18C, 32D, 41, 14, 2030, 23KS. Nothing Thika-bound.

**Needed to add it:** the exact stage location at the roundabout, and whether
this is route 237 loading from a third point or a separate service.

## 2. A Thika-bound service passes through Ruai

Rider: *"walk to Kayole Junction stage, take a car towards Kamulu, alight at
Ruai, then take a matatu that goes towards Thika — I alight at Juja."*

Checked: **no route in the network serves both Ruai and anywhere on Thika
Road.** Zero. This is presumably an Eastern Bypass link.

This matters well beyond one journey. Without it, everything on Kangundo Road
is forced through the city centre to reach Thika Road — which is why
Kamulu → Juja currently returns 197 minutes.

**Needed to add it:** the route number, its termini, and the stages between
Ruai and Thika Road. Geometry can come from the Eastern Bypass via
`tools/osm_road.py` once the stages are known.
