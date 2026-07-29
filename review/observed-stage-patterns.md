# 分阶段候选模式

> 以下内容描述每个项目中可见的工作流和风格差异。具体文件、阈值、细胞类型、
> 基因和路径都属于语料实例，不应直接泛化。

## 01 — scRNA-seq QC

典型顺序：

1. Bash 中集中写外部工具参数、参考资源和样本输入。
2. 按样本运行定量流程。
3. R 中加载计数与元数据，逐项计算 QC 指标。
4. 在每类指标附近完成汇总、分布检查和诊断图。
5. 分别保存矩阵、metadata、表格或图。

候选特征：

- Bash 保持参数区和命令区直接可见，允许样本块有少量重复。
- R 的 QC 指标计算是线性主线，检查点紧邻对应指标。
- 科学阈值应显式，但不能从本项目历史值生成通用默认值。

主要候选：`scripts/03-calculate_metrics.R`。
次要候选：`scripts/02-starsolo.sh`。
Validation holdout：`scripts/01-cellranger.sh`。

## 02 — Annotation

典型顺序：

1. 读取对象并做 QC 或过滤。
2. normalization、降维和初步聚类。
3. 用 PC、cell cycle、resolution 等诊断支持选择。
4. 生成 marker 或自动注释结果。
5. 结合人工知识确定标签并保存对象与图。

候选特征：

- `[检查点]`、`[决策点]`、`[专家经验]` 把技术步骤和生物学判断分开。
- 关键分辨率、marker 和参考选择在使用位置可见。
- manual 与 auto 两类脚本说明 Skill 不能把注释流程收敛为单一路径。

主要候选：`scripts/01-HS_BM_manual_annotation.R`、
`scripts/05-HS_PBMC_auto_run.R`。
次要候选：`scripts/02-HS_BM_auto_annotation-part1.R`、
`scripts/04-HS_BM_auto_resolution.R`。
Validation holdout：`scripts/03-HS_BM_auto_annotation-part2.R`。

## 03 — Integration

典型顺序：

1. 先合并数据并可视化未校正的批次结构。
2. 分别尝试 RPCA 或 Harmony。
3. 在调用附近解释参数选择和适用条件。
4. 用相近的降维图或分组图比较效果。
5. 把最终对象单独导出给下游。

候选特征：

- “先看 baseline，再校正”保留了证据链。
- 不同方法各用独立、短脚本，避免抽象成过度通用的 integration 框架。
- 参数理由比统一调用包装更重要。

主要候选：`scripts/02-inter-rpca.R`。
次要候选：`scripts/01-check-batch-effect.R`、
`scripts/04-save-data.R`。
Validation holdout：`scripts/03-inter-harmony.R`。

## 04 — GRN

典型顺序：

1. 构建 metacell 或准备 pySCENIC 输入。
2. 运行外部 GRN 流程并转换 regulon 格式。
3. 计算或读取 regulon 活性。
4. 进行 unsupervised 模式发现。
5. 按生物学假设聚焦特定 regulon、细胞类型或 target。

候选特征：

- 多个 part 脚本形成“提出问题—准备输入—调用 API—查看结果—继续追问”的叙事。
- `source("../R/...")` 较多，主脚本不应重写或猜测 API 内部。
- 局部函数适合技术计算和重复绘图，但 API 风格文件不应代表线性分析脚本的全局风格。
- Bash 与 Python 候选只用于学习窄任务的直接表达。

主要候选：`scripts/01-metacell.R`、
`scripts/03-unsupervised_partI.R`、
`scripts/04-hypothesis_driven_partIII.R`。
次要候选：`scripts/02-run_pyscenic.sh`、
`scripts/02-regulon2gmt.py`、
`scripts/03-unsupervised_partII.R`、
`scripts/04-hypothesis_driven_partI.R`、
`scripts/05-cell_type_specific_regulon.R`。
Validation holdout：`scripts/04-hypothesis_driven_partIV.R`。
不建议作为主风格样例：`scripts/02-regulon_activity_score.R`；它更接近可复用 API 实现。

## 05 — From pathway to program

典型顺序：

1. 读取 cNMF 结果或表达对象。
2. 汇总 activity、variance 或 top genes。
3. 进行 enrichment、pathway 或 metabolism scoring。
4. 绘制热图和比较图。
5. 输出解释性表格、图或结果对象。

候选特征：

- setup、load、main analysis、heatmap/output 的分区稳定。
- program 和 pathway 的选择直接写在分析附近。
- 语料中没有允许范围内的 `01` 脚本，上游 cNMF 生成方式未知。

主要候选：`scripts/02-interpret_cNMF_results_part1.R`、
`scripts/03-pathway_activity.R`。
次要候选：`scripts/02-interpret_cNMF_results_part2.R`。
Validation holdout：`scripts/04-metabolisum_activity.R`。

## 06 — Ligand–receptor pairs

典型顺序：

1. 汇总输入对象并准备 epithelial 或分组数据。
2. 对每个样本运行 CellChat。
3. 绘制标准网络和 pathway 视图。
4. 比较 early/late 阶段的数量或权重。
5. 聚焦具体 ligand–receptor 对并生成汇总条形图。

候选特征：

- 文件编号和输出文件名共同维护阶段契约。
- 单样本运行、重复网络图和焦点比较使用局部函数，说明函数在重复技术操作中有价值。
- `run_cellchat` 一类函数也会隐藏核心流程，因此需要把科学参数和主要步骤留在函数体或调用附近。
- 同一步骤的 count 与 weight 用平行脚本表达，适合 validation 检查是否过度拟合某一种比较。

主要候选：`scripts/03-cellchat-standard.R`、
`scripts/05-cellchat-stage-compare-LRnum.R`、
`scripts/07-cellchat-lr-avg-barplot.R`。
次要候选：`scripts/01-data-summary.R`、
`scripts/02-epithelial-prepare.R`、
`scripts/04-cellchat-visualize.R`、
`scripts/06-cellchat-lr-focus.R`。
Validation holdout：`scripts/05-cellchat-stage-compare-weight.R`。

## 07 — Trajectory

典型顺序：

1. 比较或确定降维参数。
2. 选择 root、terminal 和候选 lineage。
3. 构建 MST 与 principal curve。
4. 按 lineage 拟合动态基因。
5. 做 NMF/imputation 和动态模块。
6. 解释模块功能并筛选潜在 regulators。

候选特征：

- 研究选择具有强上下文性，root、terminal、lineage 和 cutoff 必须显式。
- 多条 lineage 脚本重复度高，但独立脚本保持了每条生物学分支的可读性。
- 逐基因拟合、缓存昂贵计算和模块绘图适合小型局部函数。
- 多个顶层 API 被不透明调用；样例只支持学习调用边界。
- `04-4` 有两个不同脚本，重复编号不能自动解释为 legacy。

主要候选：`scripts/01-trajectory-dr.R`、
`scripts/03-lineage-mst.R`、
`scripts/05-1-dynamic-genes-Mega.R`、
`scripts/07-1-dynamic-module-Ery.R`。
次要候选：`scripts/02-lineage-picker.R`、
`scripts/04-2-lineage-pcurve-Ery.R`、
`scripts/06-nmf-imputation.R`、
`scripts/08-1-gene-module-function-Ery.R`、
`scripts/09-1-gene-module-regulators-Ery.R`。
Validation holdout：`scripts/05-2-dynamic-genes-Ery.R`、
`scripts/07-2-dynamic-module-Mega.R`；可追加
`scripts/04-3-lineage-pcurve-Mono.R` 检查 pcurve 分支。
