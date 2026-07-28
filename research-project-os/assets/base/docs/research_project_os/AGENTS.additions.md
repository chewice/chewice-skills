# Suggested AGENTS.md Additions

人工审阅后，将下列适用规则合并到现有 `AGENTS.md`：

- 项目说明默认使用中文；稳定的 engineering terms、machine-readable contract
  和文件名保持英文。
- session start 时读取 `project_manifest.yaml` 和 `CURRENT_HANDOFF.md`。
- You may use superpowers, but do not write any spec or plan.
- 保留 evidence boundary 和 status transition。
- 对分析类 profile，先在聊天中确认方向，再创建
  `explore/P<order>-<core>-<short-english-summary>/` 或运行计算。
- explore task 的 scripts、derived data 和 figures 留在其 task subdir；经人工
  审核后冻结到不可覆盖的 `archive/<task>/vNNN/`。
- `pipeline/` 仅从获批 archive 整理，runtime 不依赖 explore 或 archive；
  archive/release 状态不自动证明 scientific validity。
- Pixi 只使用根 workspace；环境按依赖兼容性和复现边界划分。
- write 与 overwrite 必须使用显式 flags。
- 未经用户授权，不得 commit、push 或写入 Notion。
