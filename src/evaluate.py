#!/usr/bin/env python3
"""
Tenant Hazard Triage — evaluation harness (v2).

Model-agnostic scorer: a gold JSONL + a predictions JSONL -> metrics.

Usage:
    python3 src/evaluate.py --gold data/gold_v2.jsonl --pred outputs/preds_gold_v2_gemma4_e4b.jsonl \
                            --name "Zero-shot gemma4:e4b" --json outputs/metrics_gold_v2_gemma4_e4b.json

Gold rows: {"id","text","gold":{category,severity,...}} plus optional
  category_also   — other categories also counted correct (overlapping hazards)
  boundary        — judgement case; reported separately ("clear" subset excludes these)
  seen            — official scenario read before the rules were written
  requires_context— official label depends on facts a message can't contain

Subsets reported automatically when those fields exist:
  all   — every row
  clear — gold_v2 rows that are not boundary cases
  clean — official rows that are neither seen nor requires_context
"""
import argparse, json, math, sys
from collections import defaultdict, Counter

CATEGORIES = ["damp_mould", "excess_cold", "excess_heat", "falls", "structural",
              "fire_explosion", "electrical", "hygiene_pests", "other_unclear"]
SEVERITIES = ["emergency", "significant", "routine", "unclear"]


def load_jsonl(path):
    rows = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    sys.exit(f"Bad JSON on line {i} of {path}: {e}")
    return rows


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, c - h), 4), round(min(1, c + h), 4))


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def per_class(pairs, classes):
    tp, fp, fn, sup = Counter(), Counter(), Counter(), Counter()
    for g, p in pairs:
        sup[g] += 1
        if g == p: tp[g] += 1
        else: fp[p] += 1; fn[g] += 1
    return {c: (*prf(tp[c], fp[c], fn[c]), sup[c]) for c in classes}


def macro_f1(per):
    fs = [v[2] for v in per.values() if v[3] > 0]
    return sum(fs) / len(fs) if fs else 0.0


def score(gold_rows, pred, name):
    """gold_rows: list of gold dicts; pred: id -> prediction dict."""
    ids = [r["id"] for r in gold_rows if r["id"] in pred]
    G = {r["id"]: r for r in gold_rows}
    sev_pairs, cat_strict, cat_lenient = [], [], 0
    em_total = em_strict = em_escal = em_pred = em_pred_ok = 0
    review = policy = parse_err = schema_viol = 0
    calib = defaultdict(lambda: [0, 0]); lat = []
    for i in ids:
        g, p = G[i]["gold"], pred[i]
        gs, ps = g["severity"], p.get("severity", "unclear")
        gc, pc = g["category"], p.get("category", "other_unclear")
        sev_pairs.append((gs, ps)); cat_strict.append((gc, pc))
        if pc == gc or pc in G[i].get("category_also", []): cat_lenient += 1
        if gs == "emergency":
            em_total += 1
            em_strict += ps == "emergency"
            em_escal += (ps == "emergency" or p.get("needs_human_review") is True)
        if ps == "emergency":
            em_pred += 1; em_pred_ok += gs == "emergency"
        review += p.get("needs_human_review") is True
        policy += (pc == "other_unclear" and ps == "significant")   # impossible under the law
        parse_err += bool(p.get("parse_error")); schema_viol += bool(p.get("schema_violation"))
        if p.get("confidence"):
            calib[p["confidence"]][1] += 1; calib[p["confidence"]][0] += ps == gs
        if isinstance(p.get("latency_ms"), (int, float)): lat.append(p["latency_ms"])
    n = len(ids)
    sev_per, cat_per = per_class(sev_pairs, SEVERITIES), per_class(cat_strict, CATEGORIES)
    lat.sort()
    return {
        "name": name, "n": n,
        "headline": {
            "emergency_recall_strict": round(em_strict / em_total, 4) if em_total else None,
            "emergency_recall_strict_ci95": wilson(em_strict, em_total),
            "emergency_recall_caught_or_escalated": round(em_escal / em_total, 4) if em_total else None,
            "emergency_precision": round(em_pred_ok / em_pred, 4) if em_pred else None,
            "emergency_precision_ci95": wilson(em_pred_ok, em_pred),
            "emergency_support": em_total, "emergency_predicted": em_pred,
            "human_review_rate": round(review / n, 4) if n else None,
        },
        "severity_accuracy": round(sum(g == p for g, p in sev_pairs) / n, 4) if n else None,
        "severity_macro_f1": round(macro_f1(sev_per), 4),
        "category_accuracy_strict": round(sum(g == p for g, p in cat_strict) / n, 4) if n else None,
        "category_accuracy_lenient": round(cat_lenient / n, 4) if n else None,
        "category_macro_f1_strict": round(macro_f1(cat_per), 4),
        "severity_per_class": {k: {"precision": round(v[0], 3), "recall": round(v[1], 3), "f1": round(v[2], 3), "support": v[3]} for k, v in sev_per.items()},
        "category_per_class": {k: {"precision": round(v[0], 3), "recall": round(v[1], 3), "f1": round(v[2], 3), "support": v[3]} for k, v in cat_per.items()},
        "severity_confusion": {g: dict(Counter(p for gg, p in sev_pairs if gg == g)) for g in SEVERITIES},
        "confidence_calibration": {k: {"severity_accuracy": round(v[0] / v[1], 3), "n": v[1]} for k, v in calib.items()},
        "policy_violations": policy, "parse_errors": parse_err, "schema_violations": schema_viol,
        "latency_ms_median": lat[len(lat) // 2] if lat else None,
    }


def subsets(gold_rows):
    out = {"all": gold_rows}
    if any("boundary" in r for r in gold_rows):
        out["clear"] = [r for r in gold_rows if not r.get("boundary")]
    if any("seen" in r for r in gold_rows):
        out["clean"] = [r for r in gold_rows if not r.get("seen") and not r.get("requires_context")]
    return out


def evaluate(gold_rows, pred_rows, name):
    pred = {p["id"]: p for p in pred_rows}
    gold_ids = {r["id"] for r in gold_rows}
    res = {"name": name,
           "missing_predictions": sorted(gold_ids - set(pred)),
           "subsets": {k: score(v, pred, name) for k, v in subsets(gold_rows).items()}}
    # backwards-compatible top level = "all"
    res.update({k: v for k, v in res["subsets"]["all"].items() if k != "name"})
    return res


def pct(x): return "—" if x is None else f"{x:.1%}"
def ci(t): return "" if not t or t[0] is None else f" [{t[0]:.0%}–{t[1]:.0%}]"


def print_report(m):
    print("=" * 70); print(f"  {m['name']}"); print("=" * 70)
    if m["missing_predictions"]:
        print(f"WARNING: {len(m['missing_predictions'])} items have no prediction, e.g. {m['missing_predictions'][:3]}")
    for sname, s in m["subsets"].items():
        h = s["headline"]
        print(f"\n[{sname}]  n={s['n']}  true emergencies={h['emergency_support']}")
        print(f"  strict emergency recall     {pct(h['emergency_recall_strict'])}{ci(h['emergency_recall_strict_ci95'])}")
        print(f"  caught-or-escalated         {pct(h['emergency_recall_caught_or_escalated'])}")
        print(f"  emergency precision         {pct(h['emergency_precision'])}{ci(h['emergency_precision_ci95'])}  ({h['emergency_predicted']} predicted)")
        print(f"  sent to human review        {pct(h['human_review_rate'])}")
        print(f"  severity macro-F1 {s['severity_macro_f1']:.2f}   category accuracy {pct(s['category_accuracy_lenient'])} (strict {pct(s['category_accuracy_strict'])})")
    s = m["subsets"]["all"]
    print("\nSEVERITY confusion, all (row = gold, col = predicted):")
    print("  " + "gold\\pred".ljust(13) + "".join(c[:5].ljust(7) for c in SEVERITIES))
    for g in SEVERITIES:
        print("  " + g.ljust(13) + "".join(str(s["severity_confusion"][g].get(c, 0)).ljust(7) for c in SEVERITIES))
    cal = s["confidence_calibration"]
    if cal:
        print("\nconfidence calibration: " + ", ".join(f"{k} {v['severity_accuracy']:.0%} (n={v['n']})" for k, v in cal.items()))
    print(f"reliability: {s['parse_errors']} parse errors, {s['schema_violations']} schema violations, "
          f"{s['policy_violations']} policy violations (other_unclear + significant)")
    if s["latency_ms_median"] is not None:
        print(f"median latency: {s['latency_ms_median']} ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True); ap.add_argument("--pred", required=True)
    ap.add_argument("--name", default="model"); ap.add_argument("--json", default=None)
    a = ap.parse_args()
    m = evaluate(load_jsonl(a.gold), load_jsonl(a.pred), a.name)
    print_report(m)
    if a.json:
        json.dump(m, open(a.json, "w"), indent=2); print(f"\nmetrics written to {a.json}")


if __name__ == "__main__":
    main()
