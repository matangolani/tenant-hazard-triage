#!/usr/bin/env python3
"""
Tenant Hazard Triage — build the data file behind the showcase page (docs/data.js).

Reads the frozen test sets and every prediction file in outputs/, computes the numbers the page shows,
and picks example cases. Re-run after new results arrive:
    python3 src/build_showcase.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import load_jsonl, evaluate

# Approaches in display order. key = prediction-file label; missing files are shown as "pending".
APPROACHES = [
    # synth_val is scored too, but only for the two Kaggle runs
    ("rules",                         "Keyword rules",                 "baseline",  "No model. Hand-written keyword matching."),
    ("gemma4_e4b",                    "Gemma 4 E4B, zero-shot",        "zero-shot", "Ollama, 4-bit, rules prompt only."),
    ("qwen3.5_4b",                    "Qwen3.5 4B, zero-shot",         "zero-shot", "Ollama, 4-bit, rules prompt only."),
    ("base-hf-qwen3-4b-2507",         "Qwen3 4B, zero-shot",           "zero-shot", "Same harness as the fine-tuned model (Kaggle T4)."),
    ("ft-qwen3-4b-2507",              "Qwen3 4B, fine-tuned",          "fine-tuned","QLoRA on 813 synthetic messages (Kaggle T4)."),
    ("ensemble",                      "Fine-tuned + Qwen3.5 second opinion", "ensemble", "Fine-tuned Qwen3 4B; escalated to emergency if zero-shot Qwen3.5 says so."),
    ("tenant-hazard-triage",                  "Qwen3 4B, fine-tuned, on a Mac","deployed",  "The fine-tuned model compressed to 4-bit, served by Ollama."),
    ("ensemble-q4",                   "Ensemble, on a Mac",            "deployed",  "The demo configuration: both models 4-bit in Ollama."),
]
SETS = {"gold_v2": "Gold set (152 messages)", "official": "Official scenarios (37)", "synth_val": "Synthetic validation (85)"}


def stats(gold_rows, preds):
    P = {p["id"]: p for p in preds}
    m = evaluate(gold_rows, preds, "x")["subsets"]["all"]
    h = m["headline"]
    em = [r for r in gold_rows if r["gold"]["severity"] == "emergency" and r["id"] in P]
    silent = [r["id"] for r in em if P[r["id"]]["severity"] != "emergency" and not P[r["id"]].get("needs_human_review")]
    beyond = sum(1 for r in gold_rows if r["id"] in P and P[r["id"]].get("needs_human_review") and P[r["id"]]["severity"] != "emergency")
    return {"recall": h["emergency_recall_strict"], "recall_ci": h["emergency_recall_strict_ci95"],
            "precision": h["emergency_precision"], "precision_ci": h["emergency_precision_ci95"],
            "emergencies": h["emergency_support"], "predicted_emergencies": h["emergency_predicted"],
            "silent_misses": len(silent), "review_beyond": round(beyond / len(gold_rows), 4),
            "severity_accuracy": m["severity_accuracy"], "n": m["n"],
            "latency_ms_median": m.get("latency_ms_median")}


def pick_examples(gold_rows, preds, k_each=2):
    """A few right answers and a few honest mistakes, from the best available model."""
    P = {p["id"]: p for p in preds}
    rows = [r for r in gold_rows if r["id"] in P and len(r["text"]) < 330]
    def ex(r, kind):
        p = P[r["id"]]
        return {"kind": kind, "text": r["text"], "gold": r["gold"]["severity"], "gold_category": r["gold"]["category"],
                "pred": {k: p.get(k) for k in ("category", "severity", "vulnerable_occupants", "confidence", "needs_human_review")}}
    right_em = [ex(r, "correct") for r in rows if r["gold"]["severity"] == p_sev(P, r) == "emergency" and not r.get("boundary")]
    right_rt = [ex(r, "correct") for r in rows if r["gold"]["severity"] == p_sev(P, r) == "routine"]
    missed = [ex(r, "missed emergency") for r in rows if r["gold"]["severity"] == "emergency" and p_sev(P, r) != "emergency"]
    false_al = [ex(r, "false alarm") for r in rows if r["gold"]["severity"] != "emergency" and p_sev(P, r) == "emergency"]
    return right_em[:k_each] + right_rt[:1] + missed[:k_each] + false_al[:k_each]


REPLAY_KEY = "ensemble"
# Hand-picked to show the range: clear emergencies, look-alike routine cases, second-opinion
# escalations and the system's mistakes. Everything shown is the stored, scored prediction.
REPLAY_PICKS = ["gold-0001", "gold-0016", "gold-0090", "gold-0128", "gold-0058", "official-17", "official-06",
                "official-28", "gold-0094", "official-31", "official-05"]


def replay(gold):
    rows = []
    for s in ("gold_v2", "official"):
        f = f"outputs/preds_{s}_{REPLAY_KEY}.jsonl"
        if not os.path.exists(f):
            continue
        P = {p["id"]: p for p in load_jsonl(f)}
        for r in gold[s]:
            p = P.get(r["id"])
            if not p:
                continue
            rows.append({"id": r["id"], "set": s, "text": r["text"], "gold": r["gold"]["severity"],
                         "pred": {k: p.get(k) for k in ("category", "severity", "location", "vulnerable_occupants",
                                                        "confidence", "needs_human_review", "escalated_by_second_opinion")}})
    picks = [x for i in REPLAY_PICKS for x in rows if x["id"] == i]
    return {"picks": [x["id"] for x in picks], "rows": rows}


def p_sev(P, r):
    return P[r["id"]]["severity"]


def main():
    out = {"approaches": [], "sets": SETS, "examples": [], "example_source": None}
    gold = {s: load_jsonl(f"data/{s}.jsonl") for s in SETS}
    for key, label, kind, note in APPROACHES:
        a = {"key": key, "label": label, "kind": kind, "note": note, "results": {}}
        if key.startswith("ensemble"):
            a["short"] = "Ensemble (Mac)" if key == "ensemble-q4" else "Ensemble (FT + 3.5)"
        for s in SETS:
            f = f"outputs/preds_{s}_{key}.jsonl"
            if os.path.exists(f):
                a["results"][s] = stats(gold[s], load_jsonl(f))
        out["approaches"].append(a)
    # examples from the most developed model that has gold predictions
    for key in ("ensemble-q4", "ensemble", "tenant-hazard-triage", "ft-qwen3-4b-2507"):
        f = f"outputs/preds_gold_v2_{key}.jsonl"
        if os.path.exists(f):
            out["examples"] = pick_examples(gold["gold_v2"], load_jsonl(f))
            out["example_source"] = next(l for k, l, *_ in APPROACHES if k == key)
            break
    out["replay"] = replay(gold)
    g = gold["gold_v2"]
    out["gold_composition"] = {s: sum(r["gold"]["severity"] == s for r in g) for s in ("emergency", "significant", "routine", "unclear")}
    if os.path.exists("outputs/synth_stats.json"):
        st = json.load(open("outputs/synth_stats.json"))
        out["synthetic"] = {k: st[k] for k in ("generated", "kept", "train", "val", "severity", "rejected_by_reason", "cost_usd_reported_by_openrouter")}
    for f in ("outputs/train_log_qwen3-4b-2507.json",):
        if os.path.exists(f):
            tl = json.load(open(f)); out["training"] = {"minutes": round(tl["minutes"], 1), **tl["settings"]}
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.js", "w") as fh:
        fh.write("// generated by src/build_showcase.py — do not edit by hand\nwindow.TRIAGE = " + json.dumps(out, indent=1) + ";\n")
    done = [a["label"] for a in out["approaches"] if a["results"]]
    print(f"docs/data.js written. With results: {done}. Examples from: {out['example_source']}")


if __name__ == "__main__":
    main()
