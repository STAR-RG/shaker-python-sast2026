from pathlib import Path
from shlex import split
from subprocess import run as sp_run

from base_tool import BaseTool


def _run(command, cwd, log_fh=None):
    out = log_fh if log_fh else None
    return sp_run(split(command), cwd=cwd, stdout=out, stderr=out)


class Pytest(BaseTool):
    def setup(self):
        log_file = self.output_folder / "__install.log"

        with open(log_file, "w") as log:
            def install(command):
                print(f"$ {command}", file=log, flush=True)
                return _run(command, cwd=str(self.directory), log_fh=log)

            # install("pip install --upgrade setuptools pip")
            # install("pip install pytest wheel")
            # install("pip install networkx")
            # install("pip install  grpcio grpcio-tools")


            root = Path(self.directory)

            # All .txt in root and one level deep: try pip install -r on each
            txt_files = sorted(root.glob("*.txt")) + sorted(root.glob("*/*.txt"))
            for txt_file in txt_files:
                install(f"pip install -r {txt_file.relative_to(root)}")

            if (root / "Pipfile").exists():
                install("pipenv install --system --dev")

            setup_files = ["pyproject.toml", "setup.py", "setup.cfg"]
            if any((root / f).exists() for f in setup_files):
                ALL_EXTRAS = "dev,test,tests,testing,docs,lint,ci"
                result = install(f"pip install .[{ALL_EXTRAS}]")
                if result.returncode != 0:
                    install("pip install .")

    def tear_down(self):
        pass

    def run_tests(self, report_folder):
        report_file = report_folder / "TEST-pytest.xml"
        tests_path = self.specific_tests_path or ""

        command = f"pytest {tests_path} --junitxml {report_file.absolute()}"
        command = command.replace("  ", " ")

        print(f"> {command}", flush=True)
        _run(command, cwd=str(self.directory))
