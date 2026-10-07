#!/usr/bin/env bash
# Load the fine-tuned GGUF into Ollama as "tenant-hazard-triage", score it on both test sets with the same
# runner used for the bake-off, then score the laptop ensemble (tenant-hazard-triage + qwen3.5:4b second opinion).
#   bash scripts/deploy_ollama.sh ~/Downloads/gguf_qwen3-4b-2507          # folder or .gguf file
# Takes roughly 10–20 minutes on an M-series Mac. Safe to re-run: finished predictions are kept.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${1:?give the path to the downloaded .gguf file or its folder}"
if [ -d "$SRC" ]; then GGUF=$(ls "$SRC"/*.gguf | grep -iv mmproj | head -1); else GGUF="$SRC"; fi
[ -f "$GGUF" ] || { echo "No .gguf found at $SRC"; exit 1; }
GGUF=$(cd "$(dirname "$GGUF")" && pwd)/$(basename "$GGUF")
echo "using $GGUF ($(du -h "$GGUF" | cut -f1))"
sed "s|{{GGUF_PATH}}|$GGUF|" deploy/Modelfile.template > deploy/Modelfile
ollama create tenant-hazard-triage -f deploy/Modelfile

SECOND="qwen3.5:4b"
ollama list | grep -q "^$SECOND" || ollama pull "$SECOND"

for set in gold_v2 official; do
  echo; echo "=== tenant-hazard-triage on $set ==="
  python3 src/zeroshot_runner.py --model tenant-hazard-triage --gold "data/${set}.jsonl"
  python3 src/evaluate.py --gold "data/${set}.jsonl" --pred "outputs/preds_${set}_tenant-hazard-triage.jsonl" \
    --name "tenant-hazard-triage (fine-tuned, Ollama Q4)" --json "outputs/metrics_${set}_tenant-hazard-triage.json" > "outputs/report_${set}_tenant-hazard-triage.txt"
done
ollama stop tenant-hazard-triage 2>/dev/null || true

# Ensemble with the Q4 model; reuses the committed qwen3.5:4b predictions from the bake-off.
python3 src/ensemble.py --primary tenant-hazard-triage --name ensemble-q4
python3 src/compare.py --sets gold_v2 official synth_val
python3 src/check_results.py --write      # add the new runs to the CI snapshot
python3 src/build_showcase.py             # and to the showcase page
echo; echo "Done. Send outputs/COMPARISON.md and the 4 new outputs/preds_*_{tenant-hazard-triage,ensemble-q4}.jsonl files."
