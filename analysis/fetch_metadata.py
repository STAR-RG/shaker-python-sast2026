#!/usr/bin/env python3
"""
Cheap, cached project metadata for RQ3. No test execution.

For each repo that appears in the result set, shallow-clones at the recorded
commit and computes lightweight structural traits:
    n_files, n_py_files, n_test_files, loc (python), n_deps (declared)

Results are cached to dataset/project_metadata.csv; repos already present are
skipped, so this is safe to re-run and only touches the network once per repo.

Usage:
    python -m analysis.fetch_metadata            # fetch missing repos
    python -m analysis.fetch_metadata --force    # refetch everything
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path

from analysis.load import PROJECTS_CSV, METADATA_CSV, load_single

FIELDS = ["repo_name", "n_files", "n_py_files", "n_test_files", "loc", "n_deps", "fetch_ok"]

DEP_LINE = re.compile(r"^\s*[A-Za-z0-9_.\-]+")


def repos_in_results() -> set[str]:
    s = set(load_single("shaker")["repo_name"]) | set(load_single("rerun")["repo_name"])
    return s


def project_urls() -> dict[str, tuple[str, str]]:
    out = {}
    with open(PROJECTS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            out[row["Project_Name"]] = (row["Project_URL"], row["Project_Hash"])
    return out


def shallow_checkout(url: str, commit: str, dest: Path) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, cwd=dest, capture_output=True, text=True)
    run("git", "init", "-q")
    run("git", "remote", "add", "origin", url)
    fetched = run("git", "fetch", "-q", "--depth", "1", "origin", commit)
    if fetched.returncode == 0:
        co = run("git", "checkout", "-q", "FETCH_HEAD")
        if co.returncode == 0:
            return True
    # fallback: broader shallow clone of default branch, then try the commit
    run("git", "fetch", "-q", "--depth", "300", "origin")
    co = run("git", "checkout", "-q", commit)
    return co.returncode == 0


def count_deps(root: Path) -> int:
    deps: set[str] = set()
    for req in list(root.rglob("requirements*.txt")) + list(root.rglob("*requirements.txt")):
        if ".git" in req.parts:
            continue
        for line in req.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")) and DEP_LINE.match(line):
                deps.add(re.split(r"[<>=!~\[; ]", line)[0].lower())
    pipfile = root / "Pipfile"
    if pipfile.exists():
        in_pkgs = False
        for line in pipfile.read_text(errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("["):
                in_pkgs = s in ("[packages]", "[dev-packages]")
            elif in_pkgs and "=" in s:
                deps.add(s.split("=")[0].strip().strip('"').lower())
    return len(deps)


def measure(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    py = [p for p in files if p.suffix == ".py"]
    tests = [p for p in py if p.name.startswith("test_") or p.name.endswith("_test.py")
             or "test" in p.parts]
    loc = 0
    for p in py:
        try:
            loc += sum(1 for _ in p.open(errors="ignore"))
        except OSError:
            pass
    return {"n_files": len(files), "n_py_files": len(py),
            "n_test_files": len(tests), "loc": loc, "n_deps": count_deps(root)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    urls = project_urls()
    wanted = sorted(repos_in_results())

    have: dict[str, dict] = {}
    if METADATA_CSV.exists() and not args.force:
        with open(METADATA_CSV, newline="") as f:
            have = {r["repo_name"]: r for r in csv.DictReader(f)}

    todo = [r for r in wanted if r not in have]
    print(f"{len(wanted)} repos in results; {len(todo)} to fetch; {len(have)} cached")

    for repo in todo:
        if repo not in urls:
            print(f"  [skip] no URL for {repo}")
            have[repo] = {"repo_name": repo, "fetch_ok": 0,
                          **{k: "" for k in FIELDS if k not in ("repo_name", "fetch_ok")}}
            continue
        url, commit = urls[repo]
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / repo
            ok = shallow_checkout(url, commit, dest)
            if ok:
                m = measure(dest)
                have[repo] = {"repo_name": repo, "fetch_ok": 1, **m}
                print(f"  [ok] {repo}: files={m['n_files']} loc={m['loc']} deps={m['n_deps']}")
            else:
                have[repo] = {"repo_name": repo, "fetch_ok": 0,
                              **{k: "" for k in FIELDS if k not in ("repo_name", "fetch_ok")}}
                print(f"  [fail] {repo} (could not checkout {commit[:8]})")

    with open(METADATA_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for repo in sorted(have):
            row = have[repo]
            w.writerow({k: row.get(k, "") for k in FIELDS})
    print(f"wrote {METADATA_CSV} ({len(have)} repos)")


if __name__ == "__main__":
    main()
