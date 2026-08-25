---
name: endnote-zotero
description: 把 EndNote 文献迁入隔离 Zotero 以便在 Zotero 中管理；若源是 Microsoft Word DOCX 中的 EndNote 动态引用，再迁到可 Refresh 的 Zotero CSL ADDIN 字段。当用户要求 EndNote 库或 XML 导入 Zotero、cited-only 或指定导出范围、隔离 profile、身份映射与人工批准、结构一致性验收、Refresh 授权、恢复或 rollback 时使用。未经另行明确授权不得启动 Word、运行 Refresh 或写入日常主库。没有 100% 人工批准不得写 Zotero Word 字段。不用于 DOI/PMID 标记构建或 MCP 日常管库（改用 zotero-livecite）、已转纯文本后仍要伪造 Word 字段、普通格式咨询，或仅仅安装插件。
---

# EndNote to Zotero

主能力：把 EndNote 文献迁入隔离 Zotero，供后续在 Zotero 中管理。有 Word 稿且含 EndNote 动态字段时，再把「正文引用—文献表」迁成 `ZOTERO_ITEM` / `ZOTERO_BIBL` live field。本 Skill **没有** `zotero_mcp.word_citations` 构建入口；缺通用脚本时停在可审计的人工/半自动步骤，不要用搜索替换伪造 Zotero 字段。

用户只要管库、不要改 Word：完成导入与批准后停止，不要为了交差启动 Word。

## Safety boundary

默认只做离线和静态工作。除非用户**另行明确授权**当前这一次 live 集成，否则不要：

- 启动 Microsoft Word 或创建 Word COM 自动化；
- 运行 `scripts/refresh_word_zotero.ps1`；
- 调用 `ZoteroRefresh` 或其他 Zotero Word 宏；
- 把 EndNote All References 未经批准倒进日常主库；
- 访问除用户明确批准的只读检查 `http://127.0.0.1:23119` 以外的 Zotero Local API；
- 覆盖源 DOCX、EndNote 库、完整 XML、映射表、审计或 finalization 记录。

原始 DOCX、EndNote 库、完整 XML 和 Zotero 日常主库一律只读保留。任何自动化结果都输出为新文件。

## 三个对象

| 对象 | 含义 | 迁移要求 |
|---|---|---|
| 文献身份 | DOI、PMID、ISBN、题名、作者、年份等指向的真实文献 | 同一篇文献处理后仍必须是同一身份 |
| 正文引用 | 文献在正文中的一次或多次出现，是 Word 动态字段 | 出现位置、组合关系和显示结果必须保持 |
| 文献表 | 由全部正文引用按当前 CSL 样式算出的动态结果 | 必须由 Zotero 生成，不能用普通文本伪造 |

「引用字段数」≥「唯一文献数」。已经执行「转换为纯文本」或「移除字段代码」的文档不适用。

## Required inputs

在需要它们的阶段之前落实，缺则不要推断：

1. 从 EndNote 导出的结构化 XML（或用户指定的导出文件）；
2. 隔离 Zotero profile 及其独立数据目录；
3. 隔离工作目录与稳定 task id；
4. 是否只授权离线/静态工作，以及是否允许向隔离 profile 导入；
5. 源 `.docx` 与目标 CSL（仅当还要迁 Word 字段时）；
6. 原 EndNote 库只读路径（用于回滚和补充核对）；
7. Refresh 与交付的明确目标路径（若 Word 迁移在范围内）。

原 EndNote 输出样式可选，只用于比较格式，不用于确定文献身份。

## 发现执行面

```text
SKILL_DIR=<this-skill-root>
```

本树不包含 `zotero_mcp` 源码。阶段细节一律读 `references/endnote-migration.md`。隔离 profile 读 `references/zotero-profiles.md`。冻结产物规则读 `references/contracts.md`。用户授权 live 之后先读 `references/live-refresh-protocol.md`。hybrid 写入失败时读 `references/zotero-mcp-configuration.md`。

## Workflow

### 1. 无变更 preflight

确认目标 Zotero profile 与数据目录已隔离、未登录日常主库同步账号、Word 当前不会连到错误实例。`blocked` 则停止；`manual_review` 则说明未决条件。不得创建会覆盖原稿的目录，也不得连接 Word。

### 2. 确定迁入范围

稿件驱动：用 OOXML/ZIP 解析 EndNote 字段，按引用身份提取 cited-only 子集。管库驱动：以用户批准的导出范围为准。两种情况都导入隔离 profile，不覆盖日常主库。见 `references/endnote-migration.md` 阶段 1–3。

### 3. 身份匹配与人工批准门

匹配优先级：DOI → PMID → ISBN → 规范化题名+年份 → 作者/卷期页码辅助核对。结果至少分为精确、候选、缺失、重复、歧义。不要用最高相似度自动替代人工判断。

生成 Word 候选或向隔离库导入之前，映射必须满足：每篇源文献对应且仅对应一个目标条目；没有缺失、重复或未解释的歧义；稳定标识符一致；无标识符条目已核对题名、年份和作者；人工明确批准继续。没有 100% 人工批准，不进入导入执行或字段写入。用户只要管库时，批准后停止并交付导入清单。

### 4. 按完整字段块写候选（仅 Word 迁移）

以完整字段结构把 EndNote 引用替换为含稳定 Zotero URI 的 `ZOTERO_ITEM` 字段，保持原位置、多文献组合、前后标点和空格、正文可见文本、表格/脚注等容器中的字段边界。禁止只改上标数字或搜索替换显示文本。

若还没有通用脚本完成这一步，停在「已批准映射 + 未写字段的 candidate 计划」，列出还缺的实现，不要伪造看起来像 Zotero 的文档。

结构一致性目标：目标 Zotero 引用字段数＝源 EndNote 引用出现次数；唯一 Zotero 条目数＝人工批准映射数；Zotero 文献表字段恰好为 1；EndNote 正文引用和文献表字段均为 0；字段起止标记平衡。

### 5. 授权 Refresh，默认不执行

用户未另行授权 live 时，结束为 offline-blocked。若 live 已授权，先完整阅读 `references/live-refresh-protocol.md`，再按 `references/endnote-migration.md` 阶段 7：关闭修订、只打开候选稿、确认正确 profile、Refresh、删除旧 EndNote 文献表、Add/Edit Bibliography、再次 Refresh、另存为新候选。

### 6. 证据、finalize、恢复

不要合成成功报告。UI evidence 必须来自分开的、已取消的一次性检查。Finalize 仅在所需产物核验通过后一次性冻结。Recovery 只走到仍能核验的最高阶段；rollback 是复制到新路径的提案。见 `references/recovery-and-rollback.md`。

## Execution autonomy

- **无需确认**：读取、扫描、cited-only 规划、只读核对、映射表起草、离线审计包。
- **必须停下等人**：映射表未 100% 批准；Word 连到错误 Zotero profile；修订处于开启状态；登录/许可对话框。
- **每一类 live 集成需要一次事先、有范围的确认**：(1) 向隔离 profile 导入已批准子集（不得写入日常主库、不得 merge/delete 主库条目）；(2) 启动 Word 并 Refresh（仅 Word 迁移）；(3) 已取消的一次性对话框检查。
- standing authorization 下每个 distinct attempt 最多跑一次；从不重跑同一份授权。

## Dependencies

live 前说明：目标隔离 Zotero profile 单独运行，Local API 在 `127.0.0.1:23119`；不要同时运行多个实例。Microsoft Word 仅 Refresh 和 UI-evidence 需要。隔离操作见 `references/zotero-profiles.md`。

## Scripts

- `scripts/refresh_word_zotero.ps1` — 一次性 live Refresh（仅授权下执行）。
- `scripts/validate_word_zotero_ui.ps1` — 已取消的一次性对话框 evidence。
- `scripts/verify_skill.py` — 对本树做离线结构校验。

本 Skill **没有** `run_live_workflow.py`。不得从其他 skill 目录调用 DOI 构建脚本。

## Final delivery

交付视请求而定。只要管库：交付导入清单、批准表、隔离 profile 身份说明（不暴露个人路径或账号），不强制交 DOCX。若迁了 Word：交付目录只含**恰好两个文件**——引用完成版 DOCX 和用户原始 DOCX 的副本。命名和目标目录由用户决定。审计包留在工作目录，除非用户明确要求一并交付。

## Verification

文档迁移 run **不**跑外部包的 pytest。仅当用户明确要求改本 Skill 时运行 `scripts/verify_skill.py`。

## Output contract

报告：已完成阶段；源保护状态；映射批准比例；产物路径和关键 SHA-256；结构一致性计数；任何 blocked 或 manual-review；是否执行了 Word、`ZoteroRefresh`、Zotero Local API 或 Zotero 写入。

默认离线 run 必须明确写：**Word not launched; Refresh wrapper not executed; Zotero not modified.**

离线摘要模板：`assets/templates/offline-run-summary.md`。

## Additional resources

- `references/endnote-migration.md` — 管库导入、阶段 1–7、失败模式、验收与成果包
- `references/contracts.md` — 冻结产物规则
- `references/live-refresh-protocol.md` — 已授权 Refresh
- `references/recovery-and-rollback.md` — 恢复与 rollback 提案
- `references/zotero-profiles.md` — 隔离 profile
- `references/zotero-mcp-configuration.md` — hybrid mode（若使用写入工具）
- `evals/trigger-cases.json`、`evals/task-cases.json`
