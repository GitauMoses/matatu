"""
Place search, via Photon (photon.komoot.io) - an OpenStreetMap-backed
geocoder built for type-ahead.

Why not Mapbox, given we already use it for map tiles: its Kenyan POI
coverage is thin. "Sarit Centre", "Thika Road Mall" and "Garden City Mall"
all return nothing usable, and its geocoding bbox filter drops even
"Westlands". OSM has dense Nairobi coverage (it's what the Digital Matatus
survey itself was built against), and Photon serves it with autocomplete
semantics. Nominatim has the same data but its usage policy discourages
per-keystroke querying.

This runs server-side rather than in the app so there's one identifiable
client for rate-limiting, and so results can be paired with the nearest
matatu stage before they reach the phone.
"""
import json
import urllib.parse
import urllib.request

PHOTON_URL = "https://photon.komoot.io/api/"

# Nairobi metro, generous margin around the corridors we hold data for.
BBOX = "36.55,-1.50,37.25,-0.90"
CENTRE_LAT, CENTRE_LON = -1.2921, 36.8219

USER_AGENT = "matatu-app/0.1 (+https://github.com/GitauMoses)"

# OSM types that aren't useful destinations for a commuter.
SKIP_TYPES = {"country", "state"}


def _label(props: dict) -> tuple[str, str]:
    """(name, context) for display."""
    name = props.get("name") or props.get("street") or "Unnamed place"
    bits = [
        props.get("street") if props.get("street") != name else None,
        props.get("district"),
        props.get("city") or props.get("county"),
    ]
    context = ", ".join(b for b in bits if b)
    return name, context


def search_places(query: str, limit: int = 8,
                  near: tuple[float, float] | None = None) -> list[dict]:
    q = (query or "").strip()
    if len(q) < 2:
        return []

    lat, lon = near if near else (CENTRE_LAT, CENTRE_LON)
    params = {
        "q": q,
        "lat": lat,
        "lon": lon,
        "limit": limit,
        "bbox": BBOX,
        "lang": "en",
    }
    url = PHOTON_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        # Caller still returns any matching stage names, so search degrades
        # rather than dying when Photon is unreachable.
        return []

    out = []
    seen = set()
    for f in data.get("features", []):
        props = f.get("properties", {})
        if props.get("osm_value") in SKIP_TYPES:
            continue
        coords = f.get("geometry", {}).get("coordinates")
        if not coords:
            continue
        name, context = _label(props)
        key = (name.lower(), round(coords[1], 4), round(coords[0], 4))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "id": f"osm:{props.get('osm_type','')}{props.get('osm_id','')}",
            "name": name,
            "context": context,
            "lat": coords[1],
            "lon": coords[0],
            "source": "place",
        })
    return out
