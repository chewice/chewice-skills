# Repository Instructions

## Language

- 面向 human 的说明默认使用中文。 
- 专业术语、code、paths、commands、IDs 和 machine-readable values 等agent方便识别的内容保持英文。

## Reasoning

- 遵循第一性原理

## Superpowers

- You may use superpowers, but do not write any spec or plan.

## Research workflow

- 先读取 `CURRENT_HANDOFF.md`，再按 Read Map 加载当前 Question、BRIEF 或 Artifact。
- `QUESTIONS.md` 只保存问题索引；问题依据写入 `BRIEF.md`，Explore 结果写入 `RESULT.md`。
- Question、Artifact 与 Workstream 状态相互独立；最终状态和审核决定归 Human 所有。
- 所有 mutation 先预览，未经明确确认不得覆盖、commit、push 或写入外部服务。
- 不自动扫描、注册、更新或验证 `docs/template/`；仅在 Human 明确 `@` 后读取指定内容。
- 项目只允许根级 Pixi workspace；不得创建嵌套 `pixi.toml`、`pixi.lock` 或 `.pixi/`。
