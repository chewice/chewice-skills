# zotero-livecite

## 用途

通过 Zotero MCP 检索、核对和管理 DOI/PMID 文献；需要 Word 稿时，将明确的文献标记建成可 Refresh 的 `ADDIN ZOTERO_ITEM` 引用和 `ADDIN ZOTERO_BIBL` 文献表。正文引用必须是真实动态字段，不能用普通文本编号或静态参考文献段落代替。

| 请求 | 路线与结果 |
|---|---|
| 检索、入藏、建 collection、核对条目 | 路线 L：交付 selection JSON 和库操作结果，不启动 Word |
| 构建或刷新 Word 引用 | 先 L 再 W：先准备候选稿与审计，获 live 授权后刷新、验证并交付 DOCX |
| EndNote 文献库或原有 EndNote 字段迁移 | 改用 [endnote-zotero](../endnote-zotero/README.md) |

## 运行必需依赖

| 使用范围 | 必需依赖或输入 |
|---|---|
| 加载与文献检索 | 可加载 [SKILL.md](SKILL.md) 的 Agent、可用的 Zotero MCP connector、明确的目标库身份与 DOI/PMID |
| MCP 本地读取与 Refresh 可见性检查 | Zotero 桌面端运行且 Local API 位于 `127.0.0.1:23119`；Word 工作期间只运行一个 Zotero 实例 |
| MCP 入藏或 collection 写入 | hybrid 模式，配置 `ZOTERO_LIBRARY_ID`、`ZOTERO_API_KEY` 及库类型；API key 具备对应读写权限。只读检索不要求写权限 |
| 路线 W 随附 Python helper | 可用的 Python 与外部 `zotero_mcp` 包，且包内确实包含 `word_citations` 模块；本 skill 不包含该包源码和锁定环境 |
| 当前 `candidate-build` | 源 `.docx`、目标 CSL、独立 run root、task id、已闭合的 selection JSON；配置个人库 `ZOTERO_LIBRARY_ID` 和可读该库的 Web API 凭据。脚本会联网读回条目与 CSL JSON，候选构建本身不写库、不启动 Word |
| Refresh 与 UI evidence | Windows、PowerShell、Microsoft Word 桌面版、可用的 Zotero Word 插件；PowerShell 使用的 Python 也必须能导入上述外部包 |
| 维护本 skill 的结构校验 | Python 3；[verify_skill.py](scripts/verify_skill.py) 仅用标准库 |

安装 skill 不等于安装外部包、MCP connector 或 Word 插件。包版本和间接依赖以实际 `zotero_mcp` 环境定义为准，不能假设任意同名发行版都有 `word_citations`。可在将执行 helper 的 Python 环境中只读检查：

```bash
python3 -c "import zotero_mcp; print(zotero_mcp.__file__)"
python3 -m zotero_mcp.word_citations.refresh --help
```

Windows 中相应使用该环境的 `python` 或完整解释器路径。若包已有源码，可按 [运行说明](references/live-run-recipe.md) 使用其环境或配置 `PYTHONPATH`；缺包时先说明需要安装什么，再准备环境。凭据配置与 connector 重启见 [zotero-mcp-configuration.md](references/zotero-mcp-configuration.md)，不要把 API key 放进对话或仓库。

## 如何使用

将本目录作为 skill 加载后，以自然语言提供任务、文献标识符和目标库。只读管库示例：

> 使用 $zotero-livecite，在我的 Zotero 库中核对这组 DOI，列出候选条目并生成 selection JSON。只读，不建 collection、不新增条目。

构建 Word 候选稿示例：

> 使用 $zotero-livecite，把这份 DOCX 中的 DOI 标记建成 Zotero 动态引用，采用我指定的 CSL。使用已核对的 selection JSON，在独立目录输出候选稿与静态审计；先不启动 Word。

1. 按 [路线 L](references/mcp-library.md) 确认 library，为每个标识符选定唯一 item key；歧义先交人工核对。建 collection、加入条目和新建文献需要对应的事先授权。
2. 输出 `zotero-item-selection.json`；只要管库时到此结束。
3. 若需 Word，按 [路线 W](references/live-run-recipe.md) 使用 [run_live_workflow.py](scripts/run_live_workflow.py) 的 `candidate-build`，核验候选稿、manifest 和 Refresh 前审计。
4. 用户授权本次 Word/Refresh 后，冻结授权并按 [live-refresh-protocol.md](references/live-refresh-protocol.md) 执行一次 Refresh；再完成刷新后审计、获准的 UI evidence 与 finalize。

**当前 helper 的范围限制：** `run_live_workflow.py` 的候选构建读取 selection 中的 `doi` 并按 DOI 解析；它不是任意 PMID-only 输入的一键转换入口。PMID 可以用于路线 L 的检索与身份核对；仅有 PMID 的 Word 任务须先核对可用的构建实现，不要伪造 DOI 或声称此 helper 已支持。所谓候选阶段“离线”指不启动 Word、不执行 Refresh，当前 helper 仍需 Web API 只读访问。

从本 skill 目录运行下面命令可检查结构：

```bash
python3 scripts/verify_skill.py .
```

这是维护检查，不代表 Zotero 接通、字段成功构建或 Word Refresh 成功；普通转换和管库任务不需要跑外部包的测试套件。当前验证器尚不能解析本技能折叠写法的 `description`，会报 `frontmatter must contain only name and description`；这是已知的结构检查限制，不能据此判断 Word 转换结果。

## 交付与边界

默认使用用户日常 Zotero 库；仅用户明确要求时才配置 [隔离 profile](references/zotero-profiles.md)。默认只做离线与 MCP 只读；写库、Word/Refresh、一次性 UI 检查分别需要该类操作的事先授权，不自动 merge/delete 条目。

原稿只读，所有候选和结果写到新路径。路线 L 交付 selection JSON、选用 item key 和是否写库的说明；路线 W 最终交付目录只含完成版 DOCX 与原稿副本，中间产物留在 run root。缺 live 授权时交付候选与审计，并说明尚未刷新。恢复见 [recovery-and-rollback.md](references/recovery-and-rollback.md)。
