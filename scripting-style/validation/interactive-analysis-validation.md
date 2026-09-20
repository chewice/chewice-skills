# 分段分析验证

## 当前验证：2026-09-20 GZDlab 写作校准

本轮按用户已确认的计划实施：以当前文件目录为工作目录，使用相对路径；R 开头显式 `setwd()`、`getwd()`、`.libPaths()`；自然分段、短名、适时类型与局部展示，以及按用途存档和混合绘图。初始化目标按启动位置填写，只运行一次，不新增路径搜索、配置或执行框架。

### 来源与修改范围

- 用户指定 GZDlab 后，筛选 scripts 目录下四类文件，枚举并粗扫 294 份（含重复版本），再分组精读代表片段；不宣称逐份全文审阅。记录保留在既有 [范例索引](../examples/example-index.yaml)，25 条来源相对路径与文件类型全部核实。
- 本地来源是主要写作参考；公开 Notebook 保留为补充。只读取分析脚本，不执行来源分析，不修改来源文件或环境；未另做全量来源散列审计。
- 同步核心说明、四类指南与模板、索引、README 和 UI 描述。删除短名禁用表、重复标签要求及旧路径约定；保留既有四类型与请求 schema 1.0，validator 和 fixtures 未修改。

### 结构与兼容性

| 检查 | 本轮结果 |
|---|---|
| Skill frontmatter 与 UI | quick_validate 通过；UI 长度与 `$scripting-style` 调用标识符合要求。 |
| YAML、JSON、Notebook | 解析通过；新 Notebook 为 Python kernel，cell IDs 唯一、outputs 为空、execution_count 为 null。 |
| 模板、fixtures、文档示例 | 6 份 R 模板／fixtures 通过 parse；Python AST、Notebook cells 与 Bash `-n` 通过；5 个 R、5 个 Python 文档代码块通过语法解析。 |
| 迭代接口回归 | `python3 scripting-style/scripts/test-validate-iteration-request.py` 通过，保留四类型发现与 schema 1.0。 |
| 来源路径、内部链接、空白 | 25 条同类型来源路径与本地 Markdown 链接有效；`git diff --check` 通过。 |
| 独立复核 | 非作者复核核心说明、Python/Bash/Notebook 指南与模板、README/UI，未发现与最新路径约定冲突的具体问题。 |

### 实际执行

| 场景 | 本轮实际结果 |
|---|---|
| R 模板分段执行 | 从隔离项目根启动同一个 R 进程，分别运行模板入口与矩阵读取段、metadata 段；工作目录为 scripts，读入 2×3 矩阵及表格，class、数值与字段均可见。 |
| 样本对齐与上游修改 | 观察实际 `sample_id` / `condition_label`，将 S3/S1/S2 对齐到 S1/S2/S3；选择 control 时总量为 3，改为 treated 并重算得到 7、11。 |
| 存档、重载与最终输出 | 使用相对路径保存并重载 metadata RDS，内容一致；保存可读 TSV 与 base R PDF，确认输入、存档和产物均由脚本目录解析。 |
| 类型转换与稀疏展示 | matrix 转为 data.frame 后实际查看 class/head；100000×100000 稀疏矩阵仅查看 5×5，仍为 dgCMatrix，三个非零值未改变。 |
| 已在脚本目录的入口 | R 中显式 setwd('.')、getwd()、.libPaths() 后相对输入输出仍可访问；Bash 分别测试项目根启动与改为 cd . 后从文件目录启动。 |
| Python / Notebook 初始化 | 实际执行两个模板的标准库初始化片段，cwd 指向文件目录，相对输入可访问；未运行 pandas 数据片段或 Jupyter kernel。 |
| Bash 当前工具步骤 | 替换为隔离 stub 后每次仅调用一次，按相对路径读取合成表并生成内容一致的局部预览；未运行真实生信 CLI。 |
| 独立前向任务 | 独立 agent 仅收到 skill、合成输入及描述性任务，生成并在同一 R 会话分段运行脚本：对齐 metadata、保存后下一段重载、输出总量 3/7/11 与 base R PNG；实际查看图像，没有新增 wrapper 或方法推断。 |

当前默认环境为 R 4.6.1，Matrix 可用，**ggplot2、pandas、NumPy、SciPy、nbformat、nbclient 不可用**。ggplot 保存示例与 Python/Notebook 数据片段只做语法或结构检查；不声称执行了 ggplot2 绘图、pandas 分析或 Jupyter kernel。未为验证安装包或修改环境。本轮独立前向任务覆盖 R 描述性分析，不能证明所有未来生成行为。

本轮隔离证据在 gitignored 的 `iterations/20260920-gzdlab-writing/`，保留前期审查、已确认决定、执行说明及 temp 内的合成数据和产物；不复制 GZDlab 来源代码。

## 历史验证：2026-09-18

以下是前一轮分段执行、数据展示与去除过度包装的历史结果，不作为本轮执行记录。

### 验证范围

- 初始修改前保存当前工作区基线；保留此前三处未提交修改中“先观察盘上字段和水平，再选择”的意图。
- 本次没有执行真实生物学数据分析或复现论文。下表中的运行检查使用隔离的合成数据或测试工具。
- 分段任务由本轮实施者执行，验证片段可运行、输出可见与对象连续性；不是独立 agent 的盲测，不能证明所有未来生成行为。
- 本轮没有提供 `<SOURCE_ROOT>`，旧外部 corpus 未重跑。本页只报告本次实际检查，不沿用历史 Pass。

### 结构与兼容性

| 检查 | 结果与边界 |
|---|---|
| Skill frontmatter | `skill-creator/scripts/quick_validate.py` 通过。 |
| UI metadata、YAML、JSON | 解析通过；描述长度和 `$scripting-style` 调用标识符合现有约定。 |
| R 模板与本地 R fixtures | `parse()` 通过；两份既有 minimal-diff / OUTLINE fixtures 未修改。 |
| Python 模板与 Notebook code cells | Python AST 解析通过；新 Notebook cell IDs 唯一、outputs 为空、execution_count 为 null。 |
| Bash 模板 | `bash -n` 通过。 |
| schema 1.0 迭代接口 | `python3 scripting-style/scripts/test-validate-iteration-request.py` 通过；validator 及其测试代码未修改。 |
| 本地文档链接与 Git whitespace | 检查 Markdown 文件链接目标存在；`git diff --check` 通过。 |

### 实际运行检查

| 场景 | 实际观察 |
|---|---|
| R 单行和多行、同会话继续 | 将三个片段分别送入同一个 R 进程；首次读入 6×6 矩阵并展示 5×5 内容，后续直接使用已有对象。 |
| 非预设字段与样本对齐 | 查看表后使用实际 `condition_label` 字段；原样本顺序与矩阵不同，显式对齐并用简洁断言保护标识契约。 |
| 上游改变后的下游更新 | 显式选择测试任务指定的 control 后得到 S1/S3/S5 汇总；改为 treated 并重算后得到 S2/S4/S6，未沿用前一组结果。 |
| 小矩阵预览 | 2×3 对象按实际尺寸展示，没有套用 5×5 索引。 |
| 稀疏矩阵预览 | 创建 100000×100000、仅三个非零值的 R `Matrix` 对象；只显示 5×5 切片，原对象仍为 sparseMatrix，没有整体稠密化。 |
| 合理局部函数与重复操作 | 同一 R 会话中使用窄均值函数和 `vapply()`，科学选择仍在调用之外。 |
| R 模板读入行为 | 在临时目录提供合成 RDS/TSV，运行模板后可见行列标识、数值和真实 metadata 字段；未决段没有下游调用。 |
| Python 会话连续性 | 在一个 Python REPL 中分三段使用标准库读取合成 CSV、展示记录、按实际字段筛选、改变选择并重算；原输入对象 identity 保持不变。 |
| Bash 外部命令边界 | 在临时目录用 stub 工具运行模板，仅调用一次并得到可预览文本输出；没有第二样本或 Rscript 调度。未运行真实生信 CLI。 |

Python 当前环境没有 pandas、NumPy、SciPy、nbformat 或 nbclient。本次 **没有实跑 pandas 模板、Python 稀疏矩阵或 Jupyter kernel**；这些部分仅做源代码/JSON 检查。R-kernel 识别核对了公开 KPTracer Notebook 的 metadata 与 R source；不宣称已运行该 Notebook。

### 修改后首次检查的公开 holdout

来源在初始指南与模板修改后才读取，未用其内容制定初始规则。只审查 source，不引用 stored outputs，也未运行来源分析。

| 来源与检查范围 | 观察与处理 |
|---|---|
| [Nature：tms-bbknn](https://github.com/czbiohub-sf/tabula-muris-senis/blob/5ee7b62ec7208c240634946180a8a105a7356816/1_tabula_muris_senis/11_figure_1/tms-bbknn.ipynb)，Python，重点查看 cells 1–36 | 有读入、对象展示、批次合并、图形诊断、保存/重载。也出现前置未定义对象和 imports 之前的调用，不能当作干净会话可顺序重放的样板；已有新规则要求显式依赖与必要重算。 |
| [Cell：Figure1_S1](https://github.com/mattjones315/KPTracer-release/blob/76a022bc6ab0bd3238127843a15acb00087d97ce/reproducibility/Figure1_S1/Figure1_S1.ipynb)，Python，24 cells | 目的说明和按图分段清楚；同时存在窄算法函数、长循环、历史阈值和异常处理。选择性保留结构证据，不将所有函数判为过度包装，也不采用其完整批处理架构。 |

两者均为混合证据，**不标记整份源码符合本 Skill**。无需因这些差异增加框架或把来源参数写入规则。前三份 learning sources 的固定版本 SHA-256 与前轮读取结果一致；没有写入任何来源仓库。

### 记录位置

隔离记录位于 gitignored 的 `iterations/20260918-result-driven/`：Phase 1 保留前两轮只读审查与公开来源哈希；Phase 2 保留确认的 decisions、holdout 哈希、原始会话输出及一份检查总结。

用户随后授权清理冗余：删除已被现行规则和本页取代的旧验证报告、重复范例说明、20260914 已完成迭代的草案与记录，以及本轮完成后不再需要的全量基线、失效文件哈希和重复总结。有效规则、接口测试与 fixtures 保留；清理后重新检查链接、结构和接口回归。
