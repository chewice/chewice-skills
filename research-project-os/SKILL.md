---
name: research-project-os
description: Govern research projects with durable Agent context, evidence/status rules, Git provenance, root-level Pixi, reviewable Notion payloads, and a human-gated explore-to-archive-to-pipeline analysis lifecycle. Use for project initialization or adoption, exploratory task organization, reviewed result promotion, publication pipeline preparation, resumable handoffs, audits, or portfolio synchronization. Do not use as the primary workflow for dependency solving, data acquisition, scientific analysis, literature retrieval, or figure export; govern their durable outputs.
---

# Research Project OS

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

Choose `generic-analysis`, `bioinformatics`, `literature-review`, or
`software-development`. Profiles govern `init`; `adopt` only recommends missing
business directories and preserves the existing structure.

## Govern analysis stages

For `generic-analysis` and `bioinformatics`, discuss the direction before
creating files or computing. State the question, method, expected outputs, and
stop condition; continue only after explicit human approval. Then use
`explore-create` to scaffold one self-contained task named
`P<order>-<core>-<short-english-summary>`, such as
`P0-QC-low-quality-cells-removed`.

Keep task scripts, derived data, and figures inside its explore subdirectory.
After human result review, use `archive-promote` to preserve the explore source
and create an immutable versioned snapshot. Verify its hashes before
`pipeline-create`. Build pipeline implementations independently of both
`explore/` and `archive/`; use archive only as provenance. Run
`pipeline-release` after publication review and validation. Never treat archive
promotion or release readiness as scientific verification.

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
- Read [analysis_lifecycle.md](references/analysis_lifecycle.md) before creating,
  promoting, or publishing analysis tasks.
- Read [evidence.md](references/evidence.md) before promoting evidence.
- Read [migration_policy.md](references/migration_policy.md) before adoption.
- Read [notion_git_contract.md](references/notion_git_contract.md) before an
  authorized Notion application.

Release `0.4.0` retains manifest and payload schema `0.3.0`.
