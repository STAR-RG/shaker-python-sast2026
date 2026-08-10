#!/usr/bin/env python3
"""
Shared data layer for the Shaker/Python analysis.

Loads the two surviving result CSVs from ``results/`` and joins them into a
single per-test frame, plus helpers to map tests to their Gruber et al. ground
truth and to the ``100NOD`` manual flakiness categories.

Result CSV schema (produced by experiment/parse_results.py):
    repo_name, test_slug, sr, nsr, total_runs, pass_count, fail_count,
    failure_rate, is_flaky, status

Techniques compared (budget-matched at 100 executions/test):
    ReRun  -> results/rerun_results_100.csv   (sr=0,  nsr=100)
    Shaker -> results/shaker_169_results.csv  (sr=25, nsr=0  -> 25x4 stressed)
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RERUN_CSV = ROOT / "results" / "rerun_results_100.csv"
SHAKER_CSV = ROOT / "results" / "shaker_169_results.csv"

TESTS_CSV = ROOT / "dataset" / "tests.csv"          # 452 ground-truth flaky
FLAKY_CSV = ROOT / "dataset" / "flaky.csv"          # confirmed-flaky subset
NOD_CSV = ROOT / "dataset" / "100NOD_manual_classification.csv"
PROJECTS_CSV = ROOT / "dataset" / "projects.csv"
METADATA_CSV = ROOT / "dataset" / "project_metadata.csv"  # produced by fetch_metadata.py

NOMINAL_BUDGET = 100  # intended executions per test on both techniques


# --------------------------------------------------------------------------- #
# slug reconstruction (mirror of experiment/run_experiment.py)
# --------------------------------------------------------------------------- #
def sanitize_test_path(test_path: str) -> str:
    """Canonical test_slug from a pytest node id (matches the experiment runner)."""
    path = re.sub(r"\.py$", "", test_path.split("::")[0])
    name = "::".join([path] + test_path.split("::")[1:])
    return re.sub(r"[/\\:]+", "__", name)


def _slugs_from_meta_row(row: dict) -> list[str]:
    """Candidate slugs from a Gruber-metadata row (Project_Name/filename/class/func)."""
    fn = row.get("Test_filename", "") or ""
    cn = row.get("Test_classname", "") or ""
    func = row.get("Test_funcname", "") or ""
    param = row.get("Test_parametrization", "") or ""
    # Gruber's metadata already stores the parametrisation with its brackets
    # (e.g. "[sam@mail.com-pass-correct]"); wrapping it again would never match
    # the pytest node id recorded in the result CSVs.
    funcp = func + ((param if param.startswith("[") else f"[{param}]") if param else "")
    cls = cn.split(".")[-1] if cn else ""
    variants = []
    if cls:
        variants.append(f"{fn}::{cls}::{funcp}")
    variants.append(f"{fn}::{funcp}")
    return [sanitize_test_path(v) for v in variants]


def _ground_truth_keys(path: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            repo = row["Project_Name"]
            for slug in _slugs_from_meta_row(row):
                keys.add((repo, slug))
    return keys


def _category_map() -> dict[tuple[str, str], str]:
    cat: dict[tuple[str, str], str] = {}
    with open(NOD_CSV, newline="") as f:
        for row in csv.DictReader(f):
            repo = row["Project_Name"]
            for slug in _slugs_from_meta_row(row):
                cat[(repo, slug)] = row["flakiness category"]
    return cat


# --------------------------------------------------------------------------- #
# frame construction
# --------------------------------------------------------------------------- #
def _load_result(path: Path, technique: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["is_flaky"] = df["is_flaky"].astype(str).str.strip().str.lower() == "true"
    df["truncated"] = df["total_runs"] < NOMINAL_BUDGET
    df["technique"] = technique
    df["key"] = list(zip(df["repo_name"], df["test_slug"]))
    return df


def load_paired() -> pd.DataFrame:
    """
    One row per test present in BOTH result files (the 137-test common set).

    Columns: repo_name, test_slug, key,
             shaker_flaky, rerun_flaky, shaker_status, rerun_status,
             shaker_runs, rerun_runs, shaker_failrate, rerun_failrate,
             any_truncated, category, in_gt452, in_gt_flaky
    """
    shaker = {row["key"]: row for row in _load_result(SHAKER_CSV, "shaker").to_dict("records")}
    rerun = {row["key"]: row for row in _load_result(RERUN_CSV, "rerun").to_dict("records")}
    common = sorted(set(shaker) & set(rerun))

    cat = _category_map()
    gt452 = _ground_truth_keys(TESTS_CSV)
    gtflaky = _ground_truth_keys(FLAKY_CSV)

    meta = None
    if METADATA_CSV.exists():
        meta = pd.read_csv(METADATA_CSV).set_index("repo_name")

    rows = []
    for key in common:
        s, r = shaker[key], rerun[key]
        repo, slug = key
        row = {
            "repo_name": repo,
            "test_slug": slug,
            "key": key,
            "shaker_flaky": bool(s["is_flaky"]),
            "rerun_flaky": bool(r["is_flaky"]),
            "shaker_status": s["status"],
            "rerun_status": r["status"],
            "shaker_runs": int(s["total_runs"]),
            "rerun_runs": int(r["total_runs"]),
            "shaker_failrate": float(s["failure_rate"]),
            "rerun_failrate": float(r["failure_rate"]),
            "any_truncated": bool(s["truncated"] or r["truncated"]),
            "category": cat.get(key),
            "in_gt452": key in gt452,
            "in_gt_flaky": key in gtflaky,
        }
        if meta is not None and repo in meta.index:
            m = meta.loc[repo]
            row["n_files"] = m.get("n_files")
            row["n_test_files"] = m.get("n_test_files")
            row["loc"] = m.get("loc")
            row["n_deps"] = m.get("n_deps")
        rows.append(row)

    df = pd.DataFrame(rows).sort_values(["repo_name", "test_slug"]).reset_index(drop=True)
    df["either_flaky"] = df["shaker_flaky"] | df["rerun_flaky"]
    return df


def load_single(technique: str) -> pd.DataFrame:
    """Full (un-paired) frame for one technique: 'shaker' or 'rerun'."""
    path = SHAKER_CSV if technique == "shaker" else RERUN_CSV
    return _load_result(path, technique)


def coverage_note() -> str:
    shaker = _load_result(SHAKER_CSV, "shaker")
    rerun = _load_result(RERUN_CSV, "rerun")
    common = set(shaker["key"]) & set(rerun["key"])
    return (f"ReRun tests: {len(rerun)} | Shaker tests: {len(shaker)} | "
            f"common (analysed): {len(common)}")


if __name__ == "__main__":
    print(coverage_note())
    df = load_paired()
    print(df[["shaker_flaky", "rerun_flaky", "category", "in_gt452"]].describe(include="all"))
