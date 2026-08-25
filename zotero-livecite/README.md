# zotero-livecite

Word 正文必须是 Zotero live field；文献用 Zotero MCP 检索、入藏、建 collection。禁止把引用编号当普通文本写入 DOCX。

- 只要管库：走路线 L，不启动 Word。
- 要改 Word：先 L 再路线 W。
- EndNote 迁库用 `endnote-zotero`。

## 安装

把本目录安装为 Codex / Cursor skill。若当前仓库就是本 Skill，工作目录即 `SKILL_DIR`。

```text
python -c "import zotero_mcp; print(zotero_mcp.__file__)"
```

## 入口

- 路线 L：`references/mcp-library.md`
- 路线 W：`scripts/run_live_workflow.py`、`references/live-run-recipe.md`
- 已授权 Refresh：`scripts/refresh_word_zotero.ps1`
- 结构校验：`python scripts/verify_skill.py`
