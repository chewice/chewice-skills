# endnote-zotero

## 用途

把 EndNote 文献迁入隔离 Zotero，供后续管理；若 Word 稿仍保留 EndNote 动态字段，再准备迁为可由 Zotero Refresh 更新的引用和文献表。支持按稿件提取 cited-only 子集、逐项文献身份匹配、人工批准、结构审计与恢复。

只迁文献库时不必启动 Word。已经转为纯文本的引用不能按原 EndNote 字段迁移；DOI/PMID 正文标记构建和日常 MCP 管库使用 [zotero-livecite](../zotero-livecite/README.md)。

## 运行必需依赖

| 使用范围 | 必需依赖或输入 |
|---|---|
| 离线准备、范围和身份核对 | 可加载 [SKILL.md](SKILL.md) 且能读写文件的 Agent；EndNote 结构化 XML 或明确指定的导出文件、原库只读路径、独立工作目录与 task id |
| 从 EndNote 导出 | 能打开原库的 EndNote 环境；已有完整结构化导出时，后续静态工作不要求启动 EndNote |
| 导入文献管理 | Zotero 桌面端、独立 profile **及独立数据目录**、批准的导入范围与映射表；不得混入日常主库或自动同步日常账号 |
| Word 字段迁移 | 保留 EndNote 动态字段的源 `.docx`、目标 CSL 样式，以及可核验的完整字段迁移实现；本 skill 未提供通用迁移 builder |
| 随附 Refresh / UI 脚本 | Windows、PowerShell、Microsoft Word 桌面版与可用的 Zotero Word 插件；目标 Zotero profile 单独运行，Local API 位于 `127.0.0.1:23119` |
| Refresh 前授权校验 | 上述 PowerShell 脚本还调用 Python 中的 `zotero_mcp.word_citations.refresh`；兼容的外部 `zotero_mcp` 包必须可导入，本目录不包含它的源码 |
| 采用 MCP 写入路径时 | 可用的 Zotero MCP connector；hybrid 模式的 `ZOTERO_LIBRARY_ID`、`ZOTERO_API_KEY` 等配置及相应权限，见 [配置说明](references/zotero-mcp-configuration.md)。手工向隔离 profile 导入 XML 不以 MCP/API key 为前提 |
| 维护本 skill 的结构校验 | Python 3；[verify_skill.py](scripts/verify_skill.py) 仅用标准库，不需要 Word、Zotero 或外部包 |

外部包的具体版本和间接依赖以实际包的环境定义为准，本 skill 没有提供锁定环境。安装 skill 不等于安装 Zotero、Word 插件或 `zotero_mcp`。静态读取和审计无需启动 Word；使用本地 API、写 Zotero 或 live 刷新须满足 [SKILL.md](SKILL.md) 中对应的授权范围。

## 如何使用

将本目录作为 skill 加载后，提供导出文件、原库只读位置、工作目录、目标隔离 profile 和迁移范围。例如：

> 使用 $endnote-zotero，检查这份 EndNote XML 和原库，只准备迁入隔离 Zotero 的清单与文献身份映射，等待我逐项批准；这次不改 Word。

如需同时迁 Word 字段，再给出源 DOCX 和目标 CSL：

> 使用 $endnote-zotero，从这份保留 EndNote 动态字段的 DOCX 提取 cited-only 文献。保留原稿和完整 XML，先完成身份映射与静态审计，列出迁移候选稿所需条件。

1. 按 [迁移流程](references/endnote-migration.md) 只读检查来源，确定 cited-only 或用户批准的导出范围。
2. 按 [profile 说明](references/zotero-profiles.md) 确认隔离环境，形成逐项映射、缺失与歧义清单。按照技能入口的批准门，未获 100% 人工批准不进入导入执行或字段写入。
3. 在获准范围内向隔离 profile 导入并核对条目。仅管库的请求交付导入清单、批准表与隔离库身份说明，到此结束。
4. 若需 Word，先核验完整字段迁移实现，再生成新候选稿；没有实现则停在已批准映射和候选计划，不以普通文本编号冒充 Zotero 字段。
5. 用户另行授权本次 Word/Refresh 与 UI 检查后，才按 [live-refresh-protocol.md](references/live-refresh-protocol.md) 执行、审计并交付。

本树没有 `run_live_workflow.py`，不能从 DOI/PMID skill 借用 builder 来冒充 EndNote 字段迁移。随附 [refresh_word_zotero.ps1](scripts/refresh_word_zotero.ps1) 和 [validate_word_zotero_ui.ps1](scripts/validate_word_zotero_ui.ps1) 只服务已满足前置合同的 live 步骤。

维护本 skill 时可从本目录运行离线结构检查：

```bash
python3 scripts/verify_skill.py .
```

该检查不导入文献、不启动 Word，也不能证明实际迁移成功。

## 交付与边界

原 DOCX、EndNote 库、完整 XML 与日常 Zotero 主库保留不覆盖。只迁库时交付清单、批准表和身份说明；迁 Word 时交付目录只含完成版 DOCX 与原稿副本，中间映射、候选和审计留在工作目录。恢复与回滚按 [recovery-and-rollback.md](references/recovery-and-rollback.md) 处理。

默认仅离线/静态工作；向隔离 profile 导入、启动 Word/Refresh 和一次性 UI 检查均需各自的事先授权。报告应明确已完成阶段、批准比例、未决问题，以及是否实际启动 Word、运行 Refresh、访问 Local API 或写 Zotero。
