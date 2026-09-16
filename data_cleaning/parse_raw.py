import csv
import re
import openpyxl
from pathlib import Path
from config import EXCEL_PATH, OUTPUT_DIR, INTERCITY_INDICATORS

def split_routes_text(raw_text: str):
    """
    Split the multi-route cell content into individual route/permit strings.
    """
    if not raw_text:
        return []

    lines = raw_text.split("\n")
    entries = []
    current_entry = []

    # Regex to detect start of a route entry
    # e.g., '1.', '1  NTR-', 'ADR-', 'NTR-', '1 -'
    entry_start_pattern = re.compile(
        r"^(?:\d+[\.\)\-\s]+|\s*(?:NTR|ADR)[\-\s\d\w]+|\d+\s*(?:NTR|ADR))", 
        re.IGNORECASE
    )

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        
        # Check if line also has multiple permits separated by comma or semicolon inside the line
        sub_splits = re.split(r",\s*(?=(?:NTR|ADR)[\-\w]+)", line_clean)
        for part in sub_splits:
            part = part.strip()
            if not part:
                continue
            if entry_start_pattern.match(part) and current_entry:
                entries.append(" ".join(current_entry))
                current_entry = [part]
            else:
                current_entry.append(part)

    if current_entry:
        entries.append(" ".join(current_entry))

    results = []
    for entry in entries:
        # Extract permit ID cleanly
        m = re.search(r"\b(NTR|ADR)[\-\s_]*[0-9A-Za-z]+", entry, re.IGNORECASE)
        permit_id = m.group(0).strip() if m else ""
        
        text = entry
        if permit_id:
            idx = text.find(permit_id)
            text = text[idx + len(permit_id):]
            
        # Clean leading digits, punctuation, and spaces
        text = re.sub(r"^[\s\d\.\-\:\,\t\)]+", "", text).strip()
        text = re.sub(r"\s+", " ", text).strip()
        # Clean trailing commas/dashes
        text = re.sub(r"[\s,\-\.]+$", "", text).strip()
        
        if text:
            results.append({
                "permit_id": permit_id,
                "route_text": text
            })

    return results

def is_intercity(text: str) -> bool:
    text_lower = text.lower()
    for city in INTERCITY_INDICATORS:
        if re.search(r"\b" + re.escape(city) + r"\b", text_lower):
            # Special exceptions: 'Machakos country bus' is a CBD terminal in Nairobi
            if city == "machakos" and ("country bus" in text_lower or "bus station" in text_lower):
                continue
            return True
    return False

def parse_excel():
    print(f"Loading workbook from {EXCEL_PATH}...")
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    sheet = wb["LIST OF PTOS & ROUTES"]
    
    parsed_routes = []
    ptos_summary = []

    for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        sr_no, pto_no, pto_name, route_count, routes_raw = row[:5]
        if not pto_name:
            continue
            
        pto_no = str(pto_no).strip() if pto_no else f"UNKNOWN-{row_idx}"
        pto_name = str(pto_name).strip()
        routes_raw_str = str(routes_raw) if routes_raw else ""
        
        route_entries = split_routes_text(routes_raw_str)
        
        ptos_summary.append({
            "pto_no": pto_no,
            "pto_name": pto_name,
            "declared_routes": route_count,
            "parsed_routes_count": len(route_entries)
        })

        for r in route_entries:
            intercity = is_intercity(r["route_text"])
            parsed_routes.append({
                "pto_no": pto_no,
                "pto_name": pto_name,
                "permit_id": r["permit_id"],
                "route_text": r["route_text"],
                "is_intercity": intercity
            })

    # Save to CSV
    routes_csv_path = OUTPUT_DIR / "raw_parsed_routes.csv"
    with open(routes_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pto_no", "pto_name", "permit_id", "is_intercity", "route_text"])
        writer.writeheader()
        writer.writerows(parsed_routes)

    ptos_csv_path = OUTPUT_DIR / "ptos_summary.csv"
    with open(ptos_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pto_no", "pto_name", "declared_routes", "parsed_routes_count"])
        writer.writeheader()
        writer.writerows(ptos_summary)

    print(f"Extracted {len(ptos_summary)} PTOs and {len(parsed_routes)} total route permit entries.")
    print(f"Saved: {routes_csv_path}")
    print(f"Saved: {ptos_csv_path}")

if __name__ == "__main__":
    parse_excel()
