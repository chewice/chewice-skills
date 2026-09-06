# 问题驱动科研分析 Skills

本仓库提供两个 Codex Skills，用最小可审核结构组织计算研究：从一个可回答的
Research Question 出发，先记录 Study Design，再保存 Evidence、Inference、
Qualified Claim 与 Next decisive test。

## 核心记录

- `BRIEF.md`：探索默认只写问题、输入与首次比较；准备正式审核或验证时，再补全假设、
  estimand、证据准入、不确定性与停止条件。
- `RESULT.md`：探索默认只写问题、输入、试做、观察和下一步；正式审核前再补全
  Claim/Evidence、validation 与 review。Null、negative 和 contradictory evidence 同样保留。
- `CURRENT_HANDOFF.md`：只路由当前上下文，不复制科学事实。大型项目可在 Context Map
  中声明子项目 Handoff；小型项目只使用根上下文。
- `reports/<Q-ID>/report.html`：从已审核记录派生的阶段性或最终科研报告，不是新的事实源。

主链条为：

```text
Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test
```

## Skills

- `research-project-workflow`：初始化或接管项目，创建 Question/Artifact，维护分层上下文，
  审核证据与推断，并区分 Human approval、scientific support 和 implementation reuse。
- `report-generation`：围绕 Question 与 Claim–Evidence 关系生成和验证 HTML 报告。

探索遵循第一性原理、奥卡姆剃刀原理：先做最小比较，观察数据与图形，再决定是否扩展。
代码线性展开，减少函数包装和针对异常堆叠的 fallback、重试或兼容分支；关键科学判断直接可见。
这些原则写入仓库及生成项目的 `AGENTS.md`。

exploratory 默认使用 `Record format: compact`，描述性探索可暂时没有假设或 Claim/Evidence
编号。`new-question --analysis-mode confirmatory` 创建完整设计模板；confirmatory 执行
仍要求完整且已审核的事前设计，正式报告保留独立审核门槛。既有完整记录无需迁移。

生物医学输入按需说明样本层级、独立重复和数值含义，优先引用已有样本表。矩阵状态、
assay/layer、标识符与参考版本等写在现有输入说明中，不自动创建额外注册表。
详见 [生物医学输入说明](research-project-workflow/references/biomedical-data.md)。

具体 R/Python/Bash 分析写法可按需使用已安装的 `scripting-style`；Pixi 环境创建或迁移调用
`pixi-environment-builder`。本框架不预猜研究领域、统计方法或运行环境。

## 验证

```bash
pixi run lint
pixi run test
pixi run smoke
pixi run validate-skill
```

Mutating scripts 默认 dry-run，`--apply` 后才执行 non-destructive 写入。项目内已由用户
明确请求、不会覆盖现有内容且可恢复的 bookkeeping 无需再次询问；Human 审核决定、覆盖删除、
Git/Notion 或其他外部写入仍由 Human 明确决定。
