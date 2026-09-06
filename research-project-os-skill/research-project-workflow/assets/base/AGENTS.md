# Repository Instructions

## Language

- 面向 human 的说明默认使用中文。 
- 专业术语、code、paths、commands、IDs 和 machine-readable values 等agent方便识别的内容保持英文。

## Reasoning

- 遵循第一性原理、奥卡姆剃刀原理
- 先明确科学问题、数据生成过程、比较对象与推断单位，再选择足以检验当前解释的最简单方法；复杂方法应有具体证据支持。

## Analysis

- 按“问题 → 小范围试做 → 观察与比较 → 判断 → 必要时批量扩展”线性组织分析；先检查数据和图形，再决定下一步。
- 一次性分析直接写出；只有真实重复或独立技术操作才提取小函数。过滤、分组、阈值、协变量和统计假设不得藏在包装函数里。
- 减少反应式编程：报错先定位数据、输入或假设的原因，不叠加 fallback、自动重试、宽泛异常捕获及猜测性兼容分支；不能解释的异常明确报告。
- 不为探索预建通用 CLI、runner、插件、配置层或统一 pipeline；成熟的库函数可以直接使用。
- exploratory 分析可从简短问题和待检验解释开始，未确定的设计如实标记。记录影响判断的试做与变更，不为每次绘图或参数试探新建 Artifact。
- 描述性探索可暂时没有假设或 Claim/Evidence 编号；默认用 compact BRIEF/RESULT，正式审核前再补全 full 记录。

## Biomedical inputs

- 优先引用已有样本表，明确观测单位、独立生物学重复和 donor/sample/library/cell 等实际关系；按需说明配对、时间与批次。不要把同一个体的多个细胞、文库或访视当成独立个体。
- 使用输入前说明数值含义与处理状态：按 assay 核实物种、标识符/参考版本、单位、counts/normalized/log-transformed、实际 assay/layer 和关键处理。未知信息明确待核实，不从文件名猜测。
- 在 join、分组和比较的位置检查 ID 对齐、映射基数、样本丢失及各组独立单位数量。说明写入现有 BRIEF/RESULT 或引用数据说明，不重复维护样本注册系统。

## Superpowers

- You may use superpowers, but do not write any spec or plan.

## Research workflow

- 以 `Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test` 组织科研分析。
- 根 `CURRENT_HANDOFF.md` 是 project router；优先读取当前上下文，必要时定向查找相关数据和代码，并补充有效入口。
- `QUESTIONS.md` 只保存索引；BRIEF 是事前设计的事实源，RESULT 是事后证据与推断的事实源，Handoff 只引用而不复制。
- 保留 null、negative、contradictory 与 inconclusive evidence；technical validation、scientific support、Human approval 和 implementation reuse 不相互替代。
- 用户已明确请求的项目内、非覆盖、可恢复写入无需二次确认；mutating script 仍默认 dry-run，覆盖、删除、Git mutation 和外部写入必须获得明确授权。
- exploratory 不以设计审批为启动条件；confirmatory 需已审核的事前设计，不能把看过结果后的选择冒充事前决定。
- 具体分析脚本可使用已安装的 `scripting-style` Skill；未安装时遵循以上分析原则即可。Pixi 环境创建、迁移、审查或诊断使用 `pixi-environment-builder` Skill，项目只允许根级 Pixi workspace。
