---
name: scripting-style
description: 为新的 R、Python 或 Bash 生物信息学分析脚本设计并实现线性、直接、少封装的写法，同时保留研究问题、输入输出、关键参数、生物学决策、中间检查和结果保存；也提供两阶段迭代接口，用新脚本范例审查并改善本 Skill。用户要求编写、续写、重构或审查单细胞/单核转录组脚本，强调减少函数封装、避免过度工程化、沿用既有分析叙事，或要求输入新范例、更新风格规则、迭代 scripting-style 时使用。不用于设计 Pixi 环境、公共函数库、R package 或统一 pipeline 框架。
---

# Scripting Style

从研究问题和可观察输入出发，生成顺序可读、决策可见、能被中间结果验证的分析脚本。

## 读取必要参考

每次使用时：

1. 读取 [全局脚本风格](references/global-script-style.md)。
2. 读取 [参数组织](references/parameter-organization.md)、
   [局部函数](references/local-helper-functions.md)和
   [输出约定](references/output-conventions.md)。
3. 若任务调用用户或项目提供的 API，再读取
   [API 使用边界](references/api-usage-boundary.md)。
4. 判断任务属于哪个阶段，只读取对应的
   [阶段指南](references/stages/)。
5. 从 [范例索引](examples/example-index.yaml) 选择最接近的 1–2 个正向范例；
   只学习其结构，不复制历史路径、参数或生物学结论。

## 迭代 Skill

当用户提供新脚本范例并要求改善 `scripting-style` 时，切换到迭代模式：

1. 完整读取 [Skill 迭代接口](references/iteration-interface.md)。
2. 使用自然语言请求或 [迭代请求模板](templates/iteration-request.json) 接收输入。
3. 可运行 `scripts/validate-iteration-request.py` 做只读路径与 manifest 预检。
4. Phase 1 只比较新证据和当前规则；可写入独立 iteration review，但不得修改
   `SKILL.md`、references、examples、templates 或其他功能文件，汇报后停止。
5. 只有用户明确确认 candidates、exclusions、holdouts 和 rule changes 后，才进入 Phase 2。
6. Phase 2 只实施获确认的最小变化，并同时执行新 holdout 与旧 holdout 回归验证。

不得把两阶段压成一次自动写入，也不得把迭代报告变成 spec、plan 或复杂治理平台。

## 先给出简短工作提要

在写脚本前，用简短对话说明以下内容。保持轻量，不创建独立 spec 或 plan 文件：

```text
任务阶段：
分析问题：
输入：
输出：
本次提供的 API：
参考范例：
线性主线：
关键参数及选择依据：
需要显式保留的生物学决策：
确有必要的局部函数：
预计生成的文件：
```

信息不足时，先检查当前项目、现有脚本和用户提供的 API。只有会实质改变分析含义且
无法从上下文判断时，才向用户询问。

## 编写线性主线

按任务实际需要组织以下顺序，不为凑齐模板制造空步骤：

1. 说明脚本目标、上游输入和主要产物。
2. 加载最小依赖与明确提供的 API。
3. 定义输入、输出和本次关键参数。
4. 读取数据并检查结构、样本或分组。
5. 完成必要的数据准备。
6. 执行核心分析，使生物学和统计决策留在主线中。
7. 在高风险转换或决定后立即检查中间结果。
8. 整理结果并生成必要图表。
9. 保存当前任务需要的表格、图形和可复用对象。
10. 输出简短完成摘要。

遵循第一性原理：区分数据事实、方法假设和生物学判断；根据当前问题选择方法和参数，
不要让模板、历史脚本或惯例替代推理。

## 克制抽象

- 默认内联一次性、短小、与核心推理直接相关的步骤。
- 只在显著减少真实重复、隔离窄技术细节或表达逐元素计算时定义局部函数。
- 保持函数短、输入输出显式，并放在首次使用前附近。
- 不把 QC 阈值选择、细胞类型判断、整合策略、root/terminal、lineage、cutoff、
  基因集选择等核心决定隐藏进函数。
- 允许少量重复来保持不同样本、阶段或 lineage 分支独立可读。
- 不自动引入 class、配置层、跨文件 wrapper、插件系统、公共函数库或统一 pipeline。
- 重复已经造成实际漂移时，才提取最小共同技术步骤；不要提前为假想复用工程化。

## 尊重 API 与项目边界

- 把用户或项目提供的 API 当作不透明边界。
- 只确认加载位置、调用契约、调用前准备、调用后检查和输出。
- 不打开、复制、猜测或重新实现未获授权的 API 内部。
- 不自动设计 Pixi、Conda、容器或编辑环境。
- 不从范例复制机器特定绝对路径。
- 不修改来源范例；只在用户指定的目标文件中工作。

## 使用模板

- 新 R 分析脚本可从 [linear-analysis.R](templates/linear-analysis.R) 的结构开始。
- 窄 Python 转换任务可参考 [analysis-helper.py](templates/analysis-helper.py)。
- Bash 编排可参考 [stage-runner.sh](templates/stage-runner.sh)。
- 只有函数门槛成立时，才查看
  [local-helper-snippets.md](templates/local-helper-snippets.md)。

模板仅提供结构。删除不适用章节，替换全部占位内容，不保留虚构方法或参数。

## 完成前自检

- 能否从上到下说明脚本如何回答分析问题？
- 输入、输出、上游依赖和运行假设是否明确？
- 关键参数是否有当前任务的依据，而非照搬历史值？
- 核心生物学决定是否仍在主线可见？
- 每个局部函数是否通过了必要性门槛？
- 关键中间结果是否可观察且足以支持下一步？
- API 是否只按已知契约调用？
- 当前任务需要的图、表和对象是否命名清楚并与分析步骤对应？
- 是否出现了不必要的 class、config、wrapper、跨文件抽象或 pipeline？

若答案不理想，优先简化结构、恢复决策可见性，再交付脚本。
