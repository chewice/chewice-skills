# scripting-style

`scripting-style` 帮助 Codex 编写或修改项目内部的科研分析代码：`.R`、`.py`、`.sh` 和 `.ipynb`。它的最高原则是：

> **Write the analysis, not an application around the analysis.**

默认过程是：**编写当前片段 → 运行单行、多行或一个 cell → 展示并检查真实结果 → 决定下一步**。证据充分时自主推进，只在关键科学取舍无法确定时询问用户。

以当前脚本或 Notebook 所在目录为工作目录，读入、中间存档和最终输出均使用相对路径。R 开头默认显式执行 `setwd()`、`getwd()`、`.libPaths()` 后再加载包；根据启动位置填写相对目标，已在脚本目录则用 `setwd(".")`，后续片段不重复初始化。

读入与关键变换后，按对象特点展示少量真实内容，如矩阵的小切片或表的 `head()`；提取组件、转换类型时适时查看 `class()`。自然标题、短注释和逻辑组间空行使研究者能在同一会话中选择、运行和检查当前片段。

路径、对象名和存档用途在调用附近可见，允许 `seu`、`ref`、`df`、`p`、`fn` 等上下文清楚的短名。绘图按用途混用基础绘图、ggplot2 与包自带函数，需要据图判断时先显示，再继续。

它保留具体试做、观察比较、判断和稳定后的批量扩展，同时减少无请求的 CLI、配置系统、runner 与 Bash/Rscript 跨数据集调度。主要写作参考是 GZDlab 的代表脚本；只学习表达与组织，不继承其方法、参数或科学结论。规则按文件类型组织。

日常使用：

```text
使用 $scripting-style，以脚本目录为工作目录，用相对路径分段续写这个 R 分析：初始化后展示数据内容与类型，运行并查看结果后再决定下一步。
```

用新范例改进 Skill 时，才使用 [iteration interface](references/iteration-interface.md)；请求仍兼容 `schema_version: "1.0"`，并支持 `.ipynb`。

[公开仓库参考](references/public-repo-patterns.md) 记录已检查的 CNS 正刊相关代码、固定版本、可借鉴片段及排除项；这些来源不是通用方法或参数标准。[分段分析验证](validation/interactive-analysis-validation.md) 区分结构检查、实际执行和证据限制。
