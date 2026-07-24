---
name: research-project-os
description: Initialize, adopt, inspect, start, close, and audit research projects with durable Agent context, evidence/status governance, Git provenance, and reviewable multi-project Notion portfolio payloads. Use for research lifecycle control, session handoffs, evidence promotion, governance audits, or numbered ProjectYYYY portfolios. Do not use as the primary workflow for package solving, code organization, data acquisition, QC/statistical analysis, literature retrieval, or figure export; use a specialized workflow and register its outputs here only when lifecycle tracking is needed.
---

# Research Project OS

Externalize project memory and make every research iteration resumable,
reviewable, and evidence-aware.

## Keep execution separate

Own project context, object status, evidence boundaries, handoffs, Git
provenance, and review-first Notion synchronization. Do not absorb package
solving, code refactoring, data acquisition, scientific analysis, literature
retrieval, or figure-export recipes.

When a specialized workflow changes durable project state, register its
artifacts, validation, decisions, and next action through the existing control
layer. Specialized Skills remain optional and are never hard dependencies.

## Locate the CLI

Set the Skill and development workspace paths:

```bash
SKILL_ROOT="/path/to/installed/research-project-os"
SKILL_ROOT="$(cd "$SKILL_ROOT" && pwd -P)"
SKILL_WORKSPACE="$(dirname "$SKILL_ROOT")"
```

Run deterministic commands through the Skill's Pixi environment:

```bash
pixi run --locked --manifest-path "$SKILL_WORKSPACE/pixi.toml" \
  python "$SKILL_ROOT/scripts/research_project_os.py" --help
```

On Windows PowerShell, resolve the installed junction before locating the
workspace:

```powershell
$SkillEntry = "$env:USERPROFILE\.codex\skills\research-project-os"
$SkillItem = Get-Item -LiteralPath $SkillEntry
$SkillRoot = if ($SkillItem.Target) {
    [string]$SkillItem.Target
} else {
    $SkillItem.FullName
}
$SkillWorkspace = Split-Path -Parent $SkillRoot

pixi run --locked `
  --manifest-path (Join-Path $SkillWorkspace "pixi.toml") `
  python (Join-Path $SkillRoot "scripts\research_project_os.py") --help
```

## Select a mode

- Use `inspect` first when project state is unknown.
- Use `init` only for a new or empty directory.
- Use `adopt` for an existing project. Preserve its paths and files; create
  only the control layer, not missing profile directories.
- Use `start` to load the manifest, handoff, and Git state.
- Use `close` to archive the handoff and export a local Notion JSON payload.
- Use `audit` to validate the control layer and Git-visible sensitive files.
- Use `sync-export` to prepare a reviewed `project-adopt`, `milestone`, or
  `full-state` payload.
- Use `sync-audit` to reject stale or incomplete synchronization artifacts.

## Apply mutations safely

Treat every mutation as dry-run first:

```bash
python research_project_os.py adopt \
  --project /path/to/project \
  --profile bioinformatics
```

Review the displayed file plan, then repeat with `--apply` only when authorized.
Use `--overwrite` only for an explicitly reviewed control-file replacement.
Use `--init-git` separately when Git initialization is desired.

Never run `git add`, commit, push, or write to Notion automatically.

## Apply the project language policy

Write human-readable project explanations in Chinese by default. Preserve
stable engineering contracts in English, including paths, filenames, commands,
flags, configuration keys, object IDs, status tokens, code identifiers, and
machine-parsed Markdown headings or field labels.

Follow an existing repository language rule when it is more specific. During
adoption, preserve the existing `AGENTS.md` and place the proposed language
rule in the merge suggestions.

## Choose a profile

- `generic-analysis`: general quantitative or data analysis.
- `bioinformatics`: scientific Python/R, omics, and data-lineage-heavy work.
- `literature-review`: source retrieval and evidence synthesis.
- `software-development`: research software, libraries, CLIs, and pipelines.

For `init`, profiles add initial directories and interpretation boundaries. For
`adopt`, profile directories are recommendations only; existing paths remain
authoritative. Profiles do not change the core governance model.

## Run a session

Start:

```bash
python research_project_os.py start --project /path/to/project
```

Close in dry-run:

```bash
python research_project_os.py close \
  --project /path/to/project \
  --summary "说明本次 session outcome" \
  --completed "一项已完成内容" \
  --evidence "一项 evidence 或 validation reference" \
  --next-step "下一项 minimum action"
```

Apply only after reviewing the new handoff and payload paths.

## Organize a Notion portfolio

Use one append-only annual tree per adoption year:

```text
ProjectYYYY
├── 00｜Research OS Control
├── 01｜first_project
│   ├── 01｜项目纳入与治理基线
│   └── 02｜SES-YYYYMMDD-NNN：session summary
└── 02｜next_project
```

Keep shared Projects, Sessions, Tasks, Questions, Decisions, and Evidence
databases under `00｜Research OS Control`. Number only project adoption,
meaningful session close, and explicit milestone/full-state outputs. Never
renumber or reuse an ordinal.

The CLI never calls Notion. When the user explicitly authorizes application,
read [notion_git_contract.md](references/notion_git_contract.md), read current
direct children, validate stable IDs and ordinals, apply the reviewed payload,
then read back every affected page. Stop on any malformed title, duplicate ID,
duplicate ordinal, stale source hash, or remote disagreement.

## Load references as needed

- Read [governance_model.md](references/governance_model.md) for the complete
  project loop and control layers.
- Read [status_model.md](references/status_model.md) when changing object
  states.
- Read [evidence_model.md](references/evidence_model.md) and
  [verification_policy.md](references/verification_policy.md) before promoting
  a conclusion.
- Read [migration_policy.md](references/migration_policy.md) before adopting an
  existing project.
- Read [context_loading_policy.md](references/context_loading_policy.md) when
  starting a session or controlling context size.
- Read [language_policy.md](references/language_policy.md) before generating or
  localizing project documentation.
- Read [notion_git_contract.md](references/notion_git_contract.md) before adding
  MCP-based synchronization.

## Respect the MVP boundary

Release `0.3.1` keeps manifest and Notion payload schema `0.3.0`. The bundled
CLI does not call Notion or execute domain analysis. The project remains
exploratory until its own scientific verification gates are satisfied.
