# Artifact 与事后 Evidence

## 读取范围

从根 Context Map 定位当前 context，读取局部 Handoff（若声明）、当前 BRIEF、目标 Artifact/RESULT，以及完成当前动作所需且被明确引用的输入、code、output 和 receipt。不要扫描全部旧 Artifact。

## 创建 Artifact

Study Design 已足以执行且用户明确要求开始/记录分析时，可直接创建非覆盖 Artifact：

```bash
pixi run record-project new-artifact \
  --project /path/to/project --context root --question-id Q-001 \
  --analysis-mode exploratory
pixi run record-project new-artifact \
  --project /path/to/project --context root --question-id Q-001 \
  --analysis-mode exploratory --apply
```

`analysis-mode` 只允许 `exploratory | confirmatory`。命令从该 Question 的最大 A-ID 递增分配 `A-NNN`，用同一 ISO 8601 时间戳创建 `explore/<Q-ID>/<A-ID>/RESULT.md` 并更新对应 context 路由。默认 dry-run；`--apply` 才写入，拒绝覆盖。需要 code、config、logs 或 outputs 时再在 Artifact 内按需创建，不预建空目录。

修订或独立验证建立新 Artifact，原 Artifact 与 null、negative、contradictory、inconclusive evidence 原样保留。不得通过覆盖、只报告显著结果或静默排除冲突来“清理”证据。

## RESULT 合同：只记录事后证据

顶层 metadata 至少包含 `Question`、`Artifact`、`Analysis mode`、`Status`、`Created`、`Updated`。`Status` 只表示记录成熟度：`draft | review-ready | reviewed`，不代表 scientific validity 或 implementation reuse。

固定章节如下：

1. `Question and Claims`
2. `Provenance Receipt`
3. `Method and Deviations`
4. `Observed Evidence`
5. `Validation`
6. `Inference`
7. `Limitations and Applicability`
8. `Next Decisive Test`
9. `Human Review`
10. `Implementation Reuse`

`Question and Claims` 的 `Claims assessed:` 只列本 Artifact 检验的稳定 C-ID，不重复 Claim–Evidence table。每项 observed evidence 使用稳定 `E-NNN`，其 `Claim:` 引用一个 C-ID，并至少记录 `Source`、`Output`、relation（`support | null | negative | contradictory | inconclusive`）、observation、effect 与 uncertainty。`Provenance Receipt` 记录可用的数据版本/hash、代码 revision、环境/lock、命令、seed、输出路径/hash 与运行时间；没有发生的命令或不存在的产物必须明确为未运行/不可用，不得补写。

`Method and Deviations` 区分事前方法与 post hoc deviation。`Inference` 使用 `Assessment: pending`、`Qualified claim:`、`Uncertainty:` 三个轻量字段；Assessment 审核后只允许 `support | contradict | inconclusive | context`。它将 observation 与 interpretation 分开，检查仍成立的 assumptions、alternative explanations、causal boundary，并只提出证据允许的 qualified claim。`Next Decisive Test` 应优先区分仍可解释当前 evidence 的 competing explanations。

## 三项独立判断

- `Validation` 分开记录 `Technical Validation` 与 `Scientific and Robustness Validation`。命令成功、文件存在或 schema 正确只属于 technical validation，不构成 scientific support。
- `Human Review` 使用 `Decision: pending | approved | rejected`、`Reviewed at`、`Review rationale`。Human approval 只表示该 evidence record 经审核，可被后续综合引用；不自动证明 claim 成立。
- `Implementation Reuse` 使用 `Reuse decision: not-assessed | approved | rejected`、`Target`、`Recorded at`、`Files`。代码进入 `pipeline/` 只表示实现获准复用，不改变 evidence relation 或 scientific validity。

只有 Human 可以写 approved/rejected 决定。若复用获批，整理为独立稳定实现并记录准确目标；Pipeline runtime 不得直接依赖 `explore/` 或 Human reference template。具体分析脚本写法仍由 `scripting-style` Skill 管理。
