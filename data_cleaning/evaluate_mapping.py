import csv
from collections import defaultdict, Counter
from pathlib import Path
from config import OUTPUT_DIR, APP_ROUTES_CSV

def evaluate():
    routes_csv = OUTPUT_DIR / "route_sacco_mappings.csv"
    permits_csv = OUTPUT_DIR / "permit_mappings.csv"
    report_md = OUTPUT_DIR / "MAPPING_REPORT.md"

    routes = []
    with open(routes_csv, encoding="utf-8") as f:
        routes = list(csv.DictReader(f))

    permits = []
    with open(permits_csv, encoding="utf-8") as f:
        permits = list(csv.DictReader(f))

    total_routes = len(routes)
    mapped_routes = [r for r in routes if r["status"] == "MAPPED"]
    unmapped_routes = [r for r in routes if r["status"] == "UNMAPPED"]
    
    total_permits = len(permits)
    matched_permits = [p for p in permits if p["confidence"] in ["HIGH", "MEDIUM", "LOW"]]
    high_med_permits = [p for p in permits if p["confidence"] in ["HIGH", "MEDIUM"]]

    # Corridor breakdown
    corridors = defaultdict(lambda: {"total": 0, "mapped": 0})
    for r in routes:
        c = r["corridor"] if r["corridor"] else "other_feeder"
        corridors[c]["total"] += 1
        if r["status"] == "MAPPED":
            corridors[c]["mapped"] += 1

    # Sacco route counts
    sacco_routes = defaultdict(set)
    for r in mapped_routes:
        for s in r["saccos_mapped"].split(";"):
            s_clean = s.strip()
            if s_clean:
                sacco_routes[s_clean].add(r["route_number"])

    top_saccos = sorted(sacco_routes.items(), key=lambda x: len(x[1]), reverse=True)

    # Generate Markdown Report
    lines = []
    lines.append("# NTSA Excel to Matatu Route System: Mapping Report\n")
    lines.append("## Executive Summary\n")
    lines.append(f"- **Total App Network Routes:** {total_routes}")
    lines.append(f"- **Successfully Mapped Routes:** {len(mapped_routes)} ({len(mapped_routes)/total_routes*100:.1f}%)")
    lines.append(f"- **Unmapped Routes:** {len(unmapped_routes)} ({len(unmapped_routes)/total_routes*100:.1f}%)")
    lines.append(f"- **Total NTSA Permits Processed:** {total_permits}")
    lines.append(f"- **Permits Matched with High/Medium Confidence:** {len(high_med_permits)} ({len(high_med_permits)/total_permits*100:.1f}%)\n")

    lines.append("## Corridor Coverage\n")
    lines.append("| Corridor | Mapped | Total | Coverage |")
    lines.append("| :--- | :---: | :---: | :---: |")
    for c, stats in sorted(corridors.items(), key=lambda x: x[1]["total"], reverse=True):
        cov = (stats["mapped"] / stats["total"]) * 100 if stats["total"] else 0
        lines.append(f"| `{c}` | {stats['mapped']} | {stats['total']} | **{cov:.1f}%** |")
    lines.append("")

    lines.append("## Top Operators / Saccos by Mapped Network Routes\n")
    lines.append("| Operator / Sacco | Mapped Routes Count | Sample Routes |")
    lines.append("| :--- | :---: | :--- |")
    for sacco, r_set in top_saccos[:20]:
        sample = ", ".join(sorted(list(r_set))[:8])
        lines.append(f"| **{sacco}** | {len(r_set)} | {sample} |")
    lines.append("")

    lines.append("## Sample Major Mapped Routes\n")
    lines.append("| Route | Description | Corridor | Top Saccos | Terminals Identified |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    spotlight = ["105", "111", "110", "125", "126", "25", "58", "44G", "46B", "14", "11", "2", "38/39", "17B", "102"]
    for r in mapped_routes:
        if r["route_number"] in spotlight:
            s_preview = "; ".join(r["saccos_mapped"].split(";")[:4])
            lines.append(f"| **{r['route_number']}** | {r['description']} | `{r['corridor']}` | {s_preview} | {r['terminals_identified']} |")
    lines.append("")

    lines.append("## Unmapped Routes Breakdown\n")
    lines.append("The unmapped routes fall into known survey artifacts and hyper-local feeders:\n")
    for r in unmapped_routes:
        lines.append(f"- **Route {r['route_number']}**: {r['description']} (Corridor: `{r['corridor']}`)")
    lines.append("")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report generated at: {report_md}")
    print(f"Coverage: {len(mapped_routes)} / {total_routes} ({len(mapped_routes)/total_routes*100:.1f}%)")

if __name__ == "__main__":
    evaluate()
