# Advisor Detective

## 用途

对 Finder 已发现、由用户明确选择的导师—项目组合做背景调查。仅研究选定维度，复用已有证据，区分官方事实、具名亲历、匿名线索、信息冲突和访问失败，并记录仍需核实的问题。

## 运行必需依赖

- 可读写项目文件、检索/阅读公开网页的 Agent，以及网络访问。
- [Advisor Finder](../advisor-finder/README.md) 的真实候选和共享 JSON 记录；有效的已确认导师—项目 ID 与调查维度。没有候选时应先完成 Finder。
- 完整技能集合中的 [advisor-pipeline](../advisor-pipeline/README.md)；其脚本负责项目迁移、确认菜单、确认记录和报告生成。
- [Pixi 环境](../../pixi.toml) 中 Node.js `>=22.13,<23`；默认 `linux-64`，Windows 使用 WSL。HTML/Excel 导出无需额外 Excel 库。
- **仅社区资料同步时**：Python `>=3.11,<3.13`（已在 Pixi manifest），并需 `pdftotext`（Poppler）或 Python 包 `pypdf` 才能完成 PDF 文本抽取。两种抽取器均未声明在当前 manifest 中；缺失时先说明再配置，不把无法搜索记为“未发现”。

仅查公开资料不需要社区缓存、PDF 抽取器或社区账号；宿主浏览器工具按页面需要使用。

## 如何使用

在已完成 Finder 的申请项目中调用：

```text
$advisor-detective 请展示当前候选与调查维度菜单，
我会选择具体导师—项目组合，重点核实研究主线、训练资源和博士资助。
```

Agent 展示包含稳定 ID 的菜单，由用户选择导师和维度并确认。若已存在有效确认且请求为继续调查，则复用该记录。医学默认只查公开资料；只有另行明确允许社区资料后，才进入社区下载和解析。

社区同步的脚本入口是 [sync_community_knowledge.py](scripts/sync_community_knowledge.py)，仅在确认范围和社区授权齐备后，由 Agent 按 [社区来源说明](references/community-sources.md) 调用。

结果更新共享导师和证据 JSON，重建 `outputs/{研究方向}-导师调研.html`，补充 `advisor_detective_YYYYMMDD.xlsx` 与简短状态记录。每个选定维度都应有结果或明确缺口；匿名线索不自动变成事实或扣分依据。完整流程见 [SKILL.md](SKILL.md)。
