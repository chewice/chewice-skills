"""End-to-end smoke test for question-driven analysis and hierarchical context."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "research-project-workflow/scripts/scaffold_project.py"
RECORD = ROOT / "research-project-workflow/scripts/record_project.py"
VALIDATOR = ROOT / "research-project-workflow/scripts/validate_project.py"
REPORT = ROOT / "report-generation/scripts/generate_report.py"
TIMESTAMP = "2026-08-13T19:00:00+08:00"


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


def approved_brief() -> str:
    return f"""# Q-001 Brief

Q-ID: Q-001
Created: {TIMESTAMP}
Updated: {TIMESTAMP}
Design review: approved
Reviewed at: {TIMESTAMP}
Review rationale: Human 确认问题、estimand、证据准入与停止规则。
Closure decision: open
Closed at:
Closure rationale:

## 1. Research Question and Decision

Research question: 暴露是否改变 30 天结局？
Decision this question informs: 是否开展独立验证。
Scope and boundary: 当前队列与预定义结局。

## 2. Hypotheses and Falsifiers

| Hypothesis | Alternative explanation | Falsifier or observation that changes the judgement |
|---|---|---|
| H1 暴露改变结局 | 基线混杂产生关联 | 调整后效应消失或方向相反 |

## 3. Estimand and Inference Unit

Population: 当前队列。
Exposure or intervention: 预定义暴露。
Comparator: 未暴露组。
Outcome and time: 30 天结局。
Observation and inference unit: 个体。

## 4. Study Design and Evidence Eligibility

Analysis mode and design: exploratory cohort analysis。
Eligible evidence: 锁定数据与预定义模型。
Ineligible evidence: 未记录的 post hoc subgroup。
Controls, confounders and missingness: 调整基线混杂并报告缺失。

## 5. Analysis and Uncertainty

Analysis strategy: 估计调整后组间差异。
Assumptions and checks: positivity、model fit 与敏感性分析。
Effect and uncertainty: effect estimate 与 95% CI。

## 6. Claim-Evidence Matrix

| Claim | Decisive evidence | Current evidence | Assessment |
|---|---|---|---|
| C-001: 暴露与结局存在有边界的关联 | 独立数据方向稳定 | E-001 | pending |

## 7. Acceptance, Stopping and Risks

Acceptance criteria: 方向稳定且稳健性检查通过。
Stopping criteria: 完成独立 confirmatory Artifact。
Risks and unresolved decisions: residual confounding。
"""


def reviewed_result() -> str:
    return f"""# Q-001 / A-001 Result

Question: Q-001
Artifact: A-001
Analysis mode: exploratory
Status: reviewed
Created: {TIMESTAMP}
Updated: {TIMESTAMP}

## 1. Question and Claims

Research question: 暴露是否改变 30 天结局？
Claims assessed: C-001。

## 2. Provenance Receipt

Data source and version: locked cohort v1, sha256 recorded in source receipt。
Code revision: abc123。
Environment or lock: pixi.lock sha256 123。
Command and seed: pixi run analysis --seed 7。
Run time: {TIMESTAMP}。

## 3. Method and Deviations

Method executed: 预定义调整模型。
Deviations from BRIEF: none。

## 4. Observed Evidence

### E-001

Claim: C-001
Relation: support
Source: [分析表](../../../results/Q-001/table.tsv)
Output: results/Q-001/table.tsv
Observation: 调整后效应方向稳定。
Effect and uncertainty: effect=0.10, 95% CI 0.02–0.18。

## 5. Validation

### Technical Validation

命令成功，输出存在且可解析。

### Scientific and Robustness Validation

敏感性分析方向一致，但尚未独立复现。

## 6. Inference

Assessment: support
Qualified claim: 在当前队列和模型下，暴露与结局存在关联。
Uncertainty: 残余混杂与队列特异性仍不能排除。
Alternative explanations and causal boundary: 观察性设计不支持因果断言。

## 7. Limitations and Applicability

Limitations: 单一队列且存在残余混杂。
Applicability boundary: 仅适用于当前纳入标准。

## 8. Next Decisive Test

Test: 在独立队列按相同 estimand 建立 confirmatory Artifact。
Decision it distinguishes: 区分稳定关联与队列特异偏差。

## 9. Human Review

Decision: approved
Reviewed at: {TIMESTAMP}
Review rationale: Evidence record 可进入阶段性综合。

## 10. Implementation Reuse

Reuse decision: not-assessed
Target: not applicable; 尚未评估复用。
Recorded at: not applicable; 尚未评估复用。
Files: not applicable; 尚未评估复用。
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "study"

        run(SCAFFOLD, "--project", str(project))
        assert not project.exists()
        run(SCAFFOLD, "--project", str(project), "--apply")
        assert sorted(path.name for path in project.iterdir()) == [
            ".gitignore",
            "AGENTS.md",
            "CURRENT_HANDOFF.md",
            "QUESTIONS.md",
            "README.md",
        ]
        assert not (project / "pixi.toml").exists()

        run(
            RECORD,
            "new-context",
            "--project",
            str(project),
            "--context",
            "cohort-a",
            "--scope",
            "subprojects/cohort-a",
            "--apply",
        )
        run(
            RECORD,
            "new-question",
            "--project",
            str(project),
            "--context",
            "cohort-a",
            "--question",
            "暴露是否改变 30 天结局？",
            "--apply",
        )

        brief = project / "docs/questions/Q-001/BRIEF.md"
        brief.write_text(approved_brief(), encoding="utf-8")
        questions = project / "QUESTIONS.md"
        question_lines = questions.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(question_lines):
            if not line.startswith("| Q-001 |"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            cells[2] = "approved"
            cells[-1] = TIMESTAMP
            question_lines[index] = "| " + " | ".join(cells) + " |"
        questions.write_text("\n".join(question_lines) + "\n", encoding="utf-8")

        run(
            RECORD,
            "new-artifact",
            "--project",
            str(project),
            "--context",
            "cohort-a",
            "--question-id",
            "Q-001",
            "--analysis-mode",
            "exploratory",
            "--apply",
        )
        result = project / "explore/Q-001/A-001/RESULT.md"
        result.write_text(reviewed_result(), encoding="utf-8")
        output = project / "results/Q-001/table.tsv"
        output.parent.mkdir(parents=True)
        output.write_text("group\teffect\nexposed\t0.10\n", encoding="utf-8")

        validation = run(VALIDATOR, "--project", str(project), "--json")
        validation_payload = json.loads(validation.stdout)
        assert validation_payload["structure_consistent"] is True
        assert validation_payload["scientific_validity"] == "not_evaluated"

        local_handoff = project / "subprojects/cohort-a/CURRENT_HANDOFF.md"
        local_text = local_handoff.read_text(encoding="utf-8")
        assert "Active question: Q-001" in local_text
        assert "Current artifact: A-001" in local_text

        report_args = ("--project", str(project), "--question", "Q-001")
        dry_run = run(REPORT, *report_args, "--json")
        assert json.loads(dry_run.stdout)["artifact_selection"] == "automatic"
        report_path = project / "reports/Q-001/report.html"
        assert not report_path.exists()
        run(REPORT, *report_args, "--apply")
        run(REPORT, *report_args, "--validate-only")
        html = report_path.read_text(encoding="utf-8")
        assert "阶段性报告" in html
        assert "Claim-Evidence 综合" in html
        assert "Validation and Robustness" in html
        assert "Next Decisive Test" in html
        assert not (project / "reports/Q-001/report.pdf").exists()
        print("Smoke test passed")


if __name__ == "__main__":
    main()
