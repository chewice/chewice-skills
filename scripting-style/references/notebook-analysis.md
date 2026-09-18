# Notebook 分析

只在目标文件为 `.ipynb` 时读取本指南。Notebook 是一系列可交互的科学决定，不是加了一层 JSON 的 Python 脚本。

## 先识别语言，再按 cell 推进

读取已有 Notebook 的 `kernelspec`、`language_info` 和 source cells，确认实际语言；不能把 `.ipynb` 等同于 Python。R kernel 使用 R 的对象观察与调用语法，Python kernel 使用 Python 语法。沿用既有 kernel；metadata 与代码明显冲突时先澄清，不能静默转换。新建文件按当前任务语言设定 kernel；随附模板仅适用于 Python。

每个 cell 推进一个可观察步骤。常见顺序是：

1. 说明问题并定义当前输入；
2. 只导入后续 cell 所需依赖；
3. 读取对象并显示结构；
4. 准备当前 features、groups 或 model inputs；
5. 运行一个代表性 fit 或显式 candidate sweep；
6. 显示可比诊断；
7. 检查真实输出后，在后面的 cell 记录选择及依据；
8. 用选定结果继续；
9. 保存下游真正需要的结果；
10. 有实际观察时，再记录解释、局限或下一问。

不要强制固定 cell 数量。cell 应足够小，使科研人员可以自然地重跑一个步骤并看见结果。

每个分析段用简短 Markdown 标题和说明，或沿用项目清楚的 cell 内注释，交代目的与需要观察的问题。一个说明可以覆盖相邻的计算与展示 cells；不为每行代码单设 Markdown，不用固定章节凑齐提纲。

在同一个 kernel 中执行当前 cell，检查输出后才执行依赖它的下一 cell。默认不 `Run All` 穿过尚未决定的分组、阈值或方法选择。证据充分时 agent 自主继续，不要求用户确认每个 cell。重跑上游筛选或参数后，更新实际受影响的下游 cells，不能继续引用旧结果。

## 保留 sweep 和人工选择

candidate values 与结果诊断放在相邻 cell。selection cell 必须位于 comparison cell 之后：

```python
candidate_values = [...]  # 当前分析有依据的候选值
candidate_results = {}

for value in candidate_values:
    # 用该值拟合或变换，并保存可比较诊断。
    ...
```

下一个 cell 显示 metrics 或 plots，更后的 cell 才记录 selected value 与理由。尚未作出选择时，用 Markdown 或注释标记待判断，依赖选择的调用保持注释或暂不生成，不把 `None` / `NA` 传入下游。不得编造 optimum 或 diagnostic output。

不得仅因惯例而预填有科学含义的 cutoff、top-N、model setting 或 default。使用当前项目值，把它加入可见候选比较，或在独立 cell 明确保留为未决。

不要为 Notebook 显得完整而增加未请求的 library defaults、algorithm switches、seed、plot sampling、palette、export resolution 或多余诊断 cell。只保留能支持当前人工判断的最小证据。

若一个下游产物仍需确定 estimand、comparison unit、statistical test 或 grouping，专门留一个 pending decision cell；不得为了使 Notebook 看似完成而选择常用方法。若后续步骤并不真正使用前一选择，应在相邻 Markdown 中指出这一点，不制造虚假数据流。

新生成 Notebook 的所有 code cell 都必须使用 `execution_count: null` 和空 `outputs`。不得伪造 rich display、image、metric 或执行顺序。修改既有 Notebook 时，除非用户明确要求清空或重跑，否则保留用户已有 outputs；但不得把 stale output 当成已验证证据。

## 先原型，再批量化

变换或模型仍待理解时，用独立 cell 跑一个代表性 item。需要时检查 intermediate object 和 positive、negative 或 null control。只有技术核稳定，且后面 cell 确实遍历一个显式集合后，才抽小型 per-item function。

不要把 candidate choice、biological group、cutoff 或 interpretation 移进 helper。大型 method 或 dataset branch 在能保持实验可读时，可以留在独立 cells 或 notebooks 中。

## 不要在 Notebook 外围搭 application

不要添加 `argparse`、CLI entrypoint、YAML config loading、runner、pipeline state、retry system 或 completion marker。除非当前项目已有其他契约，否则 Notebook 参数应放在控制相应分析的可见 cell 中。

昂贵 scientific fit 可以保存并重载，使诊断或解释无需重算即可继续。save/load cell 旁必须说明这一科研用途；不要扩张成 generic cache orchestration。

## 观察优先

导入后展示少量实际内容，而不只是 shape 或载入消息。Python 的表可用 `.head()`，数组可用 `[:5, :5]`；R 的表可用 `head()`，矩阵按实际大小取局部切片。大型或稀疏对象只显示局部，不为预览将整个对象转成 dense。Python cell 的最后一个表达式可以隐式显示，若同一个 cell 需要看多个结果，使用 `display()` / `print()`；R kernel 使用对应语言的显示方式。

在关键变换后，显示真正影响下一步判断的内容、摘要或诊断。不要堆叠无用途的打印或新建通用展示函数。只有 mismatched observation identifiers、missing required layer 等失败会静默破坏分析时，才用硬 assertion。

只保存有当前科学、复查、下游或复现用途的产物。final completion cell 可有可无；诚实的待回答下一问往往更有用。
