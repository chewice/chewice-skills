"""Behavior contracts for the question-driven workflow skill."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "research-context/SKILL.md").read_text(encoding="utf-8")
CONTEXT = (ROOT / "research-context/references/context.md").read_text(
    encoding="utf-8"
)
DELEGATION = (ROOT / "research-context/references/delegation.md").read_text(
    encoding="utf-8"
)
DECISIONS = (ROOT / "research-context/references/decisions.md").read_text(
    encoding="utf-8"
)


class WorkflowContractTests(unittest.TestCase):
    def test_does_not_scaffold_or_require_record_templates(self) -> None:
        self.assertIn("不自动创建", SKILL)
        self.assertIn("doc/context.md", SKILL)
        self.assertIn("不要求", SKILL)
        self.assertIn("QUESTIONS.md", SKILL)
        self.assertNotIn("scaffold_project", "\n".join((SKILL, CONTEXT, DELEGATION, DECISIONS)))
        self.assertNotIn("record-project", SKILL)
        self.assertFalse(
            (ROOT / "research-context/assets/templates/BRIEF.md").exists()
        )

    def test_main_agent_owns_context_and_subagent_does_not_edit_it(self) -> None:
        self.assertIn("Main Agent 统一维护", CONTEXT)
        self.assertIn("不直接编辑共享摘要", CONTEXT)
        self.assertIn("不直接编辑共享 `context.md`", DELEGATION)

    def test_verification_is_not_a_single_pass_fail(self) -> None:
        self.assertIn("PASS/FAIL", DELEGATION)
        self.assertIn("技术检查通过认定科学结论成立", DELEGATION)

    def test_acceptance_scenarios_cover_recovery_and_uncertainty(self) -> None:
        self.assertIn("不自动创建", DECISIONS)
        self.assertIn("不宣称研究成功", DECISIONS)
        self.assertIn("不按多数意见选择结论", DECISIONS)
        self.assertIn("不强迫收敛", DECISIONS)
        self.assertIn("不因缺少委派能力阻塞", DECISIONS)

    def test_reports_are_not_default_output(self) -> None:
        self.assertIn("不默认产出正式 Report", SKILL)
        self.assertNotIn("generate-report", SKILL)
        self.assertNotIn("report.html", SKILL)


if __name__ == "__main__":
    unittest.main()
