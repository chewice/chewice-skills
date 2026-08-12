# 跨类型观察

这里只保留能跨越文件类型差异的原则。

## 稳定模式

- 主要 artifact 是可检查的分析记录，而不是包围分析的通用 application。
- 科研对象、变换、候选证据和人工选择按执行顺序保持可见。
- 可先内联探索代表性案例，再抽取稳定的重复技术核。
- sample、method、condition 或 lineage 分支在有助于独立阅读时可继续重复。
- 观察不等于断言：summary、对象显示、metric、plot 和外部工具结果都可以直接支持决定。
- 硬停止只保护失败后会静默改变科学含义的契约。
- 人工编辑中间文件、part 边界、对象重载和有科研用途的昂贵 cache 是有效 handoff。
- 输出按当前科研、复查、下游或复现用途选择；table/figure/object bundle 与 operational completion summary 都不是通用要求。
- 修改既有代码时，邻近同类型约定和 minimal diff 优先。
- 尚未运行的代码不能声称观察到 optimum、成功诊断或生物学结论。

## 共享的生产化边界

CLI parsing、通用 config、runner、dispatcher、state tracking、retry、completion marker 和统一 pipeline，只有用户明确要求或存在真实 reusable-tool contract 时才出现。项目常量不会仅因可能变化就必须泛化。

## 不属于跨类型规则的内容

section syntax、entrypoint shape、display behavior、shell safety syntax、helper form、cell granularity 和类型特异 output mechanics，分别留在四份类型指南中。Notebook 不教授 standalone Python 结构，任何 script 类型也不教授 Notebook cell 组织。
