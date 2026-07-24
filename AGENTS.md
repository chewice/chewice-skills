# Repository Instructions

## Scope

本仓库用于开发可复用的 `research-project-os` Codex Skill。可安装 Skill 位于
`research-project-os/`；development tests 和 architecture notes 位于仓库根目录。

## Language

项目说明默认使用中文。稳定的 engineering terms、machine-readable contract 和
文件名保持英文。

## Safety

- 所有 mutating CLI mode 默认保持 dry-run。
- 不得自动运行 `git add`、`git commit`、`git push` 或写入 Notion。
- 将 `adopt` 视为 non-destructive：保留现有项目路径和文件。
- 除非显式提供 `--overwrite`，否则拒绝覆盖。
- profiles 保持通用，不嵌入 MDD pilot project 的假设。

## Environment

- 使用 Pixi 管理 dependencies 和 tasks。
- 不得手动编辑 `pixi.lock`。
- Python dependencies 保持最小，并从 Conda 获取。

## Completion

运行 `pixi run lint`、`pixi run test`、`pixi run smoke` 和
`pixi run validate-skill`。检查 installation symlink，并确认 fixture output
或 credentials 未对 Git 可见。
