---
name: research-project-os
description: 为研究项目搭建并维持轻量、可审计的 harness，包括 human-owned 项目目的与问题队列、最小 Agent context、可恢复 handoff、根级 Pixi、逐题 explore、完整 run receipts、人工审核 archive、独立 pipeline 和 Markdown 到中文 HTML reporting API。适用于初始化或接管研究仓库、恢复 session、组织探索任务、记录可复现运行、归档结果、发表前整理和结构审计；不作为科学分析、数据下载、文献检索、依赖求解或作图的主要 workflow。
---

# Research Project OS

## 操作 harness

先解析安装 symlink，并使用 Skill workspace 根级 Pixi：

```bash
SKILL_ROOT="$(readlink -f "${CODEX_HOME:-$HOME/.codex}/skills/research-project-os")"
SKILL_WORKSPACE="$(dirname "$SKILL_ROOT")"
pixi run --locked --manifest-path "$SKILL_WORKSPACE/pixi.toml" \
  python "$SKILL_ROOT/scripts/research_project_os.py" --help
```

下文以 `rpos` 代指上述 Python CLI。接管未知仓库前先运行 `inspect`；空目录使用
`init`，已有项目使用非破坏性的 `adopt`；`start` 生成最小 context pack，
`audit` 只读检查，`close` 保存可恢复 handoff。所有 mutation 必须先 dry-run，
确认后才加 `--apply`。所有项目路径统一通过 `--project` 传入，例如：

```text
rpos init --project /path/to/project
rpos init --project /path/to/project --apply
rpos start --project /path/to/project
```

`QUESTIONS.md` 完全由 human 维护，Agent 与 CLI 只读。默认只加载
`AGENTS.md`、`QUESTIONS.md`、`CURRENT_HANDOFF.md`、
`project_manifest.yaml` 和当前 task。面向 human 的内容默认中文；专业术语、
code、paths、commands 和 machine values 保持英文。

## 逐题推进

先与 human 讨论 current question 的 inputs、method、expected outputs 和 stop
condition；得到明确批准后才创建 task 或执行计算。一次只允许一个 unresolved
explore task。scripts、derived data、figures、run receipts、Markdown source 与
HTML report 全部留在该 task。回答问题并说明限制后停止，不修改问题队列，也不自动
开始下一题。

explore code 应像可执行 lab notebook：单次逻辑保持 inline，显示 intermediates，
允许少量重复，把 reusable abstraction 留到 pipeline。每个 executable file 顶部
必须有中文 outline，并使用对应编号的中文 section headings。analysis scripts
不得包含 HTML、CSS、template 或 report rendering logic。

实际计算只通过 audited `run`：复核输入完整 SHA-256、task-local outputs、
stdout/stderr、Git 和 Pixi provenance。只有完整且经过 human review 的 task
才能进入不可变 archive。pipeline 只从验证通过的 archive 整理，正式发布使用独立
中文 HTML report。

项目只允许一个根级 Pixi workspace 和受 Git 跟踪的根 lock；忽略根 `.pixi/`，
拒绝嵌套 workspace、lock 或 environment。不得隐式 overwrite、stage、commit、
push、solve environment 或进行外部同步。

## 按需加载

- scaffold、ownership、context、安全、Pixi 和 audited execution：
  [harness.md](references/harness.md)
- 创建、运行、归档或发布分析：
  [exploration.md](references/exploration.md)
- 构建或验证 HTML：
  [reporting.md](references/reporting.md)

Release `0.6.0` 使用 manifest schema `0.4.0`，并只读兼容 legacy `0.3.0`。
