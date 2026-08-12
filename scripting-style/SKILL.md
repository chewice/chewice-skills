---
name: scripting-style
description: 为项目内部科研分析编写、续写、重构或审查直接而探索性的 `.R`、`.py`、`.sh` 和 `.ipynb` 代码；按目标文件类型读取同类型指南与范例，保留问题、具体试做、观察比较、人工判断、批量扩展和科学输出。用户强调少封装、避免应用式脚手架、沿用既有分析叙事或要求用新范例迭代 scripting-style 时使用。不用于设计环境、公共函数库、R package、通用 CLI、runner 或统一 pipeline。
---

# Scripting Style

> **Write the analysis, not an application around the analysis.**

默认产物是项目内部的科研分析记录。读者应能看见问题如何被具体尝试、检查、比较、判断并继续推进，而不必先理解一套运行框架。

## 日常入口

1. 确认目标文件类型，只完整读取对应的一份指南：
   - `.R`：[R analysis](references/r-analysis.md)
   - `.py`：[Python analysis](references/python-analysis.md)
   - `.sh`：[Bash analysis](references/bash-analysis.md)
   - `.ipynb`：[Notebook analysis](references/notebook-analysis.md)
2. 修改既有代码时，先读目标文件及其邻近的**同类型**脚本。保持当前 section、对象命名、路径锚点和分析顺序，默认做 minimal diff；只有用户明确要求重构时才扩大改动。
3. 新建代码时，若用户提供了 source root，或索引中的相对路径可从当前工作区明确解析，可从 [type-first example index](examples/example-index.yaml) 选择最多一个同类型 primary，必要时再选一个同类型 complement。只学习结构；不得复制来源中的路径、参数、环境痕迹或科学结论。不要猜测 `<SOURCE_ROOT>` 或搜索用户机器来定位范例；来源不可用时直接依照类型指南，且不声称已读取范例。
4. 任务调用用户或项目提供的 API 时，再读取 [API usage boundary](references/api-usage-boundary.md)。
5. 只有仍存在会改变分析含义的选择时，才在对话中按需简述问题、输入、预期产物、候选决定和待确认项；不要固定填写工作提要，也不要为此创建 spec 或 plan。

不得用另一种文件类型的范例推导具体写法。四种类型只共享本页的原则和边界；R section、Python CLI、Bash 调度或 Notebook cell 习惯均不可跨类型套用。

## 保留分析怎样发生

按当前问题保留下列探索链中实际需要的环节，不为凑模板制造空步骤：

`问题 -> 具体试做 -> 检查或比较 -> 人工判断 -> 批量扩展 -> 保存证据 -> 解释、局限或下一问`

- 让科学对象和数据变换按真实执行顺序自上而下出现。
- 在会影响下一步判断的位置观察结果：结构摘要、对象打印、候选表或诊断图都可以是分析本身。
- 方法尚未在当前数据上站稳时，先把一个代表性案例内联跑通。看见输出并修正后，才把稳定的逐元素技术核提成局部函数或循环。
- 候选参数或方法可以并列尝试。把比较证据留在脚本中，再将人工选择写回调用附近；不要为一次决定创建 selector、config 或自动决策器。
- 任务没有给出、项目也没有明确约定的科学参数，不得用惯例值、来源值或 package default 悄悄补齐。若它阻止代码成立，先从当前数据设计比较，或在调用附近留下明确的待定值；只有会实质改变任务且无法安全留待判断时才询问用户。
- 不要为了让代码显得完整、可复现或专业而显式展开用户未要求的 package defaults、algorithm switches、random seed、plot sampling size、颜色或导出分辨率。它们只有在任务、邻近项目约定或当前比较确实需要时才出现。
- 模糊的产物名称不等于方法授权。若生成该产物还需要确定 estimand、comparison unit、statistical test、group definition 或模型，必须把缺失决定留在主线；不要为了交付一份“完整可运行”脚本自行选标准方法。
- 不伪造步骤依赖。若用户设想的后续分析并不实际使用上一步选择，应在代码或交付说明中指出概念缺口，并保留正确 handoff，而不是把无关对象接起来。
- 允许脚本在人工编辑的中间表处暂停，分成 part，重载上一步对象，或缓存有明确科研用途的昂贵结果。这些是研究边界，不是任务状态系统。
- 实际运行后可以记录观察到的结论、局限和下一问。未运行或未检查时明确写成“待判断”，不得编造结果。

## 克制应用式结构

- CLI、通用配置、runner、dispatcher、registry、状态追踪、retry、completion marker 和统一 pipeline 只在用户明确要求，或当前文件确实有跨输入复用契约时出现。
- 项目内的样本、比较、阈值、相对路径和候选参数可以直接写在分析附近；不要仅因它们可能变化就建立参数平台。
- 不以“重复两次”作为函数门槛。样本、方法、实验变体或 lineage 的大段平行代码，只要能让参数、顺序和输出独立可读，就可继续保留。
- 只有真实维护漂移开始妨碍科学理解，或逐元素技术核已经稳定时，才抽取最小共同部分。核心判断仍留在主线。
- 观察性检查是默认；只有顺序错位、维度不合、标识符不唯一等失败会静默污染科学结论的硬契约，才用简洁断言立即停止。
- 核心持久对象使用明确名称；紧凑语义块里的 `p`、`fn`、`data_plot` 等局部名字可以保留。
- 不强制生成表格、图和对象三件套，不强制打印 operational completion summary，也不默认写 `run_summary`、`validation_pass` 或状态文件。每个输出都应有当前科研、复查、下游或复现用途。

简洁只约束表达方式，不缩减用户要求的科学分析。复杂问题应展开成可见的 analytical blocks，而不是升级成软件架构。

## 项目与 API 边界

- 把用户或项目提供的 API 当作不透明能力：只依据已知契约准备输入、调用、观察返回并保存所需结果。
- 不打开、复制、猜测或重写未获授权的 API 实现。
- 不自动设计 Pixi、Conda、容器、编辑器配置、公共函数库或 package。
- 使用项目已有的路径锚点；新代码不引入机器特定绝对路径。
- 来源范例始终只读，只修改用户指定的目标。

## 模板

模板仅在新建文件且项目没有更近的同类型先例时使用：

- [linear-analysis.R](templates/linear-analysis.R)
- [linear-analysis.py](templates/linear-analysis.py)
- [external-analysis.sh](templates/external-analysis.sh)
- [linear-analysis.ipynb](templates/linear-analysis.ipynb)

删除无关块并替换占位内容。模板不是必填章节清单，更不能替代当前分析判断。

## Skill 迭代入口

只有用户要求用新范例审查或改进 `scripting-style` 时，才完整读取 [iteration interface](references/iteration-interface.md)。日常写脚本不加载迭代流程。

迭代保持两阶段：Phase 1 只读比较并停止等待确认；Phase 2 仅实施当前对话已确认的 decisions、exclusions、holdouts 和 rule changes，同时验证新旧 holdout。`scripts/validate-iteration-request.py` 只做只读预检，不能授予写权限。

## 交付前自检

- 从目标文件向下阅读，问题、输入、变换、观察、判断和产物是否可追踪？
- 是否保留了真实探索证据，而没有只留下一个看似确定的最终调用？
- 是否出现没有当前契约支持的 CLI、config、runner、`main()`、`run_analysis()` 或状态管理？
- helper 是否在代表性案例被理解后才抽取，并且没有隐藏科学决定？
- 硬断言是否只保护可能静默污染结论的契约？
- 输出是否各有用途，未运行的结果是否明确留作待判断？
- 是否把任务未提供的 cutoff、resolution、top-N 或模型参数伪装成了合理默认值？
- 是否为了让代码跑到底而自行选择了未获授权的 comparison、test 或 group definition，或假装后续步骤依赖前一步？
- 修改既有代码时，差异是否局部且保持邻近同类型叙事？

若不理想，优先恢复可见的分析链并删除无科研作用的外围结构。
