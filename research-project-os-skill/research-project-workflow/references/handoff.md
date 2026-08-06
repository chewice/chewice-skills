# Handoff

## 恢复

依次读取 `AGENTS.md`、`CURRENT_HANDOFF.md`、只读 Git 摘要，以及 Handoff Read Map 的“必须读取”文件。仅在当前动作需要时读取“仅在需要时读取”；不得加载“不要加载”中的历史 Question、全部 references、旧 Artifact、全部日志或全部子项目。

确认 Active question、Active workstream、Current artifact、Current checkpoint 与 Status 一致。若引用缺失、状态冲突或 Handoff 超过 2,000 个中文字符，先报告问题并请求 Human 决定，不猜测当前工作。

## 切换与更新

切换 Question 或 Workstream 前，先把当前 checkpoint、验证、阻塞和下一步写清，再更新活动标识。Workstream 状态只允许“待启动”“进行中”“已完成”“终止”；阻塞、等待输入、等待审核、暂停和待验证统一记录在 `Blocker` 与 `Current checkpoint`，不创建新状态。

覆盖更新 `CURRENT_HANDOFF.md`，不生成历史 Handoff Markdown。保持以下内容：

- 当前目标与问题摘要；
- 跨工作流状态表；
- 最近完成、当前阻塞、立即下一步与验证；
- Read Map：必须读取、仅在需要时读取、不要加载。

推荐长度为 600–1,200 个中文字符，硬上限 2,000 字。不要保存完整历史、所有 Question、文献、日志、旧 Artifact、聊天或大型代码；历史交由 Git 保留。

更新后运行只读 Validator。不得因 Handoff 更新自动启动下一 Question、批准 Artifact、生成报告或执行 Git mutation。
