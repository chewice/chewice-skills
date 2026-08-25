---
name: zotero-livecite
description: 在 Microsoft Word 中把 DOI、DOI URL、裸 DOI 或 PMID: 12345678 建成可 Refresh 的 Zotero live citation（ADDIN ZOTERO_ITEM / ZOTERO_BIBL），并用 Zotero MCP 检索、建 collection、按 DOI/PMID 入藏和核对可见性。当用户要求插入或刷新 Word 动态引用、Zotero 文献表、把 DOI 加进 Zotero、为稿件建 collection、静态审计、Refresh 授权或 UI-evidence 时使用。正文引用不得写成普通文本编号或作者年份。未经另行明确授权不得启动 Word、运行 Refresh 或写入 Zotero。不用于 EndNote 迁库或 EndNote 字段迁移（改用 endnote-zotero）、普通格式咨询、把 [1] 当纯文本写入 DOCX、全库去重清 tag，或仅仅安装插件。
---

# Zotero Live Cite

正文引用必须是 Word 的 Zotero **live field**；文献身份用 **Zotero MCP** 检索、入藏、建 collection。执行面是可 import 的 `zotero_mcp`（含 `word_citations`），不是本树里的 `src/`。

## 请求分流

先判定本次请求，不要把完整 Word 流水线套到只管库的任务上。

| 用户要 | 走 | 停点 |
|---|---|---|
| 检索、入藏、建 collection、核对 DOI/PMID | 路线 L | 交付 selection / 库操作结果；不启动 Word |
| 把标记建成 Word live field、审计、Refresh、交付 DOCX | 先 L 再路线 W | 无 live 授权则停在 candidate + 授权合同 |
| EndNote 迁库或 EndNote 动态字段 | 停止 | 改用 `endnote-zotero` |

## Live field 硬规则

禁止把 `[1]`、上标数字、作者年份或 Vancouver 编号作为普通文本写入 DOCX；禁止搜索替换引文显示文本；禁止用静态参考文献段落冒充 `ZOTERO_BIBL`。离线候选可以带占位显示，但仍必须是 `ADDIN ZOTERO_ITEM` / `ADDIN ZOTERO_BIBL`。最终样式由 Zotero Refresh 渲染。

已「转换为纯文本」或已移除字段代码的文档：只能重新识别标识符并插入 live field，不能在原编号上涂改。

## Safety boundary

默认只做离线和 MCP 只读。除非用户**另行明确授权**当前这一类 live 操作，否则不要：

- 启动 Microsoft Word 或创建 Word COM；
- 运行 `scripts/refresh_word_zotero.ps1` 或调用 `ZoteroRefresh`；
- 写入 Zotero（建 collection、加 membership、新建条目）；
- 访问除用户批准的只读 `http://127.0.0.1:23119` 以外的 Local API；
- 覆盖源 DOCX 或已冻结的 manifest / 审计 / 授权 / evidence。

授权改代码不等于授权跑 Word 或写库。原稿只读；结果一律写新文件。

## 三个对象

文献身份、正文 live field、动态文献表是三件事。「引用字段数」≥「唯一文献数」，不能混成一个指标。

## 发现执行面

```text
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/zotero-livecite"
```

若当前仓库就是本 Skill，则 `SKILL_DIR` 为本目录。用 `python -c "import zotero_mcp; print(zotero_mcp.__file__)"` 定位包；不要在本仓库搜 `src/zotero_mcp`。找不到则停，给出安装或 `PYTHONPATH=<zotero-mcp>/src`。

默认使用用户日常 Zotero 库（MCP + Local API）。只有用户明确要求隔离 staging 时才读 `references/zotero-profiles.md`。Word 工作期间只运行一个 Zotero 实例。

## 路线 L：MCP 管库

缺 DOI/PMID 或库身份时不要猜。细节与工具顺序见 `references/mcp-library.md`；hybrid 失败见 `references/zotero-mcp-configuration.md`。

1. 只读列出 library、切换、按 DOI/PMID 检索。
2. 每个标识符选定恰好一个 item key（读回验证，不从显示编号反推）。歧义则 manual-review。
3. 写入（建 collection、加 membership、新建条目）需要该类事先授权。不得 merge/delete。
4. 写出 `zotero-item-selection.json`。用户只要管库：到此交付并停止。

## 路线 W：Word live field

在 L 的 selection 已闭合之后才进入。缺源 `.docx`、CSL、runs root / task id 时不要推断。字段合同见 `references/contracts.md`；命令序列见 `references/live-run-recipe.md`。

1. 只读 preflight，再 OOXML 扫描。只认显式 DOI/PMID；普通数字不是 PMID。模糊 cluster 为 manual-review。
2. 运行 `scripts/run_live_workflow.py` 的 `candidate-build`：写入合法 ADDIN 字段，冻结 manifest 与 Refresh 前审计。失败则阻断。
3. `authorize` 冻结 digest-bound 授权。用户未授权 Word 时结束为 offline-blocked。
4. 已授权 live：先读 `references/live-refresh-protocol.md`，再跑 `scripts/refresh_word_zotero.ps1` 恰好一次。
5. `post-refresh-audit` → 两次已取消的 UI evidence → `finalize`。不要合成成功报告。
6. 恢复只走到仍能核验的最高阶段；rollback 只复制到新路径。见 `references/recovery-and-rollback.md`。

## Execution autonomy

- **无需确认**：只读、扫描、clustering、MCP 检索、规划、冻结 manifest/audit/authorization、候选构建、Refresh 后审计、finalize。
- **每类 live 事先确认一次**：(1) 写 Zotero；(2) Word + 一次 `ZoteroRefresh`；(3) 两次已取消对话框检查。
- standing authorization 下每个 distinct attempt 最多一次；失败则离线修根因并换新 attempt id。不重跑同一份授权。
- 登录/许可对话框或无法消歧的重复条目必须停下。

## Scripts

- `scripts/run_live_workflow.py` — `candidate-build`、`authorize`、`post-refresh-audit`、`finalize`
- `scripts/refresh_word_zotero.ps1` — 仅授权下的一次性 Refresh
- `scripts/validate_word_zotero_ui.ps1` — 已取消对话框 evidence
- `scripts/verify_skill.py` — 本树结构校验

参数来自 `--run-root`、`--task-id`、`--source`、`--selection`、`--style-id` 和 zotero-mcp 配置。不得写机器路径。

## Final delivery

- **路线 L**：selection JSON、选用的 item key、是否写过库。不交 DOCX。
- **路线 W**：交付目录只含完成版 DOCX 和原稿副本。名称与目录由用户确认后再复制。中间产物留在 run root。

## Verification

转换或管库 run **不**跑 pytest。仅当用户要改本 Skill 或 `word_citations` 包时才读 `references/verification-matrix.md` 并跑 `scripts/verify_skill.py`。

## Output contract

报告：路线 L/W、已完成阶段、保护状态、关键 SHA-256、acceptance counts、blocked/manual-review，以及是否执行 Word、`ZoteroRefresh`、Local API、Zotero 写入。

默认离线必须写：**Word not launched; Refresh wrapper not executed; Zotero not modified.**

模板：`assets/templates/offline-run-summary.md`。

## Additional resources

- `references/mcp-library.md` — 路线 L
- `references/live-run-recipe.md` — 路线 W 命令序列
- `references/live-refresh-protocol.md` — 已授权 Refresh
- `references/contracts.md` — 冻结 JSON
- `references/zotero-mcp-configuration.md` — hybrid mode
- `references/recovery-and-rollback.md` — 恢复
- `references/implementation-map.md`、`references/verification-matrix.md` — 仅改包/Skill 时
- `references/zotero-profiles.md` — 仅用户要求隔离库时
- `evals/trigger-cases.json`、`evals/task-cases.json`
