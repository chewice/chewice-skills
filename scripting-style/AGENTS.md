# Repository Instructions

## Scope

本目录开发 `scripting-style` Codex Skill。它指导项目内部 `.R`、`.py`、`.sh` 和 `.ipynb` 科研分析代码的表达方式；生物信息学与单细胞脚本是主要证据来源，但 Skill 不限定具体学科或方法。

## Language

项目说明默认使用中文。稳定的 engineering terms、文件名、API 名称和 machine-readable contract 保持英文。

## Governing Principle

**Write the analysis, not an application around the analysis.**

- 保留问题、具体试做、观察比较、人工判断、批量扩展、证据保存以及解释或下一问。
- 让科研判断与对象变换留在主线；成熟的 package 或已提供项目 API 可以承担窄算法边界。
- CLI、config、runner、state management 和 pipeline 不是默认产物。
- 简洁不得缩减用户要求的科学分析范围。

## Reasoning

- 遵循第一性原理。
- You may use superpowers, but do not write any spec or plan.
- 区分数据事实、方法假设、人工判断和待验证事项。
- 不用历史参数、模板或来源结论替代当前任务推理。

## Type Boundary

- `.R`、`.py`、`.sh`、`.ipynb` 分别只从同类型指南、邻近代码和范例学习具体写法。
- 不把 R section、Python CLI、Bash runner 或 Notebook cell 结构跨类型迁移。
- 修改既有文件时，邻近同类型风格与 minimal diff 优先于模板。

## Source Boundary

- `<SOURCE_ROOT>` 中的范例只读；不提交来源代码、机器绝对路径、真实参数或生物学结论。
- 不打开或推断来源项目顶层 `R/` API 实现，只依据用户给出的调用契约。
- 不分析或自动设计 Pixi、Conda、容器和编辑器环境。
- 不把来源中的包安装、环境清理、危险删除、历史输出或 notebook stale state 泛化成规则。

## Iteration Gate

- Phase 1 只写 `iterations/<iteration_id>/phase1/` 的隔离审查并停止，不修改功能文件。
- Phase 2 必须同时具备 Phase 1 证据、当前对话明确确认和非空 accepted decisions。
- Holdout 在初始改动完成前保持隔离；Phase 2 同时运行新 holdout 与既有回归。
- `schema_version: "1.0"` 保持兼容；`stage_hint` 只作可选语境，不驱动阶段指南。
- validator 始终只读，不能授予 Skill 写权限。

## Completion

- 校验 frontmatter、YAML、JSON、内部链接、模板语法和 validator 兼容性。
- 用隔离前向任务检查四种类型与既有脚本 minimal-diff。
- 复核来源哈希，确认没有修改来源或环境配置。
- 未经用户确认不 commit、不 push。
