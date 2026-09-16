import csv
import re
from pathlib import Path
from config import OUTPUT_DIR

# Known canonical names for famous Saccos/operators to avoid over-stripping or awkward title-casing
KNOWN_SACCOS = {
    "SUPER METRO": "Super Metro",
    "KENYA BUS SERVICE": "KBS",
    "CITY HOPPA": "City Hoppa",
    "EMBASSAVA": "Embassava",
    "FORWARD TRAVELLERS": "Forward Travellers",
    "LOPHA": "Lopha",
    "COMPLIANT MOA": "Compliant",
    "METRO TRANS": "Metro Trans",
    "KASARANI 44": "Kasarani 44",
    "BURUBURU 58": "Buruburu 58",
    "BABA DOGO 25": "Baba Dogo 25",
    "2KR": "2KR",
    "2B": "2B",
    "8B": "8B",
    "2KW": "2KW",
    "DOUBLE M": "Double M",
    "LATEMA": "Latema Sacco",
    "UMOFINNER": "Umoinner",
    "UMOINNER": "Umoinner",
    "MEMBLEY": "Membley Sacco",
    "ROEN": "Roen",
    "ZURI": "Zuri Genesis",
    "NORTH RIFT": "North Rift",
}

def extract_route_hints(text: str):
    """
    Finds route number hints in a string like:
    'ROUTE 105', 'BURUBURU 58', 'BABA DOGO 25', 'ROUTE 44A', '38/39'
    """
    hints = []
    # Explicit 'ROUTE 105'
    m1 = re.findall(r"\bROUTE\s*([0-9]{1,3}[A-Za-z]?|[0-9]{2}/[0-9]{2})\b", text, re.IGNORECASE)
    hints.extend(m1)
    
    # Embedded numbers e.g. '58', '25', '105', '44', '110', '111', '125', '101'
    m2 = re.findall(r"\b([0-9]{1,3}[A-Za-z]?|[0-9]{2}/[0-9]{2})\b", text)
    for h in m2:
        # Ignore year-like numbers or single generic digits unless accompanied by letter
        if h in ["2015", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]:
            continue
        if len(h) >= 2 or (len(h) == 1 and h.isdigit() and h in ["1", "2", "5", "6", "7", "8"]):
            if h not in hints:
                hints.append(h)
    return hints

def clean_sacco_name(raw_name: str) -> tuple[str, list[str]]:
    """
    Cleans legal company name to commuter Sacco name, and returns any route hints.
    """
    raw_upper = raw_name.upper().strip()
    
    # Check known saccos map first
    for known_key, canonical in KNOWN_SACCOS.items():
        if known_key in raw_upper:
            hints = extract_route_hints(raw_upper)
            return canonical, hints

    # Patterns to strip
    fluff_patterns = [
        r"\bSAVINGS\s*(?:AND|&)\s*CREDIT\s*CO\-?OPERATIVE\s*SOCIETY\s*(?:LTD|LIMITED)?\b",
        r"\bMULTIPURPOSE\s*CO\-?OPERATIVE\s*SOCIETY\s*(?:LTD|LIMITED)?\b",
        r"\bCO\-?OPERATIVE\s*SOCIETY\s*(?:LTD|LIMITED)?\b",
        r"\bCO\-?OPERATIVE\s*SAVINGS\s*(?:AND|&)\s*CREDIT\s*SOCIETY\s*(?:LTD|LIMITED)?\b",
        r"\bSAVINGS\s*(?:AND|&)\s*CREDIT\s*SOCIETY\s*(?:LTD|LIMITED)?\b",
        r"\bCOMMUTER\s*SERVICE\b",
        r"\bMATATU\s*OWNERS?\b",
        r"\bTRAVELLERS\s*SACCO\s*(?:LTD|LIMITED)?\b",
        r"\bTRAVELLERS\s*(?:LTD|LIMITED)?\b",
        r"\bSACCO\s*(?:LTD|LIMITED)?\b",
        r"\bMANAGEMENT\s+LIMITED\b",
        r"\bSERVICES\s+LIMITED\b",
        r"\bTRANSPORTERS\s+LIMITED\b",
        r"\bLIMITED\b",
        r"\bLTD\b",
    ]

    cleaned = raw_upper
    for pat in fluff_patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    
    # Extract route number hints
    hints = extract_route_hints(raw_upper)

    # Format into nice title case if not empty
    if not cleaned:
        cleaned = raw_name.strip()
    else:
        # Title case, keeping acronyms like 2KR, 2KW, 2B, 8B
        words = cleaned.split(" ")
        formatted_words = []
        for w in words:
            if re.match(r"^\d+[A-Z]+$", w) or len(w) <= 3 and w.isalpha():
                formatted_words.append(w.upper())
            else:
                formatted_words.append(w.capitalize())
        cleaned = " ".join(formatted_words)

    return cleaned, hints

def normalize_all_ptos():
    ptos_in = OUTPUT_DIR / "ptos_summary.csv"
    routes_in = OUTPUT_DIR / "raw_parsed_routes.csv"
    
    ptos_out = OUTPUT_DIR / "normalized_ptos.csv"
    routes_out = OUTPUT_DIR / "normalized_routes.csv"

    pto_map = {}
    with open(ptos_in, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_name, hints = clean_sacco_name(row["pto_name"])
            pto_map[row["pto_no"]] = {
                "pto_no": row["pto_no"],
                "pto_name_raw": row["pto_name"],
                "sacco_clean": clean_name,
                "route_hints": ";".join(hints),
                "declared_routes": row["declared_routes"],
                "parsed_routes_count": row["parsed_routes_count"]
            }

    with open(ptos_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=["pto_no", "sacco_clean", "route_hints", "pto_name_raw", "declared_routes", "parsed_routes_count"]
        )
        writer.writeheader()
        writer.writerows(pto_map.values())

    normalized_routes = []
    with open(routes_in, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pto_info = pto_map.get(row["pto_no"], {})
            clean_sacco = pto_info.get("sacco_clean", row["pto_name"])
            sacco_hints = pto_info.get("route_hints", "")
            
            # Also check if the route text itself has route hints
            route_text_hints = extract_route_hints(row["route_text"])
            all_hints = list(set([h for h in sacco_hints.split(";") if h] + route_text_hints))

            normalized_routes.append({
                "pto_no": row["pto_no"],
                "sacco": clean_sacco,
                "permit_id": row["permit_id"],
                "route_hints": ";".join(all_hints),
                "is_intercity": row["is_intercity"],
                "route_text": row["route_text"],
                "pto_name_raw": row["pto_name"]
            })

    with open(routes_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["pto_no", "sacco", "permit_id", "route_hints", "is_intercity", "route_text", "pto_name_raw"]
        )
        writer.writeheader()
        writer.writerows(normalized_routes)

    print(f"Normalized {len(pto_map)} PTOs -> {ptos_out}")
    print(f"Normalized {len(normalized_routes)} Route Permits -> {routes_out}")

if __name__ == "__main__":
    normalize_all_ptos()
