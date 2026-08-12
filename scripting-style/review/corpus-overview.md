# 语料概览

## 审查范围

只读来源语料包含七个项目 `scripts/` 目录下的 59 个分析 artifact：

| 文件类型 | 数量 | 证据用途 |
|---|---:|---|
| R script | 51 | 线性对象变换、观察、人工决定、平行分支与 prototype-to-batch 的广泛证据 |
| Python script | 1 | 带真实 positional contract 的窄项目转换证据 |
| Bash script | 3 | 可见外部工具命令与显式 sample/stage blocks |
| Notebook | 4 | model-analysis cells、candidate sweeps、diagnostics 与后续人工选择的同类型证据 |

审查进入时，对 59 个 artifact 的逐文件 hash 排序后再计算 SHA-256，结果为 `3ef2cdc9524bc3fd97ab29e4a73535f490cdb4a7a8ec7f061a5b764521e874e5`。

## 最高发现

最稳定的重复顺序是：

`问题 -> 具体试做 -> 检查或比较 -> 人工判断 -> 批量扩展 -> 保存证据 -> 解释或下一问`

这支持 `Write the analysis, not an application around the analysis.`。更精致或更抽象的代码不自动构成更好的风格证据。

## 读取边界

- 只审查允许的分析 artifact 与提供语境的 README。
- 顶层项目 `R/` 实现、环境、data、resources 和 software directories 均排除。
- Notebook 只提供 source-cell 顺序与决定逻辑；stored outputs、execution counts、magics、widgets 和环境痕迹不作为已验证证据。
- 已提交记录中的来源路径全部相对于 `<SOURCE_ROOT>`。
- 机器路径、package installation、destructive temporary cleanup、历史参数、生物学结论和未公开 API internals 都不进入规则。

完整 artifact 清单见 [artifact-inventory.csv](artifact-inventory.csv)，日常使用的 canonical 角色见 [type-first example index](../examples/example-index.yaml)。
