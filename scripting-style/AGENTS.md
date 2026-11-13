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
- 不擅自生成 spec、plan、checklist 或 workflow 文档。用户明确要求分析计划、任务提示词或交接文档时，仅按指定范围交付；不把它作为无关分析的前置条件，也不据此执行仅要求规划的分析。
- 区分数据事实、方法假设、人工判断和待验证事项。
- 不用历史参数、模板或来源结论替代当前任务推理。

## Type Boundary

- `.R`、`.py`、`.sh`、`.ipynb` 分别只从同类型指南、邻近代码和范例学习具体写法。
- 不把 R section、Python CLI、Bash runner 或 Notebook cell 结构跨类型迁移。
- 普通修复保留邻近同类型风格并控制 diff；用户明确要求风格重构时，以指定的同类型参考和已确认的阅读目标为准。minimal diff 不保留本轮要求纠正的结构，模板也不替代科学方法或执行契约。

## Source Boundary

- `<SOURCE_ROOT>` 中的范例只读；不提交来源代码、机器绝对路径、真实参数或生物学结论。
- 不打开或推断来源项目顶层 `R/` API 实现，只依据用户给出的调用契约。
- 不分析或自动设计 Pixi、Conda、容器和编辑器环境。
- 不把来源中的包安装、环境清理、危险删除、历史输出或 notebook stale state 泛化成规则。

## Iteration Gate

- 维护细节遵循 `references/iteration-interface.md`；验证范围随修改影响范围确定。
- 新范例学习沿用 Phase 1／Phase 2：Phase 1 只写隔离审查，不修改功能文件；Phase 2 需审查证据、明确确认与非空 accepted decisions。新 holdout 在初始改动完成前保持隔离，随后复核并运行适用回归。
- 用户直接批准且没有新范例的规则修改，无需制造 Phase 1 intake 或 holdout；已有授权不重复询问，记录实际验证范围及限制。
- `schema_version: "1.0"` 保持兼容；`stage_hint` 只作可选语境，不驱动阶段指南。
- validator 始终只读，不能授予 Skill 写权限。

## Completion

- 措辞、链接或说明修改检查一致性及相关结构；单类型规则修改验证受影响案例与接口，跨语言核心行为修改使用有代表性的跨语言行为检查，不无条件执行四语言全套验证。
- 按影响范围校验 frontmatter、YAML/JSON、链接、模板语法或 validator 兼容性；接口未变不制造接口变更验证任务。
- 来源保持只读；只有文件身份与复用风险需要时才核对哈希，不因模型名称或文件大小启动全量审计。不修改无关来源或环境配置。
- 未经用户确认不 commit、不 push。
