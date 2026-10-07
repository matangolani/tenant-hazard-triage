# Tenant Hazard Triage — approach comparison

Ranked by strict emergency recall (the headline metric). All rows scored on the same 152-message held-out gold set.

| Approach | Emergency recall (strict) | Caught-or-escalated | Emergency precision | Severity macro-F1 | Category macro-F1 | Parse errors | Median latency |
|---|---|---|---|---|---|---|---|
| Zero-shot qwen3.5:4b | 100.0% | 100.0% | 48.2% | 0.70 | 0.75 | 0 | 3.2s |
| Zero-shot qwen3.5:9b | 100.0% | 100.0% | 43.5% | 0.69 | 0.72 | 0 | 14.4s |
| Zero-shot gemma4:e4b | 92.6% | 100.0% | 61.0% | 0.78 | 0.75 | 0 | 2.2s |
| Rules baseline (keyword matching) | 74.1% | 74.1% | 58.8% | 0.61 | 0.66 | 0 | 0.03ms |
