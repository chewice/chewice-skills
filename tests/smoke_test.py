"""End-to-end smoke test for the bundled 0.6 CLI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "research-project-os/scripts/research_project_os.py"


def run(*arguments: str) -> str:
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
    return result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "pilot"
        run("inspect", "--project", str(project))
        run("init", "--project", str(project))
        run("init", "--project", str(project), "--apply")
        questions = project / "QUESTIONS.md"
        questions.write_text(
            """# Project Questions

## Project purpose

验证可复现 QC。

## Input constraints

- 原始输入只读。

## Output requirements

- 中文 HTML。

## FAQ

### 标准是什么？

输入不变且输出可复现。

## Current question

- ID: `Q-001`
- Question: 哪些 QC thresholds 稳定？
- Completion criterion: 生成审核报告。

## Question queue

- Q-002：聚类是否稳定？

## Answered questions

- 尚未登记。
""",
            encoding="utf-8",
        )
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
        )
        run(*explore_args)
        run(*explore_args, "--apply")
        task_name = "P0-QC-stable-thresholds-selected"
        task_root = project / "explore" / task_name
        (project / "data").mkdir()
        (project / "data/input.txt").write_text("input\n", encoding="utf-8")
        (task_root / "scripts/qc.py").write_text(
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
        run_args = (
            "run",
            "--project",
            str(project),
            "--input",
            "data/input.txt",
            "--output",
            "derived/result.txt",
            "--cwd",
            f"explore/{task_name}/scripts",
        )
        run(*run_args, "--", sys.executable, "qc.py")
        run(*run_args, "--apply", "--", sys.executable, "qc.py")
        run_id = next((task_root / "runs").iterdir()).name
        receipt = f"runs/{run_id}/receipt.yaml"
        (task_root / "README.md").write_text(
            f"""# {task_name}

## Direction
- Question ID: `Q-001`

## Inputs
- `data/input.txt`

## Method
- 执行 QC。

## Expected outputs
- `derived/result.txt`

## Stop condition
- 结果已生成。

## Run order
1. `scripts/qc.py`

## Observations
- 输出稳定。

## Limitations
- 测试数据。
""",
            encoding="utf-8",
        )
        (task_root / "report.md").write_text(
            f"""---
schema_version: "1.0.0"
kind: explore
language: zh-CN
title: "QC 报告"
task: "{task_name}"
run_receipts:
  - "{receipt}"
---
## 研究问题
哪些 QC thresholds 稳定？
## 输入与方法
使用 audited run。
## 结果
输出稳定。
## 限制
测试数据。
## 结论与下一问题
可供审核。
## 可复现信息
Receipt 已记录。
""",
            encoding="utf-8",
        )
        report_args = (
            "report-build",
            "--project",
            str(project),
            "--source",
            f"explore/{task_name}/report.md",
            "--output",
            f"explore/{task_name}/report.html",
            "--kind",
            "explore",
        )
        run(*report_args)
        run(*report_args, "--apply")
        promote_args = (
            "archive-promote",
            "--project",
            str(project),
            "--task",
            task_name,
            "--review-note",
            "人工确认 QC 结果。",
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
        pipeline["pipeline"]["entrypoint"] = "run.py"
        pipeline["steps"][0]["implementation"] = "src/qc.py"
        pipeline_path.write_text(
            yaml.safe_dump(pipeline, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (project / "pipeline/run.py").write_text(
            "# 提纲\n# 1. 运行\n\n# %% 1. 运行\nprint('ok')\n",
            encoding="utf-8",
        )
        (project / "pipeline/src/qc.py").write_text(
            "# 提纲\n# 1. 结果\n\n# %% 1. 结果\nresult = 'ok'\n",
            encoding="utf-8",
        )
        (project / "pipeline/report.md").write_text(
            f"""---
schema_version: "1.0.0"
kind: release
language: zh-CN
title: "正式报告"
snapshots:
  - "{selector}"
run_receipts: []
---
## 项目目的
验证 QC pipeline。
## 输入与方法
使用审核 snapshot。
## 主要结果
流程成功。
## 限制
测试数据。
## 结论
可以发布。
## 可复现信息
来源已记录。
""",
            encoding="utf-8",
        )
        final_report = (
            "report-build",
            "--project",
            str(project),
            "--source",
            "pipeline/report.md",
            "--output",
            "reports/final.html",
            "--kind",
            "release",
        )
        run(*final_report)
        run(*final_report, "--apply")
        release = (
            "pipeline-release",
            "--project",
            str(project),
            "--report",
            "reports/final.html",
            "--review-note",
            "人工确认发布。",
        )
        run(*release)
        run(*release, "--apply")
        run("audit", "--project", str(project))
        close = (
            "close",
            "--project",
            str(project),
            "--summary",
            "完成 QC lifecycle smoke。",
            "--completed",
            "完成 archive 与 release。",
            "--output",
            "reports/final.html",
            "--next-step",
            "由 human 选择下一问题。",
        )
        run(*close)
        run(*close, "--apply")
        run("audit", "--project", str(project))
    print("Smoke test passed")


if __name__ == "__main__":
    main()
