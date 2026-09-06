---
name: research-project-workflow
description: 当用户要求建立或接管科研分析项目、把问题转成可证伪的研究设计、创建或更新 Question/BRIEF、记录探索性或验证性 Artifact/RESULT、审核证据与有边界结论、管理大型项目的分层上下文交接、恢复工作或“总结工作”时，使用此 Skill。它维护 Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test 闭环；不负责具体分析脚本风格、Pixi 环境设计或正式报告渲染。
---

# 问题驱动科研工作流

## 核心合同

以科学分析为主，遵循第一性原理和奥卡姆剃刀原理：从数据生成过程、比较对象、推断单位和竞争性解释出发，先完成能改变判断的最小分析，再按观察决定是否扩展。目录和记录服务于分析。

分析代码从上到下展开，关键科学决策直接可见；一次性逻辑不包装，真实重复才提取小函数。遇到错误先查原因，不堆叠 fallback、重试、宽泛异常捕获或预防性兼容分支。不为探索搭建通用 runner 或配置框架。

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
- 首次检查生物医学数据或改变样本分组、输入对象：读取 [`references/biomedical-data.md`](references/biomedical-data.md)，明确样本关系、独立重复和数值含义；优先引用已有样本表与数据说明。
- 恢复、切换或维护根/局部上下文：读取 [`references/handoff.md`](references/handoff.md)。
- Human 输入“总结工作”：只读取 [`references/summarize-work.md`](references/summarize-work.md)。

优先读取当前动作所需 reference、根 `CURRENT_HANDOFF.md` 的上下文路由和当前 BRIEF/RESULT。缺少线索时可定向查找相关数据、代码和资料，将有用入口补入 Required Reads；不默认扫描全部历史记录。Validator 仍只检查已声明的上下文。

## 探索的最小记录

exploratory 默认创建 `Record format: compact` 的简短 BRIEF 和 RESULT：只记录问题、输入、试做、观察与下一步。描述性探索可暂时没有 hypothesis、C-ID/E-ID 或审核章节；未知设计如实标记。先小范围试做、观察比较、形成有边界判断，再扩展。每段有独立科学目的的分析保存一个 Artifact；同一 draft 内持续补充试做，保留影响结论的参数选择和偏离，不为每次作图新建记录。已形成证据的修订或独立验证建立新 Artifact。

confirmatory 在执行前要求已审核的完整设计；compact 记录进入正式审核前补全完整模板并改为 `Record format: full`，保留已有观察、路径和日期，新增设计注明时间。探索后选定的方法不能冒充事前检验。Human review、Question closure 与正式报告是独立动作，不要求日常探索逐步等待审批。

## 边界与停止条件

- Scaffold/adopt non-destructive、lazy 且不生成固定 Pixi 环境；需要构建或修改 Pixi 环境时调用 `pixi-environment-builder` Skill。
- 具体 R、Python、Bash 写法可按需使用已安装的 `scripting-style` Skill；缺少该 Skill 时遵循上述分析原则，不阻塞分析。本 Skill 不规定具体统计方法。
- 不自动关闭 Question、批准/拒绝 Artifact、判定 scientific validity、决定 implementation reuse、生成正式 Report 或开始无关的下一 Question。
- 作用域冲突、关键输入缺失或需要新的授权时，只暂停依赖该条件的工作并说明所需决定。可恢复的结构错误直接修复；来源不明的证据标为不可用于推断；其余已授权分析可继续。不得伪造 Human 审核。
