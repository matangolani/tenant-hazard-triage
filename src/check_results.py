#!/usr/bin/env python3
"""
Tenant Hazard Triage — results regression check (runs in CI).

Re-scores every committed prediction file against its test set and compares the headline numbers
with outputs/metrics_snapshot.json. Any drift (a changed scorer, an edited test set, a swapped
prediction file) fails the build, so the numbers in the README can't silently go stale.

    python3 src/check_results.py            # compare (CI)
    python3 src/check_results.py --write    # refresh the snapshot after an intended change
"""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import load_jsonl, evaluate

SNAP = "outputs/metrics_snapshot.json"
KEYS = ("emergency_recall_strict", "emergency_recall_caught_or_escalated", "emergency_precision", "human_review_rate")


def current():
    out = {}
    for setname in ("gold_v2", "official", "synth_val"):          # the frozen test sets
        gold = f"data/{setname}.jsonl"
        if not os.path.exists(gold):
            continue
        preds = sorted(glob.glob(f"outputs/preds_{setname}_*.jsonl"))
        if not preds:
            continue
        rows = load_jsonl(gold)
        for p in preds:
            label = os.path.basename(p)[len(f"preds_{setname}_"):-6]
            m = evaluate(rows, load_jsonl(p), label)
            out[f"{setname}/{label}"] = {sub: {k: v["headline"][k] for k in KEYS} | {"severity_accuracy": v["severity_accuracy"], "n": v["n"]}
                                         for sub, v in m["subsets"].items()}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    cur = current()
    if a.write or not os.path.exists(SNAP):
        json.dump(cur, open(SNAP, "w"), indent=1, sort_keys=True)
        print(f"wrote {SNAP} ({len(cur)} runs)"); return
    snap = json.load(open(SNAP))
    problems = [f"missing run: {k}" for k in snap if k not in cur] + [f"new run not in snapshot: {k}" for k in cur if k not in snap]
    for k in set(snap) & set(cur):
        if snap[k] != cur[k]:
            problems.append(f"changed: {k}\n  was {snap[k]}\n  now {cur[k]}")
    if problems:
        print("Results differ from the snapshot:\n" + "\n".join(problems))
        print("\nIf the change is intended, run: python3 src/check_results.py --write")
        sys.exit(1)
    print(f"OK: {len(cur)} runs match {SNAP}")


if __name__ == "__main__":
    main()
