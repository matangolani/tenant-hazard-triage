#!/usr/bin/env python3
"""
Tenant Hazard Triage — the "second opinion" ensemble.

Rule (deliberately simple, applied the same way offline and in the service):
  * The primary model (the fine-tuned Qwen3-4B) supplies every field.
  * A second model (zero-shot Qwen3.5 4B) also triages the message.
  * If the second model says "emergency" and the primary doesn't, the result is escalated to
    emergency and flagged for human review. Nothing is ever de-escalated.

Rationale: a missed emergency is the costly error, the two models fail on different messages,
and the fine-tuned model is the more precise of the two on everything except severity recall.

This file also writes the offline ensemble predictions so compare.py / check_results.py score them:
    python3 src/ensemble.py            # writes outputs/preds_<set>_ensemble.jsonl
    python3 src/ensemble.py --primary tenant-hazard-triage --name ensemble-q4   # after deploy_ollama.sh
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import load_jsonl

PRIMARY, SECOND = "ft-qwen3-4b-2507", "qwen3.5_4b"


def combine(primary, second):
    """primary, second: normalised predictions for one message. Returns the ensemble prediction."""
    out = dict(primary)
    out["second_opinion"] = {"severity": second.get("severity"), "model": second.get("model")}
    if second.get("severity") == "emergency" and primary.get("severity") != "emergency":
        out["severity"] = "emergency"
        out["needs_human_review"] = True
        out["escalated_by_second_opinion"] = True
    else:
        out["escalated_by_second_opinion"] = False
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", default=PRIMARY); ap.add_argument("--second", default=SECOND)
    ap.add_argument("--name", default="ensemble"); ap.add_argument("--sets", nargs="+", default=["gold_v2", "official"])
    a = ap.parse_args()
    import json
    for s in a.sets:
        pp, sp = f"outputs/preds_{s}_{a.primary}.jsonl", f"outputs/preds_{s}_{a.second}.jsonl"
        if not (os.path.exists(pp) and os.path.exists(sp)):
            print(f"skip {s}: need {pp} and {sp}"); continue
        P, S = {r["id"]: r for r in load_jsonl(pp)}, {r["id"]: r for r in load_jsonl(sp)}
        rows = []
        for i, p in P.items():
            r = combine(p, S[i]); r["model"] = f"{a.name} ({a.primary} + {a.second})"
            rows.append(r)
        with open(f"outputs/preds_{s}_{a.name}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{s}: {len(rows)} rows, {sum(r['escalated_by_second_opinion'] for r in rows)} escalated -> outputs/preds_{s}_{a.name}.jsonl")


if __name__ == "__main__":
    main()
