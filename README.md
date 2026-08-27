# Evaluating Shaker for Flaky Test Detection in Python Projects: Replication Package

This artifact accompanies the paper **"Evaluating Shaker for Flaky Test Detection
in Python Projects"**, published at SAST 2026 (11th Brazilian Symposium on
Systematic and Automated Software Testing). The accepted version is bundled as
[`paper.pdf`](paper.pdf) in the root of this artifact.

The paper evaluates Shaker, a flaky-test detector that injects CPU and memory
stress to amplify non-determinism, on Python for the first time. It compares
Shaker against a budget-matched plain re-execution ("ReRun") baseline on 137
ground-truth flaky tests and reports a null result: at an equal execution budget,
stress injection detects no more flaky tests than simply rerunning them.

This package lets you reproduce both halves of the study:

1. **Analysis.** Turns the shipped result CSVs into every table and figure in the
   paper. It runs in under a minute and executes no tests. You can run it inside
   the provided Docker image or in a plain Python virtualenv.
2. **Execution.** Re-runs each ground-truth flaky test many times inside isolated
   Docker containers, under Shaker's stress and under the ReRun baseline,
   regenerating those CSVs. Optional and expensive (days of compute).

If you have Docker and want the short path, `./run_analysis.sh` rebuilds every
table and figure of the paper into `./output/`.

Every object is a test already confirmed flaky in the dataset of Gruber et al.
Each technique observes a test 100 times and detects it when it sees at least one
pass and one fail; otherwise it misses it. ReRun uses 100 plain re-executions
(`sr=0, nsr=100`); Shaker uses 25 stress runs of 4 workloads each (`sr=25,
nsr=0`, so 25×4 = 100 stressed executions).

Both techniques are run over the same 169 tests, since
`dataset/169_rerun_experiment.csv` and `dataset/169_shaker_experiment.csv` differ
only in `sr`/`nsr`, which is what makes the comparison paired. ReRun yielded
valid observations for 165 of them and Shaker for 137; the analysis uses the 137
common to both.

---

## Layout

| Path                                            | Contents                                                                |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| `analysis/`                                     | Scripts that rebuild the paper's tables/figures from `results/`.        |
| `experiment/`                                   | Docker orchestration runner and results parser.                         |
| `docker/`                                       | Two images: `analysis.Dockerfile` (Part A) and `Dockerfile` (Part B).   |
| `shaker_py/`                                    | The Shaker tool, modified for this study (see `shaker_py/NOTICE`).      |
| `dataset/`                                      | Study inputs: ground truth, manual labels, project list, runner inputs. |
| `results/`                                      | The two parsed result CSVs the analysis consumes (reference outputs).   |
| `raw_results/`                                  | Partial raw per-test ReRun trees (32 of 165 tests).                     |
| `run_analysis.sh`                               | Part A in Docker: one command, no local Python needed.                  |
| `build.sh`, `run_rerun.sh`, `run_169_shaker.sh` | Part B drivers (test execution; optional).                              |
| `paper.pdf`                                     | The accepted paper.                                                     |
| `LICENSE`                                       | BSD 2-Clause (code) + CC BY 4.0 (data). See [License](#license).        |

---

## Requirements

### Part 1. Analysis (reproduces the paper; recommended path)

There are two routes. A1 requires only Docker on your machine, A2 only Python.
Both produce byte-identical tables.

**A1. Docker (recommended for evaluation)**

|              |                                                                                                                |
| ------------ | -------------------------------------------------------------------------------------------------------------- |
| **OS**       | Any host with Docker (Linux, macOS, Windows). Verified on macOS (arm64) with Docker 27.4.                      |
| **Software** | Docker with a running daemon. Nothing else: no Python and no packages installed on the host.                   |
| **Hardware** | Any modern machine. No special CPU, GPU, or peripherals.                                                       |
| **Memory**   | < 1 GB                                                                                                         |
| **Disk**     | ~550 MB for the image, plus ~50 MB for this artifact unpacked                                                  |
| **Network**  | Only while building the image, which pulls the base image and three Python packages. The run itself is offline. |
| **Runtime**  | ~2 min to build the image (once), then under 1 minute per analysis run                                         |

**A2. Local Python**

|                     |                                                                              |
| ------------------- | ---------------------------------------------------------------------------- |
| **OS**              | Any (Linux, macOS, Windows). Developed on macOS and Linux.                   |
| **Software**        | Python **3.10 or newer**. No Docker. No network access needed.               |
| **Python packages** | `analysis/requirements.txt`: `scipy>=1.11`, `pandas>=2.0`, `matplotlib>=3.7` |
| **Hardware**        | Any modern machine. No special CPU, GPU, or peripherals.                     |
| **Memory**          | < 500 MB                                                                     |
| **Disk**            | ~50 MB (this artifact unpacked)                                              |
| **Runtime**         | Under 1 minute for the full analysis                                         |

Last verified with Python 3.14.5, scipy 1.18.0, pandas 3.0.5, matplotlib 3.11.1.

### Part 2. Re-running the experiments (optional)

|              |                                                                                                                                                                                                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **OS**       | Linux or macOS (the runner shells out to the `docker` CLI).                                                                                                                                                                                                       |
| **Software** | Docker (running daemon) + Python 3.10+ with `experiment/requirements.txt` (`docker`, `rich`).                                                                                                                                                                     |
| **Hardware** | Each container is capped at **2 CPUs and 2 GB RAM** (`CONTAINER_CPUS` / `CONTAINER_MEMORY` in `experiment/run_experiment.py`). The default of 10 parallel containers therefore wants ~20 cores and ~20 GB RAM; lower the `PARALLEL` argument on smaller machines. |
| **Network**  | Required. Each container clones its project from GitHub and installs dependencies from PyPI.                                                                                                                                                                      |
| **Disk**     | Several GB for the raw result trees.                                                                                                                                                                                                                              |
| **Runtime**  | Days. 137 to 165 tests, 100 executions each, under two techniques.                                                                                                                                                                                                |

> Shaker saturates the machine with `stress-ng` by design, so running Part 2 will
> make the host highly unresponsive. Do not run it on a machine you are using
> interactively.

### Part 3. Verifying the object-selection filter (optional)

`analysis/verify_selection.py` re-derives the filter behind `dataset/tests.csv`
from Gruber et al.'s published dataset. It needs `TestsOverview.csv` (238 MB),
which is not bundled here; download it from
<https://doi.org/10.5281/zenodo.4450435>. Expect ~2 GB of RAM while it runs.

---

## Installation

### A1. Docker (nothing to install but Docker)

From the root of this artifact:

```bash
./run_analysis.sh
```

That builds the analysis image and runs the whole Part A pipeline. It doubles as
the verification step: it needs no virtualenv, writes nothing into the artifact,
and leaves every generated table and figure in `./output/`.

### A2. Local Python

From the root of this artifact:

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r analysis/requirements.txt
```

### Verifying the installation

Either route must print the numbers below. `./run_analysis.sh` prints them as
part of its run; under A2, run these two commands with the virtualenv active.

```bash
python -m analysis.load
```

```
ReRun tests: 165 | Shaker tests: 137 | common (analysed): 137
```

```bash
python -m analysis.rq1_shaker_vs_rerun
```

```
  Shaker detect: 51/137 = 37.2%  CI=(29.6, 45.6)
  ReRun  detect: 49/137 = 35.8%  CI=(28.2, 44.1)
  McNemar exact two-sided p = 0.839
```

Those are the numbers reported in the paper's abstract (37.2% vs. 35.8%, McNemar
exact _p_ = 0.84) and in Table 1.

---

## Part A. Reproduce the paper's results

### A1. With Docker

```bash
./run_analysis.sh                # results -> ./output/
./run_analysis.sh my-outdir      # or write them somewhere else
```

The script builds `shaker/analysis` from `docker/analysis.Dockerfile`, runs the
five analysis steps in order, and bind-mounts the output directory so the files
appear on your host:

```
output/generated/tab_rq1_contingency.tex     <- Table 1 (RQ1)
output/generated/tab_rq2_repro.tex           <- Table 2 (RQ2)
output/generated/tab_rq3_traits.tex          <- Table 3 (RQ3)
output/img/fig_detection_rate.png
output/img/fig_overlap.png
output/img/fig_categories.png
```

Nothing is written back into the artifact, and the container needs no network. To
run a single step, or to get a shell inside the image, pass a command:

```bash
docker run --rm -v "$PWD/output:/out" shaker/analysis python -m analysis.rq2_reproducibility
docker run --rm -it --entrypoint bash shaker/analysis
```

> On Linux, `run_analysis.sh` passes `-u $(id -u):$(id -g)` so the generated
> files belong to you rather than to root. Docker Desktop handles this itself on
> macOS and Windows.

The image carries only what the analysis reads (`analysis/`, `dataset/`,
`results/`). `fetch_metadata.py` and `verify_selection.py` sit outside the
pipeline, since both need network access or a large external download, so run
those under A2 if you want them.

### A2. Without Docker

Run from this directory, with the virtualenv active:

```bash
python -m analysis.load                 # sanity check: prints the coverage note
python -m analysis.rq1_shaker_vs_rerun  # -> paper/generated/tab_rq1_contingency.tex
python -m analysis.rq2_reproducibility  # -> paper/generated/tab_rq2_repro.tex
python -m analysis.rq3_characteristics  # -> paper/generated/tab_rq3_traits.tex
python -m analysis.make_figures         # -> paper/img/fig_*.png
python -m analysis.fetch_metadata       # OPTIONAL: re-clones projects to recompute metadata
```

Outputs are written under `paper/generated/*.tex` and `paper/img/*.png`, both
created automatically. These are the exact files the paper `\input`s.

`fetch_metadata` is optional and is not needed to reproduce anything: a cached
`dataset/project_metadata.csv` is shipped, so RQ3 runs without cloning. It only
fetches the projects that appear in the result CSVs (85 of them) and is
incremental, so against the shipped cache it is a no-op; deleting the cache first
makes it re-clone all 85, which requires network access.

### Expected output

| Result                                     | Value                                                                          |
| ------------------------------------------ | ------------------------------------------------------------------------------ |
| **RQ1** Shaker vs. ReRun                   | 51/137 (37.2%) vs. 49/137 (35.8%); McNemar exact _p_ = 0.839                   |
| **RQ1** excluding truncated runs (n=119)   | 46/119 vs. 45/119; _p_ = 1.000                                                 |
| **RQ2** reproduced by either technique     | 62/137 = 45.3%, CI (37.2, 53.6)                                                |
| **RQ2** never flipped / truncated / broken | 61 / 13 / 1                                                                    |
| **RQ3** categories (n=31 labelled)         | random 13/19, network 1/6, async wait 2/3                                      |
| **RQ3** project size (n=137)               | median 1041 (reproduced) vs. 3551 LOC (missed); _p_ < 0.001; Cliff's δ = −0.36 |

### What each analysis script does

- `load.py`: shared data layer that joins the two result CSVs with the Gruber
  ground truth and manual categories. Run directly, it prints the coverage note.
- `rq1_shaker_vs_rerun.py` (RQ1): paired contingency table and McNemar's test.
- `rq2_reproducibility.py` (RQ2): per-technique and union recall, plus a
  breakdown of why non-reproduced tests failed to flip.
- `rq3_characteristics.py` (RQ3): compares reproduced against missed tests
  (Mann-Whitney U, Cliff's δ) on project traits.
- `make_figures.py`: detection-rate, overlap, and flakiness-category figures.
- `fetch_metadata.py`: clones each project at its recorded commit and records
  size metrics into `dataset/project_metadata.csv`.
- `verify_selection.py`: re-derives the object-selection filter (see Part C).
- `stats_util.py`: Wilson CI, McNemar, and Cliff's δ helpers (imported, not run).

---

## Part B. Re-run the experiments (Docker required, optional)

```bash
./build.sh                      # build the shaker/shaker-image Docker image
./run_rerun.sh [PARALLEL]       # ReRun baseline -> results/rerun_results_100.csv
./run_169_shaker.sh [PARALLEL]  # Shaker         -> results/shaker_169_results.csv
```

`PARALLEL` is the number of concurrent containers (default `10`; see the hardware
note under [Requirements](#part-2-re-running-the-experiments-optional)). Each
script installs `experiment/requirements.txt`, runs the tests, and re-parses them
into the corresponding CSV under `results/`, overwriting the shipped reference
copy. Back it up first if you want to compare.

### Smoke-testing the execution pipeline

Before committing to a multi-day run, check that the image and the runner work:

```bash
./build.sh                        # once
bash experiment/run_example.sh    # ~1 minute
```

This runs a single test from the study's sample (`wiki-futures`) with a tiny
budget (`sr=1, nsr=2`, i.e. 1×4 stressed + 2 plain = 6 executions) and prints the
parsed CSV.

The pipeline is working if `Error (no result)` is 0 and `total_runs` is 6:

```
  TOTAL TESTS:          1
  Error (no result):       0  (0.0%)

repo_name,test_slug,sr,nsr,total_runs,pass_count,fail_count,failure_rate,is_flaky,status
wiki-futures,tests__test_dispatcher__test_content_size,1,2,6,...
```

Do not expect a particular verdict. This test is flaky, so its pass/fail split
varies from run to run, and six executions are often too few for it to flip at
all. Both `status: flaky` and `status: all_passed` are fine outcomes here, and we
observed both while preparing this artifact. A test that neither flips nor errors
is the RQ2 phenomenon the paper reports; see the note on reproducibility at the
end of this section.

### What each execution component does

- `build.sh`: builds the `shaker/shaker-image` image from `docker/Dockerfile`,
  which bundles `stress-ng`, Python tooling, and the Shaker tool.
- `run_rerun.sh`: runs the ReRun baseline on `dataset/169_rerun_experiment.csv`
  (`sr=0, nsr=100`) and parses the output.
- `run_169_shaker.sh`: runs Shaker on `dataset/169_shaker_experiment.csv`
  (`sr=25, nsr=0`) with the extra dependencies in `dataset/extra_deps.csv`.
- `experiment/run_experiment.py`: reads a test CSV and launches one Docker
  container per test (or per project group); writes raw per-test result trees.
  Key options: `--input`, `--results-dir`, `--parallel`, `--image`
  (default `shaker/shaker-image`), `--timeout` (seconds, default 5400),
  `--deps-csv`, `--skip-existing`, `--group-by-project`, `--status-csv`.
- `experiment/parse_results.py`: aggregates a raw results directory into a result
  CSV with columns `repo_name, test_slug, sr, nsr, total_runs, pass_count,
fail_count, failure_rate, is_flaky, status`.

> **Note on reproducibility.** Flakiness is environment-sensitive by definition,
> and that is one of the paper's findings (RQ2). Re-running Part 2 on different
> hardware is expected to produce somewhat different per-test outcomes. The
> shipped CSVs in `results/` are the exact ones behind the paper's numbers.

---

## Part C. Verify the object-selection filter (optional)

The script that originally produced `dataset/tests.csv` from Gruber et al.'s data
was lost. `analysis/verify_selection.py` recovers and verifies it:

```bash
# download TestsOverview.csv (238 MB) from https://doi.org/10.5281/zenodo.4450435
python -m analysis.verify_selection /path/to/TestsOverview.csv
```

It confirms the recovered filter

```
Verdict_sameOrder == "Flaky" AND Order-dependent == False AND Flaky_Infrastructure == False
```

yields 952 candidate tests across 277 projects, and that every analyzed test
locatable in the ground truth is non-order-dependent, so the sample contains no
order-dependent tests by construction, as reported in the paper.

---

## Inputs and data files

- `dataset/tests.csv`, `dataset/flaky.csv`: the ground-truth flaky tests selected
  for this study (derived from Gruber et al.; see Part C).
- `dataset/100NOD_manual_classification.csv`: manual flakiness categories for a
  labelled subset (RQ3).
- `dataset/projects.csv`: repository URLs and commit hashes, 161 rows. These are
  the 159 projects that contribute tests to `tests.csv`, plus `data-genie` and
  `pyblnet`, which contribute one executed test each without appearing in the
  452-test candidate set (see the note below).
- `dataset/project_metadata.csv`: cached project size metrics (regenerated by
  `fetch_metadata.py`).
- `dataset/169_rerun_experiment.csv`, `dataset/169_shaker_experiment.csv`:
  ready-to-run runner inputs (`repo_url, commit_hash, test_path, num_run_shaker,
nsr`), derived from `tests.csv` + `projects.csv`. Same 169 tests in both; they
  differ only in `sr`/`nsr`.
- `dataset/extra_deps.csv`: extra pip dependencies some runs need.
- `raw_results/results_rerun.zip`: a partial snapshot of the raw per-test ReRun
  output trees (container/install logs and pytest XML), covering 32 tests across
  22 projects rather than the full 165. Re-parsing it reproduces those 32 rows
  exactly as they appear in `results/rerun_results_100.csv`, with one exception
  (`gwosc…test_fetch_run_json`, captured at 83 of its 100 runs; same verdict).
  Inspect it without touching the reference results:

  ```bash
  unzip raw_results/results_rerun.zip -d /tmp/raw
  python experiment/parse_results.py /tmp/raw/results_rerun /tmp/reparsed.csv
  ```

  > Do not write the output over `results/rerun_results_100.csv`. The zip covers
  > only a fifth of the tests, so doing so would truncate the reference data the
  > analysis depends on.

> **Note on the analysed sample.** 135 of the 137 analysed tests are in the
> 452-test candidate set in `dataset/tests.csv`; the two from `data-genie` and
> `pyblnet` are not. They were executed and are reported, but they fall outside
> the candidate set the selection filter produced. `python -m analysis.load`
> prints this coverage (`in_gt452`), and no reported result filters on it.

---

## Modifications to Shaker

`shaker_py/` contains a modified copy of Shaker. Both changes were required to run
the study and are contributions of the paper; neither alters Shaker's detection
mechanism or its stress configurations:

1. **Single-test execution** (`-stp` / `--specific-tests-path`). Upstream Shaker
   stresses a whole test suite, whereas the ground truth identifies flakiness per
   individual test.
2. **Heterogeneous dependency resolution.** The sampled projects declare
   dependencies in several different formats.

One file was also removed: upstream's `analytics.py`, an optional reporting
script that POSTed run summaries to a third-party endpoint that is no longer
operated. It was never imported or invoked, so dropping it changes no behaviour.
It is gone so that nothing here contacts an external service beyond cloning the
subject projects and installing their dependencies.

The four `stress-ng` configurations in `shaker_py/shaker/stressConfigurations.json`
are inherited unchanged from the original Shaker study, since evaluating exactly
that configuration on Python is the point of the paper. See `shaker_py/NOTICE`.

Upstream: <https://github.com/STAR-RG/shaker> and
<https://doi.org/10.5281/zenodo.5347973>

---

## Ethical and legal statement

This artifact contains no personal, human-subject, or otherwise sensitive data.
All data are execution metadata (pass/fail verdicts, run counts, and repository
size metrics) for automated test suites of publicly available open-source Python
packages published on PyPI. No human participants were involved and no study with
human subjects was conducted.

The subject projects themselves are not redistributed. The experiment clones each
one from its own public repository at the commit recorded in
`dataset/projects.csv`, and each remains under its own license.

The ground-truth files in `dataset/` are derived from the dataset of Gruber
et al., licensed CC BY 4.0, and are redistributed here under the same license
with attribution.

---

## License

- Code (`analysis/`, `experiment/`, `docker/`, `shaker_py/`, `*.sh`):
  BSD 2-Clause License
- Data (`dataset/`, `results/`, `raw_results/`):
  Creative Commons Attribution 4.0 International (CC BY 4.0)

See `LICENSE` for the full text, the scope of each license, and the third-party
attributions (Shaker, the Gruber et al. dataset, `stress-ng`, and the subject
projects).

## How to cite

If you use this artifact, please cite the accompanying paper:

> Gabriela Leal, Denini Silva, and Leopoldo Teixeira. "Evaluating Shaker for
> Flaky Test Detection in Python Projects." In _Proceedings of the 11th Brazilian
> Symposium on Systematic and Automated Software Testing (SAST)_, 2026.

```bibtex
@inproceedings{leal2026shakerpython,
  title     = {Evaluating Shaker for Flaky Test Detection in Python Projects},
  author    = {Leal, Gabriela and Silva, Denini and Teixeira, Leopoldo},
  booktitle = {Proceedings of the 11th Brazilian Symposium on Systematic and
               Automated Software Testing (SAST)},
  year      = {2026}
}
```

To cite this artifact specifically:

```bibtex
@misc{leal2026shakerpythonartifact,
  title     = {Replication Package for "Evaluating Shaker for Flaky Test
               Detection in Python Projects"},
  author    = {Leal, Gabriela and Silva, Denini and Teixeira, Leopoldo},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22119340},
  url       = {https://doi.org/10.5281/zenodo.22119340}
}
```

The study builds on two prior works, which should be cited where relevant:

```bibtex
@inproceedings{silva2020shaker,
  title        = {Shake it! Detecting flaky tests caused by concurrency with Shaker},
  author       = {Silva, Denini and Teixeira, Leopoldo and d'Amorim, Marcelo},
  booktitle    = {2020 IEEE International Conference on Software Maintenance and
                  Evolution (ICSME)},
  pages        = {301--311},
  year         = {2020},
  organization = {IEEE}
}

@inproceedings{gruber2021empirical,
  title        = {An empirical study of flaky tests in Python},
  author       = {Gruber, Martin and Lukasczyk, Stephan and Kroi{\ss}, Florian
                  and Fraser, Gordon},
  booktitle    = {2021 14th IEEE Conference on Software Testing, Verification and
                  Validation (ICST)},
  pages        = {148--158},
  year         = {2021},
  organization = {IEEE},
  doi          = {10.1109/icst49551.2021.00026}
}

@dataset{gruber_2021_4450435,
  title     = {Dataset of An Empirical Study of Flaky Tests in Python},
  author    = {Gruber, Martin},
  year      = {2021},
  month     = jan,
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.4450435},
  url       = {https://doi.org/10.5281/zenodo.4450435}
}
```
