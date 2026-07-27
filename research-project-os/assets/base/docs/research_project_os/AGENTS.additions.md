# Suggested AGENTS.md Additions

人工审阅后，将下列适用规则合并到现有 `AGENTS.md`：

- 项目说明默认使用中文；稳定的 engineering terms、machine-readable contract
  和文件名保持英文。
- session start 时读取 `project_manifest.yaml` 和 `CURRENT_HANDOFF.md`。
- You may use superpowers, but do not write any spec or plan.
- 保留 evidence boundary 和 status transition。
- Pixi 只使用根 workspace；环境按依赖兼容性和复现边界划分。
- write 与 overwrite 必须使用显式 flags。
- 未经用户授权，不得 commit、push 或写入 Notion。
