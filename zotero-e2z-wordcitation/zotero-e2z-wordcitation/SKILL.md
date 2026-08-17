---
name: zotero-e2z-wordcitation
description: Build, migrate, audit, authorize, recover, or finalize Zotero CSL citation and bibliography ADDIN fields in Microsoft Word DOCX files. Use for DOI/PMID marker conversion to Zotero CSL fields, EndNote-to-Zotero CSL field migration, isolated Zotero profiles, identity mapping with human approval, static OOXML audits, Refresh authorization, UI-evidence contracts, run recovery, or rollback; also use when extending the same auditable workflow so another citation-manager source still lands on Zotero CSL fields. Never perform live Word/Zotero integration without separate explicit authorization.
---

# Zotero E2Z Word Citation

Zotero 在 Word 里不同于静态文献表或 EndNote Output Style 的特性，是用 **CSL** 把「文献身份—正文引用—文献表」写成可 Refresh 的 `ZOTERO_ITEM` / `ZOTERO_BIBL` ADDIN 字段。来源可以是 DOI/PMID 标记或 EndNote 字段，目标都落到这套 CSL 字段上。可靠方案始终使用隔离环境、逐项身份映射、人工批准门、原生插件刷新和结构化验收，并保留未修改的原稿。

当前有两条可执行轨道，共用同一套对象模型和门控；新增来源或目标管理器时只加 adapter，不改核心原则。

| 轨道 | 来源 | 目标 | 实现状态 |
|---|---|---|---|
| A 标记构建 | DOI、DOI URL、裸 DOI、`PMID: 12345678` | Zotero CSL 字段 | 由 `zotero_mcp.word_citations` 执行 |
| B EndNote 迁移 | EndNote 动态引用/文献表字段 | Zotero CSL 字段 | 流程已固化；按 `references/endnote-migration.md` 执行，缺脚本时停在可审计的人工/半自动步骤 |
| 后续扩展 | 其他引用管理器、字段修复、样式复刻 | 仍必须落到 Zotero CSL 字段 | 只新增 `references/` adapter，沿用本文件的对象、隔离、门控和交付规则 |

## Safety boundary

默认只做离线和静态工作。

除非用户**另行明确授权**当前这一次 live 集成，否则不要：

- 启动 Microsoft Word 或创建 Word COM 自动化；
- 运行 `scripts/refresh_word_zotero.ps1`；
- 调用 `ZoteroRefresh` 或其他 Zotero Word 宏；
- 写入 Zotero 文献库或 staging collection；
- 访问除用户明确批准的只读检查 `http://127.0.0.1:23119` 以外的 Zotero Local API；
- 覆盖源 DOCX、冻结 manifest、审计、授权、UI-evidence、报告或 finalization 记录。

授权创建或编辑实现文件，不等于授权运行 Word 或 Zotero。没有 live 授权时，停在离线门，并准确说明尚未执行的 live 动作。

原始 DOCX、EndNote 库、完整 XML 和 Zotero 日常主库一律只读保留。任何自动化结果都输出为新文件。

## 三个对象

| 对象 | 含义 | 迁移/构建要求 |
|---|---|---|
| 文献身份 | DOI、PMID、ISBN、题名、作者、年份等指向的真实文献 | 同一篇文献处理后仍必须是同一身份 |
| 正文引用 | 文献在正文中的一次或多次出现，是 Word 动态字段 | 出现位置、组合关系和显示结果必须保持 |
| 文献表 | 由全部正文引用按当前 CSL 样式算出的动态结果 | 必须由目标管理器生成，不能用普通文本伪造 |

同一篇文献可以出现多次。「引用字段数」≥「唯一文献数」，两者不能混为一个指标。已经执行「转换为纯文本」或「移除字段代码」的文档不适用本 Skill；字段一旦解除，通常只能重新识别并插入引用。

## Applicability

在请求涉及以下任一情况时使用：

- 扫描 Word OOXML 中的 DOI / DOI URL / 裸 DOI / `PMID: 12345678` 标记；
- 推断 citation cluster，并保留重复出现；
- 把 EndNote 动态引用迁移为 Zotero 动态引用；
- 规划或 mock Zotero 条目解析与 staging；
- 在隔离 Zotero profile 中为单篇稿件建立 cited-only 快照；
- 按 DOI/PMID/ISBN/题名+年份做身份匹配，并设置人工批准门；
- 构造或审计 DOCX 中的动态引用/文献表字段；
- 冻结 citation manifest 与 acceptance counts；
- 审查 digest-bound 的 Refresh 授权合同；
- 持久化已授权的一次性 UI evidence；
- 结束一次 run、恢复状态、或生成非破坏性 rollback proposal；
- 为实现、文档或测试通用 zotero-e2z-wordcitation 包，而不导入个案历史脚本；
- 把同一套可审计流程扩展到新的来源/目标管理器。

不要用于普通引用格式咨询、手工文献表散文、与 Word 字段无关的 Zotero 库清理，或仅仅安装 Zotero/Word/EndNote。

## Required inputs

在需要它们的阶段之前落实：

1. 源 `.docx` 路径；
2. 目标 CSL style id 或 `.csl` 路径；
3. 隔离 runs root 与稳定 task id；
4. 请求的轨道/阶段，以及是否只授权离线/静态工作；
5. Zotero 库身份与 collection（仅当 staging 或可见性在范围内）；
6. Refresh 与 finalization 的明确目标/报告路径；
7. 冻结 manifest 中的 expected acceptance counts。

轨道 B 额外需要：原 EndNote 库（只读）、从 EndNote 导出的结构化 XML、隔离 Zotero profile 及其独立数据目录。原 EndNote 输出样式可选，只用于比较格式，不用于确定文献身份。

缺路径、身份、计数或授权时不要推断。只能继续那些能被现有产物证明的阶段。

## Workflow

### 1. 发现实现并冻结边界

定位仓库，不要假定机器特定路径。确认它提供：

- 包 `zotero_mcp.word_citations`（轨道 A 的执行面）；
- 入口 `zotero-word-citations` 或模块 CLI；
- 所请求阶段的离线测试；
- 仅作为可检查产物的 PowerShell wrapper。

改代码或定位阶段归属时读 `references/implementation-map.md`。组装、加载或校验持久化 JSON 时读 `references/contracts.md`。端到端复现 live run 时读 `references/live-run-recipe.md`。Zotero MCP 处于 local-only 或写工具失败时读 `references/zotero-mcp-configuration.md`。轨道 B 或涉及 Windows profile 时读 `references/endnote-migration.md` 和 `references/zotero-profiles.md`。

### 2. 无变更 preflight

扫描或创建 run 之前先做只读 preflight。将其状态当作门：

- `blocked`：停止并报告失败检查；
- `manual_review`：说明未决条件，不要自动前进；
- 安全/已批准的只读结果：继续所请求的离线阶段。

Preflight 不得创建 run 目录、复制源文件、连接 Word，或写入 Zotero。轨道 B 还要确认：目标 Zotero profile 与数据目录已隔离、未登录日常主库同步账号、Word 当前不会连到错误实例。

### 3. 静态扫描 DOCX

用 OOXML/ZIP 解析，不用 Word 自动化。保留源文件大小和 SHA-256；若提供了期望 digest 则核验。

轨道 A：只识别受支持的显式标识符。普通数字永远不是 PMID。检查所有相关 Word story，暴露畸形字段、修订、静态参考文献和不支持的放置位置，然后确定性推断 cluster。任何模糊边界或不支持的 story 都是 manual-review，不是猜测许可。

轨道 B：解析 EndNote 正文引用字段与出现次数、唯一文献身份、EndNote 文献表字段、现有修订/批注/表格/图形/分页，以及正文可见文本与引用显示文本。基线要能回答「迁移后正文或版式有没有变」，而不仅是文件能打开。细节见 `references/endnote-migration.md`。

### 4. 在任何写入前规划身份解析

先对只读网关解析标识符。缺失或歧义时 fail closed。

轨道 A：若需要新条目，先做 staging 计划与精确授权；默认离线边界下不要执行。保持 collection 身份、库身份、请求标识符、计划 item key 和出现次数稳定。校验使用 mock 或合成网关。

轨道 B：不要把 EndNote All References 全库导入隔离环境。保留完整 XML 作为来源，按 DOCX 引用身份提取 cited-only 子集，确认覆盖每一篇唯一引用文献，再导入隔离 profile。匹配优先级：DOI → PMID → ISBN → 规范化题名+年份 → 作者/卷期页码辅助核对。结果至少分为精确、候选、缺失、重复、歧义。不要用最高相似度自动替代人工判断。

### 5. 人工批准门（轨道 B 强制；轨道 A 在歧义时同样适用）

生成候选 DOCX 之前，映射必须满足：

- 每篇源文献对应且仅对应一个目标条目；
- 没有缺失、重复或未解释的歧义；
- DOI 等稳定标识符一致；无标识符条目已核对题名、年份和作者；
- 人工明确批准继续，并确认不覆盖原稿。

没有 100% 人工批准，不进入字段写入阶段。自动匹配分数只能排序，不能代替批准。

### 6. 在隔离 run 中构建候选

不要原地编辑源文件。创建或核验隔离 run 布局，复制到 candidate 路径，并在每次变换中保护 source/candidate digest。

以完整字段结构为单位写入合法的复杂 `ADDIN ZOTERO_ITEM CSL_CITATION` 字段，以及一个动态 `ADDIN ZOTERO_BIBL` 字段，并带上所需 document preferences 与 OPC relationships。保持原引用位置、多文献组合、前后标点和空格、正文可见文本、表格/脚注等容器中的字段边界。

禁止只改上标数字、搜索替换引文显示文本，或在字段起止标记之间做普通文字编辑。不要导入历史项目中的个案脚本。

### 7. 冻结 manifest 与 Refresh 前审计

manifest 只能由已接受的上游扫描、cluster、条目可见性/staging 和 candidate 事实组装。用 canonical JSON 加 SHA-256 一次性冻结。

运行静态 DOCX 审计，并将其观察与 manifest acceptance counts 比较。失败的审计阻断授权。已有字节仅在完全相同时可接受；冲突字节或 digest 漂移必须 fail closed。

轨道 B 的结构一致性目标：目标 Zotero 引用字段数＝源 EndNote 引用出现次数；唯一 Zotero 条目数＝人工批准映射数；Zotero 文献表字段恰好为 1；EndNote 正文引用和文献表字段均为 0；字段起止标记平衡。

### 8. 授权 Refresh，默认不执行

把授权绑定到精确的 manifest 文件/内容 digest、静态审计、受保护源、candidate、destination、report、diagnostic path、attempt id 和 acceptance counts。任何 live 操作前立即重核所有路径和 digest。

可选的 Zotero Local API 检查只读，且限于 IPv4 loopback 端口 `23119`。拒绝其他 host、端口、凭据、查询或 fragment。

用户未另行授权 live 集成时，在此结束为 offline-blocked，并说明还需要哪些明确批准。若 live 已授权，先完整阅读 `references/live-refresh-protocol.md`。轨道 B 的 Word/Zotero 本机步骤见 `references/endnote-migration.md` 阶段 7：关闭修订、只打开候选稿、确认正确 profile、Refresh、删除旧 EndNote 文献表、Add/Edit Bibliography、再次 Refresh、另存为新候选。

### 9. 审计 Refresh 后证据

在外部已授权的 Refresh 产生 destination 和 report 之后，加载并核验这些产物；不要合成一份成功报告。对冻结 manifest 做 Refresh 后静态审计，并绑定到 destination 字节。

引用和文献表 UI evidence 必须来自分开的、已取消的一次性检查。每条严格 evidence 记录一次性写入。要求 destination、source、working-copy digest 不变，以及 before/open/after 字段快照稳定。

### 10. 一次性 finalize

仅在全部所需产物存在且核验通过后组装 finalization：manifest、Refresh 授权、Refresh 报告、Refresh 后静态审计、引用 UI evidence、文献表 UI evidence、受保护源、最终 destination 与 acceptance counts。

一次性冻结 finalization 记录。不要把目录名、成功消息或未绑定截图当作证明。

### 11. 非破坏性恢复或提出 rollback

用 run journal 和产物谱系，只恢复到所需文件、哈希、parent 和状态迁移仍能核验的最高阶段。状态变更前获取 run lock，并使用 stale-lock 恢复规则；不要打断 live lock。

Rollback 是提案，不是自动删除或覆盖。生成只复制到新 destination 的步骤，并保留每一个 source、candidate、diagnostic、audit 和 journal 产物。

读 `references/recovery-and-rollback.md` 了解迁移与谱系细节。

## Execution autonomy and confirmation policy

2026-08-15 live test 表明，每一步都要求人工确认是不必要的。采用：

- **无需确认**：读取、扫描、clustering、规划、Zotero 只读/可见性检查、manifest/audit/authorization 冻结、候选构建、Refresh 后审计、finalization，以及任何离线或 mock 校验。Agent 应自主执行，直到交出最终交付物或碰到硬阻断。
- **每一类 live 集成需要一次事先、有范围的确认**：
  1. 写入 Zotero（创建 task collection、加入 collection membership；未经另行批准不得 merge/delete 条目）；
  2. 启动 Word 并运行 Refresh wrapper，恰好一次 `ZoteroRefresh`；
  3. 启动 Word 做两次已取消的一次性对话框检查（`ZoteroAddEditCitation`、`ZoteroAddEditBibliography`）。
- 用户可对特定任务授予 **standing authorization**（例如一直做到成功）。在此授权下，每一类 live 每个 distinct attempt 最多跑一次；失败则停止该类、在离线侧修根因（带回归测试）、创建新的 attempt id 和路径后再继续。从不重跑同一份授权。
- 即使有 standing authorization，遇到真正的人机条件仍必须停下：Zotero 登录/验证对话框、Word 许可/首次运行对话框、冻结选择规则无法解决的重复条目歧义、或任何参数化重试都修不好的结构阻断。轨道 B 还包括：映射表未 100% 批准、Word 连到错误 Zotero profile、修订处于开启状态。

## Dependencies and setup（live run 前告知用户）

在任何触及 live Word/Zotero 的阶段之前，说明这些依赖并协助用户满足：

1. **Zotero desktop** 正在运行，Local API 在 `127.0.0.1:23119`。轨道 B 必须是目标隔离 profile，且不要同时运行多个实例。
2. **Microsoft Word** 已安装（仅 Refresh 和 UI-evidence 需要 COM；scan/build/audit 是纯 OOXML）。
3. **`zotero_mcp` 包** 可被 Python import。定位它（已安装包、仓库 `src`、或 `.venv`）并告诉用户将如何调用。缺失则给出精确的安装/定位步骤，不要猜测。
4. **zotero-mcp hybrid mode**：`ZOTERO_LIBRARY_ID` + `ZOTERO_API_KEY` 写在 `~/.config/zotero-mcp/config.json` 的 `client_env` 下（见 `references/zotero-mcp-configuration.md`），然后重启 connector。若写入失败并提示 "local-only mode"，不要重试；回头检查这一步。
5. Live 执行前展示一次 import 检查（`python -c "import zotero_mcp"`）并确认 Local API 端口。
6. 轨道 B：隔离 profile 与独立数据目录已核对；完整操作见 `references/zotero-profiles.md`。

依赖检查失败或用户问如何配置时，主动指向 `references/zotero-mcp-configuration.md`、`references/live-run-recipe.md`，以及轨道 B 的 `references/endnote-migration.md`。

## Scripts and reproducibility

可复用脚本都在本 Skill 的 `scripts/` 下：

- `scripts/run_live_workflow.py` — 参数化离线阶段（`candidate-build`、`authorize`、`post-refresh-audit`、`finalize`）。
- `scripts/refresh_word_zotero.ps1` — 一次性 live Word/Zotero Refresh wrapper（仅在授权下执行）。
- `scripts/validate_word_zotero_ui.ps1` — 已取消的一次性对话框 evidence。
- `scripts/verify_skill.py` — 对本树做离线结构校验。

这些脚本是通用的：接受 `--run-root`、`--task-id`、`--source`、`--selection`、`--style-id`，并从 zotero-mcp 配置读取 `ZOTERO_LIBRARY_ID`/`ZOTERO_API_KEY`。不得包含机器特定路径或用户身份。

## Final delivery

- 交付目录只含**恰好两个文件**：finalization 绑定的引用完成版 DOCX，以及用户原始 DOCX 的副本。用户原始文件本身永不移动或修改。
- **命名和目标目录由用户决定。** Agent 提议名称（例如 `<original-stem>_引文完成版.docx`）和交付目录，等用户确认后再复制。不要擅自发明最终名称或路径。
- 测试/中间产物（candidate、audit、report、UI working copy、diagnostic、manifest、run state）永不进入交付目录。run root 下的证据默认保留；删除需要用户明确决定。
- 轨道 B 的完整成果包还包含：cited-only 元数据、自动匹配候选表、人工批准表、字段结构/正文一致性/视觉 QA 报告、简短操作说明（注明 Zotero profile、CSL 样式和刷新时间，不暴露个人路径或账号）。详见 `references/endnote-migration.md`。
- 交付前核验两个文件的 SHA-256 是否与 finalization 记录一致。若用户此后在 Word 中打开并保存了完成版，记录中的哈希会不同；此时交付用户确认的版本，记下实际哈希，并注明 finalization 记录适用于当时审计过的字节。
- 交付本身不再跑测试、审计或 live 集成。

## Verification

实现或 Skill 变更时，只用离线/静态校验：

1. 所触及阶段的 focused tests；
2. 完整 `tests/word_citations` suite；
3. 相关 Ruff 检查；
4. 不运行 wrapper 的 PowerShell AST parse；
5. protected-baseline hash test；
6. 可行时带显式 exit-code 传播的全项目测试套件；
7. `scripts/verify_skill.py` 校验本 Skill 树；
8. 附带的 `skill-creator/scripts/quick_validate.py` 与打包工具。

精确类别和停止条件见 `references/verification-matrix.md`。pytest 输出含失败、timeout 或 `KeyboardInterrupt` 时，即使 detached host 报告 exit code 0，也不得报告通过。

## Output contract

报告：

- 请求的轨道和已完成阶段；
- 源与 destination 的保护状态；
- 已创建或核验的产物，含路径和关键 SHA-256；
- acceptance counts 与门结果；
- 测试/lint/静态检查的精确通过/失败计数；
- 任何 blocked 或 manual-review 条件；
- 是否执行了 Word、`ZoteroRefresh`、Zotero Local API 或 Zotero 写入。

默认离线 run 必须明确写：**Word not launched; Refresh wrapper not executed; Zotero not modified.**

离线摘要模板：`assets/templates/offline-run-summary.md`。
