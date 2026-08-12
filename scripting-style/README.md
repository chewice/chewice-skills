# scripting-style

`scripting-style` 帮助 Codex 编写或修改项目内部的科研分析代码：`.R`、`.py`、`.sh` 和 `.ipynb`。它的最高原则是：

> **Write the analysis, not an application around the analysis.**

它保留具体试做、观察比较、人工判断和批量扩展，同时避免无请求的 CLI、配置系统、runner 与状态管理。生物信息学和单细胞分析是主要证据来源，但规则按文件类型组织，而不是按具体分析方法组织。

日常使用：

```text
使用 $scripting-style，沿用当前项目的写法续写这个 R 分析，并保留参数比较和人工选择。
```

用新范例改进 Skill 时，才使用 [iteration interface](references/iteration-interface.md)；请求仍兼容 `schema_version: "1.0"`，并支持 `.ipynb`。`PROMPT.md` 与 `review/` 是开发证据，不属于日常运行上下文。
