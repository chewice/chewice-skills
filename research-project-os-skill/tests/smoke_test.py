"""End-to-end smoke test for the dual-Skill workflow."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "research-project-workflow/scripts/scaffold_project.py"
VALIDATOR = ROOT / "research-project-workflow/scripts/validate_project.py"
REPORT = ROOT / "report-generation/scripts/generate_report.py"


def run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed: {script.name} {' '.join(arguments)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "study"
        run(SCAFFOLD, "--project", str(project))
        assert not project.exists()
        run(SCAFFOLD, "--project", str(project), "--apply")
        assert not (project / "docs/questions/Q-001").exists()
        assert not (project / "explore/Q-001/A-001").exists()

        timestamp = "2026-08-03T19:00:00+08:00"
        (project / "QUESTIONS.md").write_text(
            f"""# Research Questions

| Q-ID | Question | Status | Brief | Updated |
|---|---|---|---|---|
| Q-001 | 如何验证双 Skill 流程？ | 解决中 | docs/questions/Q-001/BRIEF.md | {timestamp} |
""",
            encoding="utf-8",
        )
        brief = project / "docs/questions/Q-001/BRIEF.md"
        brief.parent.mkdir(parents=True)
        brief.write_text(
            (
                ROOT / "research-project-workflow/assets/templates/BRIEF.md"
            )
            .read_text(encoding="utf-8")
            .replace("Q-XXX", "Q-001")
            .replace("Status: 拟定", "Status: 解决中")
            .replace("Created:", f"Created: {timestamp}")
            .replace("Updated:", f"Updated: {timestamp}")
            .replace("Human review status: pending", "Human review status: approved")
            .replace(
                "## 1. Human Question\n",
                "## 1. Human Question\n\n如何验证双 Skill 流程？\n",
            ),
            encoding="utf-8",
        )

        artifact = project / "explore/Q-001/A-001"
        for child in ("code", "config", "logs"):
            (artifact / child).mkdir(parents=True, exist_ok=True)
        (artifact / "code/analyze.py").write_text(
            "# 提纲\n# 1. 验证流程\n\n# %% 1. 验证流程\nprint('ok')\n",
            encoding="utf-8",
        )
        result = artifact / "RESULT.md"
        result.write_text(
            (
                ROOT / "research-project-workflow/assets/templates/RESULT.md"
            )
            .read_text(encoding="utf-8")
            .replace("Q-XXX", "Q-001")
            .replace("A-XXX", "A-001")
            .replace("Status: 草稿", "Status: 审核通过")
            .replace("Decision: pending", "Decision: 审核通过")
            .replace("Reviewed at:", f"Reviewed at: {timestamp}")
            .replace("Reason:", "Reason: Human 确认最小验证通过。")
            .replace(
                "## 5. Technical Validation\n",
                "## 5. Technical Validation\n\n命令成功，输出存在，最小测试通过。\n",
            )
            .replace(
                "Pipeline target:",
                "Pipeline target: pipeline/analyze.py",
            )
            .replace("Promoted at:", f"Promoted at: {timestamp}")
            .replace(
                "Promoted files:",
                "Promoted files: pipeline/analyze.py",
            ),
            encoding="utf-8",
        )
        (project / "pipeline/analyze.py").write_text(
            (artifact / "code/analyze.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        handoff = project / "CURRENT_HANDOFF.md"
        handoff.write_text(
            handoff.read_text(encoding="utf-8")
            .replace("Active question: none", "Active question: Q-001")
            .replace("Current artifact: none", "Current artifact: A-001")
            .replace("Current checkpoint: scaffold created", "Current checkpoint: Artifact 已审核并晋升")
            .replace("Updated: ", f"Updated: {timestamp} # "),
            encoding="utf-8",
        )
        run(VALIDATOR, "--project", str(project))

        report_args = (
            "--project",
            str(project),
            "--question",
            "Q-001",
            "--artifact",
            "A-001",
        )
        run(REPORT, *report_args)
        assert not (project / "reports/Q-001/report.html").exists()
        run(REPORT, *report_args, "--apply")
        run(REPORT, "--project", str(project), "--question", "Q-001", "--validate-only")
        assert (project / "reports/Q-001/report.html").is_file()
        assert not (project / "reports/Q-001/report.pdf").exists()
        assert not (project / "project_manifest.yaml").exists()
        assert not (project / "archive").exists()
        print("Smoke test passed")


if __name__ == "__main__":
    main()
