# Zotero MCP 文献管理（本 Skill）

在把 DOI/PMID 写成 Word live field 之前或同时，用 **Zotero MCP** 管理条目、collection 和可见性。本文件不授权 Word COM 或 `ZoteroRefresh`。

## 何时读

- 按 DOI/PMID 检索或确认库中是否已有条目；
- 为当前稿件建 task collection 并加入 membership；
- 解析歧义条目、列出候选 item key；
- hybrid 写入失败或工具提示 local-only。

凭证与 hybrid mode 见 `references/zotero-mcp-configuration.md`。Word 字段合同见 `references/contracts.md`。

## 硬边界

- 正文引用只能落成 `ADDIN ZOTERO_ITEM` / `ADDIN ZOTERO_BIBL`。MCP 管库不能改成「把 [1] 或作者年份写成普通段落」。
- 默认只读：`zotero_list_libraries`、`zotero_switch_library`、检索、读条目、读 collection。
- 写入（建 collection、加 membership、新建条目）需要用户对**这一类**操作的事先授权。未经另行批准不得 merge/delete。
- item key 来自读回验证，不得猜测或从显示编号反推。

## 推荐顺序

1. 确认 connector 为 hybrid：`ZOTERO_LIBRARY_ID` + `ZOTERO_API_KEY`，然后重启 connector。
2. `zotero_list_libraries` → 记下个人 user ID。
3. `zotero_switch_library(library_id=<user ID>, library_type='user')`。
4. 对文档中每个不同 DOI/PMID：检索，记录全部候选 key，选定恰好一个。
5. 若 staging 已授权：`zotero_create_collection(name='<task collection>')`，把选定条目加入该 collection。
6. 写出 `zotero-item-selection.json`（schema 与 `references/live-run-recipe.md` 一致），再进入字段构建。

## 失败时

写入报 `Cannot perform write operations in local-only mode`：不要重试盲写。回头读 `references/zotero-mcp-configuration.md`，重启 connector 后再做一次只读探针。

EndNote 库迁入 Zotero 不在本文件范围。
