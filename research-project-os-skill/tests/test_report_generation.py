"""Tests for question-centred report synthesis and delivery safety."""

from __future__ import annotations

import importlib.util
import json
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


REPORT = load_module(
    "generate_report",
    ROOT / "report-generation/scripts/generate_report.py",
)
REPORT_SCRIPT = ROOT / "report-generation/scripts/generate_report.py"


class ReportGenerationTests(unittest.TestCase):
    timestamp = "2026-08-13T19:00:00+08:00"

    def make_project(self, root: Path, *, closure: str = "open") -> None:
        for relative in (
            "docs/questions/Q-001",
            "explore/Q-001",
            "results/Q-001",
            "reports",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "QUESTIONS.md").write_text(
            f"""# Research Questions

| Q-ID | Research question | Design review | Closure decision | Brief | Updated |
|---|---|---|---|---|---|
| Q-001 | 暴露是否改变结局？ | approved | {closure} | docs/questions/Q-001/BRIEF.md | {self.timestamp} |
""",
            encoding="utf-8",
        )
        closed_at = self.timestamp if closure != "open" else ""
        closure_rationale = "证据达到停止规则。" if closure != "open" else "尚未关闭。"
        (root / "docs/questions/Q-001/BRIEF.md").write_text(
            f"""# Q-001 Brief

Q-ID: Q-001
Created: {self.timestamp}
Updated: {self.timestamp}
Design review: approved
Reviewed at: {self.timestamp}
Review rationale: 设计边界和判定规则已确认。
Closure decision: {closure}
Closed at: {closed_at}
Closure rationale: {closure_rationale}

## 1. Research Question and Decision

Research question: 暴露是否改变结局？
Decision this question informs: 是否推进验证实验。
Scope and boundary: 当前队列与预先定义结局。

## 2. Hypotheses and Falsifiers

| Hypothesis | Alternative explanation | Falsifier or observation that changes the judgement |
|---|---|---|
| H1 暴露改变结局 | 混杂解释关联 | 调整后效应消失或方向相反 |

## 3. Estimand and Inference Unit

Population: 当前队列。
Exposure or intervention: 预定义暴露。
Comparator: 未暴露组。
Outcome and time: 30 天结局。
Observation and inference unit: 个体。

## 4. Study Design and Evidence Eligibility

Analysis mode and design: confirmatory cohort analysis。
Eligible evidence: 锁定数据与预定义模型。
Ineligible evidence: post hoc subgroup。
Controls, confounders and missingness: 调整基线混杂并报告缺失。

## 5. Analysis and Uncertainty

Analysis strategy: 估计组间差异。
Assumptions and checks: positivity 与 model fit。
Effect and uncertainty: effect estimate 与 95% CI。

## 6. Claim-Evidence Matrix

| Claim | Decisive evidence | Current evidence | Assessment |
|---|---|---|---|
| C-001: 暴露改变结局 | E-001 方向稳定且区间排除零 | 待综合 | pending |

## 7. Acceptance, Stopping and Risks

Acceptance criteria: 方向稳定且稳健性通过。
Stopping criteria: 决定性复现实验完成。
Risks and unresolved decisions: residual confounding。
""",
            encoding="utf-8",
        )
        (root / "results/Q-001/table.tsv").write_text(
            "group\teffect\nlower\t0.10\n", encoding="utf-8"
        )

    def add_artifact(
        self,
        root: Path,
        artifact_id: str,
        *,
        relation: str = "support",
        assessment: str = "support",
        claim: str = "C-001",
        qualified_claim: str = "在当前队列和模型下，暴露与结局存在关联。",
        uncertainty: str = "残余混杂仍不能排除。",
        decision: str = "approved",
        status: str = "reviewed",
        remote_image: bool = False,
    ) -> Path:
        artifact = root / f"explore/Q-001/{artifact_id}"
        artifact.mkdir(parents=True)
        image = "\n![remote](https://example.org/image.png)" if remote_image else ""
        result = artifact / "RESULT.md"
        result.write_text(
            f"""# Q-001 / {artifact_id} Result

Question: Q-001
Artifact: {artifact_id}
Analysis mode: confirmatory
Status: {status}
Created: {self.timestamp}
Updated: {self.timestamp}

## 1. Question and Claims

Research question: 暴露是否改变结局？
Claims assessed: C-001。

## 2. Provenance Receipt

Data source and version: locked cohort v1。
Code revision: abc123。
Environment or lock: pixi.lock hash 123。
Command and seed: pixi run analysis --seed 7。
Run time: {self.timestamp}。

## 3. Method and Deviations

Method executed: 预定义回归模型。
Deviations from BRIEF: none。

## 4. Observed Evidence

### E-001

Claim: {claim}
Relation: {relation}
Source: [分析表](../../../results/Q-001/table.tsv)
Output: results/Q-001/table.tsv
Observation: 调整后效应方向稳定。
Effect and uncertainty: effect=0.10, 95% CI 0.02–0.18。{image}

## 5. Validation

### Technical Validation

输出存在且 hash 匹配。

### Scientific and Robustness Validation

敏感性分析方向一致，但未排除未测混杂。

## 6. Inference

Assessment: {assessment}
Qualified claim: {qualified_claim}
Uncertainty: {uncertainty}
Alternative explanations and causal boundary: 观察性设计不支持因果断言。

## 7. Limitations and Applicability

Limitations: 单一队列与残余混杂。
Applicability boundary: 仅适用于当前纳入标准。

## 8. Next Decisive Test

Test: 独立队列按同一 estimand 复现。
Decision it distinguishes: 区分稳定关联与队列特异偏差。

## 9. Human Review

Decision: {decision}
Reviewed at: {self.timestamp if decision != 'pending' else ''}
Review rationale: {'evidence record 可进入综合。' if decision != 'pending' else ''}

## 10. Implementation Reuse

Reuse decision: not-assessed
Target: not applicable; 尚未评估复用。
Recorded at: not applicable; 尚未评估复用。
Files: not applicable; 尚未评估复用。
""",
            encoding="utf-8",
        )
        return result

    def test_auto_selection_dry_run_apply_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.add_artifact(root, "A-001")
            plan = REPORT.build_plan(root, "Q-001")
            output = root / "reports/Q-001/report.html"
            self.assertFalse(output.exists())
            self.assertEqual(plan["metadata"]["artifact_selection"], "automatic")
            self.assertEqual(plan["metadata"]["report_type"], "阶段性报告")
            self.assertEqual(plan["assets"][0]["source"], "results/Q-001/table.tsv")
            REPORT.apply_plan(plan)
            self.assertTrue(REPORT.validate_report(root, output)["ok"])
            html = output.read_text(encoding="utf-8")
            self.assertIn("阶段性报告", html)
            self.assertIn("Validation and Robustness", html)
            self.assertNotIn("## 9. Human Review", html)
            metadata = json.loads(output.with_suffix(".build.json").read_text())
            self.assertEqual(metadata["source_map"][0]["evidence_id"], "E-001")
            self.assertEqual(metadata["source_map"][0]["inference_assessment"], "support")

    def test_multiple_artifacts_require_scope_then_preserve_mixed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.add_artifact(root, "A-001", relation="support", assessment="support")
            self.add_artifact(
                root,
                "A-002",
                relation="null",
                assessment="inconclusive",
                qualified_claim="在第二队列中未观察到可区分于零的效应。",
            )
            self.add_artifact(
                root,
                "A-003",
                relation="contradictory",
                assessment="contradict",
                qualified_claim="第三分析的效应方向与原假设相反。",
            )
            with self.assertRaisesRegex(ValueError, "Multiple eligible Artifacts"):
                REPORT.build_plan(root, "Q-001")
            plan = REPORT.build_plan(root, "Q-001", ["A-001", "A-002", "A-003"])
            self.assertIn("<code>support</code>: 1", plan["html"])
            self.assertIn("<code>null</code>: 1", plan["html"])
            self.assertIn("<code>contradictory</code>: 1", plan["html"])
            self.assertIn("保留的跨 Artifact 冲突或混合证据", plan["html"])

    def test_review_validation_and_reuse_decisions_remain_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            result = self.add_artifact(root, "A-001")
            plan = REPORT.build_plan(root, "Q-001", ["A-001"])
            self.assertIn("Human approval 只决定材料可纳入报告", plan["html"])
            self.assertIn("Implementation reuse=<code>not-assessed</code>", plan["html"])
            result.write_text(
                result.read_text().replace("Assessment: support", "Assessment: pending"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Inference Assessment"):
                REPORT.build_plan(root, "Q-001", ["A-001"])

    def test_invalid_design_review_and_empty_scientific_content_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.add_artifact(root, "A-001")
            brief = root / "docs/questions/Q-001/BRIEF.md"
            brief.write_text(
                brief.read_text().replace("Design review: approved", "Design review: rejected"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "exactly approved"):
                REPORT.build_plan(root, "Q-001", ["A-001"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            result = self.add_artifact(root, "A-001")
            result.write_text(
                result.read_text().replace(
                    "Qualified claim: 在当前队列和模型下，暴露与结局存在关联。",
                    "Qualified claim:",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Qualified claim"):
                REPORT.build_plan(root, "Q-001", ["A-001"])

    def test_overwrite_remote_resource_and_pdf_safety(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.add_artifact(root, "A-001")
            REPORT.apply_plan(REPORT.build_plan(root, "Q-001", ["A-001"]))
            with self.assertRaises(FileExistsError):
                REPORT.build_plan(root, "Q-001", ["A-001"])
            REPORT.apply_plan(
                REPORT.build_plan(root, "Q-001", ["A-001"], overwrite=True)
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.add_artifact(root, "A-001", remote_image=True)
            with self.assertRaisesRegex(ValueError, "Remote image"):
                REPORT.build_plan(root, "Q-001", ["A-001"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.add_artifact(root, "A-001")
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPORT_SCRIPT),
                    "--project",
                    str(root),
                    "--question",
                    "Q-001",
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
