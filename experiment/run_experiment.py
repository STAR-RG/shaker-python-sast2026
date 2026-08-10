#!/usr/bin/env python3
"""
Experiment runner: reads a CSV of tests and runs shaker via Docker for each.

Input CSV columns: repo_url, commit_hash, test_path, num_run_shaker, nsr

Output structure:
    results/{repo_name}/{sanitized_test_path}/sr{sr}_nsr{nsr}/{timestamp}/
        report.no-stress.0/
          TEST-pytest.xml
        report.0.0/
          TEST-pytest.xml
        ...

Each run gets its own timestamp folder: no overwriting. Multiple runs of the
same config accumulate under the same sr{sr}_nsr{nsr} folder.

Usage:
    python3 run_experiment.py --input tests.csv --parallel 4
    python3 run_experiment.py --input tests.csv --parallel 4 --skip-existing
    python3 run_experiment.py --input tests.csv --parallel 4 --group-by-project
    python3 run_experiment.py --input tests.csv --parallel 4 --status-csv status.csv
"""

import argparse
import csv
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from itertools import groupby
from pathlib import Path

try:
    from rich.console import Console
    from rich.live import Live
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

DOCKER_IMAGE = "shaker/shaker-image"
CONTAINER_CPUS = 2
CONTAINER_MEMORY = "2g"
STATUS_FIELDNAMES = [
    "repo_url", "test_path", "status",
    "start_time", "end_time", "duration_s", "exit_code",
]


# ── helpers ────────────────────────────────────────────────────────────────

def repo_name_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1].replace(".git", "")


def sanitize_test_path(test_path: str) -> str:
    path = re.sub(r"\.py$", "", test_path.split("::")[0])
    name = "::".join([path] + test_path.split("::")[1:])
    return re.sub(r"[/\\:]+", "__", name)


def output_dir_for(results_dir: Path, repo_url: str, test_path: str,
                   sr: int, nsr: int, timestamp: str) -> Path:
    repo = repo_name_from_url(repo_url)
    test_slug = sanitize_test_path(test_path)
    return results_dir / repo / test_slug / f"sr{sr}_nsr{nsr}" / timestamp


def already_ran(results_dir: Path, repo_url: str, test_path: str,
                sr: int, nsr: int) -> bool:
    repo = repo_name_from_url(repo_url)
    test_slug = sanitize_test_path(test_path)
    config_dir = results_dir / repo / test_slug / f"sr{sr}_nsr{nsr}"
    if not config_dir.exists():
        return False
    return any(config_dir.iterdir())


# ── docker CLI helpers ──────────────────────────────────────────────────────

def docker_image_exists(image: str) -> bool:
    result = subprocess.run(["docker", "image", "inspect", image], capture_output=True)
    return result.returncode == 0


def docker_run(image: str, environment: dict, volumes: dict) -> str:
    cmd = ["docker", "run", "-d", "--cpus", str(CONTAINER_CPUS), "--memory", CONTAINER_MEMORY]
    for key, value in environment.items():
        cmd += ["-e", f"{key}={value}"]
    for host_path, spec in volumes.items():
        cmd += ["-v", f"{host_path}:{spec['bind']}:{spec.get('mode', 'rw')}"]
    cmd.append(image)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def docker_wait(container_id: str, timeout: int) -> int:
    result = subprocess.run(
        ["docker", "wait", container_id],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    return int(result.stdout.strip())


def docker_logs(container_id: str) -> str:
    result = subprocess.run(["docker", "logs", container_id], capture_output=True, text=True)
    return result.stdout + result.stderr


def docker_remove(container_id: str):
    subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)


# ── progress tracker ────────────────────────────────────────────────────────

class ProgressTracker:
    def __init__(self, total: int):
        self.total = total
        self.done = 0
        self.errors = 0
        self.running: dict = {}   # label -> start_time
        self.recent: list = []    # [(label, status, duration_s)]
        self._lock = threading.Lock()
        self._start = time.time()

    def start(self, label: str):
        with self._lock:
            self.running[label] = time.time()

    def finish(self, label: str, status: str, count: int = 1):
        with self._lock:
            elapsed = time.time() - self.running.pop(label, time.time())
            self.done += count
            if status == "error":
                self.errors += count
            self.recent.append((label, status, elapsed))
            if len(self.recent) > 5:
                self.recent.pop(0)

    def render(self) -> str:
        elapsed = time.time() - self._start
        rate = self.done / elapsed if elapsed > 0 else 0
        remaining = self.total - self.done
        if rate > 0 and remaining > 0:
            eta = f"~{int(remaining / rate / 60)}min"
        elif remaining == 0:
            eta = "done"
        else:
            eta = "?"

        lines = [
            f"[{self.done}/{self.total}] done | "
            f"{len(self.running)} running | "
            f"{self.errors} errors | ETA {eta}"
        ]
        for label in list(self.running.keys())[-3:]:
            lines.append(f"  RUNNING  {label}")
        for label, status, dur in self.recent[-3:]:
            tag = "OK " if status == "ok" else "ERR"
            lines.append(f"  {tag}  {label} ({dur:.0f}s)")
        return "\n".join(lines)


# ── status csv ──────────────────────────────────────────────────────────────

class StatusCSV:
    def __init__(self, path: Path, rows: list):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict = {
            (r["repo_url"], r["test_path"]): {
                "repo_url": r["repo_url"],
                "test_path": r["test_path"],
                "status": "pending",
                "start_time": "",
                "end_time": "",
                "duration_s": "",
                "exit_code": "",
            }
            for r in rows
        }
        self._write()

    def update(self, repo_url: str, test_path: str, **kwargs):
        with self._lock:
            self._data[(repo_url, test_path)].update(kwargs)
            self._write()

    def _write(self):
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent, suffix=".tmp", prefix=".status_"
        )
        try:
            with os.fdopen(tmp_fd, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=STATUS_FIELDNAMES)
                writer.writeheader()
                writer.writerows(self._data.values())
            os.replace(tmp_path, self.path)
        except Exception:
            os.unlink(tmp_path)
            raise


# ── single test runner ───────────────────────────────────────────────────────

def run_single_test(row, results_dir, timeout, image,
                    tracker=None, status_csv=None, extra_deps_map=None):
    repo_url = row["repo_url"]
    commit_hash = row.get("commit_hash", "")
    test_path = row["test_path"]
    sr = int(row["num_run_shaker"])
    nsr = int(row["nsr"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    output_dir = output_dir_for(results_dir, repo_url, test_path, sr, nsr, timestamp)
    output_dir.mkdir(parents=True, exist_ok=True)

    label = f"{repo_name_from_url(repo_url)}/{sanitize_test_path(test_path)}"

    if tracker:
        tracker.start(label)
    if status_csv:
        status_csv.update(repo_url, test_path, status="running",
                          start_time=datetime.now().isoformat())

    env = {
        "REPO_URL": repo_url,
        "TEST_PATH": test_path,
        "SR": str(sr),
        "NSR": str(nsr),
        "HOST_UID": str(os.getuid()),
        "HOST_GID": str(os.getgid()),
    }
    if commit_hash:
        env["COMMIT_HASH"] = commit_hash
    repo = repo_name_from_url(repo_url)
    if extra_deps_map and repo in extra_deps_map:
        env["EXTRA_DEPS"] = extra_deps_map[repo]

    start_ts = time.time()
    exit_code = -1

    try:
        container_id = docker_run(
            image,
            environment=env,
            volumes={str(output_dir.resolve()): {"bind": "/output", "mode": "rw"}},
        )

        try:
            exit_code = docker_wait(container_id, timeout)
            logs = docker_logs(container_id)
        finally:
            docker_remove(container_id)

        with open(output_dir / "__container.log", "w") as f:
            f.write(logs)

        duration = time.time() - start_ts
        # shaker exits 1 when flaky tests are found, which is expected
        status = "ok" if exit_code in (0, 1) else "error"
        if status == "error":
            log.warning(f"[{label}] exit code {exit_code}")
        else:
            log.info(f"[{label}] OK (exit={exit_code})")

    except Exception as e:
        duration = time.time() - start_ts
        status = "error"
        log.error(f"[{label}] FAILED: {e}")
        with open(output_dir / "__error.txt", "w") as f:
            f.write(str(e))

    if tracker:
        tracker.finish(label, status)
    if status_csv:
        status_csv.update(repo_url, test_path, status=status,
                          end_time=datetime.now().isoformat(),
                          duration_s=f"{duration:.1f}",
                          exit_code=str(exit_code))

    return [(label, status)]


# ── grouped project runner ───────────────────────────────────────────────────

def group_rows(rows: list) -> list:
    key = lambda r: (r["repo_url"], r.get("commit_hash", ""))
    return [list(g) for _, g in groupby(sorted(rows, key=key), key=key)]


def run_project_group(group, results_dir, timeout, image,
                      tracker=None, status_csv=None, extra_deps_map=None):
    repo_url = group[0]["repo_url"]
    commit_hash = group[0].get("commit_hash", "")
    sr = int(group[0]["num_run_shaker"])
    nsr = int(group[0]["nsr"])
    repo = repo_name_from_url(repo_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # Build TEST_ASSIGNMENTS: one line per test "test_path:::relative/output/path"
    assignments = []
    for row in group:
        test_slug = sanitize_test_path(row["test_path"])
        rel = f"{test_slug}/sr{sr}_nsr{nsr}/{timestamp}"
        assignments.append(f"{row['test_path']}:::{rel}")

    repo_output_dir = results_dir / repo
    repo_output_dir.mkdir(parents=True, exist_ok=True)

    group_label = f"{repo} ({len(group)} tests)"

    if tracker:
        tracker.start(group_label)
    if status_csv:
        t = datetime.now().isoformat()
        for row in group:
            status_csv.update(row["repo_url"], row["test_path"],
                              status="running", start_time=t)

    env = {
        "REPO_URL": repo_url,
        "SR": str(sr),
        "NSR": str(nsr),
        "TEST_ASSIGNMENTS": "\n".join(assignments),
        "HOST_UID": str(os.getuid()),
        "HOST_GID": str(os.getgid()),
    }
    if commit_hash:
        env["COMMIT_HASH"] = commit_hash
    if extra_deps_map and repo in extra_deps_map:
        env["EXTRA_DEPS"] = extra_deps_map[repo]

    start_ts = time.time()
    exit_code = -1

    try:
        container_id = docker_run(
            image,
            environment=env,
            volumes={str(repo_output_dir.resolve()): {"bind": "/output", "mode": "rw"}},
        )

        try:
            exit_code = docker_wait(container_id, timeout)
            logs = docker_logs(container_id)
        finally:
            docker_remove(container_id)

        log_path = repo_output_dir / f"__container.{timestamp}.log"
        with open(log_path, "w") as f:
            f.write(logs)

        duration = time.time() - start_ts
        status = "ok" if exit_code in (0, 1) else "error"
        if status == "error":
            log.warning(f"[{group_label}] exit code {exit_code}")
        else:
            log.info(f"[{group_label}] OK (exit={exit_code})")

    except Exception as e:
        duration = time.time() - start_ts
        status = "error"
        log.error(f"[{group_label}] FAILED: {e}")
        with open(repo_output_dir / f"__error.{timestamp}.txt", "w") as f:
            f.write(str(e))

    if tracker:
        tracker.finish(group_label, status, count=len(group))
    if status_csv:
        t = datetime.now().isoformat()
        for row in group:
            status_csv.update(row["repo_url"], row["test_path"],
                              status=status,
                              end_time=t,
                              duration_s=f"{duration:.1f}",
                              exit_code=str(exit_code))

    return [(f"{repo}/{sanitize_test_path(r['test_path'])}", status) for r in group]


# ── main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run shaker experiments via Docker")
    parser.add_argument("--input", required=True,
                        help="CSV file (repo_url,commit_hash,test_path,num_run_shaker,nsr)")
    parser.add_argument("--parallel", type=int, default=4,
                        help="Max parallel containers (default: 4)")
    parser.add_argument("--results-dir", default="results",
                        help="Output directory (default: results/)")
    parser.add_argument("--image", default=DOCKER_IMAGE,
                        help=f"Docker image name (default: {DOCKER_IMAGE})")
    parser.add_argument("--timeout", type=int, default=5400,
                        help="Container timeout in seconds (default: 5400)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip tests that already have at least one run")
    parser.add_argument("--group-by-project", action="store_true",
                        help="One container per repo: saves clone+install time")
    parser.add_argument("--status-csv",
                        help="Path to a live-updating CSV tracking status of each test")
    parser.add_argument("--no-rich", action="store_true",
                        help="Disable rich progress display, use plain logging")
    parser.add_argument("--deps-csv", default=None,
                        help="CSV with extra deps per repo (repo_name,extra_deps)")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # load extra deps: {repo_name -> "pkg1;pkg2"}
    extra_deps_map: dict = {}
    if args.deps_csv:
        with open(args.deps_csv, newline="") as f:
            for row in csv.DictReader(f):
                extra_deps_map[row["repo_name"]] = row["extra_deps"]
        log.info(f"Loaded extra deps for {len(extra_deps_map)} repos from {args.deps_csv}")

    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))

    log.info(f"Loaded {len(rows)} tests from {args.input}")

    if args.skip_existing:
        rows = [
            r for r in rows
            if not already_ran(results_dir, r["repo_url"], r["test_path"],
                               int(r["num_run_shaker"]), int(r["nsr"]))
        ]
        log.info(f"{len(rows)} tests remaining after skipping existing runs")

    if not rows:
        log.info("Nothing to run.")
        return

    try:
        if not docker_image_exists(args.image):
            log.error(f"Docker image '{args.image}' not found. Build it first:")
            log.error(f"  docker build -f docker/Dockerfile -t {args.image} .")
            sys.exit(1)
    except FileNotFoundError:
        log.error("Docker CLI not found. Is Docker installed and on PATH?")
        sys.exit(1)

    use_rich = HAS_RICH and not args.no_rich
    status_csv = StatusCSV(Path(args.status_csv), rows) if args.status_csv else None
    tracker = ProgressTracker(total=len(rows))
    summary = {"ok": 0, "error": 0}

    if args.group_by_project:
        groups = group_rows(rows)
        log.info(f"Grouped {len(rows)} tests into {len(groups)} project groups")
        futures_fn = lambda executor: {
            executor.submit(run_project_group, g, results_dir,
                            args.timeout, args.image, tracker, status_csv,
                            extra_deps_map): g
            for g in groups
        }
    else:
        futures_fn = lambda executor: {
            executor.submit(run_single_test, row, results_dir,
                            args.timeout, args.image, tracker, status_csv,
                            extra_deps_map): row
            for row in rows
        }

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures_map = futures_fn(executor)

        if use_rich:
            console = Console(highlight=False)
            with Live(Text(tracker.render()), console=console,
                      refresh_per_second=2) as live:
                for future in as_completed(futures_map):
                    for _, status in future.result():
                        summary[status] = summary.get(status, 0) + 1
                    live.update(Text(tracker.render()))
        else:
            for future in as_completed(futures_map):
                for _, status in future.result():
                    summary[status] = summary.get(status, 0) + 1

    log.info(f"Done. ok={summary.get('ok', 0)}, error={summary.get('error', 0)}")
    log.info(f"Results saved to: {results_dir}/")


if __name__ == "__main__":
    main()
