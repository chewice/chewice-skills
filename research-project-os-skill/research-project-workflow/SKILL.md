---
name: research-project-workflow
description: 当用户要求“初始化研究项目”“接管现有研究仓库”“创建或更新研究问题”“开展 Explore”“审核并晋升 Artifact”“恢复工作”“更新交接”或输入“总结工作”时，应使用此 Skill 管理研究项目工作流。
---

# 研究项目工作流

## 范围

管理项目脚手架、Question 与 `BRIEF.md`、Explore Artifact 与 `RESULT.md`、Human review、Pipeline promotion、`CURRENT_HANDOFF.md` 和“总结工作”。保持项目轻量、可恢复且可审核；不替代科学判断、文献检索、Pipeline runtime、Git 操作或正式报告生成。

## Human ownership

- 由 Human 提出问题、批准启动、确认 Evidence Basis、限制与验收条件。
- 由 Human 决定 Question 是否“已解决”或“废弃”、Artifact 是否“审核通过”或“拒绝”，以及是否进入 Pipeline。
- 由 Agent 结构化并维护索引、BRIEF、RESULT 和 Handoff，但不得伪造 Human 决定或验证结果。

## 按需加载

- 初始化、接管、目录与 Pixi：读取 [`references/scaffold.md`](references/scaffold.md)。
- 创建或更新 Question/BRIEF：读取 [`references/question.md`](references/question.md)。
- 创建、验证、审核或晋升 Artifact：读取 [`references/explore.md`](references/explore.md)。
- 恢复、切换或更新交接：读取 [`references/handoff.md`](references/handoff.md)。
- Human 输入“总结工作”：只读取 [`references/summarize-work.md`](references/summarize-work.md)。

每次仅加载当前任务对应的 reference 和其中明确列出的项目文件。不得默认扫描全部 Question、Artifact、日志或 `docs/template/`。

## 禁止与停止条件

- 所有写入先预览；只有明确确认后执行。不得自动 commit、push、写入 Notion 或覆盖已有内容。
- 不创建 `SPEC.md`、`PLAN.md`、`current-plan.md`、`project_manifest.yaml`、archive 或虚假 Q-ID/A-ID。
- 不自动开始下一 Question，不自动批准 Artifact，不自动生成正式 Report。
- 上下文冲突、Human ownership 不明确、必要输入缺失或验证失败时立即停止并请求 Human 决定。
