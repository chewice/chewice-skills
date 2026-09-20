# Python 分析脚本

只在目标文件为 `.py` 时读取本指南。Python 脚本可以承载完整科研分析，也可以完成窄项目转换；它并不天然是命令行工具。

## 默认直接写顶层分析

imports 与短输入块之后，尽快进入真实变换或模型：

```text
问题与项目路径
-> 读取当前数据
-> 查看 shape、columns、categories 或 summary
-> 执行科研变换
-> 查看结果
-> 只保存所需产物
```

以当前 `.py` 文件所在目录为工作目录，读入、中间存档和输出均使用相对 `Path`。根据实际启动位置，在会话入口显式切换一次，例如从项目根运行 `scripts/analysis.py`：

```python
import os
from pathlib import Path

os.chdir("scripts")
print(Path.cwd())
```

若已在脚本目录则使用 `os.chdir(".")`。后续 `# %%` 片段不重跑初始化；不依赖交互会话中可能不存在的 `__file__`，不添加项目根搜索或多分支定位函数。输入例如 `Path("../data/metadata.tsv")`；`data_path`、`out_path` 和具体文件句柄放在相关读写附近。

输入路径可以先写；依赖数据内容的 columns、groups 和 comparisons，先观察已载入对象，再把选择写在首次使用附近。变量角色能从上下文辨认即可，允许 `df`、`adata`、`fig`、`ax` 等常用短名。

## 按分析目的分段运行

新建探索性脚本默认使用 `# %% 检查样本构成` 一类轻量分隔；修改既有脚本时沿用当前分段。每段标题与简短注释说明本段目的和需要观察的问题，不逐行解释语法。一个段落可以选择单行、多行或整个 cell 执行，不要求每段独立初始化。

读取、查看、转换或绘图等逻辑组之间留空行，紧密相关的语句连贯书写。长调用在括号内换行并缩进，不强制“检查点／决策点”标签。

```python
# %% 读取并检查样本信息
# 查看实际字段和记录，再确定分组与对齐方式。
metadata = pd.read_csv(metadata_path)

print(metadata.head())
print(metadata.columns)
```

复用 Python 交互会话中的对象；有 `# %%` 不代表普通 Python 进程会自动暂停。执行当前片段、读取实际输出后，再写入和执行依赖它的下一段。不要反复用 `python -c`、here-document 或新临时脚本重载同一个大对象。上游选择改变后，重跑受影响的下游片段。

除非用户要求可复用工具，或当前项目已经存在相应调用契约，否则不要生成 `argparse`、`click`、`main()`、config object、subcommands、logging setup、runner 或退出状态文件。被已知上游命令调用的小脚本可以沿用其真实 positional / environment contract，但不要把它泛化成新接口。

## 让探索结果真的可见

使用与当前对象匹配的直接观察。普通 `.py` 进程必须显式打印；只有项目既有执行方式将文件作为 interactive chunks 运行时，裸表达式才会显示：

```python
print(data.shape)
print(data.head())
print(data.dtypes)
print(data[group_column].value_counts(dropna=False))
print(result.describe())
```

读入、提取组件或类型转换后，若对象类型影响下一操作，可直接 `print(type(data))`，表格列类型用 `print(data.dtypes)`。不机械对应 R 的 `class()`，不在每一步堆叠类型与结构检查。

读入后至少展示一份与当前问题相关的实际内容，而不只显示 shape 或完成消息。NumPy 数组用 `counts[:5, :5]`，DataFrame 用 `metadata.head()` 或 `.iloc[:5, :5]`；稀疏矩阵需要稠密显示时只对小切片 `.toarray()`，不转换整个矩阵。AnnData 等对象可查看 `.obs.head()` 以及当前需要的表达层小切片；不默认选择或替换 assay/layer。

筛选、合并、转换或拟合后，按下一判断所需展示局部值、category counts、metrics 或 diagnostic plots。普通脚本中用 `print()` 或实际绘图显示调用；不假定 notebook 的隐式 display 可用。不要求每次变换都打印，也不创建通用 preview helper 或 assertion framework。

只有当前任务确实比较候选方法或参数时，才用短而显式的 loop 收集可比诊断。candidate values、metrics 和后续选择放在相邻片段。先看输出，再依据当前问题写下选择及理由；证据不足且取舍会改变分析含义时才询问用户。代码未运行时用注释保留待决定项，依赖它的调用也暂不执行，不把 `None` 传入下游来制造完整流程。不要编造 winner。公开 Notebook 不作为 standalone Python 具体语法的证据。

不得凭惯例补上有科学含义的 threshold、top-N、model setting 或 library default。使用当前项目已经确定的值、设计显式比较，或把未决值留在调用附近。

不要为显得完整而展开未请求的 library defaults、algorithm switches、seed 或 plot sampling。绘图宽高与必要分辨率可以在保存附近显式设置，不把显示设置当成模型参数，也不迁入来源固定值。

结果名称本身不授权 estimand、comparison unit、statistical test 或 group definition。缺失时保留 pending block，不要为获得 runnable final script 自行选择常用方法；也不要假装后续对象依赖一个实际未参与计算的上游选择。

## 先原型，再抽 batch helper

只有操作将在随后批量化、且当前数据上的行为仍未理解时，才先内联一个代表性 item 并检查。输入、变换和返回形态明确后，再抽取稳定的 per-item calculation。直接的一次性转换应删除这整段结构。

两个块重复不等于应该抽取。若独立 dataset 或 method 分支因保留各自输入、参数和输出而更清楚，就让它们保持独立；真实漂移开始误导阅读后，才重构技术共同部分。

函数适合稳定 numeric kernel、parser、重复绘图或其他窄变换。科学 cutoff、group definition、feature choice 和 model-selection decision 留在顶层首次使用附近。

## 使用风险相称的硬契约

只有 identifier 错位、duplicate key、矩阵方向异常、必需 category 丢失等会静默改变科学含义的失败，才直接 raise exception 或使用紧凑 assertion。普通探索仍以 shape 和 summary 为主。

不要围绕一次项目分析添加宽泛 `try/except`、投机 fallback、retry 或 cleanup machinery。除非存在已知且不改变科学含义的恢复方式，否则让意外 library error 保持可见。

## 保存科研产物，不保存运维状态

只写出检查或已知下游需要的 table、array、model artifact、figure 或 converted file。昂贵中间结果在用途明确时可以 cache。不要强制 table/figure/object bundle、completion message、manifest 或 pass marker。

沿用项目的数据格式，文件名说明对象或状态；中间保存旁说明下一用途，续做时重用同一文件名。例如，已整理的 `metadata` 要交给后续绘图时：

```python
out_path = Path("../results/sample-overview")
out_path.mkdir(parents=True, exist_ok=True)

fn = out_path / "metadata.tsv"
metadata.to_csv(fn, sep="\t", index=False)

# 后续片段从这份表继续绘图。
metadata = pd.read_csv(fn, sep="\t")
print(metadata.head())
```

绘图库沿用当前对象和项目习惯。数据整理、绘图调用与 `fig.savefig(...)` 等保存语句放在主线，需要据图判断时先实际显示。R 的 ggplot2、`ggsave()` 或图形设备语法不迁入 Python；不新增通用绘图或保存 wrapper。

只有观察结果后才能记录结论。未运行代码应保留明确的待解释事项或下一检查。
