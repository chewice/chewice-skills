# Repository Instructions

## Scope

本仓库用于开发可复用的 `research-context` Codex Skill。
可安装 Skill 位于同名目录；development tests 和 architecture notes
位于仓库根目录。

## 总原则

- 遵循第一性原理、奥卡姆剃刀原理
- 以科学分析为主：先明确问题、数据生成过程和推断单位，再选择能区分解释的最小分析。
- 探索代码保持线性、少函数包装；关键过滤、比较、阈值与假设直接可见。仅对真实重复或独立技术操作提取函数。
- 减少反应式补丁：先查明报错与异常数据的原因，不堆叠 fallback、自动重试、宽泛异常捕获或猜测性兼容分支。
- 框架只承担必要的记录和恢复；不要把探索脚本改造成通用 CLI、runner、配置系统或统一 pipeline。框架自带工具可保留必要的函数与安全检查。

## Language

项目说明默认使用中文。稳定的 engineering terms、machine-readable contract 和
文件名保持英文。

## Safety

- 所有 mutating script 默认保持 dry-run。
- 不得自动运行 `git add`、`git commit`、`git push` 或写入 Notion。
- 不自动创建项目脚手架、控制文件或 `context.md`；保留现有项目路径和文件。
- 除非显式提供 `--overwrite`，否则拒绝覆盖。

## Environment

- 使用 Pixi 管理 dependencies 和 tasks。
- 仓库只允许根级 Pixi workspace；不得跟踪 `.pixi/`。
- 不得手动编辑 `pixi.lock`。
- pixi环境构建调用 `pixi-environment-builder` skill。

## Completion

运行 `pixi run lint`、`pixi run test`、`pixi run smoke` 和
`pixi run validate-skill`。检查 Skill 的 installation symlink，并确认 fixture
output 或 credentials 未对 Git 可见。
