#!/usr/bin/env python3
"""
Tenant Hazard Triage — collect everything the Kaggle notebook needs into ONE folder to upload.

    python3 src/make_kaggle_bundle.py        # -> kaggle_bundle/

Upload kaggle_bundle/ as a private Kaggle dataset (see notebooks/KAGGLE.md).
Test sets are included only so the notebook can score base vs fine-tuned on the GPU;
the training code reads train.jsonl / val.jsonl only.
"""
import json, os, shutil, sys

FILES = {"src/ft_lib.py": "ft_lib.py", "src/spec.py": "spec.py", "src/zeroshot_runner.py": "zeroshot_runner.py",
         "src/evaluate.py": "evaluate.py", "data/synth/train.jsonl": "train.jsonl", "data/synth/val.jsonl": "val.jsonl",
         "data/gold_v2.jsonl": "gold_v2.jsonl", "data/official.jsonl": "official.jsonl"}
OUT = "kaggle_bundle"

missing = [s for s in FILES if not os.path.exists(s)]
if missing:
    sys.exit("Missing: " + ", ".join(missing) + "\nRun this from the project folder after the synthetic run.")
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
for src, dst in FILES.items():
    shutil.copy(src, os.path.join(OUT, dst))
    if dst.endswith(".jsonl"):
        n = sum(1 for l in open(src) if l.strip())
        print(f"  {dst:<20} {n:>5} rows")
    else:
        print(f"  {dst}")
# sanity: no test text inside training data
test = {json.loads(l)["text"].strip().lower() for f in ("data/gold_v2.jsonl", "data/official.jsonl") for l in open(f) if l.strip()}
leak = [r for f in ("data/synth/train.jsonl", "data/synth/val.jsonl") for r in map(json.loads, open(f)) if r["text"].strip().lower() in test]
if leak:
    sys.exit(f"STOP: {len(leak)} training rows are identical to test items.")
print(f"\nready: {OUT}/  (no training row matches a test item)")
