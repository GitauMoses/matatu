# Data Cleaning & Route Mapping Pipeline

This folder contains the Python data pipeline for extracting, cleaning, and mapping official NTSA Public Transport Operator (PTO) data from the Excel spreadsheet into the Matatu app route network.

## Source Data
- File: `/home/gitau/Downloads/Registered NMA PTOS and their Routes of Operation .xlsx`
- Sheet: `LIST OF PTOS & ROUTES`
- 228 Registered PTOs and 1,658 authorized route permit entries.

---

## Pipeline Overview

```
Registered NMA PTOS .xlsx
         │
         ▼
 1. parse_raw.py
    Extracts 228 PTOs & splits messy text into 1,658 individual permit records
    Output: output/raw_parsed_routes.csv, output/ptos_summary.csv
         │
         ▼
 2. normalize_saccos.py
    Strips legal suffixes, standardizes names (e.g. 2KR, Super Metro, Buruburu 58),
    and extracts route number hints from Sacco names
    Output: output/normalized_ptos.csv, output/normalized_routes.csv
         │
         ▼
 3. matcher.py
    Multi-signal heuristic matching engine:
    - Base and exact route number matching
    - Stage & landmark vocabulary overlap (1,300+ Nairobi stages)
    - CBD terminal alignment (Odeon, Railways, Kencom, Bus Station, etc.)
    Output: output/permit_mappings.csv, output/route_sacco_mappings.csv
         │
         ▼
 4. evaluate_mapping.py & export_corrections.py
    Coverage reports & formatted CSV exports for app research/corrections
    Output: output/MAPPING_REPORT.md, output/all_routes_saccos_updated.csv
```

---

## How to Run

Use the project's virtual environment (`backend/.venv`):

```bash
# 1. Parse raw Excel
backend/.venv/bin/python data_cleaning/parse_raw.py

# 2. Normalize Sacco names and extract route hints
backend/.venv/bin/python data_cleaning/normalize_saccos.py

# 3. Run the matching engine
backend/.venv/bin/python data_cleaning/matcher.py

# 4. Generate coverage evaluation report
backend/.venv/bin/python data_cleaning/evaluate_mapping.py

# 5. Export updated research dataset
backend/.venv/bin/python data_cleaning/export_corrections.py
```

---

## Key Results

- **Network Routes Mapped:** **104 / 134 (77.6%)** (up from only 1 route before).
- **Ngong Road Corridor:** 9 / 9 (100.0%)
- **Langata Road Corridor:** 8 / 8 (100.0%)
- **Kiambu Road Corridor:** 4 / 4 (100.0%)
- **Mombasa Road Corridor:** 10 / 11 (90.9%)
- **Kangundo Road Corridor:** 16 / 19 (84.2%)
- **Thika Road Corridor:** 10 / 12 (83.3%)
