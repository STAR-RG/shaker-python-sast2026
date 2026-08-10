#!/bin/bash
set -e

PARALLEL=${1:-10}
RESULTS_DIR="results_rerun"
INPUT_CSV="dataset/169_rerun_experiment.csv"

echo "==> Installing Python dependencies..."
pip install -r experiment/requirements.txt

echo "==> Running ReRun experiment (parallel=$PARALLEL, group-by-project)..."
python3 experiment/run_experiment.py \
    --input "$INPUT_CSV" \
    --results-dir "$RESULTS_DIR" \
    --parallel "$PARALLEL" \
    --skip-existing \
    --group-by-project \
    --status-csv "$RESULTS_DIR/status.csv"

echo "==> Parsing results..."
python3 experiment/parse_results.py "$RESULTS_DIR" results/rerun_results_100.csv

echo "==> Done. Results saved to results/rerun_results_100.csv"
