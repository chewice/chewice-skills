# 候选样例审查

## 选择原则

候选不是“代码质量排行榜”，而是用于回答不同问题的证据：

- **Primary**：主分析线清楚，关键科学决定可见，适合提炼核心风格。
- **Secondary**：补充不同语言、不同阶段或局部函数的合理用法。
- **Validation holdout**：Phase 1 只登记，不参与初始规则提炼；用于后续检查规则是否能解释未见脚本。
- **暂不采用**：更像 API、目的不清，或存在需要人工确认的问题。

候选中的路径、包、阈值、细胞类型、基因和输出名都不能直接变成通用模板。

## 01-scrna-qc

### Primary

`scripts/03-calculate_metrics.R`

- 可学习：按 QC 指标展开的线性流程；输入检查、诊断和保存靠近对应计算；表格、图和对象各有明确产物。
- 不应泛化：具体 QC 指标、阈值、数据路径和对象结构。
- 置信度：高。

### Secondary

`scripts/02-starsolo.sh`

- 可学习：Bash 参数和命令直接可见，脚本角色窄。
- 不应泛化：外部工具参数、资源路径、样本列表和环境命令。
- 置信度：中。

### Validation holdout

`scripts/01-cellranger.sh`

- 验证目标：候选规则能否覆盖另一种外部定量工具，而不把 STARsolo 细节写成硬规则。

## 02-annotation

### Primary

`scripts/01-HS_BM_manual_annotation.R`

- 可学习：检查点、决策点和专家经验显式；人工注释不是隐藏在 helper 中。
- 不应泛化：marker、标签和骨髓数据假设。
- 置信度：高。

`scripts/05-HS_PBMC_auto_run.R`

- 可学习：完整自动注释工作流仍保持顺序可读；关键输出和诊断在主线中。
- 不应泛化：PBMC 参考、细胞类型或固定自动化路线。
- 置信度：高。

### Secondary

`scripts/02-HS_BM_auto_annotation-part1.R`

- 可学习：长流程可以通过语义章节分段，而不必拆成大量函数。
- 置信度：中高。

`scripts/04-HS_BM_auto_resolution.R`

- 可学习：resolution 的比较和选择依据保持可见。
- 置信度：高。

### Validation holdout

`scripts/03-HS_BM_auto_annotation-part2.R`

- 验证目标：规则能否连接分成两部分的工作流，并保留人工确认环节。

## 03-integration

### Primary

`scripts/02-inter-rpca.R`

- 可学习：方法选择、参数理由、整合调用和诊断图紧密相邻。
- 不应泛化：RPCA 是默认方法，或历史参数是默认值。
- 置信度：高。

### Secondary

`scripts/01-check-batch-effect.R`

- 可学习：先建立未校正 baseline，再决定是否整合。
- 置信度：高。

`scripts/04-save-data.R`

- 可学习：把窄范围导出步骤保持为短脚本。
- 置信度：中。

### Validation holdout

`scripts/03-inter-harmony.R`

- 验证目标：规则能否解释替代整合方法，而不偏向 RPCA API。

## 04-grn

### Primary

`scripts/01-metacell.R`

- 可学习：输入准备、参数、API 调用、诊断和保存构成清楚边界。
- 不应泛化：metacell 是所有 GRN 的必需前置。
- 置信度：高。

`scripts/03-unsupervised_partI.R`

- 可学习：问题驱动的探索主线和阶段化输出。
- 置信度：高。

`scripts/04-hypothesis_driven_partIII.R`

- 可学习：把生物学假设写在代码附近，再用明确分析步骤回答。
- 置信度：高。

### Secondary

`scripts/02-run_pyscenic.sh`

- 可学习：外部工具编排的窄 Bash 脚本。
- 不应泛化：环境和资源路径。
- 置信度：中。

`scripts/02-regulon2gmt.py`

- 可学习：单一格式转换任务可用短、直接的 Python 完成。
- 置信度：高。

`scripts/03-unsupervised_partII.R`

- 可学习：跨 part 延续问题与产物。
- 置信度：中高。

`scripts/04-hypothesis_driven_partI.R`

- 可学习：假设驱动分析的起点和输入准备。
- 置信度：中高。

`scripts/05-cell_type_specific_regulon.R`

- 可学习：聚焦分析仍保持目标、过滤和输出可见。
- 置信度：中高。

### Validation holdout

`scripts/04-hypothesis_driven_partIV.R`

- 验证目标：规则能否解释假设驱动系列的后续脚本，而不依赖前几部分的具体问题。

### 暂不作为主样例

`scripts/02-regulon_activity_score.R`

- 原因：形态更接近可复用 API 实现，函数和接口设计会放大工程化倾向，不代表多数分析脚本。
- 用途：后续可作为反例，检验 Skill 是否能区分“分析脚本”和“库/API 文件”。

`scripts/04-hypothesis_driven_partII.R`、
`scripts/06-screen_TFs_for_given_target.R`

- 状态：用户已确认两者具有 README 未说明的特殊地位。
- 处理：具体角色尚未说明，暂标记为 `special-status-unclassified`；不宣称
  legacy、不作为普通未入选样例，也不据此形成规则。

## 05-from-pathway-to-program

### Primary

`scripts/02-interpret_cNMF_results_part1.R`

- 可学习：从结果对象到 activity、variance 和解释性图表的线性链。
- 不应泛化：program 编号、top genes 数量和历史 cutoff。
- 置信度：高。

`scripts/03-pathway_activity.R`

- 可学习：基因集选择、打分、比较和热图保持在一个可读主线内。
- 置信度：高。

### Secondary

`scripts/02-interpret_cNMF_results_part2.R`

- 可学习：对同一结果继续做富集解释，而不制造通用分析框架。
- 置信度：中高。

### Validation holdout

`scripts/04-metabolisum_activity.R`

- 验证目标：规则能否覆盖另一类 activity scoring，并避免把 pathway 细节固化。

## 06-lr-pairs

### Primary

`scripts/03-cellchat-standard.R`

- 可学习：单样本重复分析何时值得局部函数；主步骤和科学参数仍应可定位。
- 风险：核心 CellChat 流程被放进函数，是“合理复用”与“隐藏主线”的边界样例。
- 置信度：中高。

`scripts/05-cellchat-stage-compare-LRnum.R`

- 可学习：阶段比较的输入、比较维度、结果检查和输出紧邻。
- 不应泛化：early/late 分组和固定比较指标。
- 置信度：高。

`scripts/07-cellchat-lr-avg-barplot.R`

- 可学习：聚焦少数 ligand–receptor 对时，数据整理和最终图可以直接展开。
- 置信度：高。

### Secondary

`scripts/01-data-summary.R`、`scripts/02-epithelial-prepare.R`

- 可学习：上游汇总和窄范围数据准备保持独立。
- 置信度：中。

`scripts/04-cellchat-visualize.R`、`scripts/06-cellchat-lr-focus.R`

- 可学习：重复可视化可用小函数降低噪声。
- 风险：函数数量增多后可能遮蔽主分析顺序。
- 置信度：中。

### Validation holdout

`scripts/05-cellchat-stage-compare-weight.R`

- 验证目标：用同一工作流的平行分支检查规则是否只拟合 LR number。

## 07-trajectory

### Primary

`scripts/01-trajectory-dr.R`

- 可学习：降维选择、诊断和输出形成完整决策链。
- 置信度：高。

`scripts/03-lineage-mst.R`

- 可学习：root、terminal 和 lineage 决定显式，API 调用前后有检查。
- 不应泛化：具体谱系和端点。
- 置信度：高。

`scripts/05-1-dynamic-genes-Mega.R`

- 可学习：逐基因模型适合最小局部函数，外层分析顺序仍线性。
- 置信度：高。

`scripts/07-1-dynamic-module-Ery.R`

- 可学习：动态模块构建、诊断和解释输出的长流程如何用章节而非工程层分隔。
- 置信度：高。

### Secondary

`scripts/02-lineage-picker.R`

- 可学习：在正式拟合前显式展示候选 lineage。
- 置信度：高。

`scripts/04-2-lineage-pcurve-Ery.R`

- 可学习：特定谱系分支的直接参数化。
- 置信度：中高。

`scripts/06-nmf-imputation.R`

- 可学习：昂贵或重复计算可使用缓存和窄函数。
- 置信度：中高。

`scripts/08-1-gene-module-function-Ery.R`、
`scripts/09-1-gene-module-regulators-Ery.R`

- 可学习：把模块功能和 regulators 作为明确下游问题继续展开。
- 置信度：中高。

### Validation holdout

`scripts/05-2-dynamic-genes-Ery.R`、
`scripts/07-2-dynamic-module-Mega.R`

- 验证目标：在 lineage 和模块分支互换后，检查规则是否仍能保留关键决定而不过度抽象。

可追加：`scripts/04-3-lineage-pcurve-Mono.R`，专门验证 principal-curve 分支。

## 人工确认结果

2026-07-30 已确认：

1. API-like 的 `04-grn/scripts/02-regulon_activity_score.R` 作为反例，不作为正向主样例。
2. Validation holdout 在 Phase 2 初始规则草案完成前保持隔离。
3. `07-trajectory/scripts/04-3-lineage-pcurve-Mono.R` 加入正式 holdout。
4. `04-hypothesis_driven_partII.R` 和 `06-screen_TFs_for_given_target.R`
   确有 README 未说明的特殊地位。因具体角色尚未说明，暂标记为
   `special-status-unclassified`：不宣称 legacy、不作为普通未入选样例，也不据此新增规则。
