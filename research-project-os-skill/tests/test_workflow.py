"""Tests for lazy scaffolding, recording, and structural validation."""

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
RECORD = load_module(
    "record_project",
    ROOT / "research-project-workflow/scripts/record_project.py",
)
VALIDATOR = load_module(
    "validate_project",
    ROOT / "research-project-workflow/scripts/validate_project.py",
)


class WorkflowTests(unittest.TestCase):
    timestamp = "2026-08-13T12:00:00+08:00"

    def scaffold(self, root: Path) -> None:
        SCAFFOLD.apply_plan(SCAFFOLD.build_plan(root))

    def question(self, root: Path, *, context: str = "root") -> Path:
        plan = RECORD.build_new_question_plan(
            root,
            question="干预是否改变主要结局？",
            context=context,
            timestamp=self.timestamp,
        )
        RECORD.apply_plan(plan)
        return root / "docs/questions/Q-001/BRIEF.md"

    def approve_design(self, brief: Path, *, question_id: str = "Q-001") -> None:
        text = brief.read_text(encoding="utf-8")
        text = text.replace("Design review: pending", "Design review: approved")
        text = text.replace("Reviewed at:", f"Reviewed at: {self.timestamp}")
        text = text.replace("Review rationale:", "Review rationale: design accepted")
        replacements = (
            ("Decision this question informs:", "Decision this question informs: continue study"),
            ("|---|---|---|", "|---|---|---|\n| H1 | H0 | no effect |"),
            ("Population:", "Population: study population"),
            ("Analysis mode and design:", "Analysis mode and design: exploratory cohort"),
            ("Analysis strategy:", "Analysis strategy: estimate the contrast"),
            (
                "|---|---|---|---|",
                "|---|---|---|---|\n"
                "| C-001: intervention changes outcome | observed contrast | none | pending |",
            ),
            ("Acceptance criteria:", "Acceptance criteria: interval excludes null"),
        )
        for old, new in replacements:
            text = text.replace(old, new, 1)
        brief.write_text(text, encoding="utf-8")
        questions = brief.parents[3] / "QUESTIONS.md"
        text = questions.read_text(encoding="utf-8")
        lines = []
        for line in text.splitlines():
            if line.startswith(f"| {question_id} |"):
                line = line.replace("| pending | open |", "| approved | open |", 1)
            lines.append(line)
        questions.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def artifact(self, root: Path, *, context: str = "root") -> Path:
        plan = RECORD.build_new_artifact_plan(
            root,
            question_id="Q-001",
            analysis_mode="exploratory",
            context=context,
            timestamp=self.timestamp,
        )
        RECORD.apply_plan(plan)
        return root / "explore/Q-001/A-001/RESULT.md"

    def test_lazy_scaffold_creates_only_five_control_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            plan = SCAFFOLD.build_plan(root)
            self.assertFalse(root.exists())
            self.assertEqual(len(plan["files"]), 5)
            SCAFFOLD.apply_plan(plan)
            self.assertEqual(
                sorted(path.name for path in root.iterdir()),
                [".gitignore", "AGENTS.md", "CURRENT_HANDOFF.md", "QUESTIONS.md", "README.md"],
            )
            self.assertFalse((root / "pixi.toml").exists())
            self.assertFalse((root / "docs").exists())
            self.assertFalse((root / "explore").exists())

    def test_scaffold_preserves_existing_files_without_overwrite_interface(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("human rules\n", encoding="utf-8")
            plan = SCAFFOLD.build_plan(root)
            agents = next(item for item in plan["files"] if item["path"] == "AGENTS.md")
            self.assertEqual(agents["action"], "preserve")
            SCAFFOLD.apply_plan(plan)
            self.assertEqual((root / "AGENTS.md").read_text(), "human rules\n")

    def test_new_question_dry_run_then_apply_revalidates_and_is_lazy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            plan = RECORD.build_new_question_plan(
                root, question="干预是否改变主要结局？", timestamp=self.timestamp
            )
            self.assertEqual(plan["question_id"], "Q-001")
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})
            RECORD.apply_plan(plan)
            brief = root / "docs/questions/Q-001/BRIEF.md"
            self.assertTrue(brief.is_file())
            self.assertFalse((root / "explore").exists())
            self.assertIn("Q-ID: Q-001", brief.read_text(encoding="utf-8"))
            self.assertIn(self.timestamp, brief.read_text(encoding="utf-8"))
            self.assertIn(
                "Research question: 干预是否改变主要结局？",
                brief.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Decision this question informs:", brief.read_text(encoding="utf-8")
            )
            self.assertIn("Scope and boundary:", brief.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(ValueError, "after planning"):
                RECORD.apply_plan(plan)

    def test_new_artifact_requires_approved_study_design_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            brief = self.question(root)
            with self.assertRaisesRegex(ValueError, "approved Study Design"):
                self.artifact(root)
            self.approve_design(brief)
            result = self.artifact(root)
            text = result.read_text(encoding="utf-8")
            self.assertIn("Analysis mode: exploratory", text)
            self.assertIn("Status: draft", text)

    def test_project_level_question_and_artifact_ids_increment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            self.question(root)
            second = RECORD.build_new_question_plan(
                root, question="第二个问题？", timestamp=self.timestamp
            )
            self.assertEqual(second["question_id"], "Q-002")
            RECORD.apply_plan(second)
            self.approve_design(root / "docs/questions/Q-001/BRIEF.md")
            first_artifact = RECORD.build_new_artifact_plan(
                root,
                question_id="Q-001",
                analysis_mode="exploratory",
                timestamp=self.timestamp,
            )
            RECORD.apply_plan(first_artifact)
            next_artifact = RECORD.build_new_artifact_plan(
                root,
                question_id="Q-001",
                analysis_mode="confirmatory",
                timestamp=self.timestamp,
            )
            self.assertEqual(next_artifact["artifact_id"], "A-002")
            second_brief = root / "docs/questions/Q-002/BRIEF.md"
            self.approve_design(second_brief, question_id="Q-002")
            second_question_artifact = RECORD.build_new_artifact_plan(
                root,
                question_id="Q-002",
                analysis_mode="exploratory",
                timestamp=self.timestamp,
            )
            self.assertEqual(second_question_artifact["artifact_id"], "A-001")

    def test_new_context_rejects_unsafe_paths_and_updates_declared_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            for scope in ("/tmp/out", "../out", "."):
                with self.assertRaises(ValueError):
                    RECORD.build_new_context_plan(
                        root, context="cohort-a", scope=scope, timestamp=self.timestamp
                    )
            plan = RECORD.build_new_context_plan(
                root,
                context="cohort-a",
                scope="subprojects/cohort-a",
                timestamp=self.timestamp,
            )
            self.assertFalse((root / "subprojects").exists())
            RECORD.apply_plan(plan)
            local = root / "subprojects/cohort-a/CURRENT_HANDOFF.md"
            self.assertTrue(local.is_file())
            with self.assertRaisesRegex(ValueError, "already exists"):
                RECORD.build_new_context_plan(
                    root,
                    context="cohort-a",
                    scope="subprojects/other",
                    timestamp=self.timestamp,
                )
            self.question(root, context="cohort-a")
            self.assertIn(
                "Active question: Q-001", local.read_text(encoding="utf-8")
            )
            root_handoff = (root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8")
            self.assertIn("| cohort-a | subprojects/cohort-a | Q-001 |", root_handoff)

    def test_validator_reports_structure_not_scientific_validity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            result = VALIDATOR.validate_project(root)
            self.assertTrue(result["structure_consistent"], result["errors"])
            self.assertEqual(result["scientific_validity"], "not_evaluated")
            self.assertNotIn("ok", result)

    def test_validator_checks_only_declared_context_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            (root / "untracked/deep").mkdir(parents=True)
            (root / "untracked/deep/CURRENT_HANDOFF.md").write_text(
                "invalid\n", encoding="utf-8"
            )
            self.assertTrue(VALIDATOR.validate_project(root)["structure_consistent"])
            plan = RECORD.build_new_context_plan(
                root,
                context="cohort-a",
                scope="subprojects/cohort-a",
                timestamp=self.timestamp,
            )
            RECORD.apply_plan(plan)
            local = root / "subprojects/cohort-a/CURRENT_HANDOFF.md"
            local.write_text("invalid\n", encoding="utf-8")
            result = VALIDATOR.validate_project(root)
            self.assertFalse(result["structure_consistent"])
            self.assertTrue(any("lacks metadata" in error for error in result["errors"]))

    def test_legacy_paths_warn_without_invalidating_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.scaffold(root)
            (root / "archive").mkdir()
            result = VALIDATOR.validate_project(root)
            self.assertTrue(result["structure_consistent"], result["errors"])
            self.assertIn("Legacy path preserved: archive", result["warnings"])


if __name__ == "__main__":
    unittest.main()
