---
name: research-project-os
description: Initialize, adopt, inspect, start, close, and audit research projects with durable Agent context, evidence/status governance, Git provenance, root-level Pixi policy, and reviewable ProjectYYYY Notion payloads. Use for research lifecycle control, resumable handoffs, evidence promotion, governance audits, or portfolio synchronization. Do not use as the primary workflow for package solving, code refactoring, data acquisition, scientific analysis, literature retrieval, or figure export; register those workflows' durable outputs only when lifecycle tracking is needed.
---

# Research Project OS

Externalize project memory so research work is resumable, reviewable, and evidence-aware.

## Run the CLI

The install contract is a full repository workspace plus a discovery symlink to
`research-project-os/`. Resolve the link, then use the single root Pixi workspace:

```bash
SKILL_ROOT="$(readlink -f "${CODEX_HOME:-$HOME/.codex}/skills/research-project-os")"
SKILL_WORKSPACE="$(dirname "$SKILL_ROOT")"
pixi run --locked --manifest-path "$SKILL_WORKSPACE/pixi.toml" \
  python "$SKILL_ROOT/scripts/research_project_os.py" --help
```

Use `inspect` for unknown state; `init` only for an empty directory; `adopt` for
an existing project; `start` to resume; `close` to archive the handoff;
`audit` for governance; and `sync-export`/`sync-audit` for local Notion
payloads.

## Work safely

Run every mutation without `--apply` first. Review the plan, then apply only
when authorized. `adopt` preserves existing paths, `AGENTS.md`, README, data,
environment files, and `.gitignore`; profile directories remain suggestions.
Use `--overwrite` only for an explicitly reviewed control-file replacement and
`--init-git` only when requested.

Never stage, commit, push, solve environments, or write to Notion implicitly.
The CLI only creates local control files and reviewable JSON payloads.

Choose `generic-analysis`, `bioinformatics`, `literature-review`, or
`software-development`. Profiles define initial directories and interpretation
boundaries for `init`; during `adopt`, missing business directories are
recommendations only and existing project structure remains authoritative.

## Govern sessions

Load the nearest `AGENTS.md`, `project_manifest.yaml`, `CURRENT_HANDOFF.md`,
required context, relevant evidence, and Git state. Define one minimum task and
its interpretation boundary. Register validated outputs and decisions, then
close the session with the next minimum action.

Write project explanations in Chinese by default. Keep paths, keys, IDs,
statuses, commands, code symbols, and machine-parsed headings unchanged.

Projects using Pixi follow `root_workspace`: one root manifest and tracked
`pixi.lock`; root `.pixi/` is ignored and optional. Child work uses features,
environments, namespaced tasks, and `task.cwd`. `inspect` only reports;
`audit` fails on nested workspaces, locks, or `.pixi/`; `init` and `adopt`
never consolidate them.

## Load details only when needed

- Read [governance.md](references/governance.md) for context, statuses, language,
  and the Pixi policy.
- Read [evidence.md](references/evidence.md) before promoting evidence.
- Read [migration_policy.md](references/migration_policy.md) before adoption.
- Read [notion_git_contract.md](references/notion_git_contract.md) before an
  authorized Notion application.

Release `0.3.2` retains manifest and payload schema `0.3.0`.
