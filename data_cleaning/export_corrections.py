import csv
from pathlib import Path
from config import OUTPUT_DIR, APP_RESEARCH_CSV

def export():
    mappings_file = OUTPUT_DIR / "route_sacco_mappings.csv"
    research_in = APP_RESEARCH_CSV
    
    if not mappings_file.exists():
        print(f"File {mappings_file} does not exist. Run matcher.py first.")
        return

    # Load cleaned mappings
    mapped_dict = {}
    with open(mappings_file, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mapped_dict[r["route_number"]] = r

    # Update all_routes_saccos.csv
    updated_rows = []
    with open(research_in, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            r_num = row["route"]
            mapped = mapped_dict.get(r_num)
            if mapped and mapped["status"] == "MAPPED":
                saccos = [s.strip() for s in mapped["saccos_mapped"].split(";") if s.strip()]
                top_saccos = saccos[:4] # Top 4 Saccos
                row["researched_saccos"] = ", ".join(top_saccos)
                row["researched_terminal"] = mapped["terminals_identified"].replace("; ", " | ")
                row["research_confidence"] = "high" if int(mapped["permit_hits"]) >= 5 else "medium"
            updated_rows.append(row)

    out_research_csv = OUTPUT_DIR / "all_routes_saccos_updated.csv"
    with open(out_research_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"Exported updated research file to: {out_research_csv}")

if __name__ == "__main__":
    export()
