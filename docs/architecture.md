# Architecture

版本 `1.0.0` 只暴露两个团队级 Skill：

```text
research-project-workflow
├── SKILL.md
├── references/{scaffold,question,explore,handoff,summarize-work}.md
├── assets/
└── scripts/{scaffold_project,validate_project}.py

report-generation
├── SKILL.md
├── references/{html,pdf,templates,validation}.md
├── assets/{templates,css}/
└── scripts/generate_report.py
```

两者共享仓库根级 Pixi workspace。workflow 不 import report renderer；
report-generation 不改变 Question、Artifact 或 Pipeline 状态。

## 项目状态

- `QUESTIONS.md` 只保存 Question 索引，详细依据进入 `BRIEF.md`。
- `CURRENT_HANDOFF.md` 是唯一默认状态入口，旧历史交由 Git。
- Explore 使用 `explore/<Q-ID>/<A-ID>/RESULT.md`，拒绝版本原样保留。
- Question、Artifact 和 Workstream 使用三套相互独立的中文状态。
- 只有 Human 审核通过的 Artifact 可以整理进 `pipeline/`；Pipeline runtime 由项目自身负责。

## 安全

所有 mutation 默认 dry-run，并在 apply 前重新验证来源。脚手架不覆盖控制文件，
Validator 只读。报告只消费审核内容并写入 `reports/<Q-ID>/`。不存在 manifest、
archive、release、多层 lifecycle、历史 Handoff archive 或旧命令兼容层。
