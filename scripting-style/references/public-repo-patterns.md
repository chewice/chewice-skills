# 公开科研代码中的分段分析（补充来源）

当前主要写作来源是 [GZDlab 本地范例索引](../examples/example-index.yaml)，本页仅在需要公开源码佐证或 Notebook 补充时读取。检查日期：2026-09-18。以下三个项目与 Nature、Science、Cell 正刊论文的对应关系已核对；只读检查选定版本的 source cells，没有执行论文分析，也不使用 stored outputs 证明结论。

已发表代码通常是整理后的分析记录。可观察其对象变换、展示位置和选择说明，但不能据此还原作者当时的探索顺序，或把整仓库视为最佳写法。下面的 cell 编号从 **1** 开始，包含 Markdown cells。

## Nature：Tabula Muris Senis

- 论文：[A single-cell transcriptomic atlas characterizes ageing tissues in the mouse](https://doi.org/10.1038/s41586-020-2496-1)，Nature，2020。
- 固定 commit：`5ee7b62ec7208c240634946180a8a105a7356816`。
- [droplet-processing Notebook](https://github.com/czbiohub-sf/tabula-muris-senis/blob/5ee7b62ec7208c240634946180a8a105a7356816/1_tabula_muris_senis/11_figure_1/tabula-muris-senis-droplet-processing.ipynb)，Python；检查 cells 1–24。
- **借鉴：** cells 3–6 在读入表和科学对象后展示记录或对象；cells 9–12 展示 metadata、执行变换、再查看类别；后续以明确段落处理另一组输入。对象和差异沿主线可见，展示是分析过程的一部分。
- **排除：** 机器路径、旧 Scanpy API、字段映射、历史筛选和类别处理不能成为默认值。较长循环只能证明这种组织形式存在，不能证明新数据适合立即套用同一循环。

## Science：Tabula Sapiens

- 论文：[The Tabula Sapiens: A multiple-organ, single-cell transcriptomic atlas of humans](https://doi.org/10.1126/science.abl4896)，Science，2022。
- 固定 commit：`14de8b082a25dba79e12c39626843543ab92e5b5`；这里只使用 `paper1`，不混入后续论文的代码。
- [Fig2_cell_fractions Notebook](https://github.com/czbiohub-sf/tabula-sapiens/blob/14de8b082a25dba79e12c39626843543ab92e5b5/paper1/Fig2/Fig2_cell_fractions.ipynb)，Python；检查 cells 1–24。
- **借鉴：** cells 12–18 用标题区分读入、分析和变换，显示输入表、局部记录与汇总表；cell 20 接续绘图；cells 22–24 另起一段读入另一类表并展示。计算、观察与图形用途能够顺着代码追踪。
- **排除：** 开头的大型绘图 helper、通配 import、个人路径、历史参数和大量遗留注释不是探索模板。展示整张表在这个来源中存在，但新任务仍按对象大小选择局部内容。

## Cell：KPTracer

- 论文：[Lineage tracing reveals the phylodynamics, plasticity, and paths of tumor evolution](https://doi.org/10.1016/j.cell.2022.04.015)，Cell，2022。
- 固定 commit：`76a022bc6ab0bd3238127843a15acb00087d97ce`。
- [Figure3_S3_diffexp Notebook](https://github.com/mattjones315/KPTracer-release/blob/76a022bc6ab0bd3238127843a15acb00087d97ce/reproducibility/Figure3_S3/Figure3_S3_diffexp.ipynb)，**R 代码**；检查全部 21 个 cells。
- **借鉴：** cells 7–9 将计算、结果查看和后续处理分开；cells 11–17 用说明区分分析目的、计算、人工挑选及结果展示，选择留在主线并明确其人工性质。Notebook 的实际语言必须核对，不能默认 Python。
- **排除：** 人工挑选的具体内容、统计阈值、包版本和隐藏上游依赖不迁移；部分选择与图形是发表后的固定方案，不能假定适用于新任务。批处理脚本和算法库不作为默认交互分析架构。

## 如何用于本 Skill

- 这三份证据都是 `.ipynb`。它们支持 Notebook 的分段展示与选择可见性；不据此推导 `.R`、`.py` 或 `.sh` 的具体语法。R 分段、Python `# %%` 和按结果推进的执行约束来自本次用户明确要求，并由本地类型指南与验证支持。
- 仅借鉴当前分析真正需要的结构，不抄写历史参数、标识、数据内容或科学结论。公开仓库有 helper 和 pipeline，并不使它们成为本 Skill 的默认产物；稳定的窄函数和机械重复仍有合理位置。
- [本地范例索引](../examples/example-index.yaml) 的 `<SOURCE_ROOT>` 现在明确指 GZDlab 根目录，旧 sc06 来源相对路径均带 `sc06/` 前缀。保持同类型按需读取；本页不覆盖用户指定的本地写作偏好，来源缺失时也不搜索用户机器或强制下载。
- 后续验证见 [分段分析验证](../validation/interactive-analysis-validation.md)。源码形式、片段执行测试和真实科学分析的正确性分别报告。
