# Tenant Hazard Triage — approach comparison

Ranked by strict emergency recall. 95% Wilson intervals in brackets. Paired tests compare approaches on the same items (exact McNemar).

## Test set: `gold_v2` (152 items)

### all (n=152, true emergencies=54)

| Approach | Emergency recall | Emergency precision | Human review | Severity macro-F1 | Category acc. | Policy viol. |
|---|---|---|---|---|---|---|
| ensemble | 100.0% [93%–100%] | 79.4% [68%–87%] | 46.7% | 0.80 | 83.5% | 1 |
| qwen3.5_4b | 92.6% [82%–97%] | 79.4% [68%–88%] | 57.9% | 0.58 | 90.1% | 0 |
| base-hf-qwen3-4b-2507 | 87.0% [76%–94%] | 79.7% [68%–88%] | 40.1% | 0.65 | 85.5% | 0 |
| gemma4_e4b | 87.0% [76%–94%] | 87.0% [76%–94%] | 38.2% | 0.61 | 89.5% | 0 |
| ft-qwen3-4b-2507 | 85.2% [73%–92%] | 86.8% [75%–93%] | 36.8% | 0.80 | 83.5% | 1 |
| rules | 53.7% [41%–66%] | 85.3% [70%–94%] | 26.3% | 0.57 | 73.7% | 20 |

### clear (n=130, true emergencies=51)

| Approach | Emergency recall | Emergency precision | Human review | Severity macro-F1 | Category acc. | Policy viol. |
|---|---|---|---|---|---|---|
| ensemble | 100.0% [93%–100%] | 89.5% [79%–95%] | 46.2% | 0.89 | 80.8% | 1 |
| qwen3.5_4b | 94.1% [84%–98%] | 88.9% [78%–95%] | 55.4% | 0.63 | 89.2% | 0 |
| base-hf-qwen3-4b-2507 | 88.2% [77%–94%] | 93.8% [83%–98%] | 38.5% | 0.72 | 84.6% | 0 |
| gemma4_e4b | 88.2% [77%–94%] | 95.7% [86%–99%] | 39.2% | 0.64 | 88.5% | 0 |
| ft-qwen3-4b-2507 | 84.3% [72%–92%] | 97.7% [88%–100%] | 36.1% | 0.87 | 80.8% | 1 |
| rules | 54.9% [41%–68%] | 93.3% [79%–98%] | 27.7% | 0.59 | 71.5% | 18 |

### Paired tests (all items)

| A vs B | Severity correct: A-only / B-only | p | True emergencies caught: A-only / B-only | p |
|---|---|---|---|---|
| base-hf-qwen3-4b-2507 vs ensemble | 8 / 18 | 0.076 | 0 / 7 | 0.016 |
| base-hf-qwen3-4b-2507 vs ft-qwen3-4b-2507 | 8 / 16 | 0.152 | 5 / 4 | 1.000 |
| base-hf-qwen3-4b-2507 vs gemma4_e4b | 9 / 13 | 0.523 | 3 / 3 | 1.000 |
| base-hf-qwen3-4b-2507 vs qwen3.5_4b | 10 / 11 | 1.000 | 0 / 3 | 0.250 |
| base-hf-qwen3-4b-2507 vs rules | 52 / 11 | 0.000 | 18 / 0 | 0.000 |
| ensemble vs ft-qwen3-4b-2507 | 8 / 6 | 0.791 | 8 / 0 | 0.008 |
| ensemble vs gemma4_e4b | 13 / 7 | 0.263 | 7 / 0 | 0.016 |
| ensemble vs qwen3.5_4b | 10 / 1 | 0.012 | 4 / 0 | 0.125 |
| ensemble vs rules | 64 / 13 | 0.000 | 25 / 0 | 0.000 |
| ft-qwen3-4b-2507 vs gemma4_e4b | 10 / 6 | 0.454 | 3 / 4 | 1.000 |
| ft-qwen3-4b-2507 vs qwen3.5_4b | 16 / 9 | 0.230 | 4 / 8 | 0.388 |
| ft-qwen3-4b-2507 vs rules | 59 / 10 | 0.000 | 19 / 2 | 0.000 |
| gemma4_e4b vs qwen3.5_4b | 9 / 6 | 0.607 | 2 / 5 | 0.453 |
| gemma4_e4b vs rules | 56 / 11 | 0.000 | 19 / 1 | 0.000 |
| qwen3.5_4b vs rules | 58 / 16 | 0.000 | 21 / 0 | 0.000 |

p < 0.05 means the difference is unlikely to be chance. With these sample sizes, expect most small differences to be non-significant.

## Test set: `official` (37 items)

### all (n=37, true emergencies=17)

| Approach | Emergency recall | Emergency precision | Human review | Severity macro-F1 | Category acc. | Policy viol. |
|---|---|---|---|---|---|---|
| ensemble | 94.1% [73%–99%] | 80.0% [58%–92%] | 54.0% | 0.84 | 97.3% | 0 |
| qwen3.5_4b | 94.1% [73%–99%] | 80.0% [58%–92%] | 70.3% | 0.69 | 86.5% | 0 |
| gemma4_e4b | 76.5% [53%–90%] | 81.2% [57%–93%] | 46.0% | 0.70 | 94.6% | 1 |
| base-hf-qwen3-4b-2507 | 58.8% [36%–78%] | 83.3% [55%–95%] | 32.4% | 0.76 | 89.2% | 0 |
| ft-qwen3-4b-2507 | 52.9% [31%–74%] | 81.8% [52%–95%] | 29.7% | 0.74 | 97.3% | 0 |
| rules | 29.4% [13%–53%] | 55.6% [27%–81%] | 24.3% | 0.37 | 56.8% | 6 |

### clean (n=25, true emergencies=14)

| Approach | Emergency recall | Emergency precision | Human review | Severity macro-F1 | Category acc. | Policy viol. |
|---|---|---|---|---|---|---|
| ensemble | 92.9% [69%–99%] | 76.5% [53%–90%] | 68.0% | 0.79 | 96.0% | 0 |
| qwen3.5_4b | 92.9% [69%–99%] | 76.5% [53%–90%] | 80.0% | 0.69 | 92.0% | 0 |
| gemma4_e4b | 71.4% [45%–88%] | 76.9% [50%–92%] | 52.0% | 0.72 | 96.0% | 1 |
| base-hf-qwen3-4b-2507 | 57.1% [33%–79%] | 80.0% [49%–94%] | 40.0% | 0.68 | 92.0% | 0 |
| ft-qwen3-4b-2507 | 42.9% [21%–67%] | 75.0% [41%–93%] | 32.0% | 0.59 | 96.0% | 0 |
| rules | 35.7% [16%–61%] | 71.4% [36%–92%] | 28.0% | 0.55 | 64.0% | 5 |

### Paired tests (all items)

| A vs B | Severity correct: A-only / B-only | p | True emergencies caught: A-only / B-only | p |
|---|---|---|---|---|
| base-hf-qwen3-4b-2507 vs ensemble | 2 / 6 | 0.289 | 0 / 6 | 0.031 |
| base-hf-qwen3-4b-2507 vs ft-qwen3-4b-2507 | 3 / 2 | 1.000 | 3 / 2 | 1.000 |
| base-hf-qwen3-4b-2507 vs gemma4_e4b | 5 / 4 | 1.000 | 1 / 4 | 0.375 |
| base-hf-qwen3-4b-2507 vs qwen3.5_4b | 6 / 6 | 1.000 | 0 / 6 | 0.031 |
| base-hf-qwen3-4b-2507 vs rules | 14 / 3 | 0.013 | 6 / 1 | 0.125 |
| ensemble vs ft-qwen3-4b-2507 | 7 / 2 | 0.180 | 7 / 0 | 0.016 |
| ensemble vs gemma4_e4b | 6 / 1 | 0.125 | 3 / 0 | 0.250 |
| ensemble vs qwen3.5_4b | 4 / 0 | 0.125 | 0 / 0 | 1.000 |
| ensemble vs rules | 18 / 3 | 0.001 | 11 / 0 | 0.001 |
| ft-qwen3-4b-2507 vs gemma4_e4b | 4 / 4 | 1.000 | 0 / 4 | 0.125 |
| ft-qwen3-4b-2507 vs qwen3.5_4b | 6 / 7 | 1.000 | 0 / 7 | 0.016 |
| ft-qwen3-4b-2507 vs rules | 13 / 3 | 0.021 | 5 / 1 | 0.219 |
| gemma4_e4b vs qwen3.5_4b | 4 / 5 | 1.000 | 0 / 3 | 0.250 |
| gemma4_e4b vs rules | 13 / 3 | 0.021 | 9 / 1 | 0.021 |
| qwen3.5_4b vs rules | 17 / 6 | 0.035 | 11 / 0 | 0.001 |

p < 0.05 means the difference is unlikely to be chance. With these sample sizes, expect most small differences to be non-significant.

## Test set: `synth_val` (85 items)

### all (n=85, true emergencies=41)

| Approach | Emergency recall | Emergency precision | Human review | Severity macro-F1 | Category acc. | Policy viol. |
|---|---|---|---|---|---|---|
| ft-qwen3-4b-2507 | 97.6% [87%–100%] | 100.0% [91%–100%] | 48.2% | 0.99 | 98.8% | 0 |
| base-hf-qwen3-4b-2507 | 80.5% [66%–90%] | 84.6% [70%–93%] | 47.1% | 0.80 | 92.9% | 0 |

### Paired tests (all items)

| A vs B | Severity correct: A-only / B-only | p | True emergencies caught: A-only / B-only | p |
|---|---|---|---|---|
| base-hf-qwen3-4b-2507 vs ft-qwen3-4b-2507 | 1 / 17 | 0.000 | 1 / 8 | 0.039 |

p < 0.05 means the difference is unlikely to be chance. With these sample sizes, expect most small differences to be non-significant.

