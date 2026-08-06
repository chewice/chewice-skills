# 范例选择说明

## 如何选择

先确定分析阶段和语言，再从 `example-index.yaml` 选择：

1. 一个与当前任务类型最接近的 `primary`；
2. 只有当需要补充语言、绘图、输出或局部函数模式时，再选一个 `secondary`；
3. 不把 `validation-holdout`、`counterexample` 或
   `special-status-unclassified` 当作规则来源。

不要同时加载大量范例。范例只提供脚本结构和分析叙事，当前数据与用户 API 才决定方法、
参数和生物学选择。

## Primary 的意义

Primary 覆盖以下稳定证据：

- 自上而下的分析主线；
- 输入、输出和上游关系可定位；
- 关键参数与科学决策可见；
- 中间检查能支持下一步；
- 图、表和对象与分析步骤相邻；
- 局部函数只处理窄技术任务。

Primary 不是“推荐算法”，也不是“可直接复制脚本”。

## Secondary 的意义

Secondary 用于补齐 Primary 不覆盖的边界：

- Bash 外部工具编排；
- Python 窄格式转换；
- baseline 与单独导出；
- 重复绘图或逐元素计算的小函数；
- 同一工作流的其他 part 或下游解释。

## 反例与特殊状态

`04-grn/scripts/02-regulon_activity_score.R` 是 API-like 反例。它帮助区分可复用 API
实现与一次性分析脚本，不能据此增加函数、wrapper 或接口层。

`04-hypothesis_driven_partII.R` 和 `06-screen_TFs_for_given_target.R` 被用户确认有
README 未记录的特殊地位。具体角色未说明前保持未分类，不宣称 legacy，也不用于规则提炼。

## Validation holdout

Holdout 在初始规则完成前隔离，用于检验：

- 是否把某个工具或方法错误固化；
- 是否正确预测分节、顺序、参数和 API 位置；
- 是否保持中间检查与输出；
- 是否在平行分支中过度抽象；
- 是否能解释未见脚本而不复制其具体值。

验证结果见 `validation/style-validation.md`。
