#!/usr/bin/env bash
#
# Reproduce the paper's results with nothing installed on your machine but
# Docker (Part A of this artifact).
#
#   ./run_analysis.sh              # build the image and run the full analysis
#   ./run_analysis.sh my-outdir    # write results somewhere other than ./output
#
# Every table and figure in the paper is written to ./output on the host:
#   output/generated/tab_rq1_contingency.tex
#   output/generated/tab_rq2_repro.tex
#   output/generated/tab_rq3_traits.tex
#   output/img/fig_detection_rate.png
#   output/img/fig_overlap.png
#   output/img/fig_categories.png
#
# Takes about a minute after the image is built. No test execution, no network
# access at run time, and nothing is written back into the artifact.
set -euo pipefail

cd "$(dirname "$0")"

IMAGE=${IMAGE:-shaker/analysis}
OUT_DIR=${1:-output}

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker not found. Install Docker, or follow the non-Docker" >&2
    echo "       instructions in the Installation section of README.md." >&2
    exit 1
fi

echo "==> Building $IMAGE (first run only; a few minutes)..."
docker build -f docker/analysis.Dockerfile -t "$IMAGE" .

mkdir -p "$OUT_DIR"
OUT_ABS=$(cd "$OUT_DIR" && pwd)

# On Linux, run as the invoking user so the generated files are owned by you and
# not by root. Docker Desktop (macOS/Windows) already maps ownership for us.
set --
if [ "$(uname -s)" = "Linux" ]; then
    set -- -u "$(id -u):$(id -g)"
fi

echo "==> Running the analysis; results -> $OUT_ABS"
docker run --rm "$@" -v "$OUT_ABS:/out" "$IMAGE"
