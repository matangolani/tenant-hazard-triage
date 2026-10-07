# Tenant Hazard Triage — portfolio handoff


For the chat that updates the portfolio site (Next.js, Tailwind, hard-minimal style) and the CV.
Every number here comes from `outputs/COMPARISON.md` and `outputs/RESULTS.md`; don't round them up,
and don't add claims that aren't below.

## Links (fill in once pushed)
- Repo: `https://github.com/matangolani/tenant-hazard-triage`
- Write-up (GitHub Pages): `https://matangolani.github.io/tenant-hazard-triage/`
- Demo: the "Try it" section of the write-up page replays the system's stored, scored answers on 189 test messages (instant, no model). The live version runs locally only (two models in Ollama).

## One line
Triage of social-housing repair reports under Awaab's Law, with two small open models that run on a laptop.

## Short description (portfolio card, ~40 words)
A local triage tool that reads tenant repair reports and sorts them into emergency, significant or
routine under Awaab's Law, with the legal deadline worked out in code. A fine-tuned 4B model plus a
second-opinion model caught all 54 emergencies in a 152-message test set.

## Longer description (project page, ~150 words)
Since October 2025, social landlords in England must make emergency hazards safe within 24 hours.
The model reads an informal tenant message and returns the hazard category, severity, people at
risk and the legal deadline, flagging every emergency for a person.

I encoded the government's July 2026 triage guidance as 38 rules that generate the prompt, schema and
docs, generated 1,447 synthetic training messages as contrast pairs with a blind re-label filter
(898 kept, about $0.50), and fine-tuned Qwen3-4B with QLoRA on a free Kaggle T4. Fine-tuning cut false
alarms by about 40% (12 → 7) but didn't raise recall, so I added a second-opinion model:
the combined system caught 54/54 gold-set emergencies and 16/17 of the government's own scenarios,
with one silent miss across both. Evaluation uses Wilson intervals and paired McNemar tests, and CI
re-scores every prediction file on each push.

## Tech
Python · Unsloth / QLoRA · Hugging Face Transformers · Ollama (GGUF, 4-bit) · FastAPI · Docker ·
GitHub Actions · OpenRouter (GLM-5.3-Flash as data generator) · vanilla JS/SVG for the write-up page

## Key numbers (use exactly)
| | Value |
|---|---|
| Ensemble emergency recall, gold set | 54/54 (100%, 95% CI 93–100%) |
| Ensemble emergency recall, official scenarios | 16/17 (94%) |
| Silent misses (wrong and not flagged), both sets | 1 (fine-tuned alone: 16; Qwen3.5 alone: 2) |
| Fine-tuned vs base, gold false alarms | 12 → 7 (precision 80% → 87%; 98% on clear-cut cases) |
| Keyword-rules baseline, gold recall | 54% |
| Extra review load, ensemble vs Qwen3.5 alone | 2% vs 16% |
| Synthetic data | 1,447 generated, 898 kept, ~$0.50 API cost |
| Training | QLoRA r16, 2 epochs, 813 examples, free Kaggle T4 |

## Honest caveats (keep at least the first one wherever the 100% appears)
- The second-opinion partner was chosen after seeing test results; the 100% is optimistic, and the
  gain over Qwen3.5 alone is not statistically significant (p = 0.125).
- Test sets are small (54 and 17 emergencies) and contain no real tenant text.
- Fine-tuning alone did not improve emergency recall; it improved precision.

## CV bullets (pick 2–3)
- Built Tenant Hazard Triage, a local LLM triage tool for social-housing hazard reports under Awaab's Law:
  fine-tuned Qwen3-4B with QLoRA on synthetic data generated from the government's guidance, served
  through Ollama behind a FastAPI service with Docker and GitHub Actions CI.
- Designed the evaluation around missed emergencies rather than accuracy (Wilson intervals, paired
  McNemar tests, two frozen test sets); found fine-tuning cut false alarms ~40% without raising recall,
  then added a second-opinion model that caught 54/54 test-set emergencies.
- Generated 1,447 contrast-pair training messages with a blind re-label filter and contamination
  checks for about $0.50, with a hard spend cap and per-call logging.

## Interview talking points
1. **Why recall, not accuracy:** a missed emergency is the failure the law exists to prevent.
2. **Negative result, handled honestly:** fine-tuning learned the synthetic style (98% on synthetic
   validation) but not the task (53% on official scenarios). The misses were all "implied danger"
   cases, which the contrast-pair design and filter under-represented.
3. **Why the ensemble works:** the models fail on different messages; escalating on either is cheap,
   and it reduced review load versus the cautious model alone.
4. **Engineering:** the spec file is the single source for prompt, schema and docs; CI fails if any
   committed result changes; the service fails safe (flags for review) if the second model is down.
5. **Hardware constraint:** the T4 lacks bfloat16, so the stronger Qwen3.5 couldn't be fine-tuned for
   free; next step would be a bf16 GPU.

## Assets
- `docs/index.html` + `docs/data.js`: the write-up page (screenshot it for the card image).
- No demo GIF: link to the write-up page's "Try it" section instead.
- Pending: 4-bit (laptop) scores for the fine-tuned model and the ensemble, from `scripts/deploy_ollama.sh`.
  If they come in lower than the Kaggle numbers above, use the 4-bit numbers on the portfolio.
