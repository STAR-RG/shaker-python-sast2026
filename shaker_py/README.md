# Shaker (modified copy)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5347973.svg)](https://doi.org/10.5281/zenodo.5347973)

This directory contains the copy of [Shaker](https://github.com/STAR-RG/shaker)
used by this study, with the two extensions the accompanying paper contributes.
See [`NOTICE`](NOTICE) for the exact list of modifications and [`LICENSE`](LICENSE)
for the licence (BSD 2-Clause, same as upstream).

> This is **not** the upstream GitHub Action. Upstream Shaker is packaged as a
> CI action that stresses a whole test suite; here it is invoked directly, one
> test at a time, from inside the Docker image built by `../build.sh`. For the
> action, its inputs, and the `maven` support, see the upstream repository.

## What Shaker does

Shaker amplifies non-determinism by running a test under `stress-ng` while it
executes. A test is run once per stress configuration; if it passes in some runs
and fails in others, it is flaky.

The four configurations in `shaker/stressConfigurations.json` are inherited
unchanged from the original ICSME 2020 study, since evaluating exactly that
configuration on Python is the point of the accompanying paper.

## How this artifact invokes it

You do not normally call this directly: `experiment/run_experiment.py` launches
one container per test (or per project) and `docker/run_in_container.sh` runs the
command below inside it. Reproduced here so the interface is documented:

```bash
python3 /shaker/shaker.py pytest <project-dir> \
    -stp "tests/test_app.py::test_something" \
    -sr  25 \
    -nsr 0 \
    -o   /output/<subpath>
```

| Flag | Meaning |
| --- | --- |
| `-stp`, `--specific-tests-path` | Added by this study. A single Pytest node id. Without it, Shaker stresses the whole suite. |
| `-sr`, `--stress-runs` | Stress runs. Each one executes the test once per configuration, so `-sr 25` is 25x4 = 100 stressed executions. |
| `-nsr`, `--no-stress-runs` | Plain re-executions, with no `stress-ng` running. The ReRun baseline uses `-sr 0 -nsr 100`. |
| `-o`, `--output-folder` | Where the per-run JUnit XML and `__results.json` are written. |

Dependency installation happens in `tool_pytest.py:setup()`, which is the second
extension: it tries `requirements*.txt`, `Pipfile`, and
`pyproject.toml`/`setup.py`/`setup.cfg` in turn, because the sampled projects
declare dependencies in several different formats.

## Requirements

Running Shaker outside the provided Docker image additionally needs `stress-ng`
on the `PATH` and the packages in `shaker/requirements.txt`. The image built by
`../build.sh` already contains both. `stress-ng` is GPL-2.0, invoked as a
separate process, and is not redistributed with this artifact.

## Citing Shaker

> Denini Silva, Leopoldo Teixeira, and Marcelo d'Amorim. "Shake It! Detecting
> Flaky Tests Caused by Concurrency with Shaker." In _2020 IEEE International
> Conference on Software Maintenance and Evolution (ICSME)_, pp. 301-311, 2020.
