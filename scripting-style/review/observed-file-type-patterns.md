# 按文件类型观察到的模式

## R

- 核心对象沿可见主线推进，`head`、`dim`、`summary`、`table`、对象打印、`View` 或诊断图紧邻它们支持的决定。
- section 装饰随项目变化；稳定特征是科学语义分块，而不是 `# 1. Title ----`。
- 强范例保留参数或方法比较以及随后的人工选择，不只留下最终调用。
- 最清楚的 batch function 出现在代表性 gene 或 item 已经内联计算并检查之后。
- 大型平行 sample、method 或 lineage blocks 可以合理保留；复制分支引用 stale variables 则显示何时需要抽最小技术核。
- part script、editable table、object reload 与昂贵 scientific cache 是正常科研边界。

## Python script

- 唯一 standalone Python artifact 是带真实 positional invocation contract 的直接顶层转换，并含一个窄 parser helper。
- 它支持直接变换和真实调用契约，但不足以证明通用 CLI、`main()`、config 或 full-analysis architecture。
- 完整 Python 科研分析来自最高原则和 Python 指南，不能把 Notebook cell 结构复制进 `.py`。

## Bash

- 外部工具变量与命令直接可见。
- 少量已知样本可以重复完整 command block，使 paths 和 options 独立可读。
- 多阶段工具可以把昂贵候选 stage 保留成清楚的人工 command block。
- shebang、strict mode、quoting 和非破坏性路径处理是安全增强，不宣称是全语料统一风格。
- generic dispatcher、completion discovery、destructive temporary cleanup、environment activation 和机器路径不是学习目标。

## Notebook

- cells 依次推进 loading、object inspection、model preparation、fitting、candidate sweep、diagnostic display、后续 selection、downstream transformation 与 saving。
- 即使最终已经选择，candidate values 与 model-selection diagnostics 仍可保留。
- Markdown 密度由项目决定；有效科研 Notebook 不必改写成精致叙事文档。
- stored execution counts 和 outputs 是历史状态，不证明当前运行已经观察到结果。
- Notebook 只作为 `.ipynb` 的一等证据，不建立 CLI 或 standalone Python script pattern。
