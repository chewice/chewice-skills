"""Tests for the independent report-generation Skill."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCAFFOLD = load_module(
    "report_test_scaffold",
    ROOT / "research-project-workflow/scripts/scaffold_project.py",
)
REPORT = load_module(
    "generate_report",
    ROOT / "report-generation/scripts/generate_report.py",
)
REPORT_SCRIPT = ROOT / "report-generation/scripts/generate_report.py"


class ReportGenerationTests(unittest.TestCase):
    def make_reviewed_project(self, root: Path) -> Path:
        SCAFFOLD.apply_plan(SCAFFOLD.build_plan(root))
        timestamp = "2026-08-03T19:00:00+08:00"
        (root / "QUESTIONS.md").write_text(
            f"""# Research Questions

| Q-ID | Question | Status | Brief | Updated |
|---|---|---|---|---|
| Q-001 | 如何验证报告？ | 解决中 | docs/questions/Q-001/BRIEF.md | {timestamp} |
""",
            encoding="utf-8",
        )
        brief = root / "docs/questions/Q-001/BRIEF.md"
        brief.parent.mkdir(parents=True)
        brief.write_text(
            (
                ROOT / "research-project-workflow/assets/templates/BRIEF.md"
            )
            .read_text(encoding="utf-8")
            .replace("Q-XXX", "Q-001")
            .replace("Status: 拟定", "Status: 解决中")
            .replace("Human review status: pending", "Human review status: approved")
            .replace(
                "## 1. Human Question\n",
                "## 1. Human Question\n\n验证独立报告生成。\n",
            ),
            encoding="utf-8",
        )
        artifact = root / "explore/Q-001/A-001"
        artifact.mkdir(parents=True)
        results = root / "results/Q-001"
        results.mkdir(parents=True)
        (results / "table.tsv").write_text("name\tvalue\nx\t1\n", encoding="utf-8")
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
            .replace(
                "## 5. Technical Validation\n",
                "## 5. Technical Validation\n\n测试通过。\n",
            )
            .replace(
                "## 6. Results\n",
                "## 6. Results\n\n获得结果。[数据表](../../../results/Q-001/table.tsv)\n",
            ),
            encoding="utf-8",
        )
        return result

    def test_report_dry_run_then_apply_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_reviewed_project(root)
            plan = REPORT.build_plan(root, "Q-001", ["A-001"])
            output = root / "reports/Q-001/report.html"
            self.assertFalse(output.exists())
            self.assertEqual(plan["assets"][0]["source"], "results/Q-001/table.tsv")
            REPORT.apply_plan(plan)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".build.json").is_file())
            self.assertTrue((output.parent / plan["assets"][0]["target"]).is_file())
            check = REPORT.validate_report(root, output)
            self.assertTrue(check["ok"], check["errors"])
            html = output.read_text(encoding="utf-8")
            self.assertIn('<html lang="zh-CN">', html)
            self.assertIn("审核通过的 Explore", html)

    def test_report_requires_approved_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.make_reviewed_project(root)
            result.write_text(
                result.read_text(encoding="utf-8").replace(
                    "Status: 审核通过", "Status: 待审核"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not approved"):
                REPORT.build_plan(root, "Q-001", ["A-001"])

    def test_report_refuses_overwrite_without_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_reviewed_project(root)
            REPORT.apply_plan(REPORT.build_plan(root, "Q-001", ["A-001"]))
            with self.assertRaises(FileExistsError):
                REPORT.build_plan(root, "Q-001", ["A-001"])
            plan = REPORT.build_plan(
                root,
                "Q-001",
                ["A-001"],
                overwrite=True,
            )
            REPORT.apply_plan(plan)

    def test_report_rejects_remote_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.make_reviewed_project(root)
            result.write_text(
                result.read_text(encoding="utf-8")
                + "\n![remote](https://example.org/image.png)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Remote image"):
                REPORT.build_plan(root, "Q-001", ["A-001"])

    def test_pdf_capability_fails_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_reviewed_project(root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPORT_SCRIPT),
                    "--project",
                    str(root),
                    "--question",
                    "Q-001",
                    "--artifact",
                    "A-001",
                    "--format",
                    "pdf",
                    "--apply",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not configured", result.stderr)
            self.assertFalse((root / "reports/Q-001/report.pdf").exists())


if __name__ == "__main__":
    unittest.main()
