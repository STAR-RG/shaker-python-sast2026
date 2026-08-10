# Analysis pipeline

Regenerates every table and figure in the paper from the two result CSVs in
`results/` (plus cheap, cached project metadata). No test execution is required
or performed.

Full instructions, covering requirements, installation, and expected output, are
in the [README at the root of this artifact](../README.md). This file only
documents the pipeline itself.

## Inputs

- `results/rerun_results_100.csv`: ReRun baseline (`sr=0, nsr=100`).
- `results/shaker_169_results.csv`: Shaker (`sr=25, nsr=0` → 25×4 stressed).
- `dataset/tests.csv`, `dataset/flaky.csv`: Gruber et al. ground truth.
- `dataset/100NOD_manual_classification.csv`: manual flakiness categories.
- `dataset/project_metadata.csv`: cached project size metrics (RQ3).
- `dataset/projects.csv`: repo URLs + commit hashes (only for `fetch_metadata`).

## Run order

The easiest way to run all of this is `./run_analysis.sh` from the root of the
artifact, which executes the sequence below inside a Docker container and needs
no local Python. To run it directly instead, from the **root of this artifact**
with the virtualenv active:

```bash
python -m analysis.load                 # sanity: coverage note (137 common tests)
python -m analysis.rq1_shaker_vs_rerun  # -> paper/generated/tab_rq1_contingency.tex
python -m analysis.rq2_reproducibility  # -> paper/generated/tab_rq2_repro.tex
python -m analysis.rq3_characteristics  # -> paper/generated/tab_rq3_traits.tex
python -m analysis.make_figures         # -> paper/img/fig_*.png
```

`fetch_metadata` and `verify_selection` are optional and not part of this
sequence; see the root README.

Outputs land in `paper/generated/*.tex` (the files the paper `\input`s) and
`paper/img/*.png`. Both directories are created automatically.

## Modules

| Module | Role |
| --- | --- |
| `load.py` | Shared data layer: joins both result CSVs with the ground truth and manual categories. Run directly, prints the coverage note. |
| `rq1_shaker_vs_rerun.py` | RQ1: paired contingency table and McNemar's test. |
| `rq2_reproducibility.py` | RQ2: per-technique and union recall, plus why non-reproduced tests failed to flip. |
| `rq3_characteristics.py` | RQ3: reproduced vs. missed tests (Mann-Whitney U, Cliff's δ). |
| `make_figures.py` | Detection-rate, overlap, and flakiness-category figures. |
| `fetch_metadata.py` | Clones each project in the analysed sample at its recorded commit and records size metrics. Incremental, so it is a no-op against the shipped cache. |
| `verify_selection.py` | Re-derives the object-selection filter behind `dataset/tests.csv`. Needs a 238 MB download; see the root README. |
| `stats_util.py` | Wilson CI, McNemar, and Cliff's δ helpers. Imported, not run. |
