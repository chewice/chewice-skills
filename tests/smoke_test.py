"""End-to-end smoke test for the bundled CLI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


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
        explore_args = (
            "explore-create",
            "--project",
            str(project),
            "--order",
            "0",
            "--core",
            "QC",
            "--summary",
            "stable thresholds selected",
            "--question",
            "哪些 QC thresholds 稳定？",
            "--method",
            "Sensitivity analysis。",
            "--expected-output",
            "QC table",
            "--stop-condition",
            "Threshold sensitivity 已记录。",
            "--approved-by",
            "smoke-reviewer",
        )
        run(*explore_args)
        run(*explore_args, "--apply")
        task_name = "P0-QC-stable-thresholds-selected"
        task_root = project / "explore" / task_name
        task = yaml.safe_load((task_root / "task.yaml").read_text(encoding="utf-8"))
        if task["exploration"]["style"] != "narrative_linear":
            raise SystemExit("explore task lacks narrative_linear style")
        if task["exploration"]["outline_language"] != "zh-CN":
            raise SystemExit("explore task lacks Chinese outline contract")
        if not (task_root / "README.md").is_file():
            raise SystemExit("explore task lacks narrative README")
        (task_root / "scripts/qc.py").write_text(
            "print('qc')\n",
            encoding="utf-8",
        )
        promote_args = (
            "archive-promote",
            "--project",
            str(project),
            "--task",
            task_name,
            "--reviewed-by",
            "smoke-reviewer",
            "--review-summary",
            "QC 可进入主流程。",
            "--validation",
            "Sensitivity analysis passed。",
        )
        run(*promote_args)
        run(*promote_args, "--apply")
        selector = f"{task_name}@v001"
        run(
            "archive-verify",
            "--project",
            str(project),
            "--snapshot",
            selector,
        )
        pipeline_args = (
            "pipeline-create",
            "--project",
            str(project),
            "--snapshot",
            selector,
        )
        run(*pipeline_args)
        run(*pipeline_args, "--apply")
        pipeline_path = project / "pipeline/pipeline.yaml"
        pipeline = yaml.safe_load(pipeline_path.read_text(encoding="utf-8"))
        if pipeline["code_style"]["outline_language"] != "zh-CN":
            raise SystemExit("pipeline lacks Chinese outline contract")
        pipeline["steps"][0]["implementation"] = "src/qc.py"
        pipeline_path.write_text(
            yaml.safe_dump(pipeline, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (project / "pipeline/src/qc.py").write_text(
            "def run():\n    return 'ok'\n",
            encoding="utf-8",
        )
        (project / "pipeline/run.py").write_text(
            "from src.qc import run\nprint(run())\n",
            encoding="utf-8",
        )
        release_args = (
            "pipeline-release",
            "--project",
            str(project),
            "--entrypoint",
            "run.py",
            "--reviewed-by",
            "smoke-reviewer",
            "--review-summary",
            "Pipeline 可发布。",
            "--validation",
            "End-to-end smoke passed。",
        )
        run(*release_args)
        run(*release_args, "--apply")
        run("audit", "--project", str(project))
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
