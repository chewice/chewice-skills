"""Unit tests for the Research Project OS 0.6 harness."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "research-project-os"
sys.path.insert(0, str(SKILL))

from research_project_os import (  # noqa: E402
    MANIFEST_SCHEMA_VERSION,
    RELEASE_VERSION,
    ReportKind,
    build_report,
    build_report_text,
    validate_report,
)
from research_project_os.audit import (  # noqa: E402
    audit_project,
    inspect_project,
    inspect_pixi_policy,
)
from research_project_os.core import (  # noqa: E402
    ensure_manifest,
    hash_path,
    load_yaml,
    sha256_file,
    yaml_text,
)
from research_project_os.handoff import (  # noqa: E402
    apply_close,
    plan_close,
    start_context,
)
from research_project_os.lifecycle import (  # noqa: E402
    apply_archive_promotion,
    apply_explore_cancellation,
    apply_explore_task,
    apply_pipeline_creation,
    apply_pipeline_release,
    apply_run,
    current_research_question,
    plan_archive_promotion,
    plan_explore_cancellation,
    plan_explore_task,
    plan_pipeline_creation,
    plan_pipeline_release,
    plan_run,
    verify_archive_snapshot,
    verify_pipeline_release,
)
from research_project_os.scaffold import (  # noqa: E402
    apply_scaffold,
    plan_scaffold,
)


class ResearchProjectOSTests(unittest.TestCase):
    def make_project(self, root: Path) -> None:
        plan = plan_scaffold(root, "init")
        apply_scaffold(plan)

    @staticmethod
    def set_question(
        root: Path,
        *,
        question_id: str = "Q-001",
        question: str = "哪些 QC thresholds 稳定？",
        completion: str = "敏感性分析结果一致。",
    ) -> None:
        (root / "QUESTIONS.md").write_text(
            f"""# Project Questions

> 本文件完全由 human 维护。Agent 与 CLI 只读。

## Project purpose

识别稳定且可复现的细胞状态。

## Input constraints

- 原始矩阵只读。

## Output requirements

- 输出使用中文 HTML。

## FAQ

### 什么最重要？

可复现性。

## Questions

### {question_id} — 稳定 QC thresholds

- Status: `current`
- Depends on: `none`
- Review decision: `pending`
- Reviewed on: `pending`

#### Question

{question}

#### Inputs

- `data/input.txt`

#### Method reference

比较多个候选 thresholds。

#### Expected outputs

- 敏感性分析表。

#### Completion criterion

{completion}

#### Reviewed outcome

`pending`

#### Evidence

`pending`

### Q-002 — 稳定 clusters

- Status: `queued`
- Depends on: `{question_id}`
- Review decision: `pending`
- Reviewed on: `pending`

#### Question

哪些 clusters 稳定？

#### Inputs

待 Q-001 完成后讨论。

#### Method reference

待讨论。

#### Expected outputs

待讨论。

#### Completion criterion

待讨论。

#### Reviewed outcome

`pending`

#### Evidence

`pending`
""",
            encoding="utf-8",
        )

    @staticmethod
    def complete_readme(task_root: Path) -> None:
        (task_root / "README.md").write_text(
            f"""# {task_root.name}

## Direction

- Question ID: `Q-001`
- Question: 哪些 QC thresholds 稳定？

## Inputs

- `data/input.txt`

## Method

- 比较输入并生成稳定结果。

## Expected outputs

- `derived/result.txt`

## Stop condition

- 输出与输入 hash 已记录。

## Run order

1. 运行 `scripts/analyze.py`。

## Observations

- 输出生成成功。

## Limitations

- 仅覆盖测试数据。

## Code contract

- 使用中文提纲。
""",
            encoding="utf-8",
        )

    @staticmethod
    def complete_explore_report(task_root: Path, receipt: str) -> str:
        manifest = load_yaml(task_root / "report.build.yaml")
        metadata = manifest["report"]["source_metadata"]
        return f"""---
schema_version: "1.0.0"
kind: explore
language: zh-CN
title: "Q-001：QC 稳定性"
task: "{task_root.name}"
run_receipts:
  - "{receipt}"
---

# QC 稳定性

## 研究问题

哪些 QC thresholds 稳定？

## 输入与方法

读取只读输入并运行比较。

## 结果

获得稳定结果。

## 限制

仅为测试数据。

## 结论与下一问题

当前结果可供人工审核。

## 可复现信息

Run receipt 已记录。原 title 为 {metadata["title"]}。
"""

    @staticmethod
    def release_report_text(selector: str) -> str:
        return f"""---
schema_version: "1.0.0"
kind: release
language: zh-CN
title: "正式报告"
snapshots:
  - "{selector}"
run_receipts: []
---
## 项目目的
验证主流程。
## 输入与方法
使用审核 snapshot。
## 主要结果
流程成功。
## 限制
测试规模有限。
## 结论
可以发布。
## 可复现信息
来源 snapshot 已记录。
"""

    def create_completed_task(self, root: Path) -> tuple[str, str]:
        self.set_question(root)
        plan = plan_explore_task(
            root,
            order=0,
            core="QC",
            summary="stable thresholds selected",
        )
        apply_explore_task(plan)
        task_name = plan["task_name"]
        task_root = root / "explore" / task_name
        (root / "data").mkdir()
        (root / "data/input.txt").write_text("input\n", encoding="utf-8")
        script = task_root / "scripts/analyze.py"
        script.write_text(
            """# 提纲
# 1. 读取输入
# 2. 写出结果

# %% 1. 读取输入
from pathlib import Path
value = Path("../../../data/input.txt").read_text()

# %% 2. 写出结果
Path("../derived/result.txt").write_text(value + "result\\n")
""",
            encoding="utf-8",
        )
        run_plan = plan_run(
            root,
            inputs=["data/input.txt"],
            outputs=["derived/result.txt"],
            cwd=f"explore/{task_name}/scripts",
            command=[sys.executable, "analyze.py"],
        )
        run = apply_run(run_plan)
        self.assertEqual(run["status"], "success")
        self.complete_readme(task_root)
        receipt = f"runs/{run_plan['run_id']}/receipt.yaml"
        report_text = self.complete_explore_report(task_root, receipt)
        build_report_text(
            source_text=report_text,
            source_base=task_root,
            output=task_root / "report.html",
            project_root=root,
            kind=ReportKind.EXPLORE,
        )
        return task_name, run_plan["run_id"]

    def create_archive(self, root: Path) -> str:
        task_name, _ = self.create_completed_task(root)
        promotion = plan_archive_promotion(
            root,
            task_name=task_name,
            review_note="人工确认结果可进入主线。",
        )
        apply_archive_promotion(promotion)
        return promotion["selector"]

    def test_init_is_dry_run_minimal_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = plan_scaffold(root, "init")
            self.assertFalse((root / "project_manifest.yaml").exists())
            apply_scaffold(plan)
            self.assertEqual(
                {
                    path.name
                    for path in root.iterdir()
                    if path.is_file() and path.name != ".gitignore"
                },
                {
                    "AGENTS.md",
                    "CURRENT_HANDOFF.md",
                    "QUESTIONS.md",
                    "project_manifest.yaml",
                },
            )
            self.assertEqual(
                load_yaml(root / "project_manifest.yaml")["schema_version"],
                "0.4.0",
            )
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("遵循第一性原理", agents)
            self.assertIn("减少函数封装和工程化代码", agents)
            self.assertIn(
                "You may use superpowers, but do not write any spec or plan.",
                agents,
            )
            questions = (root / "QUESTIONS.md").read_text(encoding="utf-8")
            self.assertLess(
                questions.index("## Filling guide"),
                questions.index("## Project purpose"),
            )
            self.assertIn("### Status reference", questions)
            self.assertIn("### Review decision reference", questions)
            second = plan_scaffold(root, "adopt")
            self.assertFalse(
                any(
                    action.action in {"create", "overwrite"}
                    for action in second["actions"]
                )
            )

    def test_adopt_preserves_owned_and_legacy_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("existing\n", encoding="utf-8")
            (root / "QUESTIONS.md").write_text("human\n", encoding="utf-8")
            (root / "project_manifest.yaml").write_text(
                "schema_version: 0.3.0\nproject: {}\n",
                encoding="utf-8",
            )
            legacy = root / "work/notion_sync/pending"
            legacy.mkdir(parents=True)
            plan = plan_scaffold(root, "adopt", overwrite=True)
            apply_scaffold(plan)
            self.assertEqual((root / "AGENTS.md").read_text(), "existing\n")
            self.assertEqual((root / "QUESTIONS.md").read_text(), "human\n")
            self.assertTrue(legacy.is_dir())
            self.assertEqual(
                ensure_manifest(root)["schema_version"],
                "0.3.0",
            )

    def test_inspect_is_read_only_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "data/deep").mkdir(parents=True)
            before = sorted(path.as_posix() for path in root.rglob("*"))
            result = inspect_project(root)
            after = sorted(path.as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(result["recommended_mode"], "adopt")
            self.assertIn("scripts", result["project_inventory"]["code_roots"])

    def test_questions_are_human_owned_and_drive_one_task(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            before = (root / "QUESTIONS.md").read_bytes()
            current = current_research_question(root)
            self.assertEqual(current["id"], "Q-001")
            first = plan_explore_task(root, order=0, core="QC", summary="stable cells")
            apply_explore_task(first)
            self.assertEqual((root / "QUESTIONS.md").read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "Resolve the current"):
                plan_explore_task(
                    root, order=1, core="cluster", summary="stable groups"
                )
            self.assertTrue((root / first["task_path"] / "report.build.yaml").is_file())
            self.assertFalse((root / first["task_path"] / "report.md").exists())
            report_manifest = load_yaml(
                root / first["task_path"] / "report.build.yaml"
            )
            self.assertEqual(report_manifest["report"]["source_mode"], "inline")
            self.assertIsNone(report_manifest["report"]["source"])
            report_html = (root / first["task_path"] / "report.html").read_text(
                encoding="utf-8"
            )
            self.assertIn('id="rpos-markdown-source"', report_html)

    def test_question_blocks_keep_statuses_in_one_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            current = current_research_question(root)
            self.assertEqual(current["id"], "Q-001")
            self.assertEqual(current["format"], "blocks")
            self.assertIn("data/input.txt", current["inputs"])
            result = audit_project(root)
            self.assertTrue(result["ok"], result["errors"])
            self.assertFalse(
                any("legacy split" in warning for warning in result["warnings"])
            )

    def test_question_blocks_reject_multiple_current_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            path = root / "QUESTIONS.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "- Status: `queued`", "- Status: `current`"
                ),
                encoding="utf-8",
            )
            result = audit_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("more than one current" in error for error in result["errors"])
            )
            with self.assertRaisesRegex(ValueError, "exactly one question block"):
                current_research_question(root)

    def test_answered_question_requires_compact_outcome_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            path = root / "QUESTIONS.md"
            text = path.read_text(encoding="utf-8")
            text = text.replace("- Status: `current`", "- Status: `answered`", 1)
            text = text.replace(
                "- Review decision: `pending`",
                "- Review decision: `accepted_with_limitations`",
                1,
            )
            text = text.replace(
                "- Reviewed on: `pending`", "- Reviewed on: `2026-08-02`", 1
            )
            path.write_text(text, encoding="utf-8")
            result = audit_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("must fill reviewed_outcome" in error for error in result["errors"])
            )
            text = text.replace("`pending`", "人工审核确认 QC 结论。", 1)
            text = text.replace("`pending`", "`P0-QC-stable-cells@v001`", 1)
            path.write_text(text, encoding="utf-8")
            result = audit_project(root)
            self.assertTrue(result["ok"], result["errors"])
            self.assertTrue(
                any("no current question" in warning for warning in result["warnings"])
            )

    def test_question_review_decision_must_match_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            path = root / "QUESTIONS.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "- Review decision: `pending`",
                    "- Review decision: `accepted`",
                    1,
                ),
                encoding="utf-8",
            )
            result = audit_project(root)
            self.assertFalse(result["ok"])
            self.assertTrue(
                any(
                    "does not allow Review decision" in error
                    for error in result["errors"]
                )
            )
            with self.assertRaisesRegex(ValueError, "Review decision"):
                current_research_question(root)

    def test_legacy_question_layout_remains_read_only_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            (root / "QUESTIONS.md").write_text(
                """# Project Questions

## Project purpose

验证兼容性。

## Input constraints

- 输入只读。

## Output requirements

- 输出审核结果。

## FAQ

### 标准是什么？

可复现。

## Current question

- ID: `Q-001`
- Question:
  哪些 QC thresholds
  在 sensitivity analysis 中稳定？
- Completion criterion:
  生成审核报告。

## Question queue

- 尚未登记。

## Answered questions

- 尚未登记。
""",
                encoding="utf-8",
            )
            current = current_research_question(root)
            self.assertEqual(current["format"], "legacy")
            self.assertIn("sensitivity analysis", current["question"])
            result = audit_project(root)
            self.assertTrue(result["ok"], result["errors"])
            self.assertTrue(
                any("legacy split" in warning for warning in result["warnings"])
            )

    def test_cancelled_task_preserves_content_and_unblocks_next_question_task(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            first = plan_explore_task(
                root, order=0, core="QC", summary="failed direction"
            )
            apply_explore_task(first)
            task_root = root / first["task_path"]
            cancellation = plan_explore_cancellation(
                root,
                task_name=first["task_name"],
                review_note="human 决定停止该方向。",
            )
            self.assertEqual(
                load_yaml(task_root / "task.yaml")["task"]["status"],
                "ready",
            )
            apply_explore_cancellation(cancellation)
            self.assertEqual(
                load_yaml(task_root / "task.yaml")["task"]["status"],
                "cancelled",
            )
            self.assertTrue((task_root / "report.html").is_file())
            next_task = plan_explore_task(
                root,
                order=1,
                core="QC",
                summary="revised direction",
            )
            self.assertEqual(next_task["task"]["direction"]["question_id"], "Q-001")
            with self.assertRaisesRegex(ValueError, "cancelled"):
                plan_archive_promotion(
                    root,
                    task_name=first["task_name"],
                    review_note="不可归档。",
                )

    def test_report_api_is_deterministic_and_embeds_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            source = root / "report.md"
            image = root / "figure.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            source.write_text(
                """---
schema_version: "1.0.0"
kind: explore
language: zh-CN
title: "测试报告"
task: "P0-QC-test"
run_receipts: []
---

## 研究问题
问题。
## 输入与方法
方法。<script>alert(1)</script>
## 结果
![图](figure.png)
[来源](https://example.org/paper)
## 限制
限制。
## 结论与下一问题
结论。
## 可复现信息
信息。
""",
                encoding="utf-8",
            )
            output = root / "report.html"
            first = build_report(
                source=source,
                output=output,
                project_root=root,
                kind=ReportKind.EXPLORE,
            )
            content = output.read_bytes()
            second = build_report(
                source=source,
                output=output,
                project_root=root,
                kind=ReportKind.EXPLORE,
            )
            self.assertEqual(content, output.read_bytes())
            self.assertEqual(first.output_sha256, second.output_sha256)
            self.assertTrue(source.is_file())
            self.assertEqual(first.source_mode, "markdown")
            self.assertEqual(first.source, "report.md")
            html = output.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("https://example.org/paper", html)
            self.assertTrue(
                validate_report(
                    output=output,
                    project_root=root,
                    kind=ReportKind.EXPLORE,
                    require_complete=True,
                )["ok"]
            )

    def test_report_cli_and_api_generate_identical_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            source = root / "report.md"
            source.write_text(
                """---
schema_version: "1.0.0"
kind: explore
language: zh-CN
title: "一致性测试"
task: "P0-QC-test"
run_receipts: []
---
## 研究问题
问题。
## 输入与方法
方法。
## 结果
结果。
## 限制
限制。
## 结论与下一问题
结论。
## 可复现信息
信息。
""",
                encoding="utf-8",
            )
            api_output = root / "api.html"
            cli_output = root / "cli.html"
            build_report_text(
                source_text=source.read_text(encoding="utf-8"),
                source_base=root,
                output=api_output,
                project_root=root,
                kind=ReportKind.EXPLORE,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts/research_project_os.py"),
                    "report-build",
                    "--project",
                    str(root),
                    "--stdin",
                    "--source-base",
                    ".",
                    "--output",
                    "cli.html",
                    "--kind",
                    "explore",
                    "--apply",
                ],
                check=True,
                capture_output=True,
                text=True,
                input=source.read_text(encoding="utf-8"),
            )
            self.assertEqual(api_output.read_bytes(), cli_output.read_bytes())

    def test_report_validates_local_links_and_rejects_unsafe_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            resource = root / "table.tsv"
            resource.write_text("x\ty\n", encoding="utf-8")
            source = root / "report.md"
            template = """---
schema_version: "1.0.0"
kind: explore
language: zh-CN
title: "资源测试"
task: "P0-QC-test"
run_receipts: []
---
## 研究问题
x
## 输入与方法
x
## 结果
{resource}
## 限制
x
## 结论与下一问题
x
## 可复现信息
x
"""
            source.write_text(
                template.format(resource="[table](table.tsv)"),
                encoding="utf-8",
            )
            output = root / "report.html"
            build = build_report(
                source=source,
                output=output,
                project_root=root,
                kind=ReportKind.EXPLORE,
            )
            self.assertEqual(build.assets[0]["path"], "table.tsv")
            self.assertEqual(build.assets[0]["mode"], "linked")
            for unsafe in (
                "[missing](missing.tsv)",
                "[escape](../outside.tsv)",
                "[absolute](file:///tmp/outside.tsv)",
            ):
                with self.subTest(resource=unsafe):
                    source.write_text(
                        template.format(resource=unsafe),
                        encoding="utf-8",
                    )
                    output.write_text("preserve", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        build_report(
                            source=source,
                            output=output,
                            project_root=root,
                            kind=ReportKind.EXPLORE,
                        )
                    self.assertEqual(output.read_text(), "preserve")

    def test_report_rejects_remote_images_and_keeps_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            source = root / "report.md"
            source.write_text(
                """---
schema_version: "1.0.0"
kind: explore
language: zh-CN
title: "测试"
task: "P0-QC-test"
run_receipts: []
---
## 研究问题
x
## 输入与方法
x
## 结果
![remote](https://example.org/x.png)
## 限制
x
## 结论与下一问题
x
## 可复现信息
x
""",
                encoding="utf-8",
            )
            output = root / "report.html"
            output.write_text("preserve", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_report(
                    source=source,
                    output=output,
                    project_root=root,
                    kind=ReportKind.EXPLORE,
                )
            self.assertEqual(output.read_text(), "preserve")

    def test_report_rejects_non_chinese_metadata_and_core_section_reordering(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            source = root / "report.md"
            source.write_text(
                """---
schema_version: "1.0.0"
kind: explore
language: en
title: "invalid"
task: "P0-QC-test"
run_receipts: []
---
## 研究问题
x
## 结果
x
## 输入与方法
x
## 限制
x
## 结论与下一问题
x
## 可复现信息
x
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "language must be zh-CN"):
                build_report(
                    source=source,
                    output=root / "report.html",
                    project_root=root,
                    kind=ReportKind.EXPLORE,
                )
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "language: en", "language: zh-CN"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "out of order"):
                build_report(
                    source=source,
                    output=root / "report.html",
                    project_root=root,
                    kind=ReportKind.EXPLORE,
                )

    def test_audited_run_records_hashes_logs_and_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            task_name, run_id = self.create_completed_task(root)
            receipt_path = (
                root / "explore" / task_name / "runs" / run_id / "receipt.yaml"
            )
            receipt = load_yaml(receipt_path)
            self.assertEqual(receipt["run"]["status"], "success")
            self.assertEqual(
                receipt["inputs_before"],
                receipt["inputs_after"],
            )
            self.assertEqual(
                receipt["outputs"][0]["sha256"],
                sha256_file(root / "explore" / task_name / "derived/result.txt"),
            )
            self.assertTrue((receipt_path.parent / "stdout.log").is_file())
            self.assertIn("pixi.lock", receipt["provenance"]["environment"])

    def test_input_mutation_is_a_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            explore = plan_explore_task(root, order=0, core="QC", summary="mutation")
            apply_explore_task(explore)
            (root / "input.txt").write_text("before\n", encoding="utf-8")
            command = [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "Path('../../input.txt').write_text('after\\n'); "
                    "Path('derived/out.txt').write_text('out\\n')"
                ),
            ]
            run = plan_run(
                root,
                inputs=["input.txt"],
                outputs=["derived/out.txt"],
                cwd=f"explore/{explore['task_name']}",
                command=command,
            )
            applied = apply_run(run)
            self.assertEqual(applied["status"], "violation")
            self.assertTrue(
                any("inputs changed" in value for value in applied["violations"])
            )

    def test_command_start_failure_still_writes_a_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            explore = plan_explore_task(root, order=0, core="QC", summary="failed run")
            apply_explore_task(explore)
            (root / "input.txt").write_text("input\n", encoding="utf-8")
            run = plan_run(
                root,
                inputs=["input.txt"],
                outputs=["derived/out.txt"],
                cwd=f"explore/{explore['task_name']}",
                command=["command-that-does-not-exist-rpos"],
            )
            applied = apply_run(run)
            receipt_path = root / run["receipt_path"]
            receipt = load_yaml(receipt_path)
            self.assertEqual(applied["status"], "violation")
            self.assertIsNone(receipt["run"]["exit_code"])
            self.assertTrue((receipt_path.parent / "stderr.log").is_file())
            self.assertIn("sha256", receipt["logs"]["stderr"])

    def test_apply_time_symlink_violation_still_writes_a_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            explore = plan_explore_task(
                root, order=0, core="QC", summary="symlink input"
            )
            apply_explore_task(explore)
            source = root / "input.txt"
            target = root / "target.txt"
            source.write_text("input\n", encoding="utf-8")
            target.write_text("target\n", encoding="utf-8")
            run = plan_run(
                root,
                inputs=["input.txt"],
                outputs=["derived/out.txt"],
                cwd=f"explore/{explore['task_name']}",
                command=[sys.executable, "-c", "print('should not run')"],
            )
            source.unlink()
            source.symlink_to(target)
            applied = apply_run(run)
            self.assertEqual(applied["status"], "violation")
            self.assertTrue((root / run["receipt_path"]).is_file())
            self.assertTrue(
                any("symlink" in value.lower() for value in applied["violations"])
            )

    def test_output_escape_is_rejected_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            explore = plan_explore_task(root, order=0, core="QC", summary="safe output")
            apply_explore_task(explore)
            (root / "input.txt").write_text("input\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "active task"):
                plan_run(
                    root,
                    inputs=["input.txt"],
                    outputs=["../outside.txt"],
                    cwd=f"explore/{explore['task_name']}",
                    command=[sys.executable, "-c", "print('no')"],
                )

    def test_hash_path_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "input"
            directory.mkdir()
            (directory / "a.txt").write_text("a", encoding="utf-8")
            (directory / "b.txt").write_text("b", encoding="utf-8")
            record = hash_path(root, directory)
            self.assertEqual(record["file_count"], 2)
            self.assertEqual(
                {value["path"] for value in record["files"]},
                {"a.txt", "b.txt"},
            )
            self.assertTrue(all(value["sha256"] for value in record["files"]))
            target = root / "target.txt"
            target.write_text("x", encoding="utf-8")
            link = root / "link.txt"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                hash_path(root, link)

    def test_archive_is_immutable_and_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            selector = self.create_archive(root)
            result = verify_archive_snapshot(root, selector)
            self.assertTrue(result["ok"], result["errors"])
            archive_root = root / result["archive_path"]
            with self.assertRaisesRegex(FileExistsError, "Archive content"):
                build_report_text(
                    source_text="not reached",
                    source_base=archive_root,
                    output=archive_root / "report.html",
                    project_root=root,
                    kind=ReportKind.EXPLORE,
                )
            archived = root / result["archive_path"] / "derived/result.txt"
            archived.write_text("changed\n", encoding="utf-8")
            self.assertFalse(verify_archive_snapshot(root, selector)["ok"])

    def test_archive_rejects_incomplete_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.set_question(root)
            explore = plan_explore_task(root, order=0, core="QC", summary="incomplete")
            apply_explore_task(explore)
            with self.assertRaises(ValueError):
                plan_archive_promotion(
                    root,
                    task_name=explore["task_name"],
                    review_note="reviewed",
                )

    def test_archive_rechecks_inputs_after_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            task_name, _ = self.create_completed_task(root)
            (root / "data/input.txt").write_text("changed later\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "input changed after execution"):
                plan_archive_promotion(
                    root,
                    task_name=task_name,
                    review_note="人工审核。",
                )

    def test_archive_rejects_reporting_logic_in_analysis_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            task_name, _ = self.create_completed_task(root)
            script = root / "explore" / task_name / "scripts/analyze.py"
            script.write_text(
                script.read_text(encoding="utf-8")
                + "\nfrom research_project_os.reporting import build_report\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "report rendering logic"):
                plan_archive_promotion(
                    root,
                    task_name=task_name,
                    review_note="人工审核。",
                )

    def test_pipeline_and_release_are_archive_derived(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            selector = self.create_archive(root)
            pipeline = plan_pipeline_creation(root, selectors=[selector])
            apply_pipeline_creation(pipeline)
            pipeline_path = root / "pipeline/pipeline.yaml"
            document = load_yaml(pipeline_path)
            document["pipeline"]["entrypoint"] = "run.py"
            document["steps"][0]["implementation"] = "src/qc.py"
            pipeline_path.write_text(yaml_text(document), encoding="utf-8")
            (root / "pipeline/run.py").write_text(
                "# 提纲\n# 1. 运行主流程\n\n# %% 1. 运行主流程\nprint('ok')\n",
                encoding="utf-8",
            )
            (root / "pipeline/src/qc.py").write_text(
                "# 提纲\n# 1. 返回结果\n\n# %% 1. 返回结果\nresult = 'ok'\n",
                encoding="utf-8",
            )
            (root / "reports").mkdir(exist_ok=True)
            report_text = self.release_report_text(selector)
            build_report_text(
                source_text=report_text,
                source_base=root / "reports",
                output=root / "reports/final.html",
                project_root=root,
                kind=ReportKind.RELEASE,
            )
            release = plan_pipeline_release(
                root,
                report="reports/final.html",
                review_note="人工确认发布。",
            )
            apply_pipeline_release(release)
            self.assertTrue(verify_pipeline_release(root)["ok"])
            with self.assertRaisesRegex(FileExistsError, "immutable"):
                build_report_text(
                    source_text=report_text,
                    source_base=root / "reports",
                    output=root / "reports/final.html",
                    project_root=root,
                    kind=ReportKind.RELEASE,
                )
            (root / "pipeline/src/qc.py").write_text("changed\n", encoding="utf-8")
            self.assertFalse(verify_pipeline_release(root)["ok"])

    def test_pipeline_release_rejects_archive_runtime_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            selector = self.create_archive(root)
            apply_pipeline_creation(plan_pipeline_creation(root, selectors=[selector]))
            pipeline_path = root / "pipeline/pipeline.yaml"
            document = load_yaml(pipeline_path)
            document["pipeline"]["entrypoint"] = "run.py"
            document["steps"][0]["implementation"] = "src/qc.py"
            pipeline_path.write_text(yaml_text(document), encoding="utf-8")
            (root / "pipeline/run.py").write_text(
                "open('../archive/data.txt')\n",
                encoding="utf-8",
            )
            (root / "pipeline/src/qc.py").write_text("result = 1\n", encoding="utf-8")
            build_report_text(
                source_text=self.release_report_text(selector),
                source_base=root / "reports",
                output=root / "reports/final.html",
                project_root=root,
                kind=ReportKind.RELEASE,
            )
            with self.assertRaisesRegex(ValueError, "references explore/archive"):
                plan_pipeline_release(
                    root,
                    report="reports/final.html",
                    review_note="reviewed",
                )

    def test_pipeline_release_requires_report_snapshots_to_match_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            selector = self.create_archive(root)
            apply_pipeline_creation(plan_pipeline_creation(root, selectors=[selector]))
            pipeline_path = root / "pipeline/pipeline.yaml"
            document = load_yaml(pipeline_path)
            document["pipeline"]["entrypoint"] = "run.py"
            document["steps"][0]["implementation"] = "src/qc.py"
            pipeline_path.write_text(yaml_text(document), encoding="utf-8")
            (root / "pipeline/run.py").write_text(
                "# 提纲\n# 1. 运行\n\n# %% 1. 运行\nprint('ok')\n",
                encoding="utf-8",
            )
            (root / "pipeline/src/qc.py").write_text(
                "# 提纲\n# 1. 计算\n\n# %% 1. 计算\nresult = 1\n",
                encoding="utf-8",
            )
            build_report_text(
                source_text=self.release_report_text("P9-QC-unrelated@v001"),
                source_base=root / "reports",
                output=root / "reports/final.html",
                project_root=root,
                kind=ReportKind.RELEASE,
            )
            with self.assertRaisesRegex(ValueError, "snapshots do not match"):
                plan_pipeline_release(
                    root,
                    report="reports/final.html",
                    review_note="reviewed",
                )

    def test_start_context_and_close_are_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            context = start_context(root)
            self.assertEqual(
                set(context["context"]),
                {
                    "AGENTS.md",
                    "QUESTIONS.md",
                    "CURRENT_HANDOFF.md",
                    "project_manifest.yaml",
                },
            )
            close = plan_close(
                root,
                summary="完成 scaffold。",
                completed=["初始化项目。"],
                outputs=["audit result"],
                next_step="填写 current question。",
                owner="test",
            )
            applied = apply_close(close)
            self.assertNotEqual(close["previous_session"], close["new_session"])
            self.assertTrue((root / applied["archive_path"]).is_file())
            self.assertIn(
                "填写 current question",
                (root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8"),
            )
            second = plan_close(
                root,
                summary="继续维护 harness。",
                completed=[],
                outputs=[],
                next_step="继续下一步。",
                owner="test",
            )
            apply_close(second)
            self.assertNotEqual(second["previous_session"], second["new_session"])

    def test_start_context_does_not_verify_or_load_old_archives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            self.create_archive(root)
            with patch(
                "research_project_os.lifecycle.verify_archive_snapshot",
                side_effect=AssertionError("start must not verify archive content"),
            ):
                context = start_context(root)
            self.assertIsNone(context["active_task"])

    def test_pixi_nested_workspace_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            (root / "pixi.toml").write_text("[workspace]\nname='x'\n", encoding="utf-8")
            (root / "pixi.lock").write_text("version: 6\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "add", "pixi.lock"],
                check=True,
            )
            nested = root / "nested"
            nested.mkdir()
            (nested / "pixi.toml").write_text(
                "[workspace]\nname='nested'\n",
                encoding="utf-8",
            )
            policy = inspect_pixi_policy(root)
            codes = {issue["code"] for issue in policy["issues"]}
            self.assertIn("nested_workspace_manifest", codes)

    def test_lifecycle_log_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            lines = (root / "work/audit/lifecycle.jsonl").read_text().splitlines()
            events = [json.loads(line) for line in lines]
            self.assertEqual(events[0]["action"], "init")
            self.assertRegex(events[0]["event_id"], r"^EVT-\d{8}-\d{3}$")

    def test_release_constants(self) -> None:
        self.assertEqual(RELEASE_VERSION, "0.7.1")
        self.assertEqual(MANIFEST_SCHEMA_VERSION, "0.4.0")

    def test_fresh_project_audit_passes_with_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            result = audit_project(root)
            self.assertTrue(result["ok"], result["errors"])
            self.assertTrue(
                any("current question" in value for value in result["warnings"])
            )


if __name__ == "__main__":
    unittest.main()
