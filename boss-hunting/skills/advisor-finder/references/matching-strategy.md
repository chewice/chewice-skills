# Applicant-advisor matching strategy

Read this reference when creating, filtering, or ranking Finder candidates. The
contract is pathway-first and evidence-bounded; it does not estimate admission
probability.

## Medical evidence-profile branch

For `domainProfile: medical` and `evaluationMode: evidence_profile`, use this
branch instead of the generic numeric/portfolio sections below. Apply evidenced
applicable hard exclusions; record eligibility and opportunity independently.
No user hard constraints means only that additional gate is clear, not that
official application eligibility is established.

Use `evidenceProfile` (`evidence_profile` in advisor records is also accepted):

- `researchQuestionFit`: status `direct|partial|adjacent|weak|insufficient_information`,
  `reasons`, `sourceIds` (legacy `scientificFit` is mapped strong→direct,
  mismatch→weak).
- `researchRouteContinuity`: status `sustained_core|active_emerging|new_expansion|occasional_participation|unclear`.
- `piRoleConfidence`: status `verified|probable|emerging|identity_unresolved`, `level A–D`.
- `evidenceSufficiency`, `currentActivity`, module blocks `identity`,
  `researchMainline`, `collaborationNetwork`, `latestSignals`,
  `doctoralTrajectory`, plus `formalRecords`, `fitBoundary`, `keyUnknowns`,
  `nextVerification`.
- Removed and dropped on normalization: `trainingFit`, `resources`,
  `researchFunding`, `doctoralFunding`, `doctoralOutcomes`, `supportedRisks`.

Keep `fit`, `profileMatch`, `overallMatch` null and `competitiveness: unknown`.
Never apply 0.6/0.4, missing-value fallback or reach/match/safer quotas. Numeric
legacy values cannot silently order the medical shortlist. Rank denotes stable
display order (research-question fit → route continuity → name), not quality
or admission probability; citations, h-index and network centrality never sort.

Compare the user's scientific question with cited evidence of the PI's
five-year mainline. Keep strong but sparsely documented relevance and emerging
PIs for verification; source count and web coverage cannot substitute for fit.
Explain action/verification grouping, then use stable names for otherwise tied
rows. Do not label unexplored fields poor.
Known ineligibility/closed opportunities retain reasons; quantity/budget deferral
is distinct from an exclusion. Old expired adverts do not close a new intake.

Run the existing selector below for real program rows and discovery views. An
unmapped medical discovery advisor remains in `advisor_records.json`; the
selector derives `outputs/discovery-view.json` without fabricated program IDs.
The view is disposable, not another maintained fact source. Stop discovery when
agreed coverage is adequate or new searches no longer change the comparison;
carry forward unresolved candidates instead of padding the requested count.

## Generic mode required order

1. Classify the official application pathway.
2. Apply explicit user hard constraints.
3. Score research fit from recent work.
4. Assess applicant-relative profile match from the real CV.
5. Record current opportunity evidence.
6. Label competitiveness and compute an explainable overall match.
7. Run the deterministic portfolio selector.
8. Route the next action by application pathway.

Do not let a later score override an earlier hard failure.
After exclusions, resolve an unknown pathway first, then unknown hard
constraints, then unresolved objective eligibility, before recommending an
application or contact action.

## Application pathway

Use one value per advisor-program row:

- `supervisor_led`: the official process expects or materially depends on a
  supervisor's agreement. Recommended action: `contact_supervisor`.
- `committee_led`: the program admits through a committee and direct faculty
  contact is not required or not decisive. Recommended action: `apply_program`.
- `advertised_position`: recruitment is tied to a specific funded vacancy or
  project. Use `apply_vacancy` only with a current opening; otherwise `monitor`.
- `structured_program`: a cohort or doctoral-school route assigns or develops
  supervision through the program. Recommended action: `apply_program`.
- `unknown`: official evidence is insufficient. Recommended action:
  `verify_pathway`.

Do not interpret a missing reply as rejection for committee-led or structured
programs. Do not send generic supervisor outreach for a vacancy that specifies
another application route.

## Hard constraints and opportunity evidence

`hardConstraintStatus` is `pass`, `fail`, or `unknown`, with a list of exact
reasons and evidence IDs. Unknown never means pass.
When the project has no explicit additional hard constraints, the deterministic
selector normalizes this gate to `pass`; it must not invent a condition to
verify.

`opportunityStatus` is:

- `verified_open`: a current official opening or explicit recruiting statement.
- `signal_only`: recent funding, project, or lab-growth evidence that warrants
  checking but does not prove an opening.
- `unknown`: no current decisive evidence.
- `verified_closed`: a current official statement that the relevant route is
  closed or the vacancy has ended.

School prestige, rank, advisor nationality or ethnicity, alumni identity,
title, age, and “young professor” are not opportunity evidence. A title may
trigger further checking of lab stage, funding, and official rules, but cannot
raise a candidate by itself.

## Generic scores and labels

- `fit`: 0–10 research-topic/method fit, supported by current work.
- `profileMatch`: 0–10 match between the applicant's evidenced methods,
  publications, projects, prerequisites, and transferable skills and the
  target opportunity.
- `overallMatch`: deterministic `0.60 * fit + 0.40 * profileMatch`, rounded to
  one decimal. Hard constraints, eligibility, pathway, and opportunity remain
  separate gates or evidence and are never hidden inside this number. It is not
  a probability.
- `competitiveness`: `reach`, `match`, `safer`, or `unknown`, relative to the
  applicant and route. These labels plan a portfolio; they do not promise an
  offer.

Keep missing component scores as `null`; if either component is missing,
`overallMatch` is also `null`. Never coerce unknown to zero or preserve a
model-supplied total in place of the deterministic result.

## Deterministic selection

After writing the full eligible candidate pool to `outputs/candidates.json`,
run:

```bash
node .agents/skills/advisor-finder/scripts/apply_matching_strategy.mjs --project-root "$PWD"
```

Use the equivalent `.claude/skills/` path in Claude Code. The script applies
hard exclusions, stable ordering and shortlist size; generic mode also uses the
selected reach cap. It writes selected rows back to `outputs/candidates.json`, non-selected and
excluded rows to `outputs/candidates-excluded.json`, and an auditable summary
to `outputs/matching-audit.json`.

Do not hand-edit the selected portfolio after this step. If the real pool
cannot satisfy the requested mix, preserve the real candidates and the audit's
deviation instead of inventing safer options.

The script is idempotent: rerunning its already selected output merges the
previous `candidates-excluded.json` before recalculating, so hard exclusions
and audit counts are preserved. A newly written unscreened pool does not carry
old exclusions forward.
