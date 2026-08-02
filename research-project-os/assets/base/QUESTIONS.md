# Project Questions

> 本文件完全由 human 维护。Agent 与 CLI 只读，只能在聊天中建议修改。

## Filling guide

1. 先填写一次性的 `Project purpose`、输入限制、输出要求和 FAQ。
2. 每个研究问题只建立一个 `### Q-NNN — title` block，并按 Q-ID 顺序保留原位。
3. 只有 inputs、expected outputs 与 completion criterion 已明确的问题才能设为
   `current`；同一时间最多一个 `current`。
4. 人工审核后更新同一 block 的 `Status`、`Review decision`、`Reviewed on`、
   `Reviewed outcome` 和 `Evidence`，不要复制或搬动问题。

### Status reference

| Status | 什么时候使用 |
| --- | --- |
| `queued` | 问题已登记，但尚未批准启动。 |
| `current` | 当前唯一正在讨论、执行或按审核意见返工的问题。 |
| `answered` | human 已审核并决定关闭；答案可以是明确结论或“不确定”。 |
| `deferred` | 暂时搁置，但保留以后恢复的可能。 |
| `cancelled` | 明确停止，不再尝试回答。 |

### Review decision reference

| Review decision | 什么时候使用 |
| --- | --- |
| `pending` | 尚未进行 human review。 |
| `accepted` | 结果足以回答问题，可以关闭。 |
| `accepted_with_limitations` | 接受结果并关闭，但必须保留明确限制。 |
| `inconclusive` | 证据不足或相互冲突；human 接受“不确定”作为当前答案。 |
| `rework_required` | 方向仍保留，但需要补充或重做后再审核。 |
| `not_applicable` | 问题已取消，没有可审核答案。 |

常用组合：`queued/current + pending`；`answered + accepted /`
`accepted_with_limitations / inconclusive`；`deferred + pending / inconclusive /`
`rework_required`；`cancelled + not_applicable`。

`Depends on` 填依赖的 Q-ID 或 `none`。`Reviewed on` 未审核时填 `pending`，审核后填
`YYYY-MM-DD`。`Reviewed outcome` 简要记录人为判断、限制和返回项目时应知道的事项；
详细结果留在 task/archive，`Evidence` 填对应路径或 selector。

## Project purpose

尚未填写

## Input constraints

- 原始输入只读。
- 尚未填写项目特有的输入范围与排除条件。

## Output requirements

- explore 输出保留在各自 task 目录。
- 探索报告与正式报告使用 HTML。
- 尚未填写项目特有的输出要求。

## FAQ

### 项目的首要判断标准是什么？

尚未填写

## Questions

> 新增问题时复制下面的完整 block，分配新的 Q-ID，并按前面的 Filling guide 选择状态。

### Q-001 — 尚未命名

- Status: `current`
- Depends on: `none`
- Review decision: `pending`
- Reviewed on: `pending`

#### Question

尚未填写

#### Inputs

尚未填写

#### Method reference

尚未填写

#### Expected outputs

尚未填写

#### Completion criterion

尚未填写

#### Reviewed outcome

`pending`

#### Evidence

`pending`
