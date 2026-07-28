# Analysis Lifecycle

对 `generic-analysis` 和 `bioinformatics` 使用三阶段 artifact model：

```text
explore → human review → archive → pipeline → publication review
```

阶段与 scientific status 相互独立。进入 `archive/` 表示 snapshot 已由人审核，
成为 pipeline 的允许来源；它不会自动把 observation 提升为 verified evidence。

## Direction gate

根目录 `QUESTIONS.md` 是 human-owned research agenda，Agent 默认只读。一次只处理
其中唯一的 `Current question`；`Next questions` 只是候选方向，不得提前分析。
先讨论 method、expected outputs 和 stop condition。只有 human 将
`Human decision` 改为 `approved_to_run` 并明确同意后，才运行
`explore-create --apply` 或执行计算。dry-run 不代表方向获批。

当前问题得到结果后立即停止，报告 answer、limitations 和候选下游问题，等待 human
审核。由 human 记录结论、决定是否入库，并把下一题移入 `Current question`。
`docs/ai_context/open_questions.md` 只记录 Agent 的 operational blockers。

## Task contract

使用 `P<order>-<core>-<short-english-summary>/`：

- `P0`, `P1`, ... 是项目内唯一的分析顺序；一次最多有一个未归档、未取消的任务。
- 每个任务只回答一个 current `Q-` ID，不把多个下游问题打包执行。
- `core` 是单个短 ASCII token，例如 `QC`、`cluster`、`GRN`。
- 末段是不可变的简短英文 kebab-case 总结，例如
  `P0-QC-low-quality-cells-removed/`。它是 task label，不是 verified claim。

将 task 的 code、二级数据和图分别保留在自己的 `scripts/`、`derived/` 和
`figures/` 内；不要把 explore task 的 artifact 散落到项目级目录。

## Exploration coding style

把 explore code 当作可执行 lab notebook，而不是 production library。优先使用
单个主 notebook、Quarto/R Markdown，或带有明确 cell/section 分隔的 Python/R
script；按实际执行顺序自上而下组织：

1. question、assumptions、inputs 和 parameters；
2. transformation、intermediate objects 和 diagnostics；
3. observations、temporary decisions 和 limitations；
4. derived outputs 与 figures。

让关键 parameters 靠近首次使用处，为 intermediate tables/plots 使用有意义的名称，
并在对应 code section 旁记录观察。单次逻辑保持 inline，允许少量重复；不要为了
“代码整洁”预先创建 generic helpers、classes、wrappers、config layers 或跨文件
abstractions。只有逻辑已稳定且重复使用，或提取能明显隔离风险时，才写短小、命名
具体的函数。若函数隐藏 scientific choices 或迫使 reader 跨文件追踪，就保留线性
代码。

### Chinese outline contract

每个 executable code script 都在文件顶部列出简短中文提纲，并使用一一对应的编号
中文 section headings。按输入、检查、转换、诊断、输出等有意义的 workflow steps
切分，通常 3–8 段；短脚本可更少，禁止按固定行数机械切段。结构变化时同步更新提纲。

```text
Python:   # %% 1. 读取输入与参数
R:        # ---- 1. 读取输入与参数 ----
Shell:    # 1. 读取输入与参数
Notebook: 使用编号中文 Markdown headings
```

outline 和 section title 使用中文；variables、functions、paths、commands、keys 和
其他 machine-readable values 保持英文。Pipeline 虽可模块化，但其中每个 code file
仍遵守同一规则，并按该文件的单一职责切分。

每个 task 的 `README.md` 记录 primary artifact、实际 run order、观察和限制。
探索完成不要求 production API；人工审核优先检查分析意图、执行顺序和中间结果是否
易读。把模块化、参数化、复用接口和系统性 tests 留到 `pipeline/`。

## Promotion contract

用 `archive-promote` 记录 reviewer、review summary 和 validation results。保留
explore 原目录，并将完整 task 冻结为 `archive/<task>/vNNN/`。每次 promotion 创建
新版本和 file hashes；不得覆盖或编辑已有 snapshot。用 `archive-verify` 重新计算
hashes。这里的 analysis archive 不同于 `docs/handoffs/archive/` 的 session archive。

## Pipeline contract

只从已审核且 hash 验证通过的 snapshot 运行 `pipeline-create`。Agent 根据这些
来源重写或整理独立主流程，在 `pipeline.yaml` 中为每个 ordered step 填写
`implementation`，并设置一个 project-relative entrypoint。runtime code 不得读取
`explore/` 或 `archive/`；archive path 只作为 provenance 保存。

发表前运行完整 workflow 和 tests，再用 `pipeline-release` 记录 human review、
validation results 与全部 pipeline file hashes。release-ready 表示发布整理完成，
不替代 evidence verification、claim review 或 Git provenance。
