# Architecture

## 不可约主链条

```text
Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test
```

框架只保留会改变研究判断、证据可追溯性或恢复能力的结构。目录、ID、时间戳和索引是
bookkeeping，由 dry-run-by-default 的脚本处理；具体分析方法和 runtime 不进入本框架。

exploratory 默认使用 `Record format: compact`：BRIEF 包含 Question、Inputs、First Comparison；
RESULT 包含 Question、Inputs、Analysis、Observations、Interpretation and Next Step。同一 draft
持续记录试做，不要求假设或 Claim/Evidence 编号；已形成证据的修订或独立验证另建 Artifact。
confirmatory 保留完整设计及审核 receipt 的执行门槛；正式报告仍只综合审核通过的记录。

Record format 缺省为 full，既有记录不改写。compact BRIEF 保持 pending，可记录有理由的 stopped；
设计审核或 answered 前扩展为 full。compact RESULT 只用于 exploratory draft，进入审核前扩展为
full，保留原始观察、输出引用和日期。结构校验仍检查身份、索引与上下文，不认证科学有效性。

生物医学输入说明复用已有样本表，按需记录样本层级、独立重复、标识符/参考版本和数值状态。
这些信息写在现有 BRIEF/RESULT 或引用的数据说明中，不引入样本数据库或自动组学分析 pipeline。

生成的 AGENTS.md 明确线性分析、少函数包装、先诊断再修正的原则。框架工具保留必要的
函数和安全校验，不将这些工程结构强加给探索脚本。

## Source of truth

| Record | 唯一职责 | 不负责 |
|---|---|---|
| `QUESTIONS.md` | Question 索引与当前状态 | 设计、证据或结论正文 |
| `BRIEF.md` | 事前问题与 Study Design；结束时记录 closure decision | 运行结果 |
| `RESULT.md` | 单个 Artifact 的 provenance、Evidence、Inference 与 Human review | Question 设计或 Pipeline 成熟度 |
| `CURRENT_HANDOFF.md` | 上下文路由、checkpoint、blocker 与 next decisive action | 复制证据、结论或完整历史 |
| `report.html` | 面向 Human 的派生综合 | 成为新的科学事实源 |

Human approval 只表示允许采用或纳入该记录，不自动证明科学推断成立；scientific support
必须由 Evidence 与 Validation 支撑；implementation reuse 只表示实现值得复用。三者互不替代。

## 分层上下文

根 `CURRENT_HANDOFF.md` 是 project router，维护 Active context、Context Map、跨上下文依赖和
Required reads。小型项目仅保留 `root` context；大型项目才在 Context Map 中显式声明子项目
及其局部 `CURRENT_HANDOFF.md`。

局部 Handoff 只保存 Scope、active Question/Artifact、last verified checkpoint、blocker、
next decisive action、dependencies 和 Required reads。Validator 只沿 Context Map 已声明的路径
检查，不递归发现子项目。科学事实仍由相应 BRIEF/RESULT 持有。

## Skills 与实现边界

```text
research-project-workflow
├── SKILL.md
├── references/{scaffold,question,explore,handoff,summarize-work,biomedical-data}.md
├── assets/{base,templates}/
└── scripts/{scaffold_project,record_project,validate_project}.py

report-generation
├── SKILL.md
├── references/{html,pdf,templates,validation}.md
├── assets/{templates,css}/
└── scripts/generate_report.py
```

Workflow 不 import report renderer；report-generation 不改变 Question、Artifact、review 或 reuse
决定。具体分析代码交给 `scripting-style`，Pixi 环境建设交给 `pixi-environment-builder`。

## 安全与验证语义

- 所有 mutation 默认 dry-run；apply 前重验目标，完成后运行 Validator，不覆盖已有科学记录。
- Scaffold 只建立最小控制层，业务目录首次使用时创建，也不猜测 Python/R/CUDA 环境。
- Validator 的成功只表示 `structure_consistent`；`scientific_validity` 始终需要 Evidence 与 Human
  科学判断，不能由文件结构自动证明。
- 既有仓库中的旧路径只产生 migration warning，不因 adoption 被删除或判为结构错误。
- 被拒绝、null、negative 或 contradictory 的 Artifact 原样保留，修订建立新的 A-ID。
