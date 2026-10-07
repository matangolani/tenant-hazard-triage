# Fine-tuning on Kaggle

About 15 minutes of clicking, then roughly 1–2 hours unattended.

## 1. Build the upload folder (on your Mac)

```bash
cd ~/dev/projects/tenant-hazard-triage
python3 src/make_kaggle_bundle.py
```
This creates `kaggle_bundle/` with 8 files (code, training data and test sets) and checks
that no training row is identical to a test item.

## 2. Upload it as a private dataset

1. kaggle.com → **Create** → **New Dataset**.
2. Drag in **all 8 files** from `kaggle_bundle/` (the files themselves, not the folder).
3. Title: `hazard-triage-bundle`. Leave it **Private**. Click **Create**.

## 3. Import and set up the notebook

1. kaggle.com → **Create** → **New Notebook**.
2. **File → Import Notebook** → upload `notebooks/hazard_triage_finetune.ipynb`.
3. In the right-hand panel (**Settings**, or the ⋮ menu → Accelerator):
   - **Accelerator: GPU T4** (T4 ×2 is fine too; only one is used). **Not P100**, which is too old.
   - **Internet: On** (needs your verified phone number).
4. **Add Input** → **Your Datasets** → `hazard-triage-bundle`.

## 4. Run it in the background

Click **Save Version** → **Save & Run All (Commit)** → **Save**.
That runs on Kaggle's side, so you can close the tab. You'll find it under **Your Work**;
when it finishes, the **Output** tab has the files.

(If you'd rather watch it, use **Run All** in the editor instead, but keep the tab open.)

## 5. Bring the results back

From the **Output** tab, download:
- `preds_*.jsonl` (6 files) → put in `outputs/`
- `synth_val.jsonl` → put in `data/`
- `summary_*.json`, `train_log_*.json` → put in `outputs/`
- `adapter_*.zip` and any `.gguf` → keep somewhere outside the repo (they're large)

Then:
```bash
python3 src/compare.py --sets gold_v2 official synth_val
```
Send me `outputs/COMPARISON.md`, the two `summary_*.json` and the `train_log_*.json`.

## If something fails

The notebook runs a **preflight** (cell 5) before any long work: it generates answers for the longest
prompts and does one training step on the longest example. Memory or precision problems fail there,
within the first ~10 minutes, with a message saying what to change.

| Where | Symptom | Fix |
|---|---|---|
| Any | Log doesn't start with `TRIAGE NOTEBOOK v4` | You imported an old copy. Re-import the latest `hazard_triage_finetune.ipynb` |
| Cell 3 | "Bundle not found" | Add Input → Your Datasets → hazard-triage-bundle |
| Cell 3 | "GPU is too old" | Accelerator → GPU T4 |
| Cell 4 | "running in float32" | You changed MODEL. Put back `unsloth/Qwen3-4B-Instruct-2507` |
| Cell 5 | out of memory in the training step | Set `MAX_LEN = 2300` in cell 2 (a few of the longest examples get dropped) |
| Cell 7 | very slow steps | 2 epochs is about 200 optimiser steps. If each takes over 60s, set `EPOCHS = 1` |
| Cell 10 | GGUF export error | Ignore; the adapter and predictions are what matter |

Running out of memory during scoring is handled automatically: the batch is halved and retried.
