#!/bin/bash
set -e

# Single-test smoke test for the Docker execution pipeline (Part B).
#
# Runs ONE test from the study's sample under Shaker with a tiny budget
# (sr=1, nsr=2 -> 1x4 stressed + 2 plain = 6 executions) and parses the
# output. Takes ~1 minute and needs the shaker/shaker-image image built
# by ./build.sh.

cd "$(dirname "$0")/.."

python3 experiment/run_experiment.py \
  --input experiment/tests_example.csv \
  --parallel 1 \
  --results-dir results_example \
  --deps-csv dataset/extra_deps.csv

python3 experiment/parse_results.py \
  --results-dir results_example \
  --output results_example.csv

echo
echo "==> Smoke test done. Parsed output:"
cat results_example.csv
