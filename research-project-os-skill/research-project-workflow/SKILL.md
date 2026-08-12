---
name: research-project-workflow
description: 当用户要求建立或接管科研分析项目、把问题转成可证伪的研究设计、创建或更新 Question/BRIEF、记录探索性或验证性 Artifact/RESULT、审核证据与有边界结论、管理大型项目的分层上下文交接、恢复工作或“总结工作”时，使用此 Skill。它维护 Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test 闭环；不负责具体分析脚本风格、Pixi 环境设计或正式报告渲染。
---

# 问题驱动科研工作流

## 核心合同

以 `Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test` 组织科研分析。`BRIEF.md` 只记录事前问题与设计，`RESULT.md` 只记录事后证据与推断；null、negative、contradictory 和 inconclusive evidence 必须与支持性证据同样保留。

保持四类判定相互独立：technical validation 不等于 scientific support；Human approval 不等于 scientific validity；implementation reuse 不等于前述判定。Validator 只可报告 `structure_consistent`，不能替代科学审核。

## Human ownership 与 Agent autonomy

- Human 决定研究问题与关键边界，审核 Study Design，判断 evidence 是否足以支持 qualified claim，作出 Question closure、Artifact review 与 implementation reuse 决定。
- Agent 可结构化问题、提出 hypotheses/falsifiers、设计证据与不确定性评估、保留反例、起草推断和 next decisive test，并维护机械索引与上下文路由；不得伪造 Human 决定、运行 receipt、证据或验证结果。
- 用户已经明确请求的项目内、非覆盖、可恢复写入无需二次确认。脚本仍默认 dry-run，只有显式 `--apply` 才写入；覆盖、删除、Git mutation、Notion 或其他外部写入仍需明确授权。

## 按需加载

- 初始化、接管或按需扩展项目：读取 [`references/scaffold.md`](references/scaffold.md)。
- 创建、更新、审核或关闭 Question/BRIEF：读取 [`references/question.md`](references/question.md)。
- 创建 Artifact、记录 Evidence/RESULT、Human review 或 implementation reuse：读取 [`references/explore.md`](references/explore.md)。
- 恢复、切换或维护根/局部上下文：读取 [`references/handoff.md`](references/handoff.md)。
- Human 输入“总结工作”：只读取 [`references/summarize-work.md`](references/summarize-work.md)。

每次只加载当前动作所需 reference、根 `CURRENT_HANDOFF.md` 声明的上下文路由，以及当前 BRIEF/RESULT 明确引用的输入。不得递归发现未在 Context Map 声明的局部 Handoff，也不得默认扫描全部 Question、Artifact、日志或参考代码。

## 边界与停止条件

- Scaffold/adopt non-destructive、lazy 且不生成固定 Pixi 环境；需要构建或修改 Pixi 环境时调用 `pixi-environment-builder` Skill。
- 具体 R、Python、Bash 生物信息学分析脚本的线性写法属于 `scripting-style` Skill；本 Skill 只维护科研问题、设计、证据、推断与交接合同，不规定具体分析方法。
- 不自动关闭 Question、批准/拒绝 Artifact、判定 scientific validity、决定 implementation reuse、生成正式 Report 或开始无关的下一 Question。
- 科学问题或作用域冲突、必要输入缺失、证据来源不明、结构验证失败，或需覆盖/删除/外部写入时停止并请求 Human 决定。
