# Tenant Hazard Triage

Triage of social-housing hazard reports under Awaab's Law, using two small open language models
that run on a laptop. A tenant's message goes in. Out comes the hazard category, the severity
(emergency, significant, routine or unclear), the legal deadline and the people at risk, plus a
flag for human review. A person always makes the final decision.

**Write-up with results:** [showcase page](https://matangolani.github.io/tenant-hazard-triage/) ·
**Try it:** the write-up's replay section shows the system's real answers on the test messages · run it yourself: [Running it](#running-it)

<!-- RESULTS-START -->
| Approach | Emergency recall, gold (95% CI) | Emergency precision, gold | Emergency recall, official | Silent misses | Extra review load |
|---|---|---|---|---|---|
| Keyword rules | 54% (41–66%) | 85% | 29% | 37 | 4% |
| Gemma 4 E4B, zero-shot | 87% (76–94%) | 87% | 76% | 10 | 3% |
| Qwen3.5 4B, zero-shot | 93% (82–97%) | 79% | 94% | 2 | 16% |
| Qwen3 4B, zero-shot | 87% (76–94%) | 80% | 59% | 13 | 1% |
| Qwen3 4B, fine-tuned | 85% (73–92%) | 87% | 53% | 16 | 2% |
| **Fine-tuned + Qwen3.5 second opinion** | **100% (93–100%)** | 79% | **94%** | **1** | 2% |
<!-- RESULTS-END -->

*Silent misses* = true emergencies the model got wrong **and** didn't flag for review, across both
test sets. *Extra review load* = share of gold messages flagged for review that weren't called an
emergency. Gold set: 152 messages, 54 emergencies. Official scenarios: 37 worked examples from the
government guidance, 17 emergencies.

**What the numbers say.**
- **Fine-tuning made the model more precise but not more sensitive.** Against the same model before
  training, gold-set false alarms fell from 12 to 7 (precision 80% → 87%; 98% on clear-cut cases,
  the highest of any model). Recall didn't move, and stayed weak on the official scenarios. The
  fine-tuned model downgrades emergencies whose danger is implied rather than stated.
- **A second opinion closes the gap.** The fine-tuned model and zero-shot Qwen3.5 miss different
  messages. Escalating whenever either says emergency caught all 54 gold emergencies (fine-tuned
  alone: 46, McNemar p = 0.008). It needs far less review than Qwen3.5 alone (2% vs 16% extra) and
  gets severity right more often (85% vs 79%, p = 0.012). Its recall gain over Qwen3.5 alone is not
  significant (p = 0.125).
- **Caveat:** the partner model was chosen after seeing test results (all four pairings are in
  `outputs/RESULTS.md`), so the ensemble's numbers are optimistic.

## Why

Awaab's Law gives social landlords in England fixed deadlines for dangerous hazards, starting
from when they become aware of the problem: 24 hours to make an emergency safe. Phase 1 (damp,
mould and all emergency hazards) has been in force since 27 October 2025. Phase 2 extends the
deadlines to more hazard types from 30 November 2026. Spotting the emergency in a stream of
informal tenant messages is a triage problem, and a missed emergency is the failure that matters.
So the headline metric is **emergency recall**, not accuracy.

## How it works

```
official guidance ──► spec.py (38 rules) ──► prompt + JSON schema + SPEC.md
                                   │
GLM-5.3-Flash writes contrast pairs ─► blind re-label + filters ─► 898 kept (813 train)
                                   │
                    QLoRA fine-tune of Qwen3-4B-Instruct (Kaggle T4)
                                   │
          evaluate on 2 frozen test sets ──► GGUF ──► Ollama ──► FastAPI + demo page
                                   │                     ▲
                     zero-shot Qwen3.5 (second opinion) ─┘  escalate if it says emergency
```

- **One source of truth.** `src/spec.py` encodes the July 2026 MHCLG triage guidance as 33
  official rules (each cites its section) and 5 labelled project decisions. The model prompt,
  the output schema and `SPEC.md` are all generated from it.
- **Synthetic data, checked.** `src/generate_synth.py` asks the teacher for *contrast pairs*:
  two near-identical messages that differ in one decisive detail and land on different
  severities. Every message is labelled again, blind, with the student's own prompt and kept only
  if the labels agree. Further checks cover length, policy, leaked label words, near-duplicates
  and similarity to any test item. 1,447 generated, 898 kept, about $0.50 of API time ($0.63 including smoke tests).
- **Fine-tuning.** `notebooks/hazard_triage_finetune.ipynb` runs on a free Kaggle T4:
  - 4-bit QLoRA, loss on the answer tokens only.
  - The base model is scored first in the same harness, so base-vs-fine-tuned isolates the
    effect of training.
  - A preflight step catches memory and precision problems in the first few minutes.
- **Evaluation.** `src/evaluate.py` and `src/compare.py` report:
  - strict and caught-or-escalated emergency recall, emergency precision and silent misses, with
    Wilson 95% intervals
  - exact McNemar paired tests between approaches
  - subsets that exclude borderline cases and official scenarios seen while writing the rules
- **Second opinion.** `src/ensemble.py` holds the one rule shared by scoring and serving: the
  fine-tuned model fills every field, and if zero-shot Qwen3.5 says emergency the report is
  escalated and flagged. Nothing is ever downgraded. If the second model is down, the report is
  flagged rather than trusted.
- **Serving.** `src/api.py` is a FastAPI service with `POST /triage`, `GET /health` and a demo
  page. Both models run in Ollama, in parallel, with the same prompt and constrained decoding used in
  evaluation. Deadlines are computed in working days, excluding weekends and England & Wales
  bank holidays (gov.uk data).

## Running it

```bash
pip install -r requirements.txt
bash scripts/deploy_ollama.sh <gguf folder>          # loads the fine-tuned model, pulls qwen3.5:4b, scores both
uvicorn api:app --app-dir src --port 8000             # open http://localhost:8000
```

With Docker, keeping the model in Ollama on the host:

```bash
docker build -t tenant-hazard-triage .
docker run -p 8000:8000 -e OLLAMA_HOST=http://host.docker.internal:11434 tenant-hazard-triage
curl -s localhost:8000/triage -H 'content-type: application/json' \
  -d '{"text": "the socket by the kettle sparked and there is a scorch mark"}'
```

No model? `TRIAGE_BACKEND=rules uvicorn api:app --app-dir src` runs the keyword baseline instead.
`TRIAGE_SECOND_MODEL=""` turns the second opinion off.

## Reproducing the results

| Step | Command |
|---|---|
| Zero-shot bake-off (Ollama) | `bash bakeoff.sh` |
| Synthetic data (needs `OPENROUTER_API_KEY`, capped at $4) | `python3 src/generate_synth.py --calls 900` |
| Fine-tune and score on Kaggle | see `notebooks/KAGGLE.md` |
| Second-opinion ensemble from saved predictions | `python3 src/ensemble.py` |
| Load the fine-tuned model into Ollama and re-score on a Mac | `bash scripts/deploy_ollama.sh <gguf folder>` |
| Compare everything | `python3 src/compare.py --sets gold_v2 official synth_val` |
| Rebuild the showcase page data | `python3 src/build_showcase.py` |

`python3 -m pytest -q tests` runs the unit and API tests. CI (`.github/workflows/ci.yml`) does
three things on every push:
- runs the tests
- builds the Docker image
- re-scores every committed prediction file against `outputs/metrics_snapshot.json`, so the
  numbers above can't silently change

## Repository

```
src/spec.py               rules, schema, prompt (single source of truth)
src/generate_synth.py     synthetic data: teacher, filters, spend cap, call log
src/ft_lib.py             fine-tuning helpers (prompt, loss masking, scoring records)
src/zeroshot_runner.py    Ollama runner used for all local scoring
src/evaluate.py, compare.py, check_results.py   metrics, paired tests, CI regression check
src/ensemble.py           second-opinion rule (used by scoring and the service)
src/api.py, triage_service.py, deadlines.py    service, backends, working-day deadlines
notebooks/                Kaggle fine-tuning notebook + instructions
data/gold_v2.jsonl        152-message gold test set (frozen)
data/official.jsonl       37 official MHCLG scenarios (frozen)
outputs/                  predictions, reports, RESULTS.md (full lab notebook)
docs/                     showcase page (GitHub Pages)
web/                      demo page served by the API
```

## Limitations

- **Neither test set contains real tenant text.** The gold messages were written by a
  language model. The official scenarios are landlord-written summaries.
- **Emergencies are about 35% of the gold set,** far above a real inbox, so precision on real
  traffic would be lower than measured.
- **The test sets are small,** and most differences between the language models are not
  statistically significant.
- **Gold labels come from one annotator,** who reviewed AI-proposed corrections against the rules.
- **The fine-tuned model (Qwen3-4B) isn't either bake-off model.** Qwen3.5 and Gemma 4 are
  built for bfloat16, which the free T4 lacks. In float32, Gemma 4 ran out of memory and Qwen3.5
  would have taken many hours. Details in `outputs/RESULTS.md`.
- **The ensemble was picked on the test sets.** See the caveat above.
- **Fine-tuned numbers are from the full-precision model on Kaggle.** `scripts/deploy_ollama.sh`
  re-scores the 4-bit version that runs on a laptop.
- **This is decision support, not automation.** Fire hazards in communal areas fall under the
  Fire Safety Order, which the schema doesn't model.

## Sources and licence

- MHCLG, [Awaab's Law Phase 2: Guidance to support triaging of hazards](https://www.gov.uk/government/publications/awaabs-law-phase-2-hazards-guidance-for-social-landlords/awaabs-law-phase-2-guidance-to-support-triaging-of-hazards) (July 2026)
- MHCLG, [Awaab's Law Phase 2: Guidance for social landlords](https://www.gov.uk/government/publications/awaabs-law-phase-2-guidance-for-social-housing-landlords/awaabs-law-phase-2-guidance-for-social-landlords) (July 2026)
- The official scenarios in `data/official.jsonl` are Crown copyright, reproduced under the
  [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- Bank holidays: [gov.uk/bank-holidays.json](https://www.gov.uk/bank-holidays.json).
- Code: MIT licence (see `LICENSE`).
