# Exploration

使用以下 artifact sequence：

```text
current question → human approval → explore → human review → archive
→ pipeline → HTML release
```

task 命名为 `P<order>-<core>-<short-english-summary>`，例如
`P0-QC-low-quality-cells-removed`。最多保留一个未 archive、未 cancelled 的
task。task 目录集中保存 `task.yaml`、`README.md`、`report.md`、渲染后的
`report.html`、build manifest、scripts、derived data、figures 与 run receipts。

执行前先讨论 inputs、method、expected outputs 和 stop condition。human approval
发生在交互中，不要求在 `QUESTIONS.md` 重复登记状态。完成后说明答案、限制和可能的
下一问题，然后停止；问题路线始终由 human 维护。

若 task 因失败 receipt 或方向改变而不再继续，经 human 明确确认后使用
`explore-cancel --task ... --review-note ...`；保留 task 内容，只由 CLI 将
`task.yaml` 标为 `cancelled`，再允许创建下一 task。

explore code 是可执行 lab notebook，不是 production library。按实际执行顺序组织：

1. inputs、assumptions 与 parameters；
2. transformations 与可见 intermediates；
3. diagnostics 与 observations；
4. outputs 与 limitations。

优先减少函数封装和工程化代码，单次逻辑保持 inline 并允许少量重复。不要仅为整洁而
引入 generic helpers、classes、wrappers、configuration layers 或跨文件
abstractions。只有逻辑已经稳定，或抽取能隔离实质风险时，才使用短小、具体的
function。

每个 executable file 顶部使用简短中文 outline，并设置对应编号中文 section：

```text
Python: # %% 1. 读取输入与参数
R:      # ---- 1. 读取输入与参数 ----
Shell:  # 1. 读取输入与参数
```

analysis scripts 只写 Markdown、tables 与 figures 所需的计算结果，不包含 HTML、
CSS、templates 或 rendering；计算完成后单独调用 `report-build`。

只有 README 与 report 完整、全部 receipts 成功、声明输入未改变、outputs 仍匹配
hashes 且 human review 已记录时，才能创建 append-only `vNNN` archive snapshot。
pipeline implementation 只能依据验证通过的 snapshots 重写；runtime 不得读取
`explore/` 或 `archive/`。

`pipeline.yaml` 内的 `pipeline.entrypoint` 与每个 step 的 `implementation` 均以
`pipeline/` 为路径基准，例如 `run.py`、`src/qc.py`；不要写成
`pipeline/run.py` 或 `pipeline/src/qc.py`。
