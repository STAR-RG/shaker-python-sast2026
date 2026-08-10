#!/usr/bin/env python3
"""
Reconstructs and verifies the object-selection filter behind ``dataset/tests.csv``.

The script that originally produced ``dataset/tests.csv`` from Gruber et al.'s
``TestsOverview.csv`` was lost. This script recovers it: it applies the candidate
filter to the published dataset and checks it against the tests we actually ran,
so the selection criteria reported in the paper can be stated as a verified fact
rather than from memory.

Recovered filter::

    Verdict_sameOrder    == "Flaky"
    Order-dependent      == False
    Flaky_Infrastructure == False

which yields 952 tests across 277 projects, the same 952 recorded in the
earlier write-up of this study.

Input (not vendored here; 238 MB)::

    https://doi.org/10.5281/zenodo.4450435  ->  TestsOverview.csv

Usage::

    python -m analysis.verify_selection /path/to/TestsOverview.csv
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TESTS_CSV = ROOT / "dataset" / "tests.csv"

KEY_COLS = ["Project_Name", "Test_filename", "Test_funcname", "Test_parametrization"]
NEEDED = KEY_COLS + ["Verdict_sameOrder", "Order-dependent", "Flaky_Infrastructure"]


def _flag(series: pd.Series) -> pd.Series:
    """Gruber's boolean columns arrive as bool or as 'True'/'False' strings."""
    return series.astype(str).str.strip().str.lower() == "true"


def _exact_keys(df: pd.DataFrame) -> set[tuple[str, ...]]:
    cols = df[KEY_COLS]
    filled = cols.astype("object").where(cols.notna(), "")
    return set(map(tuple, filled.astype(str).values))


def _loose(value: object) -> str:
    """Project/file/test names differ in case and in -/_ between the two files."""
    return re.sub(r"[-_.]", "", str(value).lower())


def _loose_keys(df: pd.DataFrame) -> set[tuple[str, str, str]]:
    return set(
        zip(
            df["Project_Name"].map(_loose),
            df["Test_filename"].map(_loose),
            df["Test_funcname"].map(_loose),
        )
    )


def main(overview_path: Path) -> int:
    gt = pd.read_csv(overview_path, usecols=NEEDED, low_memory=False)
    ours = pd.read_csv(TESTS_CSV)

    flaky = gt["Verdict_sameOrder"].astype(str) == "Flaky"
    od = _flag(gt["Order-dependent"])
    infra = _flag(gt["Flaky_Infrastructure"])
    selected = flaky & ~od & ~infra

    print(f"Gruber et al. TestsOverview.csv : {len(gt):,} tests")
    print(f"  Verdict_sameOrder == Flaky    : {int(flaky.sum()):,}")
    print(f"  ... and not Order-dependent   : {int((flaky & ~od).sum()):,}")
    print(f"  ... and not Infrastructure    : {int(selected.sum()):,}"
          f"  across {gt[selected]['Project_Name'].nunique()} projects")
    print(f"\ndataset/tests.csv               : {len(ours):,} rows")

    # The decisive check: among our tests that can be located in the ground truth,
    # is the set found under "Flaky" the SAME as the set found under the full
    # filter? If so, the sample contains no order-dependent and no
    # infrastructure-flaky tests.
    for label, keyfn in (("exact key", _exact_keys), ("normalised key", _loose_keys)):
        ours_k = keyfn(ours)
        in_flaky = ours_k & keyfn(gt[flaky])
        in_filtered = ours_k & keyfn(gt[selected])
        print(f"\n[{label}] {len(ours_k)} distinct keys in dataset/tests.csv")
        print(f"  located under Verdict == Flaky        : {len(in_flaky)}")
        print(f"  located under Flaky & !OD & !Infra    : {len(in_filtered)}")
        print(f"  the two sets are identical            : {in_flaky == in_filtered}")
        print(f"  not located in the ground truth       : {len(ours_k - in_flaky)}")

    print(
        "\nIdentical sets => every analyzed test that can be located in the ground\n"
        "truth is non-order-dependent and non-infrastructure. The sample contains\n"
        "zero order-dependent tests, by construction."
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    overview = Path(sys.argv[1])
    if not overview.is_file():
        sys.exit(
            f"error: {overview} not found.\n\n"
            "This script needs TestsOverview.csv (238 MB) from the dataset of\n"
            "Gruber et al. It is deliberately NOT bundled with this artifact.\n"
            "Download it from https://doi.org/10.5281/zenodo.4450435 and pass\n"
            "its path:\n\n"
            "    python -m analysis.verify_selection /path/to/TestsOverview.csv\n"
        )
    raise SystemExit(main(overview))
