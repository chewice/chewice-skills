# Suggested AGENTS.md Additions

人工审阅后，将下列适用规则合并到现有 `AGENTS.md`：

- 项目说明默认使用中文；稳定的 engineering terms、machine-readable contract
  和文件名保持英文。
- session start 时读取 `project_manifest.yaml`、`CURRENT_HANDOFF.md` 和
  human-owned `QUESTIONS.md`；Agent 默认不得修改后者。
- You may use superpowers, but do not write any spec or plan.
- 保留 evidence boundary 和 status transition。
- 对分析类 profile，一次只讨论或执行 `QUESTIONS.md` 的唯一 current question；
  human 标记 `approved_to_run` 并明确同意后，才创建
  `explore/P<order>-<core>-<short-english-summary>/` 或运行计算。
- 一次最多有一个未归档、未取消的 explore task；报告当前答案和限制后停止，
  不提前分析候选问题，也不自行推进 `QUESTIONS.md`。
- explore task 的 scripts、derived data 和 figures 留在其 task subdir；经人工
  审核后冻结到不可覆盖的 `archive/<task>/vNNN/`。
- explore code 按实际执行顺序线性组织，保留 intermediate objects 和相邻
  observations；单次逻辑保持 inline，不要过早函数化或拆成跨文件 abstraction。
- 每个 explore 和 pipeline code file 使用文件顶部中文提纲及对应编号中文 section
  headings；按有意义的 workflow steps 切分，code identifiers 保持英文。
- 模块化、参数化和系统性 tests 留到 `pipeline/`；它仅从获批 archive 整理，
  runtime 不依赖 explore 或 archive。archive/release 状态不自动证明
  scientific validity。
- Pixi 只使用根 workspace；环境按依赖兼容性和复现边界划分。
- write 与 overwrite 必须使用显式 flags。
- 未经用户授权，不得 commit、push 或写入 Notion。
