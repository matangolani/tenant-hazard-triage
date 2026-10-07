#!/usr/bin/env python3
"""
Tenant Hazard Triage — keyword-rules baseline.

The honest "why not just regex?" floor. Deterministic keyword matching, no ML.
Reads the gold file's texts (ignoring gold labels) and writes predictions in the
project schema. Whatever a fine-tuned model achieves has to beat THIS to justify
its existence.

Usage:
    python3 baseline_rules.py --in data/gold.jsonl --out outputs/preds_rules.jsonl
"""
import argparse, json, re, time

DEADLINES = {  # keyed off severity; gov.uk figures, stored here not hardcoded downstream
    "emergency":   "make safe within 24 hours",
    "significant": "investigate within 10 working days; make safe within 5 working days",
    "routine":     "none (normal repair obligations)",
    "unclear":     "refer_to_human",
}

# --- category keyword sets (checked in priority order) ---
CATEGORY_RULES = [
    ("fire_explosion", ["gas", "smoke", "flames", "flame", "fire ", "on fire", "burning smell",
                        "burning plastic", "explosion", "carbon monoxide", "co alarm", "spark"]),
    ("electrical",     ["socket", "wiring", "wires", "wire ", "electric shock", "shock off", "shocks",
                        "fuse board", "fuse", "trip switch", "consumer unit", "plug ", "immersion",
                        "light fitting", "electrics", "scorch"]),
    ("hygiene_pests",  ["mice", "mouse", "rat", "rats", "cockroach", "pest", "infestation", "bedbug",
                        "bed bug", "maggot", "flies", "fly ", "pigeon", "ants", "wasp", "silverfish",
                        "sewage", "droppings", "dead pigeon"]),
    ("damp_mould",     ["mould", "mold", "damp", "condensation", "musty", "mouldy"]),
    ("excess_heat",    ["boiling hot", "unbearably hot", "too hot", "overheat", "red hot",
                        "cant cool", "no ventilation", "30 degrees"]),
    ("excess_cold",    ["freezing", "no heating", "heating has packed", "heating isnt working",
                        "heating been off", "no heat", "boiler wont", "boiler is broken",
                        "boiler broken", "cold in here", "so cold", "radiator", "draught", "no gas"]),
    ("falls",          ["handrail", "banister", "trip", "loose step", "nearly fell", "fall ",
                        "stairlift", "steps up"]),
    ("structural",     ["ceiling", "crack", "collapse", "came down", "sagging", "render", "roof",
                        "slate", "floorboard", "floor tile", "wall ", "bulging", "structural",
                        "window", "door", "hatch", "coving", "fence", "paving", "decking", "leak"]),
]

EMERGENCY_KW = ["gas", "smoke", "flames", "on fire", "carbon monoxide", "co alarm",
                "came down", "collapse", "pouring", "electric shock", "shock off",
                "sparks", "burning smell", "burning plastic", "cant breathe",
                "fire escape", "fire door"]
VULN_KW = {
    "infant": ["baby", "newborn", "8 month", "4 month", "2 month", "15 month", "3 week old", "toddler", "cot", "nursery"],
    "child": ["kids", "kid ", "son", "daughter", "children", "young family", "little ones", "6 and"],
    "elderly": ["elderly", "82", "90", "74", "nan", "mum shes", "mother", "frail", "pensioner"],
    "disabled": ["disabled", "wheelchair", "mobility"],
    "pregnant": ["pregnant"],
    "respiratory_condition": ["asthma", "asthmatic", "copd", "chest", "respiratory", "wheez"],
    "other_health_condition": ["heart condition", "angina", "eczema"],
}
HEALTH_HAZARD_CATS = {"damp_mould", "excess_cold", "excess_heat"}

ROUTINE_KW = ["no rush", "minor", "cosmetic", "small bit", "a bit of", "tiny", "small patch",
              "not urgent", "neither urgent", "just noting", "just flag", "when someones passing",
              "drips", "dripping", "needs changing", "blown", "snapped off", "come off its hinge",
              "wont stay shut", "doesnt work"]
UNCLEAR_KW = ["something is wrong", "help me", "whats happening", "im really struggling",
              "dont know who", "please help i", "reported it ages ago"]

def detect_category(t):
    for cat, kws in CATEGORY_RULES:
        if any(k in t for k in kws):
            return cat
    return "other_unclear"

def detect_vulnerable(t):
    found = []
    for label, kws in VULN_KW.items():
        if any(k in t for k in kws):
            found.append(label)
    return found

def detect_severity(t, cat, vuln):
    # very short / vague -> unclear
    if len(t.split()) <= 4 or any(k in t for k in UNCLEAR_KW):
        return "unclear", "low"
    # explicit emergency signals
    if any(k in t for k in EMERGENCY_KW):
        return "emergency", "high"
    # vulnerable occupant + health-relevant hazard -> escalate
    if vuln and cat in HEALTH_HAZARD_CATS:
        return "emergency", "medium"
    # routine markers
    if any(k in t for k in ROUTINE_KW):
        return "routine", "medium"
    # default: a real hazard, not clearly urgent
    return "significant", "medium"

def predict(text):
    t = text.lower()
    cat = detect_category(t)
    vuln = detect_vulnerable(t)
    sev, conf = detect_severity(t, cat, vuln)
    needs_human = sev in ("emergency", "unclear") or conf == "low"
    return {
        "category": cat,
        "severity": sev,
        "deadline": DEADLINES[sev],
        "location": "unspecified",
        "vulnerable_occupants": vuln,
        "duration": "unspecified",
        "confidence": conf,
        "needs_human_review": needs_human,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = []
    with open(args.inp) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            t0 = time.perf_counter()
            pred = predict(row["text"])
            pred["latency_ms"] = round((time.perf_counter() - t0) * 1000, 4)
            pred["id"] = row["id"]
            out.append(pred)

    with open(args.out, "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(out)} predictions to {args.out}")

if __name__ == "__main__":
    main()
