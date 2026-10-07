# Tenant Hazard Triage — Baseline Results (v1)

**Date:** 2026-09-21
**Gold set:** 152 hand-labelled tenant messages (held out; never used for training)
**Scored by:** `src/evaluate.py` — model-agnostic; identical ruler for every approach.

---

## Gold set composition (what we're scoring against)

- Severity: **27 emergency**, 66 significant, 53 routine, 6 unclear
- Emergencies are ~18% of the set (deliberately oversampled vs a real inbox, so
  emergency recall is measurable).

---

## Baseline 1 — keyword rules (the "why not just regex?" floor)

| Metric | Value | Meaning |
|---|---|---|
| **Strict emergency recall** | **74.1%** (20/27) | true emergencies correctly labelled `emergency` |
| Caught-or-escalated recall | 74.1% | labelled emergency OR flagged for human review |
| Emergency precision | 58.8% | of predicted emergencies, share that were real |
| Severity accuracy | 59.9% | (not the headline — classes imbalanced) |
| Severity macro-F1 | 0.61 | |
| Category accuracy | 69.1% | |
| Category macro-F1 | 0.66 | |
| Latency | 0.03 ms/item | trivially fast (it's just string matching) |

### The number that matters: 26% of emergencies missed

**7 of 27 emergencies were under-triaged** — all 7 were called `significant`
instead of `emergency`. In the real world that's the exact failure the law exists
to prevent: a dangerous case sent to the slow queue.

### Honest finding: the human-review net didn't help here

Caught-or-escalated recall (74.1%) is **identical** to strict recall. The rules
baseline only flags for human review what it *already* calls emergency or unclear,
so the 7 misses slipped through un-escalated. Lesson for the LLM version: the
escalation safety-net is only worth anything if confidence is *calibrated* — i.e.
the model marks genuinely borderline cases as low-confidence so they get escalated.
That's now a concrete design goal, not an afterthought.

### Where the rules are weak (all expected for a keyword floor)

- **Routine recall is poor (0.32):** rules over-call `significant`. 33 routine
  cases were inflated to significant — a keyword like "crack" or "leak" fires
  regardless of how minor the tenant says it is. Context (which an LLM can read)
  is exactly what's missing.
- **Electrical recall weak (0.38):** fire keywords ("burning smell", "spark")
  greedily claim cases that are really electrical, and "shock"/"socket" phrasings
  get missed. Category boundaries need semantics, not substrings.
- **Emergency precision only 59%:** 13 significant cases were over-called
  emergency. Over-triage is the safer direction, but it's not free.

---

## What this establishes

This is the **floor to beat**. A fine-tuned local model has to clear 74% strict
emergency recall (and ideally lift routine precision and category accuracy) to
justify its existence. If it can't beat keyword matching, that's a finding worth
knowing before any GPU time is spent.

---

# Zero-shot bake-off (2026-10-01)

Three open-weight models (all Apache 2.0) were run through Ollama on a 16GB
M-series Mac, with no fine-tuning and no examples: rules-only prompt, temperature 0,
and output constrained to the JSON schema. All were scored on the same 152-message gold set.

| Approach | Emergency recall (strict) | 95% CI | Emergency precision | Severity macro-F1 | Category macro-F1 | Sent to human review | Median latency |
|---|---|---|---|---|---|---|---|
| qwen3.5:4b | 100% (27/27) | 88–100% | 48% | 0.70 | 0.75 | 59% | 3.2s |
| qwen3.5:9b | 100% (27/27) | 88–100% | 44% | 0.69 | 0.72 | 60% | 14.4s |
| gemma4:e4b | 93% (25/27) | 77–98% | **61%** | **0.78** | **0.75** | 49% | **2.2s** |
| Rules baseline | 74% (20/27) | 55–87% | 59% | 0.61 | 0.66 | 26% | 0.03ms |

Reliability: 0 parse errors and 0 schema violations across all 456 model calls,
because constrained decoding works.

## Findings that hold up

1. **LLMs clearly beat keyword rules on emergency recall.** The rules baseline's
   upper confidence bound (87%) sits below the Qwen models' lower bound (88%).
2. **Recall differences between the three LLMs are NOT meaningful.** 100% vs 93%
   is two cases out of 27, and the intervals overlap heavily. No LLM-vs-LLM recall
   claim can be made at this sample size.
3. **Bigger was not better.** qwen3.5:9b has the worst precision and is 4.5× slower
   than the 4B. It is dropped.
4. **The real failure mode is over-triage.** The models put 41–62 messages in the
   24-hour emergency queue against 27 real emergencies. In 16 cases all three
   models agreed on "emergency" when gold said otherwise.
5. **Self-reported confidence is useless zero-shot.** 91–97% of answers are
   "high", and "high" is right only 65–77% of the time. Calibration is flat.
6. **"Caught-or-escalated = 100%" is hollow.** It's achieved by sending 49–60% of
   *all* messages to human review. Escalating half the inbox is not triage.
   Strict recall stays the headline metric, and the review rate must be reported
   alongside it.
7. **Gemma's misses share a pattern:** latent danger with no harm yet (coving
   hanging and "could drop"; water pooling next to an electric point; repeated
   small shocks). That's a specific, learnable gap.

## Finding that changes the plan: the measuring stick is noisy

The error analysis shows that a large share of "model errors" are actually
**label errors or spec gaps**. They come from two sources:

**(a) Gold labels that contradict the written labelling guide.** Examples:
an electric shock labelled `routine`; a gas smell labelled `significant` when an
almost identical gas message is `emergency`; trip hazards and handrails labelled
`structural` when the guide says `falls` (this alone explains falls precision of
0.20); 11 messages that name a vulnerable person but have an empty
`vulnerable_occupants`. This is normal for a first labelling pass by one
non-expert annotator, and it's why label audits exist.

**(b) The model prompt drifted from the labelling guide.** The prompt classed
fire-safety equipment and carbon monoxide as `fire_explosion`, and doors,
windows and leaks as `structural`. The guide the gold set was labelled with says
neither, which accounts for 10 of the 25 unanimous category disagreements.
Fix: generate the prompt from the taxonomy document so there is one source of
truth.

**Sensitivity check.** Correcting only the labels where the guide's explicit
rule decides the answer (7 severity, 7 category; no judgement calls):

| Model | Emergency recall | Emergency precision | Severity F1 | Category F1 |
|---|---|---|---|---|
| qwen3.5:4b | 100% → 100% | 48% → 61% | 0.70 → 0.74 | 0.75 → 0.81 |
| gemma4:e4b | 93% → 91% | 61% → 76% | 0.78 → 0.81 | 0.75 → 0.82 |
| rules | 74% → 71% | 59% → 71% | 0.61 → 0.62 | 0.66 → 0.69 |

The ranking is stable, but every absolute number moves by up to 15 points. Any
number reported before the audit would have been wrong.

## Verdict

- **Do not fine-tune yet.** Fix the gold set and the spec first. Otherwise a
  fine-tuned model trained to the guide gets marked down for following it.
- **Carry two models forward:** qwen3.5:4b (best recall, trigger-happy) and
  gemma4:e4b (best judgement and fastest). Decide on fine-tuned results.
- **Fine-tuning has a sharper target now.** Keep recall, raise emergency
  precision, and make the escalation signal meaningful (cut the review rate).
  Training data should be built around contrastive boundary pairs: near-identical
  messages that differ in one detail (imminence, active harm, a vulnerable person).
- **Methodology rule from here on:** the gold set is test-only. Prompt
  iteration happens on a separate synthetic dev set, never against gold.

---

# Methodology change: spec v2 (2026-10-02)

The v1 numbers above are archived in `outputs/v1/`. They are **not comparable**
to anything that follows, because the rules, the prompt and the test labels all
changed.

## What changed and why

1. **The spec now comes from the official guidance.** v1's labelling guide was
   written from secondary summaries; the MHCLG triaging guidance (July 2026) had
   been listed as "to verify" and never read. `src/spec.py` is now the single
   source of truth: 33 rules paraphrase the official text (each one cites its
   section) and 5 are labelled project decisions. The prompt, `SPEC.md` and the
   JSON schema are all generated from it, so the prompt and the labels can't
   drift apart again.
2. **What the official text says that v1 got wrong:**
   - For damp, cold and heat, an emergency is "particularly vulnerable **or**
     already has symptoms". v1 required both.
   - Most fire hazards are emergencies: failing smoke alarms, sparks from
     sockets and any gas smell are named explicitly. Many electrical hazards are
     emergencies too.
   - "Significant" only exists for the eight named categories. Emergencies
     apply to any housing hazard. So `other_unclear` + `significant` is
     impossible, and the scorer now counts it as a policy violation.
   - Toilets, drainage, sewage and washing facilities are domestic hygiene;
     losing your only usable toilet is an emergency.
   - Carbon monoxide or fumes from a failing boiler fall under fire and
     explosions.
   - Deadlines were checked against the landlord guidance. They match the
     figures v1 had been using without verification.
3. **The tie-breaker changed.** v1 said "if torn, choose the more severe". v2
   says to choose what the rules best support and send the uncertainty to the
   human-review flag. Inflated severity was the main cause of over-triage.
4. **There's a second test set: 37 official scenarios** (`data/official.jsonl`),
   labelled by the government. 12 were read before the rules were written, and
   3 depend on facts a tenant message can't contain. The **clean** score uses
   the remaining 25. Caveat: those 25 have no routine cases, so they test the
   emergency/significant line only.
5. **The gold set was re-checked against v2 rules** (`review_gold_v2.html`),
   in three tiers: rule-decided (default accept), impossible under the law
   (choose), and judgement calls (default keep, tagged `boundary`, reported
   separately as the "clear" subset). The proposals were written from the rules
   without looking at model outputs. Checked afterwards: of 32 default severity
   changes, both models already agreed with 16, one with 11 and neither with 5.
   In 3 boundary cases both models said emergency and v2 keeps the lower label.
   The overall direction agrees with the models because the official
   definition of an emergency is broader than v1's.
6. **The scorer now reports:** subsets (all / clear / clean), the human-review
   rate, policy violations, lenient category accuracy (overlapping hazards
   accepted, as the guidance advises), Wilson intervals, and exact McNemar
   paired tests between approaches.

## Known limitations (carried into the README)

- **Neither test set contains real tenant text.** The 152 messages were written
  by an LLM; the official scenarios are landlord-written summaries.
- **The gold v2 changes were proposed by the same AI that wrote the messages.**
  The user approved each one and their decision overrides.
- **The emergency share is now about 35%, far above a real inbox.** Precision
  on real traffic would be much lower than measured.
- **The test sets are small:** about 52 gold emergencies and 14 clean official
  emergencies. Small differences between models won't be significant.
- **Fire hazards in communal parts are regulated by the Fire Safety Order**,
  not Awaab's Law. The schema can't express "urgent under a different law".

---

# Zero-shot bake-off v2 (2026-10-05)

Spec v2 prompt (hash `b9fc1aae1628`), temperature 0, schema-constrained, on a 16GB
M-series Mac. Full tables: `outputs/COMPARISON.md`. Gold v2: 152 items, 54
emergencies (35.5%), 22 tagged `boundary`. Official: 37 scenarios, 17 emergencies;
the clean subset is 25 scenarios with 14 emergencies.

| Approach | Gold: emerg. recall | Gold: emerg. precision | Official: emerg. recall | Official clean: recall | Review beyond emergencies* |
|---|---|---|---|---|---|
| qwen3.5:4b | 92.6% (50/54) [82–97] | 79.4% | 94.1% (16/17) | 92.9% (13/14) | 16.4% |
| gemma4:e4b | 87.0% (47/54) [76–94] | 87.0% | 76.5% (13/17) | 71.4% (10/14) | 2.6% |
| rules | 53.7% (29/54) [41–66] | 85.3% | 29.4% (5/17) | 35.7% (5/14) | – |

\* The runner sends every predicted emergency to a human by design, so the raw
"human review" rate mostly counts emergencies. This column is the share of messages
flagged for review that the model did **not** call an emergency, which is the
extra load on the review queue.

## Findings

1. **Both LLMs beat the rules baseline decisively** (McNemar p < 0.001 on gold
   emergencies; p ≤ 0.021 on official).
2. **Qwen vs Gemma is not statistically separable on either set alone.** On
   emergencies, Qwen catches 5 that Gemma misses on gold (Gemma catches 2 that Qwen
   misses; p = 0.45), and 3 vs 0 on official (p = 0.25). Pooled across both sets
   it is 8 vs 2 (p ≈ 0.11). The direction is consistent, but it is not proven.
3. **Gemma's misses are silent; Qwen's are often escalated.** 10 of Gemma's 11
   missed emergencies went out with no human-review flag. Only 2 of Qwen's 5 did.
   Gemma effectively never uses the review flag (2.6% beyond emergencies), so its
   safety net doesn't work. For this task a silent miss is the worst failure.
4. **Gemma's misses repeat the v1 pattern: latent danger before harm.** Examples:
   water dripping through a light fitting, a leak through a ceiling with
   flickering lights, scorched immersion-heater switch, a roof slate fallen where
   children play, a constantly chirping smoke alarm with the battery removed.
5. **The models over-call the same cases.** All 7 of Gemma's false emergencies on
   gold are among Qwen's 13. 7 of Qwen's 13 (and 5 of Gemma's 7) are tagged
   `boundary`, meaning either label is defensible. That is why emergency precision on the `clear` subset is 89–96%.
6. **No model ever outputs `unclear`** (0/5 on gold). This caps severity macro-F1
   at about 0.6. Severity accuracy is about 80% for both models.
7. **Latency figures aren't comparable between runs.** Qwen's median was 2.8s on
   gold and 15.7s on official; Gemma's was 5.6s and 1.8s. The Mac was in use
   during the runs. Latency gets a dedicated measurement with the fine-tuned model.

## Decision: fine-tune Qwen3.5-4B, with Gemma 4 E4B as fallback

Recall is the headline metric, and Qwen leads on it on both sets. Its failures
are over-calling and over-reviewing, which are a cost problem that fine-tuning
on contrast pairs is designed to reduce. Gemma's failures are silent misses, the
outcome the law exists to prevent. Training notes: Unsloth advises against QLoRA
(4-bit) for Qwen3.5 and lists about 10GB for a 4B bf16 LoRA, which fits a 16GB
T4 (fp16). The kernels can be slow to compile on T4. If Qwen training is blocked
on Kaggle, switch to Gemma 4 E4B QLoRA (about 10GB) with the same data.

---

# Synthetic training data (2026-10-05)

Teacher: GLM-5.3-Flash via OpenRouter. Its thinking can't be switched off
("Reasoning is mandatory"), so the generator runs at low thinking effort.
Generator: `src/generate_synth.py`; per-call log in `data/synth/calls.jsonl`.

| | |
|---|---|
| Jobs (API prompts) | 898 of 900 (2 failed and were dropped) |
| Messages written | 1,447 |
| **Kept after checks** | **898 (62%)**: 813 train / 85 val, split by job so contrast pairs never straddle |
| Cost | about $0.63 in total, including smoke tests ($0.50 for the main run) |
| Time | 10 minutes for the main run (32 parallel requests) |

**Kept data:** emergency 405 (45%), routine 292 (33%), significant 194 (22%),
unclear 7. Contrast pairs: 384 messages kept as complete pairs and 257 as surviving
halves. Every category has at least 63 examples.

**Why messages were rejected (549):**
- **Blind re-label disagreed on severity: 387.** In 333 of these, the
  re-label was one level more severe (235 were significant → emergency). Reading
  them shows two causes. Most often the writer overshot. For example, it was asked
  for "significant" cold and wrote a complete loss of heating in cold weather,
  which rule EC-E makes an emergency. The rest are genuine borderline cases.
- **Writer missed the requested label: 143,** 86 of them on "significant" targets.
- **Category disagreed: 15. Contamination (too close to a test item): 0.**
  Near-duplicates: 1.

**What this means for training (to check in the results):**
1. **Significant is the hardest class to generate,** and so the rarest in the
   training data. That is the same emergency/significant boundary the models get
   wrong. The filter keeps clear-cut examples and drops borderline ones, which
   protects label quality but means the hardest cases are under-taught.
2. **Emergencies are 45% of training data** (gold is 35%), which may push the
   student towards over-calling.
3. **There are only 7 `unclear` examples,** and the human-review flag in the targets
   is derived from severity. The fine-tuned model will probably almost never flag
   a non-emergency for review. So the number to watch is **silent misses**:
   emergencies the model gets wrong *and* doesn't flag for review. Zero-shot,
   Qwen had 2 and Gemma 10.


## Change: fine-tune Qwen3-4B-Instruct-2507 (2026-10-05)

Neither bake-off model can be fine-tuned on Kaggle's free T4 in a reasonable time.
The T4 has no bfloat16, and Unsloth refuses float16 for both newer architectures,
so it falls back to float32:
- **Qwen3.5-4B:** float32, split across two GPUs, and the fast linear-attention
  kernels (flash-linear-attention, causal-conv1d) are missing. Estimated many hours.
- **Gemma 4 E4B (4-bit):** float32 compute. It used 11.1 GB of 14.6 GB just to load,
  and ran out of memory on the first batch of 8 prompts of about 2,000 tokens each.

**Qwen3-4B-Instruct-2507** (Apache 2.0, standard transformer) is Unsloth's documented
free-T4 path, running in float16 with 4-bit QLoRA. The fine-tuning effect is measured
inside one harness: base vs fine-tuned, same GPU, prompt and decoding. That comparison
doesn't depend on which model won the Ollama bake-off. The bake-off still documents
zero-shot behaviour across model families. This was a hardware constraint, not a
quality finding.

**Pipeline safeguards added after three failed runs:**
- A version banner in the log.
- A float32 guard that stops the run.
- A preflight that runs the longest prompts and one training step before any long work.
- Automatic halving of the scoring batch on out-of-memory errors.


## Results: fine-tuning and the second-opinion ensemble (2026-10-07)

Run: Qwen3-4B-Instruct-2507, 4-bit QLoRA (r 16, 2 epochs, lr 2e-4) on 813 synthetic messages,
free Kaggle T4. Base and fine-tuned scored in the same harness (same GPU, prompt, greedy decoding).
Full tables: `outputs/COMPARISON.md`.

| | Recall, gold (54) | Precision, gold | Recall, official (17) | Silent misses (both) | Extra review, gold | Recall, synth_val (41) |
|---|---|---|---|---|---|---|
| Qwen3 4B, zero-shot | 47 (87%) | 80% | 10 (59%) | 13 | 1% | 33 (80%) |
| Qwen3 4B, fine-tuned | 46 (85%) | 87% | 9 (53%) | 16 | 2% | 40 (98%) |
| Qwen3.5 4B, zero-shot | 50 (93%) | 79% | 16 (94%) | 2 | 16% | – |
| **Fine-tuned + Qwen3.5 second opinion** | **54 (100%)** | 79% | **16 (94%)** | **1** | 2% | – |

### What fine-tuning did
1. **Precision up, recall flat.** Gold false alarms 12 → 7; clear-subset precision 93.8% → 97.7%,
   the highest of any approach. Emergencies caught 47 → 46 (paired 5 vs 4, p = 1.0). Severity
   macro-F1 0.65 → 0.80.
2. **No gain on the official scenarios** (10 → 9 of 17, paired 3 vs 2, p = 1.0).
3. **It learned the training distribution very well:** synth_val recall 80% → 98% (p = 0.039),
   precision 85% → 100%. The gap between that and the real test sets is the main finding.
4. **The predicted failure mode happened.** The review flag is derived from severity in the
   training targets, so the fine-tuned model almost never flags a non-emergency (extra review 2%).
   Its 8 gold misses are all labelled significant or routine *and* unflagged, so they are silent.
5. **The misses share a pattern: implied danger.** Water dripping from a light fitting, a leak
   pooling by an electric point, a slate falling where children play, an elderly tenant with no
   heating in January. The danger is in the combination, not in an explicit word. Contrast pairs
   teach "one decisive detail flips the label", and the blind re-label filter dropped borderline
   messages, so this kind of case is under-represented in training.
6. **Gold and official differ for another reason too:** official scenarios are third-person
   landlord summaries, a style the generator rarely wrote.

### The ensemble (option B)
Rule, fixed before scoring: the fine-tuned model fills every field; if the second model says
emergency, escalate to emergency and flag for review; never downgrade. `src/ensemble.py`, used
by both scoring and the service.

All four second-opinion partners were tried (escalation rule as above):

| Partner | Recall gold | Precision gold | Recall official | Silent misses (both) |
|---|---|---|---|---|
| Keyword rules | 89% | 83% | 59% | 13 |
| Qwen3 4B zero-shot (same base) | 94% | 80% | 71% | 8 |
| Gemma 4 E4B | 93% | 86% | 76% | 8 |
| **Qwen3.5 4B** | **100%** | 79% | **94%** | **1** |

A softer variant (partner's emergency only adds a review flag, severity unchanged) gives the same
silent-miss counts with the fine-tuned model's precision, but leaves the 24-hour clock off until a
person looks; it was not adopted because the clock matters.

**Versus Qwen3.5 alone** (McNemar, gold): emergencies caught 54 vs 50 (4/0, p = 0.125, not
significant); severity correct 10/1 discordant (p = 0.012); extra review 2% vs 16%. Versus the
fine-tuned model alone: 8/0, p = 0.008. Official: same recall as Qwen3.5 (16/17), review rate
54% vs 70%. The one remaining silent miss is official-28 (uninsulated hot-water cylinder in a loft
above a child's bedroom), which both models call significant.

**Caveats.** The partner was chosen after seeing these results, so the ensemble's numbers are
optimistic; the test sets are small. The fine-tuned predictions come from the fp16 model on Kaggle;
`scripts/deploy_ollama.sh` re-scores the Q4 GGUF (`tenant-hazard-triage`, `ensemble-q4`) on a Mac. Running
two models doubles compute per message but runs in parallel; both fit in 16 GB at 4 bits.

### If I continued
- Train on Qwen3.5 on a bf16 GPU (the stronger zero-shot base).
- Generate implied-danger cases deliberately, and third-person landlord-summary style.
- Teach the review flag independently of severity, so the model can say "not sure".
