# 全局脚本风格

## 核心目标

让读者只沿当前脚本向下阅读，就能回答：

- 研究问题是什么；
- 输入来自哪里；
- 当前步骤做了哪些关键选择；
- 用什么中间证据支持继续分析；
- 生成了哪些图、表和对象。

## 稳定规则

### 保持线性分析叙事

按“目标与契约 → 加载 → 参数 → 输入 → 检查 → 准备 → 核心分析 → 再检查 →
整理与可视化 → 保存”的自然顺序编写。可以省略不适用步骤，但不要把主线分散进
多个本地模块。

### 默认是分析记录，不是应用

项目内科研脚本默认写成 **executable analysis record**，不是 command-line application 或
execution-management layer。主脚本应直接暴露科学工作流：

```text
定义分析输入 → 读入数据 → 检查关键假设 → 执行分析 → 检查结果 →
保存有科学意义的产物 → 作图
```

除非用户明确要求或外围 workflow 已有契约，否则不要自动加入：

- `commandArgs()`、argparse 或自定义 CLI parser；
- 泛型 `--input`、`--output-root`、`--label`、`--expected-*` 接口；
- 靠 completion 文件自动发现任务或样本；
- completion markers、run-state tracking、execution summaries；
- 仅记录「校验通过」的 input-contract / audit 表；
- 通用 filesystem orchestration；
- pipeline-status 词汇，如 `COMPLETE`、`PASS`、`expected`、`run state`。

**项目特异性允许。** 当前分析需要的 sample / library / dataset ID、项目相对路径、阈值、
比较组和实验分组，可以直接写在脚本前部。这不是 code smell；它往往比引入 CLI 抽象更易读、
更易复现。不要仅因「将来可能变」而泛化这些常量。仅当同一脚本**确实**要作为跨多组输入的
可复用工具时，才泛化或改为参数注入。

仍禁止机器特定绝对路径（`/home/...`、盘符、`~`）；允许的是锚点下的项目相对路径与分析常量。

**样本来自分析输入，不来自执行发现。** 已知样本或文库集合时，优先显式定义或从研究设计 /
analysis manifest 读取，例如：

```r
library_ids <- library_manifest$library_id
# 或固定项目分析：
library_ids <- c("GSM1", "GSM2", "GSM3")
```

不要用上游 job 的 completion 产物反推样本集，例如扫描 `complete.tsv` 再取目录名。

**尽快进入科学主线。** 依赖与短输入定义之后，应较快出现有科学意义的计算。不要让脚本前半被
argument parsing、filesystem discovery、配置层、校验基建或执行管理占满；若读者必须先理解
一套 execution framework 才能看到分析，应简化结构。

### 用语义分节，并让 R 章节可导航

章节是否存在、如何切分，先由分析语义决定，不按固定行数或装饰模板切段。标题说明当前
分析意图，例如“检查样本与分组”或“选择用于下游的 lineage”。

需要在 VS Code/RStudio OUTLINE 中导航的 R 脚本，使用 title-first、delimiter-last 的
section syntax：

```r
# 1. 检查样本与分组 ----

## 1.1 核验分组契约 ----
```

- 标题写在分隔符前，行末至少 4 个连续 `-`；
- 顶层使用一个 `#`，需要层级时使用 `##`、`###`；
- 不写 `# ---- 1. 标题 ----`，避免 OUTLINE 名称带前导装饰符；
- 普通 `# 1. 标题` 注释不是 document symbol，不能替代 section heading。

若用户或 repository 要求文件顶部有中文“脚本提纲”，提纲项与正文顶层 section 的编号和
语义一一对应；顶部提纲用于快速概览，正文 section 承担 OUTLINE 导航。短脚本未被要求时
不必重复一份顶部提纲。

静态 section 检查通过但编辑器仍显示 `No symbols found` 时，检查 R Language Service 是否
启动、连接或刷新；不要继续改写分析代码来猜测编辑器环境问题。

### 使用可迁移的相对路径

项目内部输入、输出、脚本、API 和资源默认使用相对路径。每个脚本只采用一个明确锚点，
优先服从 repository 或 runner 已规定的 working directory，并在脚本头部或运行说明中写清
基准。不要混用 repository-relative、task-relative 和 script-relative 路径而不说明。

不要硬编码 `/home/...`、用户目录、Windows drive path、`~`、机器安装目录或绝对
`setwd()`。项目内已知的 sample / library ID 与相对路径优先写成分析常量。仅当输入在项目
外部、无法合理相对化，或项目已有 CLI / manifest / runner 契约时，才用该契约注入；不复制进
repository，也不写成新的机器路径常量，更不要仅为项目内常量自动包一层 CLI。

允许运行时为存在性检查、日志或审计解析 absolute path，但不要把解析结果写回源码或作为
可迁移配置保存。不要为少量路径增加 YAML、环境变量层、path manager class 或通用 helper。

### 保留科学决定

把会改变解释的选择放在主线或调用附近，并解释当前依据：

- QC 指标与阈值；
- normalization、PC、resolution 或 integration strategy；
- annotation reference、marker 与标签映射；
- root、terminal、lineage 和 pseudotime；
- regulon、gene set、ligand–receptor、module 或 cutoff。

不要只写“使用默认参数”，也不要复制范例中的历史数值。

### 检查应保护下一步，并 Fail Fast

在高风险转换后立即使用与问题匹配的检查：

- 结构：维度、列名、类型、唯一键；
- 构成：样本数、分组数、细胞数、缺失值；
- 结果：分布、交叉表、摘要统计、候选排名；
- 诊断：降维图、QC 图、拟合曲线、网络或热图；
- 契约：预期列、对象槽位、输出文件。

检查必须能支持下一步决策。不要为“看起来完整”堆积无解释的打印。

对应当满足的 invariant，优先用简洁断言立即失败，例如 R 中的 `stopifnot(...)`，
Python 中的 `assert`，Bash 中的显式退出。只检查当前任务里真正重要、且静默出错会污染
下游解释的数据契约。

不要为每一个理论上可能发生的异常建立防御瀑布：存在性检查层层嵌套、`warning` 后继续、
第二 fallback、第三 fallback。除非该异常在当前任务中有现实发生概率，否则不写。

**校验通过后通常消隐。** 校验保护科学正确性，本身不是子系统。`stopifnot` / 等价断言通过后
继续分析即可。不要默认构造或保存 `input_contract`、`count_check`、`run_summary`、
`validation_summary`、`execution_status` 等对象或文件，除非它们本身回答科学、QC、provenance
问题，或用户 / 外围 workflow 明确要求。成功校验通常不需要变成输出文件。

### 减少不必要的控制流

尽量减少嵌套 `if` / `else`、`switch`、`tryCatch`、early return 和 speculative fallback。
若分析可写成直接数据变换，就直接写。

条件判断仍然适用于：

- 防止静默的数据错位；
- 验证关键输入或不可恢复契约；
- 根据真实实验设计必须区分的处理路径。

原则是减少不必要 branching，而不是消灭 branching。不要为假想未来场景预留分支。

区分**科学分支**与**运维分支**。保留代表真实分析差异的分支，例如 human vs mouse、
chemistry 版本、case vs control、某项生物学测量有无、正当的统计边界情况。对主要为运维目的
的分支保持怀疑：job 是否完成、输出文件是否存在、用户是否提供了某 CLI 参数、是否走
fallback path、当前是哪种 execution mode。运维分支仅在 workflow 确实需要时添加。

### 一个分析概念，一个局部块

一个 metric、比较或决策尽量在一个连续代码块内完成：计算、必要中间变量、就地写入、
紧邻检查。不要把简单步骤拆成 function definition → helper → configuration → call →
post-processing → metadata merge。

### 保持数据流可见，使用具体命名

尽量让核心数据对象保持稳定并可追踪，例如 `counts`、`metadata`、`seu`、`sce`、
`results`。优先就地累积结果：

```r
metadata$mito_frac <- ...
metadata$nuclear_frac <- ...
```

除非代表真正不同的数据语义，否则不要制造无信息量的版本链或容器：
`metadata_v1`、`metadata_tmp`、`metadata_final2`、`analysis_context`、
`result_container`、`metric_registry`。

变量名应反映科研含义（如 `mito_genes`、`case_cells`、`doublet_score`）。避免
`obj`、`tmp`、`res2`、`data_new`、`x1`、`holder`、`context`、`manager`。
不要为了假想通用性，把具体 biological concept 改成抽象术语。

### 注释解释科学，不解释语法

注释主要说明：

- 为什么做这一步；
- 指标代表什么；
- 阈值或参数的依据；
- 对应的 biological / statistical concept；
- 特殊处理为什么存在。

不要写没有信息量的语法旁白，例如“# create directory”或“# calculate mean”。
有价值的注释形如：

```r
# Nuclear fraction: intronic reads / (intronic + exonic reads)
# Use donor-level pseudobulk to avoid treating nuclei as independent replicates.
```

### 必要分析复杂度 vs 偶然架构复杂度

科学问题本身可以复杂。用户明确要求的 QC、doublet、annotation、DEG、pathway、
敏感性分析或图形，全部实现——这是 necessary analytical complexity。

简洁只约束**如何写代码**，不缩减**做多少科学分析**。正确方式是并列增加
analytical blocks，而不是因此引入 AnalysisManager、MetricRegistry、PipelineExecutor、
ConfigLoader、DatasetAdapter 或 ResultFactory 等 accidental software complexity。

### 修改既有脚本时采用 minimal-diff

修改用户指定的既有科研脚本时，默认：

- 保持原有 section、变量命名习惯和对象组织方式；
- 在原位置增加逻辑；
- 不无故搬动代码；
- 不顺手全面重构；
- 不把已有 script 改写成另一种 architecture。

除非用户明确要求 refactor。来源范例仍只读，不得修改。

### 以认知复杂度为目标

多个科学上等价的实现之间，优先选择：更少抽象、更少分支、更浅嵌套、更少间接层、
更少隐藏状态、更可见的数据流、更显式的分析决策、更局部的推理。

最终目标是 minimum cognitive complexity，不是最少代码行数。允许中间变量改善思考，
不要把多步逻辑压成难读的一行（code golf）。

优先使用该生态成熟、常见、易识别的写法（如 R 中的 `Matrix::colSums`、`dplyr`、
Seurat / SingleCellExperiment、ggplot2）。标准函数已能清楚完成任务时，不要自造
wrapper。

不要仅因数据“可能很大”就提前引入 parallel abstraction、disk cache、multiprocessing
framework、memory scheduler 或自定义稀疏算法。只有实际出现内存不足、明显性能瓶颈或
不合理运行时间时，才对瓶颈做局部优化，不顺便重构整个分析。

### 输出靠近产生它的分析

整理结果后立即保存相应图表或对象。文件名表达阶段、对象和比较维度。对于昂贵或会被
下游复用的结果，保存可重载对象；对于人工审查，保存表格和图。

## 函数与重复

默认内联：

- 只使用一次的短步骤；
- 直接表达科学推理的步骤；
- 参数和决策需要在主线中被读者看见的步骤。

允许局部函数：

- 同一技术操作真实重复多次；
- 逐基因、逐样本或逐图的计算单元；
- bootstrap、resampling、模型拟合或绘图保存等窄技术细节；
- 输入输出容易用一两句话说明。

函数只负责一个窄动作。不要为了“整洁”把整段核心分析包成
`run_analysis()`，也不要建立 class、公共 helper 层或通用 pipeline。

少量平行重复是可接受的，特别是不同 sample、stage、lineage 或方法分支。只有重复
已经造成修改漂移时，才提取最小共同技术步骤。

## R、Python 与 Bash 的角色

### R

承载统计分析、生物学判断、诊断和可视化。优先对象和参数在使用位置可见，避免把一次性
分析改造成 package 风格。

### Python

适合窄范围格式转换或文件桥接。使用清楚入口和最小参数；不自动引入 class、配置框架
或多模块布局。

### Bash

适合外部工具调用和少量脚本编排。显示输入、输出、调用顺序、错误退出和进度；不要发展
成工作流管理器。

## 项目级而非通用规则

以下做法可沿用当前项目约定，但不能成为 Skill 的全球默认：

- 固定 `setwd("scripts")`；
- 特定 `data/`、`output/` 或 figure 目录；
- `View()` 交互检查；
- 固定路径变量名；
- 固定完成消息；
- 固定覆盖行为。

先查看当前仓库说明和邻近脚本，再决定这些细节。

## 禁止泛化与投机工程

- 不复制绝对路径、用户目录或环境命令。
- 不在新脚本中硬编码机器绝对路径；默认使用有明确锚点的相对路径。
- 不把范例中的参数值设为默认值。
- 不根据单个脚本创建强制规则。
- 不依据编号、修改时间或命名相似性宣称脚本已废弃。
- 不从 README 的排版或环境部分学习脚本风格。

除非用户明确要求或当前任务已有现实需要，否则不要主动加入：generic configuration /
YAML / CLI framework、class hierarchy、workflow engine、caching / retry / fallback
framework、compatibility layer、plugin architecture、logging framework、state
management、checkpoint system、execution registry、automatic recovery、generic
dataset adapter。

YAGNI 只约束软件架构复杂度，不限制用户明确要求增加的科学分析工作。

特别警惕仅凭工程惯例自动产生的理由，例如“为了更健壮 / 未来扩展 / 兼容更多数据集 /
可维护性 / 模块化 / 安全，我对所有步骤加入检查……”。这些操作都必须有**当前任务中的
具体理由**，不能自动实施。
