---
name: research-project-os
description: Govern research projects with durable Agent context, evidence/status rules, Git provenance, root-level Pixi, readable narrative exploration, reviewed archives, publication pipelines, and reviewable Notion payloads. Use for project initialization or adoption, exploratory task organization, result promotion, resumable handoffs, audits, publication preparation, or portfolio synchronization. Do not use as the primary workflow for dependency solving, data acquisition, scientific analysis, literature retrieval, or figure export; govern their durable outputs.
---

# Research Project OS

## Run the CLI

Resolve the installed skill symlink and use its root Pixi workspace:

```bash
SKILL_ROOT="$(readlink -f "${CODEX_HOME:-$HOME/.codex}/skills/research-project-os")"
SKILL_WORKSPACE="$(dirname "$SKILL_ROOT")"
pixi run --locked --manifest-path "$SKILL_WORKSPACE/pixi.toml" \
  python "$SKILL_ROOT/scripts/research_project_os.py" --help
```

Use `inspect` for unknown state; `init` or `adopt` to govern; `start`, `close`,
and `audit` for sessions; and `sync-export`/`sync-audit` for Notion payloads.

## Work safely

Run mutations without `--apply` first, then apply only after authorization.
`adopt` preserves paths. Use `--overwrite` and `--init-git` only when requested.

Never stage, commit, push, solve environments, or write to Notion implicitly.

Choose `generic-analysis`, `bioinformatics`, `literature-review`, or
`software-development`.

## Govern analysis stages

For analysis profiles, state the question, method, expected outputs, and stop
condition. Treat root `QUESTIONS.md` as the human-owned research agenda: read it,
never edit it unless explicitly asked, and address only its one `Current
question`. Discuss while `Human decision` is `discuss`; create files or compute
only after it becomes `approved_to_run` and the human explicitly agrees. Use
`explore-create` with the current `Q-` ID for one self-contained task named
`P<order>-<core>-<short-english-summary>`, such as
`P0-QC-low-quality-cells-removed`.

Treat explore code as an executable lab notebook with visible intermediates and
nearby observations. Give every script a short Chinese outline with numbered
Chinese headings, split by workflow steps. Keep one-off logic inline; avoid
generic helpers, classes, config layers, and cross-file abstractions until stable.

Keep scripts, derived data, figures, and `README.md` inside the task. Permit only
one unarchived, uncancelled task. Report its answer and limitations, then stop;
do not analyze queued questions. After human review, use `archive-promote`, then
verify hashes before `pipeline-create`. Refactor approved logic into tested,
independent pipeline code with Chinese outlines. Run `pipeline-release` after
publication review. Lifecycle status never implies scientific verification.

## Govern sessions

Load the nearest `AGENTS.md`, manifest, `QUESTIONS.md`, handoff, required
context, relevant evidence, and Git state. Define one minimum task and boundary.
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

Release `0.5.0` retains manifest and payload schema `0.3.0`.
