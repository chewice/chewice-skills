# 问题驱动科研分析 Skills

本仓库提供两个 Codex Skills，用最小可审核结构组织计算研究：从一个可回答的
Research Question 出发，先记录 Study Design，再保存 Evidence、Inference、
Qualified Claim 与 Next decisive test。

## 核心记录

- `BRIEF.md`：事前定义问题、假设与 falsifier、estimand、inference unit、证据准入、
  分析与不确定性，以及 acceptance/stopping criteria。
- `RESULT.md`：事后记录 provenance、observed evidence、validation、inference、限制、
  适用边界与下一项最有辨别力的检验。Null、negative 和 contradictory evidence 同样保留。
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

具体 R/Python/Bash 分析写法由 `scripting-style` 负责；Pixi 环境创建或迁移调用
`pixi-environment-builder`。本框架不预猜研究领域、统计方法或运行环境。

## 验证

```bash
pixi run lint
pixi run test
pixi run smoke
pixi run validate-skill
```

Mutating scripts 默认 dry-run，`--apply` 后才执行 non-destructive 写入。项目内已由用户
明确请求、不会覆盖现有内容且可恢复的 bookkeeping 无需再次询问；科学判断、覆盖删除、
Git/Notion 或其他外部写入仍由 Human 明确决定。
