# Repository Instructions

## Scope

本仓库用于开发可复制或安装的 `scripting-style` Codex Skill。该 Skill 指导 Codex
编写线性、直接、少封装的 R、Python 和 Bash 生物信息学分析脚本，不负责项目脚手架、
环境求解、公共函数库或统一分析平台。仓库也提供两阶段迭代接口，用新范例改善 Skill。

## Language

项目说明默认使用中文。稳定的 engineering terms、文件名、API 名称和
machine-readable contract 保持英文。

## Reasoning

- 遵循第一性原理。
- You may use superpowers, but do not write any spec or plan.
- 写脚本前可以在对话中给出简短工作提要，但不得为此创建独立 spec、plan 文件。
- 区分数据事实、方法假设和生物学判断；模板与历史参数不得替代当前任务推理。

## Scripting Style

- 优先自上而下的线性分析主线。
- 减少函数封装、class、配置层、跨文件 wrapper 和工程化代码。
- 一次性且短小的核心分析步骤优先内联，允许为局部可读性保留少量重复。
- 只有在显著减少真实重复、隔离窄技术细节或表达逐元素计算时，才建立小型局部函数。
- 不得把 QC 阈值、注释选择、整合方法、root/terminal、lineage、cutoff 或基因集等
  核心生物学与统计决策隐藏进函数。

## Boundaries

- 不修改 `<SOURCE_ROOT>` 中的来源范例。
- 不打开或推断来源项目顶层 `R/` 的实现；只按已知契约看待 API。
- 不分析或自动设计 Pixi、Conda、容器及编辑器环境。
- 不把来源脚本中的绝对路径、环境细节或历史参数设置为通用默认值。
- 不创建公共函数库、R package、复杂代码分析平台或统一 pipeline。

## Iteration Gate

- 新范例默认只读，不复制完整源代码到 Skill。
- Phase 1 只在 `iterations/<iteration_id>/phase1/` 生成差异审查，不得修改 Skill
  的规则、索引、模板或其他功能文件，并在汇报后停止。
- Phase 2 必须同时具备 Phase 1 报告、用户当前对话中的明确确认和非空 accepted decisions。
- Validation holdout 在初始变化完成前保持隔离。
- 全局规则不得由单个新脚本产生；冲突证据优先收窄规则，而不是增加抽象层。
- Phase 2 必须同时检查新 holdout 与原有 holdout，避免修复一个范例却破坏既有风格。

## Completion

- 运行 Skill 结构校验。
- 检查 YAML、模板语法和文档内部链接。
- 使用确认的 validation holdout 做轻量风格验证。
- 迭代时校验 request contract、Phase 1/2 gate 和旧规则回归。
- 确认未修改来源项目，且没有生成真实数据、credentials 或缓存。
