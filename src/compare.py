#!/usr/bin/env python3
"""
Tenant Hazard Triage — compare approaches on each test set, with paired significance tests.

Reads outputs/preds_<set>_<model>.jsonl for the given sets, scores each against
data/<set>.jsonl, prints a ranked table per subset, and runs exact McNemar tests
between every pair of approaches on the SAME items (more sensitive than comparing
confidence intervals). Writes outputs/COMPARISON.md.

Usage:
    python3 src/compare.py                        # sets: gold_v2 official
    python3 src/compare.py --sets gold_v2
"""
import argparse, glob, json, os, sys
from math import comb
from itertools import combinations
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import load_jsonl, evaluate, pct


def mcnemar_p(b, c):
    """Exact two-sided McNemar p-value from discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sets", nargs="+", default=["gold_v2", "official"])
    a = ap.parse_args()
    md = ["# Tenant Hazard Triage — approach comparison", "",
          "Ranked by strict emergency recall. 95% Wilson intervals in brackets. "
          "Paired tests compare approaches on the same items (exact McNemar).", ""]
    for setname in a.sets:
        gpath = f"data/{setname}.jsonl"
        if not os.path.exists(gpath):
            print(f"skip {setname}: {gpath} not found"); continue
        gold = load_jsonl(gpath)
        runs = {}
        for f in sorted(glob.glob(f"outputs/preds_{setname}_*.jsonl")):
            label = f[len(f"outputs/preds_{setname}_"):-len(".jsonl")]
            runs[label] = {p["id"]: p for p in load_jsonl(f)}
        if not runs:
            print(f"skip {setname}: no predictions"); continue
        metrics = {k: evaluate(gold, list(v.values()), k) for k, v in runs.items()}
        md += [f"## Test set: `{setname}` ({len(gold)} items)", ""]
        for sub in next(iter(metrics.values()))["subsets"]:
            rows = sorted(metrics.items(), key=lambda kv: kv[1]["subsets"][sub]["headline"]["emergency_recall_strict"] or 0, reverse=True)
            s0 = rows[0][1]["subsets"][sub]
            md += [f"### {sub} (n={s0['n']}, true emergencies={s0['headline']['emergency_support']})", "",
                   "| Approach | Emergency recall | Emergency precision | Human review | Severity macro-F1 | Category acc. | Policy viol. |",
                   "|---|---|---|---|---|---|---|"]
            for k, m in rows:
                s, h = m["subsets"][sub], m["subsets"][sub]["headline"]
                rc, pc_ = h["emergency_recall_strict_ci95"], h["emergency_precision_ci95"]
                md.append(f"| {k} | {pct(h['emergency_recall_strict'])}" + (f" [{rc[0]:.0%}–{rc[1]:.0%}]" if rc[0] is not None else "") +
                          f" | {pct(h['emergency_precision'])}" + (f" [{pc_[0]:.0%}–{pc_[1]:.0%}]" if pc_[0] is not None else "") +
                          f" | {pct(h['human_review_rate'])} | {s['severity_macro_f1']:.2f} | {pct(s['category_accuracy_lenient'])} | {s['policy_violations']} |")
            md.append("")
        # paired tests on the full set
        ids = [r["id"] for r in gold]; G = {r["id"]: r["gold"] for r in gold}
        md += ["### Paired tests (all items)", "",
               "| A vs B | Severity correct: A-only / B-only | p | True emergencies caught: A-only / B-only | p |", "|---|---|---|---|---|"]
        for A, B in combinations(sorted(runs), 2):
            common = [i for i in ids if i in runs[A] and i in runs[B]]
            okA = lambda r, i: r[i].get("severity") == G[i]["severity"]
            b = sum(okA(runs[A], i) and not okA(runs[B], i) for i in common)
            c = sum(okA(runs[B], i) and not okA(runs[A], i) for i in common)
            em = [i for i in common if G[i]["severity"] == "emergency"]
            hit = lambda r, i: r[i].get("severity") == "emergency"
            be = sum(hit(runs[A], i) and not hit(runs[B], i) for i in em)
            ce = sum(hit(runs[B], i) and not hit(runs[A], i) for i in em)
            md.append(f"| {A} vs {B} | {b} / {c} | {mcnemar_p(b, c):.3f} | {be} / {ce} | {mcnemar_p(be, ce):.3f} |")
        md += ["", "p < 0.05 means the difference is unlikely to be chance. With these sample sizes, expect most small differences to be non-significant.", ""]
    text = "\n".join(md)
    print(text)
    open("outputs/COMPARISON.md", "w").write(text + "\n")
    print("\nsaved to outputs/COMPARISON.md")


if __name__ == "__main__":
    main()
