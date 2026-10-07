#!/usr/bin/env python3
"""
Tenant Hazard Triage — specification v2. THE single source of truth.

Everything else is generated from this file: the model prompt (render_prompt),
the human-readable spec (render_markdown -> SPEC.md), the JSON output schema,
and the deadline strings. Labels in the test sets are checked against these rules.

Sources (Open Government Licence v3.0):
  HG = MHCLG, "Awaab's Law Phase 2: Guidance to support triaging of hazards" (July 2026)
  LG = MHCLG, "Awaab's Law Phase 2: Guidance for social landlords" (July 2026)

Rules come ONLY from HG's principle sections (definitions, "how would a reasonable
landlord respond", "circumstances increasing vulnerability") and LG's scope and
timescale sections. HG's worked-scenario tables are a held-out test set and were
deliberately excluded when writing these rules.

Each rule is tagged kind="official" (paraphrases the cited text) or
kind="project" (our own decision where the guidance is silent).
"""

SPEC_VERSION = "2.0"

# ---------------------------------------------------------------- categories
CATEGORIES = {
    "damp_mould":     "Damp and/or mould growth, including condensation-driven mould.",
    "excess_cold":    "The home cannot be kept at a safe temperature: heating failure, uncontrollable heating loss.",
    "excess_heat":    "Dangerously high indoor temperature caused by a defect (e.g. heating stuck on, windows that cannot open). Not heat caused solely by the weather.",
    "falls":          "Falls on the level (floors, paths, yards, thresholds), on stairs/steps/ramps (incl. handrails, banisters, guarding) and between levels (windows, balconies, landings).",
    "structural":     "Structural collapse or failure, or building components that could become displaced or fall (ceilings, walls, render, roof tiles, chimneys, fixtures).",
    "fire_explosion": "Fire, smoke, fumes and explosion risks: gas smells, burning or scorching, sparks, fumes from faulty boilers (including carbon monoxide), failing smoke/fire alarms, blocked or unusable escape routes and fire doors.",
    "electrical":     "Unsafe electrical installations: shocks, exposed live parts, damaged or loose sockets and switches, faulty consumer units, water reaching electrics.",
    "hygiene_pests":  "Domestic hygiene: pests and infestations, sewage, drainage, toilets and washing facilities, waste storage, food-preparation areas.",
    "other_unclear":  "Any other hazard (e.g. a door that cannot be secured, asbestos, hot surfaces), a request that is not a hazard (admin, cosmetic, noise from neighbours), or too vague to tell.",
}
AWAAB_SIGNIFICANT_CATEGORIES = [c for c in CATEGORIES if c != "other_unclear"]

SEVERITIES = ["emergency", "significant", "routine", "unclear"]
VULN = ["infant", "child", "elderly", "disabled", "respiratory_condition",
        "other_health_condition", "pregnant"]
CONFIDENCE = ["high", "medium", "low"]

# --------------------------------------------------------------- deadlines (LG §1, §4)
DEADLINES = {
    "emergency":   "investigate and make safe within 24 hours",
    "significant": "investigate within 10 working days; make safe within 5 working days of the investigation; written summary to tenant within 3 working days",
    "routine":     "outside Awaab's Law timescales; normal repair policy",
    "unclear":     "refer to a human to gather more information",
}

# -------------------------------------------------------------------- rules
# applies_to: "all" or a category key.
RULES = [
    # ---------- scope and severity definitions
    dict(id="G-EMERG", applies_to="all", kind="official", source="LG §4.3; Reg 3",
         text="Emergency: an imminent and significant risk of harm to health or safety, i.e. a reasonable landlord would make it safe within 24 hours. Can apply to ANY housing hazard (except overcrowding), including ones outside the eight named categories."),
    dict(id="G-SIGNIF", applies_to="all", kind="official", source="LG §2.1, §4.2; Reg 3",
         text="Significant: a significant risk of harm that a reasonable landlord would make safe within 15 working days. Only possible for the eight named hazard categories. A non-emergency issue in other_unclear is therefore routine, never significant."),
    dict(id="G-SCOPE", applies_to="all", kind="official", source="LG §2.1; HG out-of-scope sections",
         text="Routine (outside Awaab's Law): minor, isolated or superficial problems; issues not caused by a defect in the building (heat caused only by the weather, tenants' own appliances, clutter, noise from neighbours)."),
    dict(id="P-ADMIN", applies_to="all", kind="project", source="project decision",
         text="Requests that are not about a hazard at all (admin, keys, rent, cosmetic wear, a broken doorbell) are other_unclear and routine."),
    dict(id="G-ANYONE", applies_to="all", kind="official", source="HG Triaging",
         text="A vulnerable person is not required for a hazard to be significant or an emergency: some hazards are dangerous to anyone."),
    dict(id="G-FACE", applies_to="all", kind="official", source="HG General points",
         text="Take reported vulnerabilities and health conditions at face value; no medical evidence is needed."),
    dict(id="G-OVERLAP", applies_to="all", kind="official", source="HG General points; fire and electrical definitions",
         text="When hazards overlap (e.g. fire and electrical, damp and cold), choose the main one; the priority is severity, not the exact category."),
    dict(id="P-MITIGATE", applies_to="all", kind="project", source="project decision",
         text="A tenant's own stop-gap (switching off power, unplugging, stopping use, moving a cot) does not lower severity: the defect is still there."),
    dict(id="P-UNCLEAR", applies_to="all", kind="project", source="project decision (HG expects follow-up questions)",
         text="Unclear: the message suggests a possible problem but gives no basis to judge severity. Use it instead of guessing."),
    dict(id="P-UNSURE", applies_to="all", kind="project", source="project decision",
         text="If the rules leave you genuinely unsure between two severities, choose the one the rules best support, set confidence to low and needs_human_review to true. Do not inflate severity to be safe; uncertainty goes to the human-review flag."),

    # ---------- damp and mould (HG)
    dict(id="DM-E", applies_to="damp_mould", kind="official", source="HG Damp §3",
         text="Emergency if the household includes someone particularly vulnerable OR someone already has symptoms linked to damp/mould (e.g. a child's asthma worsening)."),
    dict(id="DM-S", applies_to="damp_mould", kind="official", source="HG Damp §3",
         text="Significant if serious health outcomes are likely if it is not dealt with, including damp/mould that is adversely affecting living conditions without an immediate risk."),
    dict(id="DM-O", applies_to="damp_mould", kind="official", source="HG Damp §3",
         text="Routine if minor or isolated (e.g. small patches on grout or sealant) with no wider issues."),
    dict(id="DM-V", applies_to="damp_mould", kind="official", source="HG Damp §4",
         text="Vulnerable: children aged 14 or under; asthma, COPD, other lung, cardiovascular or allergic conditions; weakened immune system; mental health conditions; pregnancy; mobility issues keeping someone indoors. Mould in a bedroom weighs more than in a hallway; extent and duration matter."),
    # ---------- excess cold
    dict(id="EC-E", applies_to="excess_cold", kind="official", source="HG Cold §3",
         text="Emergency if someone is particularly vulnerable OR already has cold-related symptoms; or a complete loss of heating during colder periods."),
    dict(id="EC-S", applies_to="excess_cold", kind="official", source="HG Cold §3",
         text="Significant if the home cannot be adequately heated and serious health outcomes are likely, especially in colder periods."),
    dict(id="EC-V", applies_to="excess_cold", kind="official", source="HG Cold §4",
         text="Vulnerable: aged 65+ or under 5; pregnancy; chemotherapy/radiotherapy; long-term conditions (mobility, cardiovascular, respiratory, immune, mental health). Also weigh the weather and whether some rooms can still be heated or the whole home is affected. Energy costs are not the landlord's responsibility."),
    # ---------- excess heat
    dict(id="EH-E", applies_to="excess_heat", kind="official", source="HG Heat §3",
         text="Emergency if someone is particularly vulnerable OR is experiencing serious heat-related health effects."),
    dict(id="EH-S", applies_to="excess_heat", kind="official", source="HG Heat §3",
         text="Significant if indoor temperatures are high enough to risk health because of a defect."),
    dict(id="EH-O", applies_to="excess_heat", kind="official", source="HG Heat §3",
         text="Routine (out of scope) if the heat is caused solely by hot weather with no defect."),
    dict(id="EH-V", applies_to="excess_heat", kind="official", source="HG Heat §4",
         text="Vulnerable: aged 65+; babies and children 5 or under; pregnancy; heart, breathing or other underlying conditions; mobility problems; some medications."),
    # ---------- falls
    dict(id="FA-E", applies_to="falls", kind="official", source="HG Falls §3",
         text="Emergency if a fall is very likely and could cause serious harm, particularly where someone is vulnerable."),
    dict(id="FA-S", applies_to="falls", kind="official", source="HG Falls §3",
         text="Significant if falls are likely because of the condition of the property."),
    dict(id="FA-O", applies_to="falls", kind="official", source="HG Falls §3",
         text="Routine if it is an everyday trip or slip not made worse by a defect, or caused by misuse of ladders/furniture or tenants' own work."),
    dict(id="FA-V", applies_to="falls", kind="official", source="HG Falls §4",
         text="Vulnerable: over 60 for falls on the level or stairs; under 5 for falls between levels (windows, balconies); balance, mobility or sensory problems; brittle bones."),
    # ---------- structural
    dict(id="ST-E", applies_to="structural", kind="official", source="HG Structural §3",
         text="Emergency if failure poses imminent danger: large cracks appearing suddenly or rapidly worsening (e.g. from water ingress); cracked or sagging ceilings or walls indicating instability; leaning walls or displaced external elements such as roof tiles, chimneys or brickwork."),
    dict(id="ST-S", applies_to="structural", kind="official", source="HG Structural §3",
         text="Significant if no imminent danger but potential for serious harm: ceiling plaster that could fall, poorly fixed fixtures or fittings, rotten floors or damaged balconies at risk while in use."),
    dict(id="ST-O", applies_to="structural", kind="official", source="HG Structural §3",
         text="Routine if minor or superficial (e.g. superficial cracking in render) with no likely risk of collapse."),
    # ---------- fire and explosions
    dict(id="FI-E", applies_to="fire_explosion", kind="official", source="HG Fire §3",
         text="Most fire hazards are emergencies. Emergency: defective, absent or failing smoke/fire alarms; inaccessible or unusable escape routes or exits due to defects; uncontrolled ignition sources such as open flames or sparks from sockets and switches. Any risk of gas explosion (a gas smell) is always an emergency."),
    dict(id="FI-V", applies_to="fire_explosion", kind="official", source="HG Fire §4",
         text="Vulnerable: limited mobility or difficulty evacuating; neurodivergent conditions, learning difficulties or sensory impairments; over 60."),
    # ---------- electrical
    dict(id="EL-E", applies_to="electrical", kind="official", source="HG Electrical §3",
         text="Many electrical hazards are emergencies. Emergency: exposed live parts; damaged socket-outlets or defective equipment that could cause shock, burns or fire; any clear risk of electric shock; hazards readily accessible to children or other vulnerable people."),
    dict(id="EL-S", applies_to="electrical", kind="official", source="HG Electrical §3",
         text="Significant if no imminent danger but potential for serious harm, e.g. a deteriorated installation needing remedial work, or a defect that may become dangerous if left."),
    dict(id="EL-O", applies_to="electrical", kind="official", source="HG Electrical §3",
         text="Routine (out of scope) if the problem is with an appliance that is not part of the building."),
    dict(id="P-EL-MINOR", applies_to="electrical", kind="project", source="project decision",
         text="A simple fault with no shock, burn or fire risk (a dead socket, a blown bulb) is routine."),
    dict(id="EL-V", applies_to="electrical", kind="official", source="HG Electrical §4",
         text="Vulnerable: children, especially under 5; learning disabilities, neurodivergence or dementia; pregnancy; people relying on powered medical equipment."),
    # ---------- hygiene
    dict(id="HY-E", applies_to="hygiene_pests", kind="official", source="HG Hygiene §3",
         text="Emergency if there is an immediate, serious risk to health: serious pest infestation; escape of raw sewage; failure of drainage or sanitation; loss of a usable toilet or washing facilities; a food-preparation area that cannot be cleaned."),
    dict(id="HY-S", applies_to="hygiene_pests", kind="official", source="HG Hygiene §3",
         text="Significant if serious health outcomes are likely: ongoing pests linked to building defects; unreliable toilet or washing facilities; persistent blockages, slow drainage or leaks."),
    dict(id="HY-V", applies_to="hygiene_pests", kind="official", source="HG Hygiene §4",
         text="Vulnerable: aged 65+; babies and children under 5; reduced mobility; long-term health conditions. Pests in kitchens are more likely to be emergencies."),
]

# ------------------------------------------------------------- output schema
SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "severity": {"type": "string", "enum": SEVERITIES},
        "location": {"type": "string"},
        "vulnerable_occupants": {"type": "array", "items": {"type": "string", "enum": VULN}},
        "duration": {"type": "string"},
        "confidence": {"type": "string", "enum": CONFIDENCE},
        "needs_human_review": {"type": "boolean"},
    },
    "required": ["category", "severity", "location", "vulnerable_occupants",
                 "duration", "confidence", "needs_human_review"],
}


def render_prompt():
    """System prompt for the model. Generated, never hand-edited. Contains no worked examples."""
    lines = [
        "You triage repair reports from social-housing tenants in England under Awaab's Law. "
        "You assist a human; you never make the final decision.",
        "",
        "Return ONLY a JSON object with: category, severity, location, vulnerable_occupants, duration, confidence, needs_human_review.",
        "",
        "CATEGORY — the single main hazard in the message:",
    ]
    lines += [f"- {k}: {v}" for k, v in CATEGORIES.items()]
    lines += ["", "SEVERITY — emergency, significant, routine or unclear. General rules:"]
    lines += [f"- {r['text']}" for r in RULES if r["applies_to"] == "all"]
    for cat in AWAAB_SIGNIFICANT_CATEGORIES:
        rs = [r for r in RULES if r["applies_to"] == cat]
        if rs:
            lines += ["", f"Rules for {cat}:"] + [f"- {r['text']}" for r in rs]
    lines += [
        "",
        "OTHER FIELDS:",
        "- location: the room or area named in the message, briefly, or \"unspecified\".",
        "- vulnerable_occupants: only people explicitly mentioned, from: " + ", ".join(VULN) + ". Empty list if none. Never assume.",
        "- duration: how long the problem has existed if stated, else \"unspecified\".",
        "- confidence: high, medium or low — how sure you are of the severity.",
        "- needs_human_review: true if severity is emergency or unclear, if confidence is low, or if you have any doubt that could put someone at risk.",
        "",
        "Label only what the message says. Do not invent facts.",
    ]
    return "\n".join(lines)


def render_markdown():
    out = [f"# Tenant Hazard Triage — Specification v{SPEC_VERSION}", "",
           "Generated from `src/spec.py` — do not edit by hand.", "",
           "**Sources (Open Government Licence v3.0):**",
           "- HG: MHCLG, *Awaab's Law Phase 2: Guidance to support triaging of hazards* (July 2026)",
           "- LG: MHCLG, *Awaab's Law Phase 2: Guidance for social landlords* (July 2026)", "",
           "Rules are drawn only from HG's principle sections and LG's scope/timescale sections. "
           "HG's worked scenarios are a held-out test set and were not used to write these rules. "
           "Rules marked *project* are our own decisions where the guidance is silent.", "",
           "## Categories", ""]
    out += [f"- **{k}** — {v}" for k, v in CATEGORIES.items()]
    out += ["", "## Deadlines (LG, verified)", ""] + [f"- **{k}**: {v}" for k, v in DEADLINES.items()]
    out += ["", "## Rules", "", "| id | applies to | kind | rule | source |", "|---|---|---|---|---|"]
    out += [f"| {r['id']} | {r['applies_to']} | {r['kind']} | {r['text']} | {r['source']} |" for r in RULES]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "prompt":
        print(render_prompt())
    else:
        print(render_markdown())
