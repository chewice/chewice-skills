"""End-to-end smoke test for the bundled CLI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "research-project-os/scripts/research_project_os.py"


def run(*arguments: str) -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed ({result.returncode}): {' '.join(arguments)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "pilot"
        run("inspect", "--project", str(project))
        run(
            "init",
            "--project",
            str(project),
            "--profile",
            "bioinformatics",
        )
        run(
            "init",
            "--project",
            str(project),
            "--profile",
            "bioinformatics",
            "--apply",
        )
        run("audit", "--project", str(project))
        run("start", "--project", str(project))
        run(
            "close",
            "--project",
            str(project),
            "--summary",
            "已完成项目 smoke test。",
            "--completed",
            "已运行 audit。",
            "--evidence",
            "Smoke test 已通过。",
            "--next-step",
            "人工审阅项目。",
        )
        run(
            "close",
            "--project",
            str(project),
            "--summary",
            "已完成项目 smoke test。",
            "--completed",
            "已运行 audit。",
            "--evidence",
            "Smoke test 已通过。",
            "--next-step",
            "人工审阅项目。",
            "--apply",
        )
        run("audit", "--project", str(project))

        existing = Path(temporary) / "existing"
        existing.mkdir()
        (existing / "workflow.py").write_text("print('keep')\n", encoding="utf-8")
        run(
            "adopt",
            "--project",
            str(existing),
            "--profile",
            "bioinformatics",
            "--apply",
        )
        if (existing / "analysis").exists() or (existing / "data").exists():
            raise SystemExit("adopt created profile business directories")
        run("audit", "--project", str(existing))
    print("Smoke test passed")


if __name__ == "__main__":
    main()
