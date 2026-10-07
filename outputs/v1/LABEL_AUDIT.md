# Gold set label audit — proposed changes (v1 → v2)

Nothing here is applied yet. Every change needs your sign-off.

## A. Mechanical fixes — the written guide's rule decides the label

These need no judgement. The current label contradicts an explicit rule.

### Severity
| id | current | proposed | guide rule |
|---|---|---|---|
| gold-0045 | routine | emergency | "live wiring or shocks" → emergency |
| gold-0054 | significant | emergency | "shocks" → emergency |
| gold-0020 | significant | emergency | sparks + scorch mark: "live wiring" / "burning" → emergency |
| gold-0051 | significant | emergency | "gas smell" → emergency (gold-0012 is already emergency) |
| gold-0079 | significant | emergency | "burning smell" → emergency (gold-0003 is already emergency) |
| gold-0105 | significant | emergency | "no heat with a disabled/elderly resident in the cold" |
| gold-0049 | significant | emergency | hazard "actively harming a vulnerable occupant" (pregnant, feeling faint) |

### Category
| id | current | proposed | guide rule |
|---|---|---|---|
| gold-0004, 0015, 0027, 0036, 0101, 0134 | structural | falls | "trip / fall / broken stair or handrail → falls" |
| gold-0149 | other_unclear | hygiene_pests | "pests / sanitation / food safety → hygiene_pests" |

### Vulnerable occupants (the message names them; the label is empty)
| id | add |
|---|---|
| gold-0028 | respiratory_condition (COPD) |
| gold-0064 | elderly (father) |
| gold-0104 | infant |
| gold-0121, 0136 | child |
| gold-0123 | respiratory_condition (asthmatic) |
| gold-0131 | infant, child |
| gold-0143 | elderly, other_health_condition (74, angina) |
| gold-0149 | child (young family) |

## B. Taxonomy rulings needed — the spec is silent, so you decide

Once ruled, these become mechanical and are written into the guide.

1. **Fire-safety equipment** (smoke alarms, CO alarms, fire doors, fire escapes):
   `fire_explosion` or `other_unclear`?
2. **Carbon monoxide / boiler fumes:** `fire_explosion` or `other_unclear`?
3. **Plumbing and fixtures with no wider hazard** (dripping taps, gutters, toilet,
   letterbox, slow drain): `other_unclear` or `structural`?
4. **Leaks that damage the building fabric** (ceiling stains, soft plaster):
   `structural`?
5. **Poor lighting on stairs:** `falls` (the hazard) or `electrical` (the fault)?
6. **Hot surfaces** (red-hot radiator, burn risk): `excess_heat` or `other_unclear`?

## C. Judgement cases — blind re-label

Severity calls where the guide doesn't mechanically decide the answer. Re-label
them **without** looking at your original label or any model output. A random
control sample of about 20 undisputed items gets mixed in, so we can measure
your own consistency (Cohen's kappa between pass 1 and pass 2).

gold-0033, 0041, 0057, 0064, 0069, 0075, 0090, 0107, 0110, 0113, 0123, 0147
