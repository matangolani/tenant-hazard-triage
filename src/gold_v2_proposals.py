#!/usr/bin/env python3
"""
Proposed changes to the gold set (v1 -> v2), checked against spec v2.

Three tiers:
  rule    — a spec rule decides the label. Default: ACCEPT.
  forced  — the current label is impossible under the law (e.g. 'significant'
            outside the eight hazard categories). You choose the alternative.
            Default: the proposal.
  suggest — a judgement call the rules don't settle. Default: KEEP your label.
            These items are tagged `boundary` and reported separately.

Mechanical additions (named vulnerable occupants, accepted overlapping categories)
are listed separately and applied by default.

No model predictions were consulted to decide WHAT to propose; every proposal
cites a spec rule. (Model agreement is computed afterwards, for transparency.)
"""

SEV = {  # id: (proposed_severity, rule_ids, note)
    # ---------------- rule tier
    "gold-0020": ("emergency", ["FI-E", "EL-E"], "Sparks from a socket plus a scorch mark: the fire guidance lists sparks from sockets as an emergency ignition source."),
    "gold-0029": ("emergency", ["HY-E"], "The only toilet is unusable: 'loss of usable toilet facilities' is listed as an emergency."),
    "gold-0033": ("emergency", ["FA-E", "FA-V"], "Unrestricted 4th-floor window and a 3-year-old: falls between levels, under-5s most vulnerable, fall very likely and serious. (A similar official scenario exists and was seen — it is excluded from the clean official score.)"),
    "gold-0045": ("emergency", ["EL-E", "P-MITIGATE"], "An electric shock from the shower unit is a clear risk of shock. Not using the shower doesn't remove the defect."),
    "gold-0049": ("emergency", ["EH-E", "EH-V"], "Pregnant and feeling faint from uncontrollable heat: vulnerable AND symptoms."),
    "gold-0051": ("emergency", ["FI-E"], "Any gas smell: 'the risk of a gas explosion would always be an emergency'."),
    "gold-0054": ("emergency", ["EL-E"], "Repeated shocks from light switches: clear risk of electric shock."),
    "gold-0057": ("emergency", ["EC-E", "EC-V"], "No heating at all, two children under 5, properly cold: vulnerable plus complete loss of heating in a cold period."),
    "gold-0058": ("emergency", ["ST-E"], "A slate has come off and more may follow: 'displaced external elements such as roof tiles' is listed as an emergency."),
    "gold-0063": ("emergency", ["FI-E"], "Smoke alarm faulty and now disabled: 'defective or failing fire detection or alarm systems' is listed as an emergency."),
    "gold-0066": ("emergency", ["EL-E"], "Exposed wires within children's reach: exposed live parts accessible to children."),
    "gold-0069": ("emergency", ["DM-E", "DM-V", "P-MITIGATE"], "Mould in a 2-month-old's nursery: particularly vulnerable occupant, in a bedroom. Moving the cot doesn't remove the hazard."),
    "gold-0073": ("emergency", ["EL-E"], "Loose sockets hanging off the wall, one warm, a baby who pulls himself up: damaged sockets accessible to a child."),
    "gold-0079": ("emergency", ["FI-E", "EL-E", "P-MITIGATE"], "Burning electrical smell of unknown source: uncontrolled ignition risk."),
    "gold-0084": ("routine", ["P-ADMIN"], "Changing a rent date is not a hazard, so it's routine rather than unclear."),
    "gold-0090": ("emergency", ["EL-E"], "Water dripping through a working light fitting: defective equipment that could cause a shock. Consistent with your own emergency labels for gold-0025 and gold-0128."),
    "gold-0095": ("emergency", ["ST-E"], "Render has fallen and more is loose above a busy entrance: displaced external elements."),
    "gold-0105": ("emergency", ["EC-E", "EC-V", "G-FACE"], "Wheelchair user, GP says avoid the cold, no heating for 2 days: particularly vulnerable."),
    "gold-0110": ("emergency", ["EL-E", "P-MITIGATE"], "Scorch marks on the immersion switch and a hot smell: defective equipment that could cause burns or fire."),
    "gold-0113": ("emergency", ["FI-E", "FI-V"], "A failing smoke alarm the elderly, mobility-limited resident can't reach: failing alarm, vulnerable occupant."),
    "gold-0123": ("emergency", ["DM-E", "DM-V", "G-FACE"], "Spreading bedroom mould and the tenant is asthmatic: a pre-existing lung condition makes them particularly vulnerable."),
    "gold-0126": ("emergency", ["ST-E"], "A wall bulging and cracking where it wasn't before: instability, a sudden change."),
    "gold-0139": ("emergency", ["EL-E"], "Shower water leaking into the kitchen ceiling and the light flickering when it runs: water reaching live electrics. Consistent with gold-0025 and gold-0128."),
    "gold-0147": ("emergency", ["EC-E"], "The only heater in the bedsit has failed in midwinter: 'a complete loss of heating during colder periods' is listed as an emergency."),
    "gold-0149": ("emergency", ["HY-E"], "Raw sewage coming up and the bathroom is unusable: escape of sewage and loss of toilet facilities."),
}
FORCED = {  # id: (proposed_severity, alternative, rule_ids, note)
    "gold-0018": ("routine", "emergency", ["G-SIGNIF", "G-EMERG"], "A door lock isn't one of the eight categories, so it can't be 'significant'. Routine assumes the door can still be shut securely; if it can't be secured at all, the landlord guidance treats that as an emergency."),
    "gold-0047": ("emergency", "routine", ["G-SIGNIF", "G-EMERG"], "Can't be 'significant' (not one of the eight). The door swings open and can't be locked overnight; the landlord guidance's own example treats an unsecurable front door as an emergency."),
    "gold-0094": ("routine", "emergency", ["G-SIGNIF"], "A red-hot radiator is a hot-surface hazard, not one of the eight, so not 'significant'. Routine unless you judge the burn risk to young children as imminent."),
    "gold-0118": ("routine", "emergency", ["G-SIGNIF"], "A blocked air vent with no damp or fumes reported isn't one of the eight hazards in itself, so not 'significant'."),
    "gold-0127": ("routine", "emergency", ["G-SIGNIF"], "A kitchen window that won't open, with no damp, heat or other hazard described: not 'significant'."),
    "gold-0129": ("emergency", "routine", ["G-SIGNIF", "G-EMERG"], "Asbestos isn't one of the eight, so not 'significant'. A broken tile that may contain asbestos can release fibres, which is arguably an imminent risk. Your call."),
    "gold-0146": ("routine", "emergency", ["G-SIGNIF"], "A hob extractor that doesn't extract, with no damp or fumes described: not 'significant'."),
}
SUGGEST = {  # id: (suggested_severity, rule_ids, note)   default = keep your label
    "gold-0004": ("emergency", ["FA-E", "FA-V"], "Handrail off the stairs and an elderly neighbour has already stumbled: a fall may be 'very likely' for someone over 60."),
    "gold-0007": ("emergency", ["HY-E", "HY-V"], "Mice in the kitchen with young children: pests in food areas are 'more likely to be an emergency'. Ages not stated."),
    "gold-0011": ("significant", ["EC-S", "EC-V"], "No heat in the living room (a key space), other rooms fine, no vulnerable people mentioned."),
    "gold-0013": ("significant", ["DM-S", "DM-V"], "A damp patch in a bedroom with peeling paper since winter: more than a small isolated patch; bedrooms weigh more."),
    "gold-0016": ("emergency", ["EL-E"], "A switch that feels warm suggests overheating, which could be a fire risk."),
    "gold-0019": ("significant", ["ST-E", "ST-S", "ST-O"], "A crack that is slowly lengthening: not 'rapidly worsening', but not clearly superficial either."),
    "gold-0021": ("emergency", ["HY-E", "HY-V"], "A cockroach infestation including the kitchen: 'serious pest infestation'."),
    "gold-0027": ("significant", ["FA-S"], "Loose carpet on the top two stairs: falls are likely because of the condition of the property."),
    "gold-0030": ("significant", ["EL-S"], "Dimming lights and repeated tripping: a deteriorated installation needing remedial work."),
    "gold-0036": ("significant", ["FA-S"], "Lifting kitchen tiles the tenant has already caught a foot on twice."),
    "gold-0041": ("emergency", ["EC-E", "EC-V"], "A 4-month-old's room has no heat (vulnerable), but other rooms can be heated, which the guidance says to weigh."),
    "gold-0043": ("emergency", ["HY-E", "HY-V"], "A rat in the kitchen and a toddler (under 5): pests in food areas with a vulnerable child."),
    "gold-0050": ("routine", ["ST-S", "ST-O"], "A fence panel has already blown down; the remaining risk of harm seems low."),
    "gold-0064": ("emergency", ["EH-E", "EH-O"], "An elderly man got dizzy in the heat (vulnerable plus symptoms), but this only applies if the heat comes from a defect ('no ventilation') rather than the weather alone."),
    "gold-0075": ("emergency", ["FA-E"], "A completely loose banister and a near-fall while carrying a baby. Compare gold-0068, which you labelled emergency."),
    "gold-0083": ("significant", ["ST-S", "ST-E"], "Coving hanging down that 'could drop': the guidance lists fixtures that could fall as significant, and imminent danger as emergency."),
    "gold-0085": ("emergency", ["HY-E"], "Maggots under the units and the kitchen can't be used: a food-preparation area that can't be cleaned."),
    "gold-0091": ("significant", ["FI-E"], "Unchanged, with a note: a broken fire door on a communal landing is covered by the Fire Safety Order, and the landlord guidance says Awaab's Law covers fire hazards inside homes, not regulated common parts. The scheme can't express 'urgent under a different law'."),
    "gold-0108": ("emergency", ["ST-E"], "A cracked kitchen ceiling shedding plaster and getting worse: cracking ceilings indicating instability."),
    "gold-0121": ("emergency", ["HY-E"], "A spreading bedbug infestation with children already bitten."),
    "gold-0134": ("emergency", ["FA-E", "FA-V"], "No handrail on steps with a drop beside them, and a tenant with poor balance."),
    "gold-0144": ("emergency", ["FI-E"], "Unchanged, with a note: a locked fire escape is an emergency, but if it's in communal parts it's covered by the Fire Safety Order rather than Awaab's Law."),
}
CAT = {  # id: (proposed_category, rule_ids, note)   rule tier
    "gold-0004": ("falls", ["FA-V"], "Handrails on stairs come under falls ('falls over guarding associated with stairs')."),
    "gold-0015": ("falls", ["FA-O"], "A loose paving slab on a path is a falls-on-the-level hazard."),
    "gold-0018": ("other_unclear", ["G-SIGNIF"], "Door security isn't one of the eight categories."),
    "gold-0027": ("falls", ["FA-S"], "Loose stair carpet is a falls-on-stairs hazard."),
    "gold-0029": ("hygiene_pests", ["HY-E"], "Toilets and sanitation come under domestic hygiene."),
    "gold-0033": ("falls", ["FA-V"], "Windows are a falls-between-levels hazard."),
    "gold-0036": ("falls", ["FA-S"], "Lifting floor tiles are a falls-on-the-level hazard."),
    "gold-0037": ("hygiene_pests", ["HY-S"], "No hot water means washing facilities are inadequate, which is domestic hygiene."),
    "gold-0038": ("falls", ["FA-O"], "Broken paving is a falls-on-the-level hazard."),
    "gold-0047": ("other_unclear", ["G-SIGNIF"], "Door security isn't one of the eight categories."),
    "gold-0063": ("fire_explosion", ["FI-E"], "Smoke alarms are fire detection."),
    "gold-0089": ("excess_cold", ["EC-S"], "Heating that only partly works is an excess cold issue."),
    "gold-0090": ("electrical", ["EL-E"], "Water in a light fitting is an electrical hazard."),
    "gold-0091": ("fire_explosion", ["FI-E"], "Fire doors are a fire safety measure."),
    "gold-0094": ("other_unclear", ["G-SIGNIF"], "A hot radiator surface isn't electrical."),
    "gold-0101": ("falls", ["FA-O"], "Wobbly decking is a falls-on-the-level hazard."),
    "gold-0122": ("hygiene_pests", ["HY-S"], "Slow drainage comes under domestic hygiene."),
    "gold-0127": ("other_unclear", ["G-SIGNIF"], "A window that won't open, with no named hazard, is not structural collapse."),
    "gold-0130": ("hygiene_pests", ["HY-S"], "Waste disposal is part of the domestic hygiene definition."),
    "gold-0134": ("falls", ["FA-V"], "A missing handrail on steps is a falls-on-stairs hazard."),
    "gold-0140": ("hygiene_pests", ["HY-S"], "Pest birds and droppings come under pests."),
    "gold-0149": ("hygiene_pests", ["HY-E"], "Sewage is domestic hygiene."),
    "gold-0151": ("fire_explosion", ["FI-E"], "The fire definition covers 'fumes ... from failure of systems such as boilers', so carbon monoxide goes here."),
}
ALSO = {  # accepted alternative categories (G-OVERLAP) — scored as correct too
    "gold-0003": ["fire_explosion"], "gold-0020": ["fire_explosion"], "gold-0079": ["electrical"],
    "gold-0110": ["fire_explosion"], "gold-0117": ["fire_explosion"], "gold-0125": ["electrical"],
    "gold-0139": ["electrical"], "gold-0025": ["structural"], "gold-0090": ["structural"],
    "gold-0052": ["damp_mould"], "gold-0102": ["damp_mould", "excess_cold"], "gold-0112": ["hygiene_pests"],
    "gold-0120": ["structural"], "gold-0042": ["falls"], "gold-0107": ["falls"], "gold-0071": ["damp_mould"],
    "gold-0024": ["other_unclear"], "gold-0044": ["other_unclear"], "gold-0053": ["other_unclear"],
    "gold-0130": ["other_unclear"], "gold-0140": ["other_unclear"], "gold-0151": ["other_unclear"],
    "gold-0037": ["other_unclear"],
}
VULN_ADD = {  # people explicitly named in the message but missing from the label
    "gold-0014": ["respiratory_condition"], "gold-0028": ["respiratory_condition"],
    "gold-0064": ["elderly"], "gold-0104": ["infant"], "gold-0115": ["other_health_condition"],
    "gold-0121": ["child"], "gold-0123": ["respiratory_condition"], "gold-0131": ["infant", "child"],
    "gold-0134": ["other_health_condition"], "gold-0136": ["child"],
    "gold-0143": ["elderly", "other_health_condition"], "gold-0144": ["child"], "gold-0149": ["child"],
}
