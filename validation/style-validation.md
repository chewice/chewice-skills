# 轻量风格验证

## 范围与方法

- 验证日期：2026-07-30
- 状态：完成首次静态 holdout 验证
- 初始规则来源：仅使用已确认的 Primary、Secondary 和 API-like Counterexample
- 验证对象：9 个确认的 validation holdout
- 方法：比较脚本分节、步骤顺序、参数位置、API 边界、中间检查、局部函数与输出保存
- 未执行分析脚本，未检查生物学结果
- 未打开顶层 `R/`，未读取 Pixi 文件或数据目录

Holdout 中出现的具体参数、路径、工具和生物学对象没有写入通用规则。

## 结果摘要

| Holdout | 结果 | 主要结论 |
|---|---|---|
| `01-scrna-qc/scripts/01-cellranger.sh` | Partial | 参数和重复样本块符合直接 Bash 风格；历史脚本缺少显式错误退出、输入检查和完成摘要 |
| `02-annotation/scripts/03-HS_BM_auto_annotation-part2.R` | Pass | 线性 QC—聚类—决策—注释—保存主线、检查点和 API 边界均被规则覆盖 |
| `03-integration/scripts/03-inter-harmony.R` | Pass | 方法参数理由、替代整合方法、诊断图和对象保存说明规则未固化 RPCA |
| `04-grn/scripts/04-hypothesis_driven_partIV.R` | Pass | 假设—通路—TF 筛选—调控证据—可视化保持线性，API 仅在调用边界出现 |
| `05-from-pathway-to-program/scripts/04-metabolisum_activity.R` | Partial | setup—load—score—heatmap 清楚；只保存图，证明不能强制每个脚本同时保存图、表和对象 |
| `06-lr-pairs/scripts/05-cellchat-stage-compare-weight.R` | Partial | 两组平行 Wilcoxon 主线和输出清楚，保留重复优于强行 wrapper；上游输入检查较弱 |
| `07-trajectory/scripts/04-3-lineage-pcurve-Mono.R` | Pass | lineage、root、terminal 和曲线参数可见；API 采用准备—调用—绘图—保存边界 |
| `07-trajectory/scripts/05-2-dynamic-genes-Ery.R` | Partial | 逐基因局部函数边界合理，参数和输出可见；前置单基因试算存在静态变量依赖风险 |
| `07-trajectory/scripts/07-2-dynamic-module-Mega.R` | Partial | 小型绘图函数、昂贵计算缓存和长脚本分节符合规则；含机器特定环境路径及未定义缓存字段风险 |

`Pass` 表示候选规则能解释主要结构且未发现影响风格泛化的冲突。`Partial` 表示主结构可解释，
但存在不能升级为通用规则的历史写法或静态风险。

## 逐项验证

### 01 — Cell Ranger Bash

正确预测：

- 全局资源参数与样本参数分开；
- 命令顺序直接可见；
- 两个样本保留平行重复，没有建立 workflow framework；
- 每个样本有独立输出目录。

不一致：

- 脚本没有 `set -euo pipefail`、输入存在性检查或完成提示。

处理：

这些安全项继续保留在 Bash 模板中，因为它们是用户在 Phase 2 明确要求的增强；不宣称
它们是所有来源脚本共有的历史风格。

### 02 — Annotation part 2

正确预测：

- 输入、QC、降维、resolution 比较、决策、自动注释和保存按顺序展开；
- `[检查点]` 与 `[决策点]` 表达分析语义；
- QC、PC、resolution、score cutoff 在使用附近可见；
- 外部 annotation API 的输入准备、调用和返回检查清楚；
- 图、metadata 与对象按用途保存。

未形成新规则：具体 QC cutoff、marker、resolution、权重和 score cutoff。

### 03 — Harmony integration

正确预测：

- 读取未校正对象作为 baseline 上游；
- `theta` 的分析含义在调用附近解释；
- 整合后按 project、sample 和 annotation 生成可比较诊断；
- 保存下游对象；
- 说明整合规则必须方法中立，不能把 RPCA 固化。

### 04 — GRN hypothesis part IV

正确预测：

- 先明确新通路问题，再选择 gene set 和打分；
- 依次用相关性、target overlap、hub 和 cell-type variance 形成证据链；
- 外部 theme 与 variance API 只学习加载和调用边界；
- 多个 TF 绘图块保留少量重复，科学对象在主线可见；
- 图表紧邻对应筛选步骤保存。

未形成新规则：通路、TF、overlap threshold、importance cutoff 和绘图样式。

### 05 — Metabolism activity

正确预测：

- setup、load、score、aggregation 和 heatmap 分节；
- gene-set 文件、score 方法、cell type 排除和颜色选择可定位；
- 关键矩阵维度在转换后检查。

泛化修订：

初始阶段指南曾倾向同时保存分数矩阵、表格和图；该脚本只保存 heatmap。因此正式规则改为
“按人工复查和下游复用需要选择输出类型”，不要求凑齐所有产物。

### 06 — CellChat weight comparison

正确预测：

- stage、样本和 pseudocount 在分析前可见；
- LR-level 与 pathway-level 两段平行流程保持指标差异；
- 两个短而相似的 Wilcoxon 块没有被强行抽成通用函数；
- 结果表、条件图和结束摘要与分析步骤对应。

局限：

读取 sample metadata 和合并网络表后缺少显式结构检查。Skill 继续要求风险相称的输入检查，
但不把某一种 `head()`、`dim()` 或 `table()` 写成固定模板。

### 07 — Mono principal curve

正确预测：

- lineage、reduction、dims、curve flexibility、root 与 terminal 显式；
- 外部 lineage API 不透明；
- 调用前检查 lineage 列，调用后用曲线和 pseudotime 图检查；
- 对象保存支持下一条 lineage 继续写入。

未形成新规则：具体谱系、细胞 barcode、reduction、自由度和 sample size。

### 07 — Ery dynamic genes

正确预测：

- lineage 和模型参数集中且解释；
- 上游 lineage/pseudotime 列有明确契约检查；
- `de.test()` 是逐基因重复计算的合理局部函数；
- 显著与非显著基因绘图保留平行重复；
- 保存调整后 p 值供后续 module 使用。

静态风险：

全基因扫描前的单基因试算块引用了随后才在局部函数内定义的
`expressionFamily` 与 `leftcensored`。这更像未清理的探索检查，不能作为正向风格。
Skill 的“检查必须保护下一步”规则应能提示删除或补全该块，但本轮不修改来源脚本。

### 07 — Mega dynamic modules

正确预测：

- 关键 DREMI、FDR 和 cluster 参数直接可见；
- `DynamicPlot()` 与 `DREVIGridPlot()` 只封装重复绘图；
- 核心筛选、聚类、module 重排和保存仍在线性主线；
- 对昂贵 DREMI 结果建立 cache 有明确复现目的；
- 外部 API 只按调用边界处理。

静态风险与排除项：

- 脚本中出现机器特定 `.pixi` Python 路径；它不进入 Skill 风格。
- cache 的参数列表引用了当前脚本中未定义的 `demo.genes`，复现块可能不完整。
- `if (FALSE)` 复现段是特定脚本的调试/复现选择，不升级为模板。

## 多脚本支持的稳定规则

- 自上而下的线性分析主线。
- 关键方法参数和科学决定在主线或调用附近可见。
- 语义分节表达分析阶段，不需要统一装饰语法。
- 外部 API 使用准备—调用—检查—保存边界，不推断内部。
- 高风险转换后使用与下一步相匹配的检查。
- 输出路径和产物角色显式，输出类型由复查和下游复用需求决定。
- 局部函数适合逐元素计算、重复技术调用或绘图，不隐藏核心决策。
- 平行方法、stage 或 lineage 分支可以保留少量重复。
- 绝对环境路径和历史参数不能泛化。

## 只适用于特定阶段的规则

- QC：按指标展开并比较过滤前后构成。
- Annotation：明确区分检查、聚类选择和专家注释判断。
- Integration：先保留 baseline，再解释校正方法和强度。
- GRN：区分 unsupervised 总览与 hypothesis-driven 聚焦。
- Program/pathway：显式说明 program 与 gene-set 选择。
- LR pairs：明确 sender/receiver、stage 和比较指标。
- Trajectory：显式保留 root、terminal、lineage、pseudotime 与动态模型选择。

## 仍不确定或不稳定的模式

- 是否统一设置工作目录；
- 是否使用交互式 `View()`；
- 是否每个脚本都打印完成摘要；
- 输出目录和路径变量的统一名称；
- 覆盖已有输出的统一策略；
- 函数数量或脚本长度上限；
- 是否把参数集中在文件顶部或放在使用点附近。

这些项目继续作为项目级选择，不设全局硬规则。

## 验证失败或无法泛化的模式

- “每个脚本必须同时保存图、表和对象”无法泛化，已修订。
- “所有 Bash 范例都有错误退出和输入检查”不成立；模板保留它们是明确的安全增强。
- 环境路径、工具参数、数据库、阈值、谱系和具体生物学对象均无法泛化。
- Holdout 中的未定义变量、探索残片和机器路径不能成为风格规则。
- 不能依据单个重复块规定必须函数化，也不能依据单个长函数规定禁止函数。

## 结论

初始 Skill 的核心规则通过 7 个阶段的 holdout 检查。两处措辞已根据验证收紧：

1. 输出类型由实际复查和下游用途决定。
2. Bash 安全项标记为明确增强，而不是语料共有事实。

没有把 holdout 的具体方法、参数或环境细节加入规则，也没有修改任何来源脚本。
