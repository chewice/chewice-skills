# Architecture

Research Project OS `0.6.0` 使用一个 Skill 入口和三个按需层：

- `harness`：scaffold、ownership、context、Pixi、safety 与 audit。
- `exploration`：逐题 explore、audited run、archive 与 pipeline。
- `reporting`：独立 Markdown → HTML API。

CLI entrypoint 只负责参数与输出；实现位于 `research_project_os/` package。项目长期
上下文收敛为 `AGENTS.md`、`QUESTIONS.md`、`CURRENT_HANDOFF.md` 和
`project_manifest.yaml`。Notion、多 profile、中央 evidence/status/task/decision
台账已移除。

所有 mutation 默认 dry-run，apply 使用 atomic write 和 source revalidation。
计算通过 `run` 记录完整 SHA-256、stdout/stderr、Git/Pixi provenance。报告由独立
API 统一渲染，analysis scripts 不包含 HTML logic。
