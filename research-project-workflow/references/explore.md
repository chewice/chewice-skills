# Explore Artifact

## 读取范围

读取 `CURRENT_HANDOFF.md`、当前 `BRIEF.md`、当前 `explore/<Q-ID>/<A-ID>/`，以及完成当前验证所需的指定输入与日志。不得读取全部旧 Artifact。

## 创建与执行

Human 批准 Explore 方向后，在当前 Question 下按现有最大编号递增创建 `A-NNN`：

```text
explore/<Q-ID>/<A-ID>/
├── RESULT.md
├── code/
├── config/
└── logs/
```

不得覆盖已有 Artifact。被拒绝的 `A-001` 原样保留，修订建立 `A-002`。Explore 临时配置与日志不得提前晋升为根级稳定配置。

Artifact 状态只允许“草稿”“待审核”“审核通过”“拒绝”。从“草稿”进入“待审核”前，确认命令执行成功、声明输出存在、最小验证通过、`RESULT.md` 已完整记录关键限制。技术验证是门槛，不是独立状态。

## RESULT 合同

记录 Artifact/Question ID、状态、时间戳、目标、输入、方法与命令、输出、技术验证、结果、限制、Human Review 和 Promotion。不得伪造命令、输出或验证。

只有 Human 可以将 Artifact 标记为“审核通过”或“拒绝”。Human Review 必须记录决定、时间和理由；“待审核”不得冒充通过。

## Promotion

只有“审核通过”的 Artifact 可进入 `pipeline/`。由 Human 明确目标后，将获批的代码/配置整理到独立 Pipeline 实现，并在 RESULT 中记录 `pipeline target`、`promotion commit`（若存在）、`promoted at` 和 `promoted files`。Promotion 不增加 Artifact 状态。

Pipeline runtime 不得直接依赖 `explore/` 或 `docs/template/`。正式调度、运行、测试和结果生成由研究项目自身负责。未获 Human 审核、验证失败、目标不明确或可能覆盖已有 Pipeline 时停止。
