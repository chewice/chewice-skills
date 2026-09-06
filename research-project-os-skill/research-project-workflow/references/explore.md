# Artifact 与事后 Evidence

## 读取范围

从根 Context Map 定位当前 context，优先读取当前 BRIEF、目标 Artifact/RESULT 和相关输入。线索不足时定向查找数据和代码，补充有效入口；不要扫描全部旧 Artifact。

## 创建 Artifact

用户已要求开始或记录分析时，可直接创建非覆盖 Artifact。exploratory 从已登记的问题和简短 BRIEF 开始，不要求设计审批或填完所有设计章节；执行前说明当前数据和首次检查或比较，描述性探索无需先提出假设。confirmatory 才要求完整且已审核的事前设计：

```bash
pixi run record-project new-artifact \
  --project /path/to/project --context root --question-id Q-001 \
  --analysis-mode exploratory
pixi run record-project new-artifact \
  --project /path/to/project --context root --question-id Q-001 \
  --analysis-mode exploratory --apply
```

`analysis-mode` 只允许 `exploratory | confirmatory`。命令从该 Question 的最大 A-ID 递增分配 `A-NNN`，用同一 ISO 8601 时间戳创建 `explore/<Q-ID>/<A-ID>/RESULT.md` 并更新对应 context 路由。默认 dry-run；`--apply` 才写入，拒绝覆盖。需要 code、config、logs 或 outputs 时再在 Artifact 内按需创建，不预建空目录。

同一 draft 内可持续补充试做、图形和判断，不为每次参数试探创建 Artifact。已形成证据的修订或独立验证建立新 Artifact，原证据与 null、negative、contradictory、inconclusive evidence 原样保留。不得通过覆盖、只报告显著结果或静默排除冲突来“清理”证据。

## RESULT 合同：只记录事后证据

顶层 metadata 至少包含 `Question`、`Artifact`、`Analysis mode`、`Status`、`Created`、`Updated`。`Status` 只表示记录成熟度：`draft | review-ready | reviewed`，不代表 scientific validity 或 implementation reuse。

exploratory 默认使用 `assets/templates/RESULT-exploratory.md`，带 `Record format: compact` 和五个章节：`Question`、`Inputs`、`Analysis`、`Observations`、`Interpretation and Next Step`。记录实际输入、代码/命令、输出与观察、解释的不确定性及下一步理由；输入说明可引用 BRIEF，只补本次实际使用的样本、layer 或处理变化。首次接触生物医学输入时读取 [`biomedical-data.md`](biomedical-data.md)。描述性发现不要求 C-ID/E-ID、Human Review 或 Implementation Reuse。

compact 仅适用于 `exploratory + draft`。进入 `review-ready/reviewed` 前，参照 `assets/templates/RESULT.md` 补全 full 章节并改为 `Record format: full`；把已有观察及输出引用原样带入，保留日期和偏离，再为需审核的主张与证据分配编号。不改写 analysis mode；独立 confirmatory 新建 Artifact。确认性 Artifact 默认使用 full 模板。既有无 Record format 的记录按 full 验证。

full RESULT 章节如下：

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

只有 Human 可以写 approved/rejected 决定；这些字段可保持 pending/not-assessed，不阻塞日常探索与有依据的 Agent inference。只有确需稳定复用时才讨论 pipeline；若复用获批，记录准确目标并避免 runtime 依赖易变的探索产物。分析代码遵循根 AGENTS.md 的线性、少包装原则，具体写法可按需使用已安装的 `scripting-style` Skill。
