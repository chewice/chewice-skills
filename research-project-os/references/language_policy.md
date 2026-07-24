# Language Policy

## Default

项目说明和面向人的研究叙述默认使用中文。稳定的 engineering terms 和文件名保持
英文。

## Preserve stable contracts

以下内容保持英文或原始形式：

- 文件名、目录名、路径、命令、CLI flags 和环境变量；
- YAML/JSON keys、code identifiers、API/package names；
- object IDs、status/priority tokens 和 schema values；
- 被 CLI 解析的 Markdown headings 与 field labels；
- Git commit、accession、checksum 和外部系统中的稳定标识。

允许在中文说明中直接使用 `Git`、`Notion`、`Pixi`、`Research Project OS`、
`handoff`、`payload`、`audit`、`pseudobulk` 等稳定术语，避免为了形式统一而制造
不清晰的译名。

## Generate and adopt

- `init` 生成中文叙述和英文稳定 contract。
- `adopt` 不覆盖现有 `AGENTS.md`；把语言规则写入
  `docs/research_project_os/AGENTS.additions.md` 供人工合并。
- 如果现有仓库定义了更具体的语言规则，以现有仓库为准。

## Localize an adopted project

1. 保留 machine-parsed headings、field labels、keys 和 state tokens。
2. 翻译当前 handoff、register 内容、policy、project description 和 evidence
   narrative。
3. 不修改 `docs/handoffs/archive/` 中的历史 handoff。
4. 运行 project audit 和 tests，确认 parser 与 state validation 未受影响。
5. 如果 pending Notion payload 因 source hash 变化而 stale，删除旧的本地
   stale payload 并重新生成；不要原地编辑，也不要自动写入 Notion。
