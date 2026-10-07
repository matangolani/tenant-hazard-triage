# Tenant Hazard Triage — Specification v2.0

Generated from `src/spec.py` — do not edit by hand.

**Sources (Open Government Licence v3.0):**
- HG: MHCLG, *Awaab's Law Phase 2: Guidance to support triaging of hazards* (July 2026)
- LG: MHCLG, *Awaab's Law Phase 2: Guidance for social landlords* (July 2026)

Rules are drawn only from HG's principle sections and LG's scope/timescale sections. HG's worked scenarios are a held-out test set and were not used to write these rules. Rules marked *project* are our own decisions where the guidance is silent.

## Categories

- **damp_mould** — Damp and/or mould growth, including condensation-driven mould.
- **excess_cold** — The home cannot be kept at a safe temperature: heating failure, uncontrollable heating loss.
- **excess_heat** — Dangerously high indoor temperature caused by a defect (e.g. heating stuck on, windows that cannot open). Not heat caused solely by the weather.
- **falls** — Falls on the level (floors, paths, yards, thresholds), on stairs/steps/ramps (incl. handrails, banisters, guarding) and between levels (windows, balconies, landings).
- **structural** — Structural collapse or failure, or building components that could become displaced or fall (ceilings, walls, render, roof tiles, chimneys, fixtures).
- **fire_explosion** — Fire, smoke, fumes and explosion risks: gas smells, burning or scorching, sparks, fumes from faulty boilers (including carbon monoxide), failing smoke/fire alarms, blocked or unusable escape routes and fire doors.
- **electrical** — Unsafe electrical installations: shocks, exposed live parts, damaged or loose sockets and switches, faulty consumer units, water reaching electrics.
- **hygiene_pests** — Domestic hygiene: pests and infestations, sewage, drainage, toilets and washing facilities, waste storage, food-preparation areas.
- **other_unclear** — Any other hazard (e.g. a door that cannot be secured, asbestos, hot surfaces), a request that is not a hazard (admin, cosmetic, noise from neighbours), or too vague to tell.

## Deadlines (LG, verified)

- **emergency**: investigate and make safe within 24 hours
- **significant**: investigate within 10 working days; make safe within 5 working days of the investigation; written summary to tenant within 3 working days
- **routine**: outside Awaab's Law timescales; normal repair policy
- **unclear**: refer to a human to gather more information

## Rules

| id | applies to | kind | rule | source |
|---|---|---|---|---|
| G-EMERG | all | official | Emergency: an imminent and significant risk of harm to health or safety, i.e. a reasonable landlord would make it safe within 24 hours. Can apply to ANY housing hazard (except overcrowding), including ones outside the eight named categories. | LG §4.3; Reg 3 |
| G-SIGNIF | all | official | Significant: a significant risk of harm that a reasonable landlord would make safe within 15 working days. Only possible for the eight named hazard categories. A non-emergency issue in other_unclear is therefore routine, never significant. | LG §2.1, §4.2; Reg 3 |
| G-SCOPE | all | official | Routine (outside Awaab's Law): minor, isolated or superficial problems; issues not caused by a defect in the building (heat caused only by the weather, tenants' own appliances, clutter, noise from neighbours). | LG §2.1; HG out-of-scope sections |
| P-ADMIN | all | project | Requests that are not about a hazard at all (admin, keys, rent, cosmetic wear, a broken doorbell) are other_unclear and routine. | project decision |
| G-ANYONE | all | official | A vulnerable person is not required for a hazard to be significant or an emergency: some hazards are dangerous to anyone. | HG Triaging |
| G-FACE | all | official | Take reported vulnerabilities and health conditions at face value; no medical evidence is needed. | HG General points |
| G-OVERLAP | all | official | When hazards overlap (e.g. fire and electrical, damp and cold), choose the main one; the priority is severity, not the exact category. | HG General points; fire and electrical definitions |
| P-MITIGATE | all | project | A tenant's own stop-gap (switching off power, unplugging, stopping use, moving a cot) does not lower severity: the defect is still there. | project decision |
| P-UNCLEAR | all | project | Unclear: the message suggests a possible problem but gives no basis to judge severity. Use it instead of guessing. | project decision (HG expects follow-up questions) |
| P-UNSURE | all | project | If the rules leave you genuinely unsure between two severities, choose the one the rules best support, set confidence to low and needs_human_review to true. Do not inflate severity to be safe; uncertainty goes to the human-review flag. | project decision |
| DM-E | damp_mould | official | Emergency if the household includes someone particularly vulnerable OR someone already has symptoms linked to damp/mould (e.g. a child's asthma worsening). | HG Damp §3 |
| DM-S | damp_mould | official | Significant if serious health outcomes are likely if it is not dealt with, including damp/mould that is adversely affecting living conditions without an immediate risk. | HG Damp §3 |
| DM-O | damp_mould | official | Routine if minor or isolated (e.g. small patches on grout or sealant) with no wider issues. | HG Damp §3 |
| DM-V | damp_mould | official | Vulnerable: children aged 14 or under; asthma, COPD, other lung, cardiovascular or allergic conditions; weakened immune system; mental health conditions; pregnancy; mobility issues keeping someone indoors. Mould in a bedroom weighs more than in a hallway; extent and duration matter. | HG Damp §4 |
| EC-E | excess_cold | official | Emergency if someone is particularly vulnerable OR already has cold-related symptoms; or a complete loss of heating during colder periods. | HG Cold §3 |
| EC-S | excess_cold | official | Significant if the home cannot be adequately heated and serious health outcomes are likely, especially in colder periods. | HG Cold §3 |
| EC-V | excess_cold | official | Vulnerable: aged 65+ or under 5; pregnancy; chemotherapy/radiotherapy; long-term conditions (mobility, cardiovascular, respiratory, immune, mental health). Also weigh the weather and whether some rooms can still be heated or the whole home is affected. Energy costs are not the landlord's responsibility. | HG Cold §4 |
| EH-E | excess_heat | official | Emergency if someone is particularly vulnerable OR is experiencing serious heat-related health effects. | HG Heat §3 |
| EH-S | excess_heat | official | Significant if indoor temperatures are high enough to risk health because of a defect. | HG Heat §3 |
| EH-O | excess_heat | official | Routine (out of scope) if the heat is caused solely by hot weather with no defect. | HG Heat §3 |
| EH-V | excess_heat | official | Vulnerable: aged 65+; babies and children 5 or under; pregnancy; heart, breathing or other underlying conditions; mobility problems; some medications. | HG Heat §4 |
| FA-E | falls | official | Emergency if a fall is very likely and could cause serious harm, particularly where someone is vulnerable. | HG Falls §3 |
| FA-S | falls | official | Significant if falls are likely because of the condition of the property. | HG Falls §3 |
| FA-O | falls | official | Routine if it is an everyday trip or slip not made worse by a defect, or caused by misuse of ladders/furniture or tenants' own work. | HG Falls §3 |
| FA-V | falls | official | Vulnerable: over 60 for falls on the level or stairs; under 5 for falls between levels (windows, balconies); balance, mobility or sensory problems; brittle bones. | HG Falls §4 |
| ST-E | structural | official | Emergency if failure poses imminent danger: large cracks appearing suddenly or rapidly worsening (e.g. from water ingress); cracked or sagging ceilings or walls indicating instability; leaning walls or displaced external elements such as roof tiles, chimneys or brickwork. | HG Structural §3 |
| ST-S | structural | official | Significant if no imminent danger but potential for serious harm: ceiling plaster that could fall, poorly fixed fixtures or fittings, rotten floors or damaged balconies at risk while in use. | HG Structural §3 |
| ST-O | structural | official | Routine if minor or superficial (e.g. superficial cracking in render) with no likely risk of collapse. | HG Structural §3 |
| FI-E | fire_explosion | official | Most fire hazards are emergencies. Emergency: defective, absent or failing smoke/fire alarms; inaccessible or unusable escape routes or exits due to defects; uncontrolled ignition sources such as open flames or sparks from sockets and switches. Any risk of gas explosion (a gas smell) is always an emergency. | HG Fire §3 |
| FI-V | fire_explosion | official | Vulnerable: limited mobility or difficulty evacuating; neurodivergent conditions, learning difficulties or sensory impairments; over 60. | HG Fire §4 |
| EL-E | electrical | official | Many electrical hazards are emergencies. Emergency: exposed live parts; damaged socket-outlets or defective equipment that could cause shock, burns or fire; any clear risk of electric shock; hazards readily accessible to children or other vulnerable people. | HG Electrical §3 |
| EL-S | electrical | official | Significant if no imminent danger but potential for serious harm, e.g. a deteriorated installation needing remedial work, or a defect that may become dangerous if left. | HG Electrical §3 |
| EL-O | electrical | official | Routine (out of scope) if the problem is with an appliance that is not part of the building. | HG Electrical §3 |
| P-EL-MINOR | electrical | project | A simple fault with no shock, burn or fire risk (a dead socket, a blown bulb) is routine. | project decision |
| EL-V | electrical | official | Vulnerable: children, especially under 5; learning disabilities, neurodivergence or dementia; pregnancy; people relying on powered medical equipment. | HG Electrical §4 |
| HY-E | hygiene_pests | official | Emergency if there is an immediate, serious risk to health: serious pest infestation; escape of raw sewage; failure of drainage or sanitation; loss of a usable toilet or washing facilities; a food-preparation area that cannot be cleaned. | HG Hygiene §3 |
| HY-S | hygiene_pests | official | Significant if serious health outcomes are likely: ongoing pests linked to building defects; unreliable toilet or washing facilities; persistent blockages, slow drainage or leaks. | HG Hygiene §3 |
| HY-V | hygiene_pests | official | Vulnerable: aged 65+; babies and children under 5; reduced mobility; long-term health conditions. Pests in kitchens are more likely to be emergencies. | HG Hygiene §4 |

