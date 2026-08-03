"""Tests for scaffolding and read-only project validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
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
    "scaffold_project",
    ROOT / "research-project-workflow/scripts/scaffold_project.py",
)
VALIDATOR = load_module(
    "validate_project",
    ROOT / "research-project-workflow/scripts/validate_project.py",
)


class WorkflowTests(unittest.TestCase):
    def scaffold(self, root: Path) -> None:
        SCAFFOLD.apply_plan(SCAFFOLD.build_plan(root))

    def register_question(
        self,
        root: Path,
        *,
        status: str = "解决中",
        review: str = "approved",
    ) -> Path:
        timestamp = "2026-08-03T19:00:00+08:00"
        (root / "QUESTIONS.md").write_text(
            """# Research Questions

| Q-ID | Question | Status | Brief | Updated |
|---|---|---|---|---|
| Q-001 | 如何验证流程？ | STATUS | docs/questions/Q-001/BRIEF.md | TIMESTAMP |
""".replace("STATUS", status).replace("TIMESTAMP", timestamp),
            encoding="utf-8",
        )
        brief = root / "docs/questions/Q-001/BRIEF.md"
        brief.parent.mkdir(parents=True)
        text = (
            (ROOT / "research-project-workflow/assets/templates/BRIEF.md")
            .read_text(encoding="utf-8")
            .replace("Q-XXX", "Q-001")
            .replace("Status: 拟定", f"Status: {status}")
            .replace("Created:", f"Created: {timestamp}")
            .replace("Updated:", f"Updated: {timestamp}")
            .replace("Human review status: pending", f"Human review status: {review}")
        )
        brief.write_text(text, encoding="utf-8")
        return brief

    def add_artifact(
        self,
        root: Path,
        *,
        artifact: str = "A-001",
        status: str = "审核通过",
        decision: str = "审核通过",
    ) -> Path:
        artifact_root = root / f"explore/Q-001/{artifact}"
        for child in ("code", "config", "logs"):
            (artifact_root / child).mkdir(parents=True, exist_ok=True)
        result = artifact_root / "RESULT.md"
        text = (
            (ROOT / "research-project-workflow/assets/templates/RESULT.md")
            .read_text(encoding="utf-8")
            .replace("Q-XXX", "Q-001")
            .replace("A-XXX", artifact)
            .replace("Status: 草稿", f"Status: {status}")
            .replace("Decision: pending", f"Decision: {decision}")
            .replace("## 5. Technical Validation\n", "## 5. Technical Validation\n\n测试通过。\n")
        )
        result.write_text(text, encoding="utf-8")
        return result

    def test_scaffold_is_dry_run_then_creates_only_stable_parents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            plan = SCAFFOLD.build_plan(root)
            self.assertFalse(root.exists())
            self.assertTrue(all(item["action"] == "create" for item in plan["files"]))
            SCAFFOLD.apply_plan(plan)
            for relative in SCAFFOLD.PROTECTED_FILES:
                self.assertTrue((root / relative).is_file(), relative)
            for relative in SCAFFOLD.DIRECTORIES:
                self.assertTrue((root / relative).is_dir(), relative)
            self.assertFalse((root / "docs/questions/Q-001").exists())
            self.assertFalse((root / "explore/Q-001").exists())
            self.assertFalse((root / "project_manifest.yaml").exists())

    def test_adopt_preserves_existing_control_files_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("human rules\n", encoding="utf-8")
            plan = SCAFFOLD.build_plan(root, overwrite=True)
            agents = next(item for item in plan["files"] if item["path"] == "AGENTS.md")
            self.assertEqual(agents["action"], "preserve")
            SCAFFOLD.apply_plan(plan)
            self.assertEqual((root / "AGENTS.md").read_text(), "human rules\n")

    def test_fresh_scaffold_validates_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            result = VALIDATOR.validate_project(root)
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(before, after)
            self.assertIn("No Question is registered", result["warnings"])

    def test_question_brief_artifact_and_handoff_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            self.register_question(root)
            self.add_artifact(root)
            handoff = root / "CURRENT_HANDOFF.md"
            text = handoff.read_text(encoding="utf-8")
            text = text.replace("Active question: none", "Active question: Q-001")
            handoff.write_text(text, encoding="utf-8")
            result = VALIDATOR.validate_project(root)
            self.assertTrue(result["ok"], result["errors"])

    def test_final_question_requires_human_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            self.register_question(root, status="已解决", review="pending")
            result = VALIDATOR.validate_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("requires Human review" in error for error in result["errors"]))

    def test_unapproved_artifact_cannot_record_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            self.register_question(root)
            result_path = self.add_artifact(
                root,
                status="待审核",
                decision="pending",
            )
            result_path.write_text(
                result_path.read_text(encoding="utf-8").replace(
                    "Pipeline target:", "Pipeline target: pipeline/qc.py"
                ),
                encoding="utf-8",
            )
            result = VALIDATOR.validate_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("promotion facts" in error for error in result["errors"]))

    def test_pipeline_cannot_depend_on_human_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            (root / "pipeline/run.py").write_text(
                "open('../docs/template/reference.py')\n",
                encoding="utf-8",
            )
            result = VALIDATOR.validate_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("docs/template" in error for error in result["errors"]))

    def test_agents_invariants_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8").replace(
                    "遵循第一性原理", "遵循经验"
                ),
                encoding="utf-8",
            )
            result = VALIDATOR.validate_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("invariant" in error for error in result["errors"]))

    def test_legacy_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            (root / "archive").mkdir()
            result = VALIDATOR.validate_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("legacy path" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
