# scripting-style

`scripting-style` 帮助 Codex 编写或修改项目内部的科研分析代码：`.R`、`.py`、`.sh` 和 `.ipynb`。它的最高原则是：

> **Write the analysis, not an application around the analysis.**

默认过程是：**编写当前片段 → 运行单行、多行或一个 cell → 展示并检查真实结果 → 决定下一步**。证据充分时自主推进，只在关键科学取舍无法确定时询问用户。

读入与关键变换后，按对象特点展示少量真实内容，如矩阵的小切片或表的 `head()`。代码按分析目的分段，附简短说明，使研究者能在同一会话中选择、运行和检查任一当前片段。

它保留具体试做、观察比较、判断和稳定后的批量扩展，同时减少无请求的 CLI、配置系统、runner 与 Bash/Rscript 跨数据集调度。生物信息学和单细胞分析是主要证据来源，但规则按文件类型组织，而不是按具体分析方法组织。

日常使用：

```text
使用 $scripting-style，分段续写这个 R 分析：导入后展示部分数据，每段说明目的，运行并查看结果后再决定下一步。
```

用新范例改进 Skill 时，才使用 [iteration interface](references/iteration-interface.md)；请求仍兼容 `schema_version: "1.0"`，并支持 `.ipynb`。

[公开仓库参考](references/public-repo-patterns.md) 记录已检查的 CNS 正刊相关代码、固定版本、可借鉴片段及排除项；这些来源不是通用方法或参数标准。[分段分析验证](validation/interactive-analysis-validation.md) 区分结构检查、实际执行和证据限制。
