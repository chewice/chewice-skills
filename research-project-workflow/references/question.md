# Question 与 BRIEF

## 读取范围

读取 `CURRENT_HANDOFF.md`、目标 Question 在 `QUESTIONS.md` 中的唯一索引行、对应 `BRIEF.md`、BRIEF 明确引用的资料，以及 Human 明确 `@` 的 template。不得加载其他 Question。

## 创建 Question

从现有最大 Q-ID 递增分配 `Q-NNN`，保留 Human 原始问题的简短表达。在 Human 同意记录后：

1. 创建 `docs/questions/<Q-ID>/BRIEF.md`。
2. 在 `QUESTIONS.md` 增加一行 `Q-ID | Question | Status | Brief | Updated`。
3. 初始状态使用“拟定”；Human 明确开始后改为“解决中”。
4. 使用同一个 ISO 8601 时间戳更新索引与 BRIEF。

Question 状态只允许“拟定”“解决中”“已解决”“废弃”。只有 Human 明确接受最终结论或明确停止时，才可写入“已解决”或“废弃”。

## BRIEF 合同

维护以下章节：Human Question、Problem Interpretation、Context and Scope、Evidence Basis、Evidence Synthesis、Proposed Resolution、Inputs/Outputs/Dependencies、Validation and Acceptance Criteria、Open Questions and Risks、Human Review、Closure Summary。

将项目事实、文献与官方指导、Human 指定参考代码分别记录在 Evidence Basis。不得把未经验证的推测表述为证据。先由 Agent 起草 interpretation、synthesis、resolution 与 validation，再由 Human 确认限制、依据、解决方式和验收条件。

## Ownership

Human 负责提出问题、批准开始、确认不可突破限制、Evidence Basis、解决方式、验收条件、Artifact 审核、Question 状态与 Pipeline 决定。Agent 负责结构化问题、调研与综合证据、设计验证、维护风险、记录 Human 决定及更新 BRIEF。

`QUESTIONS.md` 只保存索引，不写入完整 Evidence、方案、结果、日志或审核论证。信息不足、索引冲突或 Human 未批准启动时停止。
