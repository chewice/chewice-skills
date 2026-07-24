# Architecture

Research Project OS 由精简 Skill、确定性 CLI、control-layer templates、profiles
和按需 references 组成。

| Mode | Behavior |
| --- | --- |
| `inspect`, `start`, `audit`, `sync-audit` | 只读 |
| `init`, `adopt`, `close`, `sync-export` | 默认 dry-run，需 `--apply` |

`adopt` 保留现有布局并只添加 control layer。所有命令都不会自动 stage、
commit、push、求解环境或调用 Notion。

Git 保存 code、根级 environment lock、handoff 和 evidence；Notion payload
只承载经审阅的 portfolio navigation 与摘要。Pixi 使用单一根 workspace；
inspect/audit 只治理布局，不修改环境。

科研分析、数据获取、文献检索和图形导出由专门 workflow 执行，其 durable
outputs 仅在影响 provenance、decision 或 handoff 时登记。
