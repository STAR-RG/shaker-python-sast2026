#!/bin/bash
set -e

PARALLEL=${1:-10}
RESULTS_DIR="results_169_shaker"
INPUT_CSV="dataset/169_shaker_experiment.csv"

echo "==> Installing Python dependencies..."
pip install -r experiment/requirements.txt

DEPS_ARG=""
if [ -f "dataset/extra_deps.csv" ]; then
    DEPS_ARG="--deps-csv dataset/extra_deps.csv"
    echo "==> Using extra deps: dataset/extra_deps.csv"
fi

echo "==> Running Shaker experiment on 169 tests (sr=25 nsr=0, parallel=$PARALLEL)..."
python3 experiment/run_experiment.py \
    --input "$INPUT_CSV" \
    --results-dir "$RESULTS_DIR" \
    --parallel "$PARALLEL" \
    --skip-existing \
    --group-by-project \
    --status-csv "$RESULTS_DIR/status.csv" \
    $DEPS_ARG

echo "==> Parsing results..."
python3 experiment/parse_results.py "$RESULTS_DIR" results/shaker_169_results.csv

echo "==> Done. Results saved to results/shaker_169_results.csv"
