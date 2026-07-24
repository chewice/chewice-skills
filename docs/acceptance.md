# MVP Acceptance Criteria

- Skill release 为 `0.3.1`，manifest 与 Notion payload schema 保持 `0.3.0`。
- Skill metadata 通过 official quick validator。
- `inspect`、`init`、`adopt`、`start`、`close`、`audit`、`sync-export` 和
  `sync-audit` 提供 help。
- `init` 与 `adopt` 默认 dry-run，apply 后保持 idempotent。
- `adopt` 保留现有文件和目录名，只创建 control layer，不创建缺失的 profile
  业务目录。
- `inspect` 返回 bounded `project_inventory`，不递归扫描大型 data 或 artifact
  trees。
- `close` 归档上一份 handoff，并导出可审阅的 JSON payload。
- schema `0.3.0` payload 描述 `ProjectYYYY`、control、project、output 和
  append-only ordinal policy，并支持 application receipt read-back。
- 编号 allocator 对 malformed title、duplicate ordinal 和 duplicate stable
  ID fail closed；不复用 ordinal gaps。
- 生成项目包含 machine-readable manifest、current handoff、immutable
  archive path、status policy、decisions、questions、tasks、evidence
  registry 和 Notion queue directories。
- generic、bioinformatics、literature-review 和 software-development profiles
  为 `init` 生成不同目录计划；在 `adopt` 中仅提供未执行的目录建议。
- boundary evals 证明 environment solving、code organization、data acquisition、
  QC/statistical analysis、literature retrieval 和 figure export 不由本 Skill 接管。
- 生成的项目说明默认使用中文，同时保留稳定的 machine-readable contract
  为英文。
- Unit tests 与 smoke tests 通过 Pixi 在受支持 host platform 运行。
- 安装使用 `~/.agents/skills/` 下可发现的 symlink。
