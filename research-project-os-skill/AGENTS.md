# Repository Instructions

## Scope

本仓库用于开发可复用的 `research-project-workflow` 与 `report-generation`
Codex Skills。可安装 Skill 位于同名目录；development tests 和 architecture notes
位于仓库根目录。

## 总原则

- 遵循第一性原理、奥卡姆剃刀原理

## Language

项目说明默认使用中文。稳定的 engineering terms、machine-readable contract 和
文件名保持英文。

## Safety

- 所有 mutating script 默认保持 dry-run。
- 不得自动运行 `git add`、`git commit`、`git push` 或写入 Notion。
- 将 scaffold/adopt 视为 non-destructive：保留现有项目路径和文件。
- 除非显式提供 `--overwrite`，否则拒绝覆盖。

## Environment

- 使用 Pixi 管理 dependencies 和 tasks。
- 仓库只允许根级 Pixi workspace；不得跟踪 `.pixi/`。
- 不得手动编辑 `pixi.lock`。
- pixi环境构建调用 `pixi-environment-builder` skill。

## Completion

运行 `pixi run lint`、`pixi run test`、`pixi run smoke` 和
`pixi run validate-skill`。检查两个 Skill 的 installation symlink，并确认 fixture
output 或 credentials 未对 Git 可见。
