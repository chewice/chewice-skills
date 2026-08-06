# 建议的验证集拆分

## 目标

验证集不是测试生物学结果是否正确，而是检查候选 Skill 是否：

1. 能让未参与提炼的脚本保持线性、直接和可读。
2. 不会把某个工具、方法、阶段或历史参数写成硬规则。
3. 能在减少函数与保留必要复用之间做出稳定判断。
4. 能保持科学决定、输入输出和不透明 API 边界可见。

## 隔离原则

- Primary 和 Secondary 用于 Phase 2 的初始规则提炼。
- Validation holdout 在初始规则定稿前不用于增加新规则。
- 先把规则应用到 holdout，记录无法解释之处；再决定是规则过拟合、holdout 是合理例外，还是需要最小修订。
- 不因 validation 失败而复制 holdout 的具体参数、路径或工具调用。

## 建议拆分

| 阶段 | 学习集重点 | Validation holdout | 主要验证问题 |
|---|---|---|---|
| 01 QC | R 中逐项 QC；STARsolo Bash | `01-cellranger.sh` | Bash 规则是否工具中立 |
| 02 Annotation | manual + auto 主线；resolution 决策 | `03-HS_BM_auto_annotation-part2.R` | 分段工作流与人工确认 |
| 03 Integration | baseline + RPCA + export | `03-inter-harmony.R` | 是否误把 RPCA 固化 |
| 04 GRN | metacell、unsupervised、hypothesis；窄 Bash/Python | `04-hypothesis_driven_partIV.R` | 是否适用于未见的假设驱动后续 |
| 05 Program | cNMF 解释与 pathway activity | `04-metabolisum_activity.R` | 是否误把 pathway 细节固化 |
| 06 LR pairs | CellChat 标准流程、LR number、聚焦图 | `05-cellchat-stage-compare-weight.R` | 平行比较指标是否仍可表达 |
| 07 Trajectory | DR、MST、Mega dynamic genes、Ery module | `05-2-dynamic-genes-Ery.R`; `07-2-dynamic-module-Mega.R`; `04-3-lineage-pcurve-Mono.R` | lineage/module/pcurve 互换时是否过度抽象 |

正式追加 holdout：

- `07-trajectory/scripts/04-3-lineage-pcurve-Mono.R`
  - 用途：单独检查 principal-curve 分支。
  - 2026-07-30 已由用户确认加入。

## 逐脚本验证问题

### 01-cellranger.sh

- 是否能保留参数和命令顺序，而不要求包装成函数或配置系统？
- 是否避免复制 STARsolo 的命令结构？
- 是否把环境细节与脚本风格分开？

### 02 annotation part 2

- 是否能从显式上游输入继续，而不要求把 part 1/2 合并成工程 pipeline？
- 人工判断、marker 证据和最终标签是否仍可定位？
- 是否能提供非交互检查，而不强制删除探索性检查？

### Harmony integration

- 候选规则是否只要求说明“为什么选当前方法和参数”，而非要求 RPCA？
- baseline、诊断图和导出是否仍有清楚位置？

### GRN hypothesis part IV

- 未见问题能否沿用“问题—输入—API—检查—输出”的结构？
- 规则是否避免猜测顶层 `R/` API 内部？
- 是否会为了复用前几部分而引入跨文件 wrapper？

### Metabolism activity

- 通路类规则能否适用于不同 scoring 对象？
- 具体基因集、数据库和 cutoff 是否仍由当前任务决定？

### CellChat weight comparison

- 与 LR number 相似的步骤应允许局部重复，还是已经值得最小函数？
- 比较指标变化是否在主线中清晰可见？
- 输出命名是否能区分两个分支？

### Trajectory holdouts

- per-gene 或 per-module 技术函数是否保持窄职责？
- lineage、root、terminal、cutoff 和目标模块是否仍显式？
- 规则是否错误地要求把 Ery/Mega 分支合并成通用框架？

## 判定矩阵

每个 holdout 后续按以下维度记录 `pass`、`partial` 或 `fail`：

| 维度 | Pass 条件 |
|---|---|
| 主线可见 | 核心分析能按文件顺序阅读 |
| 科学决定可见 | 关键参数、假设和选择理由容易定位 |
| 检查充分 | 关键转换前后有与风险相称的检查 |
| 抽象克制 | 新函数/循环/配置确有重复或技术隔离收益 |
| API 边界清楚 | 输入准备、调用、返回检查和输出清楚 |
| 输出契约清楚 | 产物名称、类型、路径和上游关系可判断 |
| 方法中立 | 没有把学习集的工具或数值当成默认真理 |
| 环境中立 | 没有复制机器特定环境路径或 excluded 配置 |

## 防止信息泄漏

Phase 2 在首次 validation 前应只使用候选索引中的 Primary、Secondary 和
Counterexample。若之后查看 holdout 并修改规则，必须在验证记录中标明：

- 哪条规则失败；
- 是泛化失败还是合理例外；
- 做了什么最小修订；
- 修订是否重新检查其他阶段。

当前状态：**拆分已于 2026-07-30 确认，Phase 2 已获准开始。**
