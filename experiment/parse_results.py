#!/usr/bin/env python3
"""
Parse shaker XML results to CSV.

Traverses the results directory structure:
    results/{repo_name}/{test_slug}/sr{sr}_nsr{nsr}/{timestamp}/report.*/TEST-pytest.xml

For each (repo, test, sr_nsr_config), aggregates all runs found and determines
flakiness: a test is flaky if it has at least 1 pass AND 1 fail across all runs.

Usage:
    python3 parse_results.py --results-dir results/ --output results.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from xml.etree import ElementTree


FIELDNAMES = [
    "repo_name",
    "test_slug",
    "sr",
    "nsr",
    "total_runs",
    "pass_count",
    "fail_count",
    "failure_rate",
    "is_flaky",
    "status",
]

CONFIG_RE = re.compile(r"^sr(\d+)_nsr(\d+)$")


def parse_xml(xml_file: Path) -> List[Tuple[str, bool]]:
    """Return list of (test_name, failed) from a JUnit XML file."""
    try:
        root = ElementTree.parse(xml_file).getroot()
    except ElementTree.ParseError as e:
        print(f'Error parsing:  f{e}')
        return []

    testcases = root.findall("testcase")
    if not testcases:
        testcases = root.findall("testsuite/testcase")

    results = []
    for tc in testcases:
        name = f"{tc.get('classname', '')}.{tc.get('name', '')}"
        failed = tc.find("failure") is not None or tc.find("error") is not None
        skipped = tc.find("skipped") is not None
        if not skipped:
            results.append((name, failed))

    return results


def collect_runs(config_dir: Path) -> Dict[str, List[bool]]:
    """
    Aggregate all runs under a sr{sr}_nsr{nsr} dir.
    Returns {test_name: [failed_run_1, failed_run_2, ...]}
    """
    test_results: Dict[str, List[bool]] = {}

    for timestamp_dir in sorted(config_dir.iterdir()):
        if not timestamp_dir.is_dir():
            continue
        for report_dir in sorted(timestamp_dir.iterdir()):
            if not report_dir.is_dir() or not report_dir.name.startswith("report."):
                continue
            for xml_file in report_dir.glob("*.xml"):
                for name, failed in parse_xml(xml_file):
                    test_results.setdefault(name, []).append(failed)

    return test_results


def analyze(test_results: Dict[str, List[bool]], sr: int, nsr: int) -> dict:
    """Determine flakiness from aggregated run results."""
    if not test_results:
        return {
            "total_runs": 0,
            "pass_count": 0,
            "fail_count": 0,
            "failure_rate": 0.0,
            "is_flaky": False,
            "status": "error",
        }

    # Use the test that ran the most times (the target test)
    # If there's only one specific test, this is straightforward
    all_results = [r for runs in test_results.values() for r in runs]
    total_runs = len(all_results)
    fail_count = sum(all_results)
    pass_count = total_runs - fail_count

    if total_runs == 0:
        status = "error"
        is_flaky = False
    elif fail_count == 0:
        status = "all_passed"
        is_flaky = False
    elif pass_count == 0:
        status = "all_failed"
        is_flaky = False
    else:
        status = "flaky"
        is_flaky = True

    return {
        "total_runs": total_runs,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "failure_rate": round(fail_count / total_runs, 4) if total_runs else 0.0,
        "is_flaky": is_flaky,
        "status": status,
    }


def main():
    parser = argparse.ArgumentParser(description="Parse shaker XML results to CSV")
    parser.add_argument("results_dir_pos", nargs="?", help="Results directory (positional)")
    parser.add_argument("output_pos", nargs="?", help="Output CSV file (positional)")
    parser.add_argument("--results-dir", default="results", help="Results directory (default: results/)")
    parser.add_argument("--output", default="results.csv", help="Output CSV file (default: results.csv)")
    args = parser.parse_args()

    if args.results_dir_pos:
        args.results_dir = args.results_dir_pos
    if args.output_pos:
        args.output = args.output_pos

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}", file=sys.stderr)
        sys.exit(1)

    rows = []

    for repo_dir in sorted(results_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        for test_dir in sorted(repo_dir.iterdir()):
            if not test_dir.is_dir():
                continue
            for config_dir in sorted(test_dir.iterdir()):
                if not config_dir.is_dir():
                    continue
                m = CONFIG_RE.match(config_dir.name)
                if not m:
                    continue

                sr, nsr = int(m.group(1)), int(m.group(2))
                test_results = collect_runs(config_dir)
                stats = analyze(test_results, sr, nsr)

                if stats["total_runs"] == 0:
                    print(f"WARN: 0 runs for {repo_dir.name}/{test_dir.name}/sr{sr}_nsr{nsr}", file=sys.stderr)

                rows.append({
                    "repo_name": repo_dir.name,
                    "test_slug": test_dir.name,
                    "sr": sr,
                    "nsr": nsr,
                    **stats,
                })

    output_file = Path(args.output)
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    total      = len(rows)
    flaky      = sum(1 for r in rows if r["status"] == "flaky")
    all_passed = sum(1 for r in rows if r["status"] == "all_passed")
    all_failed = sum(1 for r in rows if r["status"] == "all_failed")
    errors     = sum(1 for r in rows if r["status"] == "error")

    pct = lambda n: f"{n/total*100:.1f}%" if total else "0%"

    print()
    print("=" * 40)
    print(f"  TOTAL TESTS:          {total}")
    print("=" * 40)
    print(f"  Flaky detected:       {flaky:>4}  ({pct(flaky)})")
    print(f"  Always passed:        {all_passed:>4}  ({pct(all_passed)})")
    print(f"  Always failed:        {all_failed:>4}  ({pct(all_failed)})")
    print(f"  Error (no result):    {errors:>4}  ({pct(errors)})")
    print("=" * 40)
    print(f"  Output: {output_file}")
    print()


if __name__ == "__main__":
    main()
