# zotero-livecite

把 Word 正文引用建成 **Zotero live citation**（`ZOTERO_ITEM` / `ZOTERO_BIBL` 字段），并用 Zotero MCP 检索、入藏、建 collection。禁止把引用编号或作者年份当普通文本写入 DOCX。

EndNote 迁库请用 `endnote-zotero`。

## 安装

把本目录安装为 Codex / Cursor skill。执行面是外部环境中的 `zotero_mcp`：

```text
python -c "import zotero_mcp; print(zotero_mcp.__file__)"
```

## 入口

- MCP 管库：`references/mcp-library.md`
- 离线字段构建：`scripts/run_live_workflow.py`
- 已授权 Refresh：`scripts/refresh_word_zotero.ps1`
- 结构校验：`python scripts/verify_skill.py`
