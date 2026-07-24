# Research Project OS Skill Architecture

## Objective

提供可复用的 project-governance Skill：外部化 Agent memory，区分 exploration
与 verified evidence，保留 provenance，并准备可审阅的 Git/Notion
synchronization，同时不与单一科研领域耦合。

## Components

```text
SKILL.md
  → mode selection and Agent behavior
deterministic CLI
  → inspect/init/adopt/start/close/audit/sync-export/sync-audit
base assets
  → project control-plane templates
profiles
  → init directory plans and domain-specific interpretation boundaries;
    adopt treats directories as recommendations only
references
  → governance, evidence, verification, migration, and sync contracts
```

## Mode contracts

| Mode | Mutation | Purpose |
| --- | --- | --- |
| `inspect` | none | 检测项目状态，并推荐 `init` 或 `adopt` |
| `init` | explicit `--apply` | 在空项目中创建 governance files |
| `adopt` | explicit `--apply` | 在不重构目录的前提下补充缺失 governance files |
| `start` | none | 加载 manifest、handoff、tasks、questions 和 Git state |
| `close` | explicit `--apply` | 归档 handoff、更新当前状态并导出 Notion JSON |
| `audit` | none | 验证 structure、statuses、references、Git visibility 和 queues |
| `sync-export` | explicit `--apply` | 导出 hierarchy-aware immutable payload |
| `sync-audit` | none | 检查 schema、source hashes、queue state 和 application receipt |

## Authority model

- Git 对 code、environments、complete reports、evidence details、已回写的
  decisions 和完整 handoff 具有权威性。
- Notion 用于 cross-project views、task priority、session summaries、
  evidence indexes 和 human approvals。
- CLI 只写 JSON payload。Notion MCP layer 必须按 `ProjectYYYY`、共享 control
  databases 和 append-only ordinal contract 执行 read-before-write，遇到
  conflict 停止，并验证 read-back。

## Safety model

- 所有 mutation 默认 dry-run。
- 除非显式提供 `--overwrite`，否则跳过现有文件。
- `adopt` 不重命名或移动项目内容。
- `adopt` 只创建 control layer；缺失的 profile 业务目录仅作为建议。
- adoption 期间不替换现有 `AGENTS.md`、`README.md` 和 `.gitignore`；merge
  suggestions 单独写入。
- Git initialization 由 `--init-git` 单独控制。
- 所有 mode 都不会 stage、commit、push 或发送 Notion request。

## Scope boundary

Research Project OS 不实现 environment solving、code refactoring、data
acquisition、QC/statistical analysis、literature retrieval 或 figure export。
专门 workflow 的 durable outputs 只在影响 provenance、evidence、decision 或
handoff 时进入 control layer。
