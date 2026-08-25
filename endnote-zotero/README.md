# endnote-zotero

把 EndNote 文献迁入隔离 Zotero 以便管理。若 Word 稿含 EndNote 动态字段，再迁成 Zotero live field。默认离线；没有 100% 人工批准不导入主库、不写 Word 字段。

DOI/PMID 正文 live field 与 MCP 日常管库请用 `zotero-livecite`。

## 安装

把本目录安装为 Codex / Cursor skill。主流程是 `references/endnote-migration.md`。

## 入口

- 管库导入与 Word 迁移：`references/endnote-migration.md`
- 隔离 profile：`references/zotero-profiles.md`
- 已授权 Refresh：`scripts/refresh_word_zotero.ps1`
- 结构校验：`python scripts/verify_skill.py`
