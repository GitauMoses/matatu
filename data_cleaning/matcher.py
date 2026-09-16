import csv
import re
from collections import defaultdict
from pathlib import Path
from config import (
    OUTPUT_DIR,
    APP_ROUTES_CSV,
    APP_STAGES_CSV,
    APP_PATHS_CSV,
    CBD_TERMINALS,
    CORRIDORS
)

def get_base_number(num_str: str) -> str:
    m = re.match(r"^(\d+)", num_str)
    return m.group(1) if m else num_str

def load_app_network():
    routes = []
    with open(APP_ROUTES_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            routes.append(r)

    paths = defaultdict(list)
    with open(APP_PATHS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            paths[r["route_id"]].append(r["stage_id"])

    stages = {}
    with open(APP_STAGES_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            stages[r["stage_id"]] = r["name"].lower().strip()

    # Collect vocabulary of meaningful stage keywords
    all_stage_keywords = set()
    stopwords = {
        "terminal", "terminus", "stage", "roundabout", "hospital", "school",
        "market", "centre", "center", "mwisho", "towards", "house", "station",
        "point", "street", "road", "avenue", "junction", "apartments", "hotel", "court"
    }
    for s in stages.values():
        clean_s = re.sub(r"[/,\-]", " ", s)
        for part in clean_s.split():
            part = part.strip()
            if len(part) >= 4 and part not in stopwords:
                all_stage_keywords.add(part)

    route_data = []
    for r in routes:
        rid = r["route_id"]
        num = r["number"].strip()
        base_num = get_base_number(num)
        
        # Identify CBD terminal
        cbd_match = None
        desc_lower = (r["description"] + " " + r["inbound_to"]).lower()
        for term, aliases in CBD_TERMINALS.items():
            if any(a in desc_lower for a in aliases):
                cbd_match = term
                break

        # Collect keywords for this route
        full_text = f"{r['description']} {r['outbound_to']} {r['inbound_to']} {r['corridor']}"
        route_kw = set()
        for sid in paths.get(rid, []):
            if sid in stages:
                full_text += f" {stages[sid]}"
                
        clean_full = re.sub(r"[/,;\-]", " ", full_text.lower())
        for part in clean_full.split():
            part = part.strip()
            if part in all_stage_keywords:
                route_kw.add(part)

        route_data.append({
            "route_id": rid,
            "number": num,
            "base_num": base_num,
            "description": r["description"],
            "outbound_to": r["outbound_to"].strip(),
            "inbound_to": r["inbound_to"].strip(),
            "corridor": r["corridor"].strip().lower(),
            "cbd_terminal": cbd_match,
            "keywords": route_kw
        })

    return route_data, all_stage_keywords

def detect_cbd_terminals_in_text(text: str) -> list[str]:
    found = []
    text_lower = text.lower()
    for term, aliases in CBD_TERMINALS.items():
        if any(re.search(r"\b" + re.escape(a) + r"\b", text_lower) for a in aliases):
            found.append(term)
    return found

def match_all():
    routes, stage_vocab = load_app_network()
    permits_path = OUTPUT_DIR / "normalized_routes.csv"
    
    permits = []
    with open(permits_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            permits.append(r)

    print(f"Loaded {len(routes)} app routes and {len(permits)} normalized permits.")

    permit_matches = []
    route_to_saccos = defaultdict(lambda: {"saccos": defaultdict(int), "terminals": set(), "permits_count": 0})

    for p in permits:
        p_hints = set(h.lower().strip() for h in p["route_hints"].split(";") if h.strip())
        hint_bases = set(get_base_number(h) for h in p_hints if h)
        text_lower = p["route_text"].lower()
        permit_terminals = detect_cbd_terminals_in_text(text_lower)

        # Extract keywords present in this permit
        clean_p_text = re.sub(r"[/,;\-]", " ", text_lower)
        p_kw = set(w for w in clean_p_text.split() if w in stage_vocab)

        qualifying_matches = []

        for r in routes:
            num = r["number"]
            num_lower = num.lower()
            b_num = r["base_num"].lower()
            
            overlap_kw = r["keywords"] & p_kw
            overlap_count = len(overlap_kw)

            has_exact_num = (num_lower in p_hints) or bool(re.search(r"\b" + re.escape(num_lower) + r"\b", text_lower))
            has_base_num = (b_num in hint_bases) or bool(re.search(r"\b" + re.escape(b_num) + r"\b", text_lower))

            score = 0
            reasons = []

            if has_exact_num:
                score += 50
                reasons.append(f"Exact number '{num}'")
            elif has_base_num:
                score += 35
                reasons.append(f"Base number '{b_num}'")

            if overlap_count > 0:
                score += min(overlap_count * 12, 48)
                reasons.append(f"{overlap_count} waypoints ({', '.join(list(overlap_kw)[:3])})")

            # Bonus for CBD terminal match
            if r["cbd_terminal"] and r["cbd_terminal"] in permit_terminals:
                score += 15
                reasons.append(f"Terminal '{r['cbd_terminal']}'")

            # Qualification threshold
            if (has_exact_num and overlap_count >= 1) or (has_base_num and overlap_count >= 1) or (overlap_count >= 2 and score >= 35):
                confidence = "HIGH" if (has_exact_num and overlap_count >= 1) or score >= 70 else ("MEDIUM" if score >= 45 else "LOW")
                qualifying_matches.append({
                    "route_number": num,
                    "score": score,
                    "confidence": confidence,
                    "reasons": "; ".join(reasons)
                })

        qualifying_matches.sort(key=lambda x: x["score"], reverse=True)

        if qualifying_matches:
            top = qualifying_matches[0]
            matched_routes_str = "; ".join([f"{m['route_number']} ({m['confidence']}:{m['score']})" for m in qualifying_matches[:3]])
            permit_matches.append({
                "pto_no": p["pto_no"],
                "sacco": p["sacco"],
                "permit_id": p["permit_id"],
                "primary_route": top["route_number"],
                "all_matches": matched_routes_str,
                "confidence": top["confidence"],
                "score": top["score"],
                "reasons": top["reasons"],
                "route_text": p["route_text"]
            })

            # Attribute permit to top matching routes
            for m in qualifying_matches:
                if m["score"] >= top["score"] - 15 and m["confidence"] in ["HIGH", "MEDIUM"]:
                    r_num = m["route_number"]
                    route_to_saccos[r_num]["saccos"][p["sacco"]] += 1
                    route_to_saccos[r_num]["permits_count"] += 1
                    for t in permit_terminals:
                        route_to_saccos[r_num]["terminals"].add(t.title())
        else:
            permit_matches.append({
                "pto_no": p["pto_no"],
                "sacco": p["sacco"],
                "permit_id": p["permit_id"],
                "primary_route": "",
                "all_matches": "",
                "confidence": "UNMATCHED",
                "score": 0,
                "reasons": "Insufficient keyword overlap",
                "route_text": p["route_text"]
            })

    # Save permit level matches
    permits_out_csv = OUTPUT_DIR / "permit_mappings.csv"
    with open(permits_out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=["pto_no", "sacco", "permit_id", "primary_route", "all_matches", "confidence", "score", "reasons", "route_text"]
        )
        writer.writeheader()
        writer.writerows(permit_matches)

    # Build final Route -> Saccos table
    routes_summary = []
    for r in routes:
        r_num = r["number"]
        mapped = route_to_saccos.get(r_num)
        if mapped and mapped["saccos"]:
            # Sort saccos by frequency
            sorted_saccos = sorted(mapped["saccos"].items(), key=lambda x: x[1], reverse=True)
            sacco_list = [s[0] for s in sorted_saccos]
            terminals_list = sorted(list(mapped["terminals"]))
            routes_summary.append({
                "route_number": r_num,
                "description": r["description"],
                "corridor": r["corridor"],
                "status": "MAPPED",
                "permit_hits": mapped["permits_count"],
                "saccos_mapped": "; ".join(sacco_list),
                "terminals_identified": "; ".join(terminals_list),
            })
        else:
            routes_summary.append({
                "route_number": r_num,
                "description": r["description"],
                "corridor": r["corridor"],
                "status": "UNMAPPED",
                "permit_hits": 0,
                "saccos_mapped": "",
                "terminals_identified": "",
            })

    routes_out_csv = OUTPUT_DIR / "route_sacco_mappings.csv"
    with open(routes_out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=["route_number", "description", "corridor", "status", "permit_hits", "saccos_mapped", "terminals_identified"]
        )
        writer.writeheader()
        writer.writerows(routes_summary)

    mapped_count = sum(1 for r in routes_summary if r["status"] == "MAPPED")
    print(f"Mapped {mapped_count} out of {len(routes)} app routes ({mapped_count/len(routes)*100:.1f}%)")
    print(f"Saved: {permits_out_csv}")
    print(f"Saved: {routes_out_csv}")

if __name__ == "__main__":
    match_all()
