# 范例选择说明

## 先按文件类型选择

选择范例前先确定目标 artifact：

- `.R` 只读取 R 范例；
- `.py` 只读取 Python 范例；
- `.sh` 只读取 Bash 范例；
- `.ipynb` 只读取 Notebook 范例。

随后才在同类型内匹配最接近的任务。最多使用一个 `primary`；只有确实补足缺口时，再使用一个 `complement`。不得用另一文件类型推导 section syntax、entrypoint、control flow、output display 或其他具体代码形态。

便携 Skill 中的 `<SOURCE_ROOT>` 被有意保留为未解析占位，避免发布个人机器路径。只有用户明确提供 root，或当前工作区存在无歧义的项目根时才解析；不得在任务范围外搜索用户机器。来源不可用时，直接使用对应类型指南，并且不得声称已检查索引中的源码。

## 角色

- `primary`：某个同类型分析模式的强证据。
- `complement`：补充 handoff、直接外部命令、交互选择或 API call 等较窄边界。
- `validation_holdout`：在一次新生成或新迭代中，初始变化完成前保持隔离，不作为该轮学习范例。
- `counterexample`：帮助识别 API / tool 边界，但不能驱动默认分析形态。

当前索引的历史 corpus holdout 已在 2026-08-13 全语料审查中被查看，因此本次记录将它们诚实归类为 retrospective same-type regression，而不是 blind holdout。未来迭代仍应重新冻结新的 prospective holdout。

索引推荐的是书写结构，不是算法。除非当前任务独立提供，否则来源路径、参数、样本、生物学标签、模型选择、stored output 和环境细节均不可迁移。

## 证据边界

R corpus 最广，可以支持完整的探索到批量链。standalone Python 只有一个来源文件，因此只支持窄直接转换和已有 positional contract，不能建立通用 Python CLI 风格。Notebook 是 cell-by-cell model analysis 与参数选择的一等同类型证据，但 stale execution state 与环境痕迹被排除。Bash 来源支持可见命令顺序和显式 sample blocks；安全增强是有意增加的 safeguard，不是语料共有习惯。

holdout 结果见 [style validation](../validation/style-validation.md)；用新证据修改索引时见 [iteration interface](../references/iteration-interface.md)。
