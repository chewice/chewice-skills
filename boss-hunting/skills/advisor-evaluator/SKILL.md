---
name: advisor-evaluator
description: >
  Combine Advisor Finder objective application facts and research-fit results
  with user-selected Advisor Detective evidence. Use when the user wants a final
  comparison, ranking, risk review, or application-ready Excel workbook. Keep
  research fit, objective eligibility, and subjective background findings
  separate while producing one directly usable application table.
---

# Advisor Evaluator

Produce a decision aid and mode-appropriate workbook without collapsing
objective application conditions and subjective advisor suitability into one
opaque score.

Read:

- `outputs/advisor_records.json`
- `outputs/program_records.json`
- `outputs/evidence.json`
- `outputs/candidates.json`
- `outputs/matching-audit.json`
- `project.json`

If present, read `../advisor-pipeline/references/core-data-contract.md`. Read
`references/workbook-contract.md` before building or validating the workbook.
For medical mode read `../advisor-pipeline/references/medical-profile.md`.

## Alignment

Join program-level records by stable `advisor_program_id`, not fuzzy advisor-name matching.
Preserve multiple programs for one advisor as separate application rows.
Medical discovery without a real program joins only by `advisor_id` and exports
the advisor-level view; do not invent program/intake/IDs to pass alignment.

Check:

- Every application row maps to a real advisor and official program;
  exploration-only rows state that a program has not yet been verified.
- Objective facts are current for the requested intake.
- Detective results cover the same selected sections for compared advisors.
- `not_checked`, `not_found`, access failure, and conflicting evidence remain
  distinct.

## Decision model

Medical `evaluationMode: evidence_profile` uses this branch in place of the
numeric model below: display `scientificFit` and `trainingFit` with reasons and
sources, eligibility, opportunity, resource access levels, research funding,
doctoral funding, visible doctoral outcomes, unknowns, supported risks and next
verification. Keep `fit`, `profileMatch`, `overallMatch` null and competitiveness
unknown. Never call the old formula or portfolio quotas as fallback. Rank is
display order only. Use action/verification groups, preserve sparse strong-fit
candidates, and use stable name order for ties. Missing/blocked facts are not
zero; no implicit admission probability or safer-advisor promise. Digital
scoring, if separately requested, needs explicit anchors/weights and cannot
replace unknown evidence.

For generic mode show seven separate layers:


1. **Research fit**: numeric, formula-driven, and sourced from Finder.
2. **Profile match**: applicant-relative methods, work, prerequisites, and
   transferable skills from the real CV.
3. **Hard constraints**: `pass`, `fail`, or `unknown`; unknown is not pass.
4. **Application pathway**: supervisor-led, committee-led, advertised
   position, structured program, or unknown.
5. **Opportunity evidence**: verified open, signal only, unknown, or verified
   closed.
6. **Objective feasibility**: `eligible`, `ineligible`, or
   `needs_confirmation`, with explicit reasons.
7. **Advisor suitability**: selected-section findings, supported risks, and
   confidence.

Ask for optional weights only for numeric selected dimensions. Normalize weights
over dimensions consistently selected for the compared advisors. Do not score
an unselected or merely unavailable section as zero.

Anonymous leads cannot directly change a score. Display a supported severe risk
separately even when an overall numeric result is high.

## Priority

Recommend application priority using transparent rules:

- Do not recommend an objectively ineligible row as a primary application.
- Exclude a verified hard-condition failure or verified-closed opportunity.
- Keep unresolved feasibility visible instead of silently filtering it.
- Route the next action using the official application pathway; a missing
  faculty reply is not a rejection for committee-led or structured programs.
- Prefer strong research fit when eligibility is comparable.
- Surface verified severe risks before total scores.
- Explain the recommendation in plain language and list the next verification
  action.

## Workbook

First produce the main HTML report with
`../advisor-pipeline/scripts/build_advisor_report.mjs --project-root "$PWD"`.
Its `outputs/{topic}-导师调研.html` name follows the academic field/direction.
Use a simple layout centered on concise evidence comparison, key unknowns,
sources and next steps. Generate from shared state, not a second maintained
report database. The following Excel output remains supplemental; HTML is
required for a completed advisor research deliverable.
Each study, funding/training finding, qualification, deadline and comparison
reason must have its corresponding direct HTTP(S) source link beside it, using
item-level source IDs in shared evidence. Follow the report contract for safe
links and pending-source labels; a final source list alone is insufficient.

For medical discovery generate `advisor_research_discovery_YYYYMMDD.xlsx` with
the medical project/config and advisor-level projection; application fields
not investigated read “本次未核验”. For application mode generate
`advisor_application_ready_YYYYMMDD.xlsx` using the deterministic
builder. It automatically uses the Codex spreadsheet runtime when available and
portable OOXML otherwise. Do not install packages or create and patch an ad-hoc
workbook builder. The primary sheet must be usable without manually joining
other sheets.

Medical tables include question/method scope, training support, representative
DOIs, verified route/rotation/contact rules, separate eligibility/opportunity,
resource access level, separate research/doctoral funding, doctoral samples and
limits, unknowns, supported risks, next verification, dates and clickable sources.
Do not fetch QS or H-index by default to fill generic columns.

For generic/application tables include:

- School, QS edition, program, degree/intake, official link, deadline, tuition,
  scholarships, materials, and RP requirement.
- Advisor research/papers, email, homepage, and multiline recruiting/contact
  requirements.
- Research fit, profile match, overall match, competitiveness, hard-condition
  status/reasons, application pathway, opportunity status, recommended action,
  objective feasibility, selected backcheck result, supported risks, gaps,
  official sources, and last verified date.

Use separate sheets for fit, evidence, sources/freshness, and configuration.

## Verification

- Scan for duplicate `advisor_program_id` rows.
- Verify typed numbers, dates, formulas, filters, frozen panes, wrapping, and
  conditional formatting.
- Scan formulas for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, and `#N/A`.
- Confirm every application claim has official application sources/access dates;
  discovery rows explicitly retain uninvestigated application fields.
- Check that the HTML comparison and information sections show concrete source
  links beside supported items; unsupported or unlinked items remain explicitly
  pending, without invented URLs or unrelated citations.
- Stop rather than fabricate missing application facts.
