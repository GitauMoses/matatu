"""
Step 1: flatten the NTSA PTO registry into one row per permit.

Input:  ~/Downloads/Registered NMA PTOS and their Routes of Operation .xlsx
Output: datacleaning/out/permits.csv (sacco, permit_no, via_raw, via_points)

Each ROUTES cell holds a numbered list like:
    1.\tNTR-00539- kikuyu, dagoreti, gikambura,
    2.\tADR-YM3SEOK- Railways, Karen via bomas kawangware...
One line = one permit. We split the sacco's cell into permit rows and the
via-point string into a normalized token list, but we don't try to match
routes here — that's step 2.
"""
import csv
import re
from pathlib import Path

import openpyxl

XLSX = Path("/home/gitau/Downloads/Registered NMA PTOS and their Routes of Operation .xlsx")
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# "1.\tNTR-00539- kikuyu, ..." / "1  ADR-K9BFZR3- Bus station, ..."
LINE_RE = re.compile(r"^\s*\d+[.\s]+\s*([A-Z]{3}-[A-Za-z0-9]+)\s*-\s*(.*)$")


def normalize_token(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s/]", " ", s)  # drop punctuation except / (e.g. 19/60)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_via(via_raw: str) -> list[str]:
    parts = [p.strip() for p in via_raw.split(",")]
    return [normalize_token(p) for p in parts if p.strip()]


def flatten_routes_cell(sacco: str, cell: str) -> list[dict]:
    rows = []
    if not cell:
        return rows
    # permits are newline-separated, but some cells run them together with
    # just the "N." marker — split on the marker itself to be safe.
    chunks = re.split(r"(?=\d+[.\s]+[A-Z]{3}-)", cell.replace("\r", "\n"))
    for chunk in chunks:
        chunk = chunk.strip().strip(",").strip()
        if not chunk:
            continue
        m = LINE_RE.match(chunk)
        if not m:
            continue
        permit_no, via_raw = m.group(1), m.group(2).strip()
        via_points = split_via(via_raw)
        rows.append(
            {
                "sacco": sacco.strip(),
                "permit_no": permit_no,
                "via_raw": via_raw,
                "via_points": "|".join(via_points),
            }
        )
    return rows


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb.active
    out_rows = []
    skipped = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        sr, pto_no, pto_name, route_count, routes_cell = row[:5]
        if not pto_name or not routes_cell:
            continue
        parsed = flatten_routes_cell(pto_name, routes_cell)
        if route_count and len(parsed) != int(route_count):
            skipped.append((pto_name, route_count, len(parsed)))
        out_rows.extend(parsed)

    out_path = OUT / "permits.csv"
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sacco", "permit_no", "via_raw", "via_points"])
        w.writeheader()
        w.writerows(out_rows)

    print(f"wrote {len(out_rows)} permits -> {out_path}")
    if skipped:
        print(f"{len(skipped)} saccos had a route_count mismatch with parsed permits (parser noise, check manually):")
        for name, expected, got in skipped[:15]:
            print(f"  {name}: expected {expected}, parsed {got}")


if __name__ == "__main__":
    main()
