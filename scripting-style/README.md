# scripting-style

`scripting-style` 帮助 Codex 编写或修改项目内部的科研分析代码：`.R`、`.py`、`.sh` 和 `.ipynb`。它的最高原则是：

> **Write the analysis, not an application around the analysis.**

默认过程是：**编写当前片段 → 运行单行、多行或一个 cell → 展示并检查真实结果 → 决定下一步**。证据充分时自主推进，只在关键科学取舍无法确定时询问用户。

以当前脚本或 Notebook 所在目录为工作目录，读入、中间存档和最终输出均使用相对路径。R 开头默认显式执行 `setwd()`、`getwd()`、`.libPaths()` 后再加载包；根据启动位置填写相对目标，已在脚本目录则用 `setwd(".")`，后续片段不重复初始化。

读入与关键变换后，按对象特点展示少量真实内容，如矩阵的小切片或表的 `head()`；提取组件、转换类型时适时查看 `class()`。自然标题、短注释和逻辑组间空行使研究者能在同一会话中选择、运行和检查当前片段。

路径、对象名和存档用途在调用附近可见，允许 `seu`、`ref`、`df`、`p`、`fn` 等上下文清楚的短名。绘图按用途混用基础绘图、ggplot2 与包自带函数，需要据图判断时先显示，再继续。

它保留具体试做、观察比较、判断和稳定后的批量扩展，同时减少无请求的 CLI、配置系统、runner 与 Bash/Rscript 跨数据集调度。主要写作参考是 GZDlab 的代表脚本；只学习表达与组织，不继承其方法、参数或科学结论。规则按文件类型组织。

## 运行必需依赖

本 Skill 是写作与执行方式指南。仅编写或审查代码时，需要能读取本目录 [SKILL.md](SKILL.md)、对应类型指南及目标代码的 Agent；修改文件还需目标路径写入权限，没有统一的必装分析软件包。

实际运行代码时，按文件类型准备依赖，不要求同时安装全部环境：

| 任务 | 必需条件 |
| --- | --- |
| R 分析 | 可交互分段执行的 R 会话，以及当前代码使用的包；随附 R 模板使用 `Matrix` |
| Python 分析 | 可交互分段执行的 Python 3 会话，以及当前代码使用的包；随附 Python 模板使用 `pandas` |
| Bash 外部工具步骤 | Bash，以及当前命令实际调用的外部工具；模板中的 `TODO_TOOL` 必须替换为所需工具 |
| Notebook | 能逐 cell 执行的 Notebook 宿主与对应语言 kernel，例如 Jupyter 或支持 Notebook 的编辑器；随附模板为 Python kernel，使用 `pandas` |
| Skill 迭代请求预检 | Python 3；[预检脚本](scripts/validate-iteration-request.py) 仅使用标准库，日常写脚本无需运行 |

`ggplot2`、Seurat、Scanpy 等仅在具体分析需要时准备。GZDlab 原始范例不是日常运行依赖，来源不可用时依照本地指南工作。环境构建与安装依赖属于另行明确的任务。

## 如何使用

在已加载本 Skill 的 Agent 对话中，给出目标文件、当前问题、输入位置，以及本次是只编写还是实际分段执行。例如：

```text
使用 $scripting-style，以脚本目录为工作目录，用相对路径分段续写这个 R 分析：初始化后展示数据内容与类型，运行并查看结果后再决定下一步。
```

只需要改写时可以说：`使用 $scripting-style，整理 scripts/analysis.py 的分段、路径和局部数据展示；本轮只修改代码，不运行分析。` 未发现 Skill 时，指定本目录 `SKILL.md` 的实际路径请 Agent 读取。

新建文件可参考 [R](templates/linear-analysis.R)、[Python](templates/linear-analysis.py)、[Bash](templates/external-analysis.sh) 或 [Notebook](templates/linear-analysis.ipynb) 模板；先替换问题、输入和工具占位内容，再按真实结果续写。模板不是可直接批跑的完整分析，已有代码优先保持邻近风格和局部修改。

用新范例改进 Skill 时，才使用 [iteration interface](references/iteration-interface.md)；请求仍兼容 `schema_version: "1.0"`，并支持 `.ipynb`。

[公开仓库参考](references/public-repo-patterns.md) 记录已检查的 CNS 正刊相关代码、固定版本、可借鉴片段及排除项；这些来源不是通用方法或参数标准。[分段分析验证](validation/interactive-analysis-validation.md) 区分结构检查、实际执行和证据限制。
