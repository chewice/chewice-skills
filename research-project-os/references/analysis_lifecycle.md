# Analysis Lifecycle

对 `generic-analysis` 和 `bioinformatics` 使用三阶段 artifact model：

```text
explore → human review → archive → pipeline → publication review
```

阶段与 scientific status 相互独立。进入 `archive/` 表示 snapshot 已由人审核，
成为 pipeline 的允许来源；它不会自动把 observation 提升为 verified evidence。

## Direction gate

运行任何新分析前，先在聊天中提出 research question、method、expected outputs 和
stop condition。只有 human 明确同意后，才运行 `explore-create --apply` 或执行计算。
dry-run 只展示计划，不代表方向获批。

## Task contract

使用 `P<order>-<core>-<short-english-summary>/`：

- `P0`, `P1`, ... 是项目内唯一的分析顺序；允许多个任务并行探索，不要求前序完成。
- `core` 是单个短 ASCII token，例如 `QC`、`cluster`、`GRN`。
- 末段是不可变的简短英文 kebab-case 总结，例如
  `P0-QC-low-quality-cells-removed/`。它是 task label，不是 verified claim。

将 task 的 code、二级数据和图分别保留在自己的 `scripts/`、`derived/` 和
`figures/` 内；不要把 explore task 的 artifact 散落到项目级目录。

## Promotion contract

用 `archive-promote` 记录 reviewer、review summary 和 validation results。保留
explore 原目录，并将完整 task 冻结为 `archive/<task>/vNNN/`。每次 promotion 创建
新版本和 file hashes；不得覆盖或编辑已有 snapshot。用 `archive-verify` 重新计算
hashes。这里的 analysis archive 不同于 `docs/handoffs/archive/` 的 session archive。

## Pipeline contract

只从已审核且 hash 验证通过的 snapshot 运行 `pipeline-create`。Agent 根据这些
来源重写或整理独立主流程，在 `pipeline.yaml` 中为每个 ordered step 填写
`implementation`，并设置一个 project-relative entrypoint。runtime code 不得读取
`explore/` 或 `archive/`；archive path 只作为 provenance 保存。

发表前运行完整 workflow 和 tests，再用 `pipeline-release` 记录 human review、
validation results 与全部 pipeline file hashes。release-ready 表示发布整理完成，
不替代 evidence verification、claim review 或 Git provenance。
