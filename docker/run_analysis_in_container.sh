#!/usr/bin/env bash
#
# Entrypoint of the analysis image (docker/analysis.Dockerfile).
#
# With no arguments it runs the full Part A pipeline and writes the paper's
# tables and figures to /out (bind-mount it to see them on the host).
#
# With arguments, it runs them instead, e.g.
#   docker run --rm -v "$PWD/output:/out" shaker/analysis \
#       python -m analysis.rq1_shaker_vs_rerun
#   docker run --rm -it --entrypoint bash shaker/analysis
set -euo pipefail

cd /artifact

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

if ! touch /out/.write-test 2>/dev/null; then
    echo "error: /out is not writable from inside the container." >&2
    echo "       Mount a writable directory, e.g.  -v \"\$PWD/output:/out\"" >&2
    echo "       On Linux you may also need  -u \"\$(id -u):\$(id -g)\"" >&2
    exit 1
fi
rm -f /out/.write-test

step() {
    echo
    echo "================================================================"
    echo "==> $1"
    echo "================================================================"
    shift
    "$@"
}

step "Sanity check: dataset coverage"      python -m analysis.load
step "RQ1: Shaker vs. ReRun (McNemar)"     python -m analysis.rq1_shaker_vs_rerun
step "RQ2: Reproducibility"                python -m analysis.rq2_reproducibility
step "RQ3: Test/project characteristics"   python -m analysis.rq3_characteristics
step "Figures"                             python -m analysis.make_figures

echo
echo "================================================================"
echo "==> Done. Generated files, in the host directory mounted at /out"
echo "    (./output unless you asked for another one):"
echo "================================================================"
find /out -type f \( -name '*.tex' -o -name '*.png' \) | sed 's|^/out/|  |' | sort

cat <<'EOF'

Expected headline numbers (paper abstract and Table 1):

  Shaker detect: 51/137 = 37.2%  CI=(29.6, 45.6)
  ReRun  detect: 49/137 = 35.8%  CI=(28.2, 44.1)
  McNemar exact two-sided p = 0.839

EOF
