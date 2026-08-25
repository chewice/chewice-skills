---
name: zotero-livecite
description: 把 Microsoft Word DOCX 中的 DOI、DOI URL、裸 DOI 或 PMID: 12345678 建成可 Refresh 的 Zotero live citation（ADDIN ZOTERO_ITEM / ZOTERO_BIBL），并用 Zotero MCP 检索、建 collection、按 DOI/PMID 入藏和核对可见性。当用户要求 Word 动态引用字段、Zotero 文献表、staging、静态审计、Refresh 授权、UI-evidence 或 MCP 管库时使用。正文引用不得写成普通文本编号或作者年份。未经另行明确授权不得启动 Word、运行 Refresh 或写入 Zotero。不用于 EndNote 迁库或 EndNote 字段迁移（改用 endnote-zotero）、普通格式咨询、把 [1] 当纯文本写入 DOCX，或仅仅安装插件。
---

# Zotero Live Cite

把正文里的显式 DOI/PMID 标记写成可 Refresh 的 Zotero **live citation**：复杂字段 `ADDIN ZOTERO_ITEM CSL_CITATION` 与动态 `ADDIN ZOTERO_BIBL`。文献身份用 **Zotero MCP** 检索、入藏、建 collection 并核对可见性。执行面是可 import 的 `zotero_mcp`（含 `word_citations`），不是本 Skill 树里的 `src/`。

## Live field 硬规则

正文引用必须是 Word 的 Zotero 字段，由 Zotero Refresh 生成显示文本。禁止：

- 把 `[1]`、上标数字、作者年份或 Vancouver 编号作为普通文本写入 DOCX；
- 搜索替换引文显示文本，或只改字段起止标记之间的可见文字；
- 用静态参考文献段落冒充 `ZOTERO_BIBL`。

离线候选可以写入合法字段结构加占位显示，但仍必须是 ADDIN 字段，不能是纯文本编号。Refresh 之后由 Zotero 渲染最终样式。

## Safety boundary

默认只做离线和静态工作。除非用户**另行明确授权**当前这一次 live 集成，否则不要：

- 启动 Microsoft Word 或创建 Word COM 自动化；
- 运行 `scripts/refresh_word_zotero.ps1`；
- 调用 `ZoteroRefresh` 或其他 Zotero Word 宏；
- 写入 Zotero 文献库或 staging collection；
- 访问除用户明确批准的只读检查 `http://127.0.0.1:23119` 以外的 Zotero Local API；
- 覆盖源 DOCX、冻结 manifest、审计、授权、UI-evidence、报告或 finalization 记录。

授权创建或编辑实现文件，不等于授权运行 Word 或 Zotero。没有 live 授权时，停在离线门，并准确说明尚未执行的 live 动作。原始 DOCX 只读保留；任何自动化结果都输出为新文件。

## 三个对象

| 对象 | 含义 | 要求 |
|---|---|---|
| 文献身份 | DOI、PMID 等指向的真实文献 | 同一篇文献处理后仍必须是同一身份 |
| 正文引用 | 文献在正文中的一次或多次出现 | 必须是 Zotero live field，不能是普通文本 |
| 文献表 | 由全部正文引用按当前 CSL 算出的动态结果 | 必须由 Zotero 生成，不能用普通文本伪造 |

「引用字段数」≥「唯一文献数」，两者不能混为一个指标。已「转换为纯文本」或已移除字段代码的文档不适用。

## Required inputs

在需要它们的阶段之前落实，缺则不要推断：

1. 源 `.docx` 路径；
2. 目标 CSL style id 或 `.csl` 路径；
3. 隔离 runs root 与稳定 task id；
4. 是否只授权离线/静态工作；
5. Zotero 库身份与 collection（仅当 staging 或可见性在范围内）；
6. Refresh 与 finalization 的明确目标/报告路径；
7. 冻结 manifest 中的 expected acceptance counts。

## 发现执行面

```text
SKILL_DIR=<this-skill-root>
```

用 `python -c "import zotero_mcp; print(zotero_mcp.__file__)"` 定位包。不要在本 Skill 仓库里搜索 `src/zotero_mcp`。找不到则停，给出安装或 `PYTHONPATH=<zotero-mcp>/src`，不要猜测路径。

确认包提供：`zotero_mcp` MCP 工具与 `zotero_mcp.word_citations`。MCP 管库读 `references/mcp-library.md`。改 word_citations 代码时读 `references/implementation-map.md`。组装 JSON 时读 `references/contracts.md`。端到端 live 序列读 `references/live-run-recipe.md`。写工具失败或 local-only 时读 `references/zotero-mcp-configuration.md`。隔离 profile 读 `references/zotero-profiles.md`。

## Workflow

### 1. 无变更 preflight

扫描或创建 run 之前先做只读 preflight。`blocked` 则停止；`manual_review` 则说明未决条件、不要自动前进。Preflight 不得创建 run 目录、复制源文件、连接 Word，或写入 Zotero。

### 2. 静态扫描 DOCX

用 OOXML/ZIP 解析，不用 Word 自动化。保留源文件大小和 SHA-256。只识别受支持的显式标识符；普通数字永远不是 PMID。检查所有相关 Word story，暴露畸形字段、修订、静态参考文献和不支持的放置位置，然后确定性推断 cluster。模糊边界或不支持的 story 都是 manual-review。

### 3. 用 Zotero MCP 规划身份并管库

先对只读网关或 MCP 检索解析标识符。缺失或歧义时 fail closed。默认只读；创建 collection、加入 membership 或新建条目需要该类 live 授权。细节见 `references/mcp-library.md`。保持 collection 身份、库身份、请求标识符、计划 item key 和出现次数稳定。歧义时走人工批准：每篇源文献对应且仅对应一个目标条目。未经另行批准不得 merge/delete。

### 4. 在隔离 run 中构建候选

不要原地编辑源文件。以完整字段结构写入合法的复杂 `ADDIN ZOTERO_ITEM CSL_CITATION` 字段，以及一个动态 `ADDIN ZOTERO_BIBL` 字段，并带上所需 document preferences 与 OPC relationships。禁止写入普通文本引用编号。

### 5. 冻结 manifest 与 Refresh 前审计

manifest 只能由已接受的上游扫描、cluster、条目可见性/staging 和 candidate 事实组装。用 canonical JSON 加 SHA-256 一次性冻结。失败的静态审计阻断授权。冲突字节或 digest 漂移必须 fail closed。

### 6. 授权 Refresh，默认不执行

把授权绑定到精确的 manifest digest、静态审计、受保护源、candidate、destination、report、diagnostic path、attempt id 和 acceptance counts。可选 Local API 检查只读，且限于 `http://127.0.0.1:23119`。用户未另行授权 live 时，结束为 offline-blocked。若 live 已授权，先完整阅读 `references/live-refresh-protocol.md`。

### 7. 审计 Refresh 后证据

加载外部已授权 Refresh 产生的 destination 和 report；不要合成成功报告。引用和文献表 UI evidence 必须来自分开的、已取消的一次性检查。

### 8. 一次性 finalize

仅在全部所需产物存在且核验通过后组装 finalization，一次性冻结。不要把目录名、成功消息或未绑定截图当作证明。

### 9. 非破坏性恢复或提出 rollback

只恢复到所需文件、哈希、parent 和状态迁移仍能核验的最高阶段。Rollback 是提案，不是自动删除或覆盖。细节见 `references/recovery-and-rollback.md`。

## Execution autonomy

- **无需确认**：读取、扫描、clustering、MCP 只读检索、规划、可见性检查、manifest/audit/authorization 冻结、候选构建、Refresh 后审计、finalization，以及任何离线或 mock 校验。自主执行直到交付或硬阻断。
- **每一类 live 集成需要一次事先、有范围的确认**：(1) 写入 Zotero（创建 task collection、加入 membership；未经另行批准不得 merge/delete）；(2) 启动 Word 并运行 Refresh wrapper，恰好一次 `ZoteroRefresh`；(3) 启动 Word 做两次已取消的一次性对话框检查。
- standing authorization 下，每一类 live 每个 distinct attempt 最多跑一次；失败则停止该类、离线修根因、换新 attempt id。从不重跑同一份授权。
- 遇到登录/许可对话框、冻结规则无法解决的重复条目歧义、或参数化重试修不好的结构阻断时必须停下。

## Dependencies

live 阶段前说明并协助满足：Zotero desktop 在 `127.0.0.1:23119`；Microsoft Word（仅 Refresh/UI-evidence）；`import zotero_mcp` 成功；Zotero MCP connector 可用且 hybrid mode 见 `references/zotero-mcp-configuration.md`。展示一次 import 检查并确认 Local API 端口。

## Scripts

- `scripts/run_live_workflow.py` — 离线阶段：`candidate-build`、`authorize`、`post-refresh-audit`、`finalize`。
- `scripts/refresh_word_zotero.ps1` — 一次性 live Refresh（仅授权下执行）。本 Skill 脚本是参数化入口；不要与 zotero-mcp 仓库里同名 wrapper 混用路径。
- `scripts/validate_word_zotero_ui.ps1` — 已取消的一次性对话框 evidence。
- `scripts/verify_skill.py` — 对本树做离线结构校验。

接受 `--run-root`、`--task-id`、`--source`、`--selection`、`--style-id`；从 zotero-mcp 配置读 `ZOTERO_LIBRARY_ID`/`ZOTERO_API_KEY`。不得包含机器特定路径。

## Final delivery

交付目录只含**恰好两个文件**：finalization 绑定的引用完成版 DOCX，以及用户原始 DOCX 的副本。命名和目标目录由用户决定；提议后等确认再复制。测试/中间产物永不进入交付目录。交付前核验两个文件的 SHA-256 是否与 finalization 记录一致。

## Verification

文档转换 run **不**跑 pytest、Ruff 或全项目套件。仅当用户明确要求改本 Skill 或 `word_citations` 包时，才读 `references/verification-matrix.md` 并运行 `scripts/verify_skill.py`。pytest 输出含失败、timeout 或 `KeyboardInterrupt` 时，即使 host 报告 exit 0，也不得报告通过。

## Output contract

报告：已完成阶段；源与 destination 保护状态；产物路径和关键 SHA-256；acceptance counts 与门结果；任何 blocked 或 manual-review；是否执行了 Word、`ZoteroRefresh`、Zotero Local API 或 Zotero 写入。

默认离线 run 必须明确写：**Word not launched; Refresh wrapper not executed; Zotero not modified.**

离线摘要模板：`assets/templates/offline-run-summary.md`。

## Additional resources

- `references/mcp-library.md` — Zotero MCP 检索、collection、入藏
- `references/contracts.md` — 冻结 JSON 合同
- `references/implementation-map.md` — 外部包模块地图
- `references/live-run-recipe.md` — 参数化 live 序列
- `references/live-refresh-protocol.md` — 已授权 Refresh
- `references/recovery-and-rollback.md` — 恢复与 rollback 提案
- `references/verification-matrix.md` — 仅 skill/包变更
- `references/zotero-mcp-configuration.md` — hybrid mode
- `references/zotero-profiles.md` — 隔离 profile
- `evals/trigger-cases.json`、`evals/task-cases.json`
