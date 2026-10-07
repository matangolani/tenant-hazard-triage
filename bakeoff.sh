#!/usr/bin/env bash
# Tenant Hazard Triage — zero-shot bake-off v2.
# Runs each model over both test sets (gold_v2 + official), plus the rules baseline,
# scores everything, then prints a comparison with paired significance tests.
# Safe to stop (Ctrl+C) and re-run: finished predictions are kept.
#
# Usage (from the project folder):   bash bakeoff.sh
set -euo pipefail
cd "$(dirname "$0")"

MODELS=("qwen3.5:4b" "gemma4:e4b")
SETS=("gold_v2" "official")

for set in "${SETS[@]}"; do
  [ -f "data/${set}.jsonl" ] || { echo "Missing data/${set}.jsonl — see README.md"; exit 1; }
done

for set in "${SETS[@]}"; do
  python3 src/baseline_rules.py --in "data/${set}.jsonl" --out "outputs/preds_${set}_rules.jsonl" >/dev/null
done
echo "rules baseline done"

for m in "${MODELS[@]}"; do
  s=$(echo "$m" | sed 's/[^A-Za-z0-9._-]/_/g')
  for set in "${SETS[@]}"; do
    echo; echo "=== $m on $set ==="
    python3 src/zeroshot_runner.py --model "$m" --gold "data/${set}.jsonl"
    python3 src/evaluate.py --gold "data/${set}.jsonl" --pred "outputs/preds_${set}_${s}.jsonl" \
      --name "Zero-shot $m" --json "outputs/metrics_${set}_${s}.json" > "outputs/report_${set}_${s}.txt"
    echo "scored -> outputs/report_${set}_${s}.txt"
  done
  ollama stop "$m" 2>/dev/null || true   # free memory before the next model
done

echo
python3 src/compare.py
