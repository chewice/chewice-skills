# 总结工作

仅在 Human 输入“总结工作”时执行本流程。

## 1. 核对事实

读取 `AGENTS.md`、`CURRENT_HANDOFF.md`、当前 Question 索引行、当前 `BRIEF.md`、当前 `RESULT.md`（若存在）、必要验证结果，以及只读的 `git status`、`git diff --stat` 和最近相关 commit。不得扫描整个仓库。

## 2. 输出总结

总结今天处理的问题、完成工作、关键判断、运行与验证结果、Human 已确认决定、未完成事项和下一步入口。区分事实、推断与待确认内容。

## 3. 更新项目记忆

为本次收尾生成一个带时区的 ISO 8601 时间戳，并统一用于所有更新：

- 更新 `QUESTIONS.md` 的 Status、Brief 和 Updated。只有 Human 明确确认时，才写“已解决”或“废弃”。
- 更新 BRIEF 的 Context、Evidence Basis/Synthesis、Proposed Resolution、Validation、Human Review、Open Questions、Closure Summary 和 Updated。
- 若存在当前 Artifact，更新 RESULT 的状态、验证、Human Review、通过/拒绝理由、Promotion 事实和时间戳；不得自行批准。
- 只有发现新的、长期有效且可跨 Question 复用的行为规则时，才更新 `AGENTS.md`。不得写入临时进度、参数、错误或单次结果。
- 覆盖更新 `CURRENT_HANDOFF.md` 的状态、最近完成、阻塞、下一步、验证和 Read Map。

## 4. 验证与停止

运行：

```bash
pixi run validate-project --project /path/to/project
```

验证失败时列出错误，不宣称完成。不得自动 commit/push、批准 Artifact、关闭 Question、开始下一 Question、生成正式 Report、修改 `docs/template/` 或伪造验证结果。
