# Governance

Project files are durable memory; Agents are temporary executors.

Load the nearest `AGENTS.md`, manifest, current handoff, manifest-required
context, task-relevant evidence, and Git state. Do not load every report or
archived handoff.

Use these states without collapsing them:

| Object | States |
| --- | --- |
| Project | `proposed`, `active`, `on_hold`, `completed`, `archived` |
| Task | `backlog`, `ready`, `in_progress`, `blocked`, `done`, `cancelled` |
| Analysis | `draft`, `exploratory`, `candidate`, `verified`, `stable`, `legacy`, `deprecated`, `rejected` |
| Evidence | `observed`, `candidate`, `verified`, `invalidated` |
| Decision | `proposed`, `approved`, `rejected`, `superseded` |

Execution is not validation. Human review grants `stable` and `approved`.

For analysis profiles, keep artifact stages distinct from these states:
`explore/` contains approved-to-run tasks, `archive/` contains immutable
human-reviewed snapshots, and `pipeline/` contains the independent release
workflow. Historical explore tasks may coexist, but only one may remain
unarchived and uncancelled. `QUESTIONS.md` is a human-owned, Agent-read-only
research agenda; operational uncertainties stay in `open_questions.md`.
Promotion does not itself grant `verified` evidence or `stable` analysis.

Use Chinese for human-facing project narrative. Preserve commands, paths,
keys, IDs, state tokens, code, and parsed headings. Existing repository rules
take precedence.

## Pixi

Default policy:

```yaml
governance:
  pixi:
    policy: root_workspace
    allow_nested_package_manifests: true
```

Allow exactly one root `pixi.toml` with `[workspace]` or root `pyproject.toml`
with `[tool.pixi.workspace]`. Commit root `pixi.lock`; ignore root `.pixi/`,
which may be absent after clone.

Group environments by dependency compatibility and reproducibility boundary,
not folders. Use root features, environments, `<component>:<task>` names, and
`task.cwd`.

Nested workspace manifests, locks, and `.pixi/` are errors. Package-only
`[package]` or `[tool.pixi.package]` manifests follow
`allow_nested_package_manifests`; they never receive local locks or `.pixi/`.
`inspect` reports only. `audit` provides evidence and migration advice.
`init`/`adopt` never move, delete, merge, or solve environments.
