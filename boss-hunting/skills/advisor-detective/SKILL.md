---
name: advisor-detective
description: >
  Perform evidence-backed background research on user-selected academic
  advisors after Advisor Finder. Use when the user asks to investigate, compare,
  or backcheck specific advisors. Research only explicitly selected information
  sections, preserve exact advisor-program identities, optionally consult
  consented local community sources, and report supported findings, conflicts,
  risks, and information gaps without treating anonymous claims as facts.
---

# Advisor Detective

Investigate whether a shortlisted advisor is suitable for the user. Do not
repeat objective program research already completed by Advisor Finder.

## Required inputs

Read:

- `outputs/advisor_records.json`
- `outputs/program_records.json`
- `outputs/evidence.json`
- `project.json`

If the full skill set is present, read
`../advisor-pipeline/references/core-data-contract.md` before shared-record
writes and `../advisor-pipeline/references/investigation-contract.md` for the
confirmation/result contract. The menu script already owns the mode-specific
catalog: 11 generic sections, or the five medical modules A–E. During a
confirmed run, look up only the selected section IDs in
`references/investigation-sections.md`; do not load unselected section detail.
In medical mode read `../advisor-pipeline/references/medical-profile.md`, the
Global Core and selected-region entries in `medical-sources.md`, and
`browser-research-policy.md` (credential status words and provider fallback).
Public browser interaction does not authorize additional candidates or
sections. Medical projects never load or download community sources: none of
the five modules is community-relevant. Read `references/community-sources.md`
only for generic projects whose source policy permits it and where a
reputation-related section is selected with independent consent.

Require exact `investigation.confirmed.selectedAdvisorProgramIds` and
`investigation.confirmed.selectedSections` from `project.json`. The confirmed
revision and fingerprint must still match the current draft. Validate every ID
against the Finder output. A draft, count, advisor name alone, or Top N
instruction is not authorization to research.

## Direct invocation fallback

When the user invokes Advisor Detective directly, do not assume they know the
internal IDs or section names.

1. If Finder's structured outputs are missing or contain no real candidates,
   explain that Phase 1 is required and stop. Never substitute example data.
2. Run `node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD"`
   (or the equivalent `.claude/skills/` path). This initializes or safely
   migrates the current shared contract before selection without
   discarding or rewriting existing Finder outputs. Do not hand-compose the
   missing project files.
3. If the exact advisor or section selection is missing, run the same
   interactive selection gate defined in Advisor Pipeline. Render the menu with
   `node .agents/skills/advisor-pipeline/scripts/render_investigation_menu.mjs --root "$PWD"`
   and show its output verbatim — it already contains the numbered
   advisor-program rows with stable IDs, the ordered section catalog for the
   project's mode (11 generic sections or the five medical modules) with its
   defaults, and the Web-equivalent cost level. Then ask separately for
   community-source consent only when the source policy permits it, show a final summary, and wait for
   explicit confirmation.

   While selecting, read only `project.json`, `outputs/candidates.json`, and
   the dimension catalog. Do not open advisor records, evidence bundles,
   previous detective results, or the community cache, and make no network
   request until a confirmation snapshot exists.
4. Resolve names or list numbers to stable `advisorProgramId` values. If one
   name maps to multiple programs, make the user choose the exact program.
5. After showing the final summary and receiving explicit confirmation, run the
   bundled `advisor-pipeline/scripts/confirm_investigation.mjs` with
   `--confirmed-by-user`. Do not hand-edit `confirmed`, and do not treat a
   partially answered or saved draft menu as authorization.

If a valid non-empty configuration was already persisted and the user's command
is to run or resume that investigation, show a compact summary and use it. Ask
again only when the user requests a change or the stored IDs are no longer
valid.

## Confirmation gate

Before any network research or community-cache refresh, show:

- Exact selected advisors and programs.
- Exact selected sections.
- The cost level calculated with the canonical Web thresholds.
- Whether local community sources are requested.

Proceed only after a current confirmation snapshot is persisted. Community
snapshots additionally require
`investigation.confirmed.sourcePolicy: community_allowed`,
`investigation.confirmed.communitySources.consented: true`, a selected
community-relevant section, and the same current revision/fingerprint. If
consent is false, continue other selected research without downloading them.

## Research workflow

For medical mode follow the five-module menu in
`references/investigation-sections.md`: A identity and research positioning →
B five-year mainline → C collaboration network → D latest signals and projects
→ E doctoral trajectory. Use a five-year original-research window and 1–2 years
of frontier evidence as adjustable windows. Read actual contribution statements
before attributing leadership; a last author without contribution evidence is
at most `probable`. Collaborators are described at depth 1 only and are never
recursively investigated; citation neighbours are not collaborators. Project
records keep the published amount, unit and basis and are never converted into
doctoral personal funding. Distinguish doctoral trainees from postdocs, count
only people with supervision evidence, and never derive graduation, placement
or success rates. Training fit, lab resources, doctoral funding, training
environment, mentoring style and personality are out of scope; retain unknowns
rather than inferring from group size, title or authorship. Work may be split
across subagents that write `runs/<run-id>/subagents/*.json`; only the Main
Agent merges them with `merge_subagent_findings.mjs`.

For each selected advisor:

1. Read current Finder facts and evidence.
2. Skip unselected sections and write `用户未选择复核`.
3. Reuse current sources and query only missing, stale, or conflicting evidence.
4. Separate official facts, identified firsthand accounts, anonymous leads, and
   same-source copies.
5. Record short excerpts, URL, access date, identity status, and which finding
   the source supports.
6. Preserve rebuttals, corrections, dates, and conflicting accounts.
7. Write selected-section results back to `advisor_records.json` and evidence
   rows to `outputs/evidence.json`.

If a new official application fact appears incidentally, update the shared
program or advisor record. Do not restart a complete application search.

## Community knowledge

When source policy is `community_allowed`, a reputation-related section is
selected and consent is true:

1. Inspect `references/community-knowledge-metadata.json`.
2. Refresh only when missing, explicitly requested, or stale under the current
   policy.
3. Require `search_ready: true` before interpreting the PDF source as searched.
4. Search local text by advisor full name, Chinese name, institution, and lab.
5. Open relevant original links when accessible.
6. Continue with relevant public sources such as X/Twitter, 小红书, Reddit, Rate
   My Professors, institutional records, or identified public accounts.

Use the script path relative to this skill:

```bash
python3 scripts/sync_community_knowledge.py
```

If no PDF extractor exists, explain the project-local dependency option and
wait for user consent before installing anything. A non-searchable source must
be reported as `未完成检索`, never `未发现记录`.

## Evidence and privacy

- Anonymous material is an `anonymous_lead`, not a verified fact.
- Mirrors and reposts are `same_source_copy`, not extra corroboration.
- Do not automatically change a score because an advisor appears on a list.
- Do not expose student names, contact details, health information, private
  family information, or details that facilitate doxxing.
- Severe claims require a primary record, an identified firsthand account, or
  multiple genuinely independent sources before becoming a supported risk.
- When evidence remains weak, write a neutral lead and a concrete verification
  step.

## Output

Update the main field/direction-named `outputs/{topic}-导师调研.html` using
`../advisor-pipeline/scripts/build_advisor_report.mjs --project-root "$PWD"`
after shared records are updated. Keep it concise, focused on findings,
source links, uncertainty and next verification. The workbook below remains
a supplemental export, not the sole final report.

Maintain a compact `DETECTIVE_STATE.md` summary containing:

- Selected advisor-program IDs.
- Selected sections.
- Community consent and cache search status.
- Per-advisor completion and evidence count.
- Access limitations and unresolved conflicts.

Generate `advisor_detective_YYYYMMDD.xlsx` with a deterministic builder. Include
only the selected-section result columns plus an explicit configuration and
evidence sheet. The shipped builder already falls back to portable OOXML when
the Codex spreadsheet runtime is unavailable; do not install packages or write
and patch a replacement executable under `runs/`. Mark unselected sections as
`用户未选择复核`.

## Completion

Complete only when every selected advisor has:

- A result or explicit access/information gap for every selected section.
- Field-level evidence links.
- Conflict and privacy checks.
- No conclusion derived from a failed or skipped source.
- A regenerated main HTML report reflecting only confirmed/selected research.
