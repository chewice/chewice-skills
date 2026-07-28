---
name: research-project-os
description: Govern research projects with durable Agent context, evidence/status rules, Git provenance, root-level Pixi, readable narrative exploration, reviewed archives, publication pipelines, and reviewable Notion payloads. Use for project initialization or adoption, exploratory task organization, result promotion, resumable handoffs, audits, publication preparation, or portfolio synchronization. Do not use as the primary workflow for dependency solving, data acquisition, scientific analysis, literature retrieval, or figure export; govern their durable outputs.
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

Use `inspect` for unknown state, `init` for an empty directory, `adopt` for an
existing project, `start` to resume, `close` for handoffs, `audit` for
governance, and `sync-export`/`sync-audit` for local Notion payloads.

## Work safely

Run every mutation without `--apply` first. Apply only after review and
authorization. `adopt` preserves existing paths and recommends missing profile
directories. Use `--overwrite` only for reviewed control-file replacement and
`--init-git` only when requested.

Never stage, commit, push, solve environments, or write to Notion implicitly.

Choose `generic-analysis`, `bioinformatics`, `literature-review`, or
`software-development`.

## Govern analysis stages

For analysis profiles, state the question, method, expected outputs, and stop
condition; create files or compute only after human approval. Use
`explore-create` for one self-contained task named
`P<order>-<core>-<short-english-summary>`, such as
`P0-QC-low-quality-cells-removed`.

Treat explore code as an executable lab notebook: organize it top-to-bottom
with explicit intermediates and nearby observations. Give every script a short
Chinese outline and matching numbered Chinese section/cell headings; split by
meaningful workflow steps, not fixed line counts. Keep one-off logic inline and
tolerate duplication. Avoid generic helpers, classes, config layers, and
cross-file abstractions until logic stabilizes.

Keep scripts, derived data, figures, and the narrative `README.md` inside the
task. After human review, use `archive-promote` for an immutable snapshot and
verify hashes before `pipeline-create`. Refactor approved logic into modular,
tested pipeline code independent of `explore/` and `archive/`, retaining
Chinese outlines per file. Run
`pipeline-release` after publication review. Archive or release status never
implies scientific verification.

## Govern sessions

Load the nearest `AGENTS.md`, manifest, handoff, required context, relevant
evidence, and Git state. Define one minimum task and interpretation boundary.
Register validated outputs and decisions; close with the next minimum action.

Write project explanations in Chinese by default. Keep paths, keys, IDs,
statuses, commands, code symbols, and machine-parsed headings unchanged.

For Pixi, keep one root manifest and tracked lock; ignore root `.pixi/`. Use
features, environments, namespaced tasks, and `task.cwd` for child work.
`audit` fails on nested workspaces, locks, or `.pixi/`; no command consolidates
them.

## Load details only when needed

- Read [governance.md](references/governance.md) for context, statuses, language,
  and the Pixi policy.
- Read [analysis_lifecycle.md](references/analysis_lifecycle.md) before creating,
  promoting, or publishing analysis tasks.
- Read [evidence.md](references/evidence.md) before promoting evidence.
- Read [migration_policy.md](references/migration_policy.md) before adoption.
- Read [notion_git_contract.md](references/notion_git_contract.md) before an
  authorized Notion application.

Release `0.4.2` retains manifest and payload schema `0.3.0`.
