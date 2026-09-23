# Core project and researched-record contract

Read this reference for project bootstrap, Finder, Evaluator, or writes to
shared advisor/program/evidence/status records. It intentionally excludes
Detective authorization and application-material schemas.

## Project files

| Path | Purpose |
| --- | --- |
| `project.json` | User inputs and workflow configuration |
| `status.json` | Current phase, stage, and real progress counters |
| `outputs/candidates.json` | Compact Finder rows for the Web candidate table |
| `outputs/candidates-excluded.json` | Hard-excluded and portfolio-deferred Finder rows |
| `outputs/matching-audit.json` | Deterministic shortlist and reach-cap audit |
| `outputs/advisor_records.json` | Advisor facts, fit, selected-section results, and source IDs |
| `outputs/program_records.json` | Deduplicated school/program/application facts |
| `outputs/evidence.json` | Field-level evidence and community leads |
| `outputs/ranking.json` | Evaluator ranking and allowed later targets |

`project.json` uses camelCase. Researched entity records use the snake_case
fields below. Do not write aliases for the same project field.

## Deterministic CLI bootstrap

For a normal local folder rather than a Web-created project, run:

```bash
node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD"
node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD" --check
```

Use the equivalent `.claude/skills/` path in Claude Code. The initializer
creates or migrates `project.json`/`status.json`, creates only missing empty
output arrays, preserves existing outputs byte-for-byte, and backs up a file
before normalization. Do not hand-compose another contract.

Project schema is **9**; status and researched-record schemas remain **2**.

Direct use may pass `--config path/to/input-patch.json` to `init_project.mjs`.
The JSON patch contains only known user inputs, not constructed progress or
candidate facts; the initializer merges it, backs up changed files and preserves
existing research records. Repeating the same patch is idempotent.
Core project fields are `schemaVersion`, stable `id`/`slug`, `name`,
`applicantName`, `season`, `degree`, `target`, normalized weighted `interests`,
`shortlistTarget`, `portfolioStrategy`, `hardConstraints`, `cv`, timestamps, and the workflow
configuration objects. `portfolioStrategy` is `balanced`, `conservative`, or
`ambitious`; it shapes the reach/match/safer mix but is never an admission
probability.
Leave unknown target, degree, season, applicant name, and interests blank.

The applicant name must be the confirmed real or preferred professional name,
never a sample identity. General-mode Finder requires a readable current-applicant
CV under `inputs/`; research-interest text cannot replace it. Medical discovery
does not require a CV or identity; medical application accepts relevant structured
background with a declared source. RP/outreach retain their existing CV, identity
and exact-target confirmation gates.

### Medical project configuration

`domainProfile` is `general` (legacy/default) or `medical`. `searchMode` is
`application` (general default) or `discovery` (medical default). `evaluationMode`
is `weighted_score` for general and `evidence_profile` for medical. This release
does not expose a medical numerical-scoring mode. Keep `portfolioStrategy` for
compatibility, but medical selection never uses its quotas or old scores.

`medicalProfile` (schema 10) contains arrays `fields`, `diseasesOrMechanisms`,
`researchQuestions`, `researchObjects`, `researchScales`, `researchModes`
(research paradigm), `methodPreferences`, `adjacentInterests`, `exclusions`,
`regions`, and a `diseaseScope` string (`unasked`, `undecided`, `single_disease`,
`multiple_diseases`, `pan_disease`, `mechanism_first`, or the user's more precise
scope). `currentSkills` and `desiredTraining` were removed
(`MEDICAL_PROFILE_REMOVED_KEYS`); migration deletes them and never carries them
forward.

`medicalProfile.inputStatus` tracks `fields`, `diseaseScope`, `researchModes`,
`regions`, and `exclusions`: `unasked`, `answered`, `undecided`, or
`unrestricted`. Non-empty input becomes answered; only a user's explicit choice
permits undecided/unrestricted. `medicalIntakeStatus(project)` checks exactly
three steps: fields → disease / mechanism / question → regions. Research
paradigm, objects, scales and method preferences are optional and never block.

`target` is the single authoritative region/school scope. At initial import only,
an empty target is filled from `medicalProfile.regions`. Subsequently update
`target`; normalization derives `regions` by splitting semicolon/newline-separated
scope. A confirmed unrestricted region can have an empty target plus
`inputStatus.regions: "unrestricted"`. Do not retain two contradictory scopes.

`applicantBackground` has `source: self_reported|documented|not_provided`, arrays
`education`, `researchExperience`, `qualifications`, and optional `notes`.
Structured entries may be strings or field objects preserving provenance. They
are inputs for specific checks, not proof that every eligibility rule passes.
Application additionally requires degree, intake (`season`), funding/other hard
constraints (explicitly “none” is valid), and relevant background/CV. Missing
qualifications remain `needs_confirmation`.

`browserResearch` stores `enabled`, `policy: public_read_only`,
`backend: builtin_web` by default, and `allowPublicDownloads`. Legacy `auto`
also means built-in web first; preserve an explicitly selected other backend.
This field chooses a preference, not an installed tool or permission. Discover
the actual host's built-in web/search tools and follow their current schemas;
use official static pages/APIs as fallback and existing interactive browsers
only when dynamic JS/forms require them. A missing interactive browser does
not imply built-in web search is unavailable.
Migration defaults both Boolean permissions to false. Set them explicitly when
configuring a new medical search under the public-research policy; this does not
install tools, enable paid services, permit login or override host permissions.

Normalization preserves extra medical/background fields and existing outputs.
Initializer backups precede writes, cannot overwrite a prior backup, and repeated
initialization is idempotent. Future schemas are rejected rather than downgraded.

## Status

Preserve this shape and derive every count from artifacts:

```json
{
  "schemaVersion": 2,
  "phase": "intake|finder|detective|evaluator|completed",
  "stage": "intake|discovery|research_discovery|research_fit|objective_screen|selection|investigation|ranking|completed",
  "candidateCount": 0,
  "shortlistCount": 0,
  "objectiveReadyCount": 0,
  "selectedCount": 0,
  "evidenceCount": 0,
  "evidenceCoverage": 0,
  "rankingCount": 0,
  "updatedAt": "ISO-8601"
}
```

## Stable IDs

- `advisor_id`: normalized institution plus advisor name; never array position.
- `program_id`: institution plus official program, degree, and intake.
- `advisor_program_id`: advisor ID plus program ID.
- Preserve display names separately from IDs.
- An unmapped discovery advisor exists only in `advisor_records.json` and its
  derived exploration view. Never fabricate a program, intake or advisor-program
  ID. `candidates.json` and exact investigation/material choices still require a
  real `advisorProgramId`; one advisor with several real opportunities has several
  rows. A changed institution retains historical sources, not transferred resources.

## Field and source states

Every nontrivial researched field distinguishes:

- `verified`: a current source supports the value.
- `not_found`: named sources were checked and did not expose it.
- `not_checked`: outside scope or not researched.
- `inaccessible`: the named source could not be accessed; not evidence of absence.
- `conflict`: current sources disagree; preserve each claim.
- `stale`: a prior value needs refresh for the current intake.
- `not_applicable`: this field does not apply to the exact claim/opportunity.

Use field-level evidence rows:

```json
{
  "evidence_id": "ev_...",
  "entity_id": "program_or_advisor_id",
  "fields_supported": ["deadline"],
  "source_type": "official_program",
  "url": "https://...",
  "title": "Official admissions page",
  "accessed_at": "ISO-8601",
  "excerpt": "Short exact supporting text",
  "evidence_strength": "official",
  "status": "verified"
}
```

Evidence strengths are `official`, `identified_firsthand`, `anonymous_lead`,
and `same_source_copy`. Mirrors/reposts are not independent corroboration.

Important claims also preserve `claim_type: fact|interpretation|question`,
`claim`, `source_updated_at`, `applicable_intake`, `page_locator`,
`reading_depth: metadata|abstract|full_text`, `retrieval_method:
static_web|official_api|browser`, `final_url`, `page_title`,
`query_or_filter_summary`, `extraction_status: success|partial|blocked|failed`,
`failure_reason`, optional local `snapshot_path`, and `same_source_group`.
Record the actual `retrieval_provider` and `retrieval_tool` when a tool is used.
GPT host built-in search/open/find/link access is `retrieval_method: static_web`,
`retrieval_provider: gpt_builtin_web`, with its real tool name (for example,
`web__run` only when that is the tool actually invoked). Wisp Science host browser
tools (`web_open_tab`, `web_scan`, `web_execute_js`, `web_screenshot`,
`web_save_assets`, `web_agent_*`) are an interactive browser:
record `retrieval_method: browser`, `retrieval_provider: wisp_science_browser` and
the real tool name. `official_api` remains for actual API use.
Capability discovery is not a retrieval; do not create successful evidence or
claim Browser Use installation from a backend preference or callable tool alone.
Store only actual observations. `partial`/`blocked` extraction cannot establish
`not_found`; metadata/abstract reading cannot prove contribution or methods review.

### Field-level links in the HTML report

Attach `sourceIds` (or the existing `source_ids` spelling) to the specific
research item, resource/funding claim, doctoral outcome, qualification,
deadline or comparison reason that they support. Resolve these IDs against
`outputs/evidence.json`; the evidence must match the entity, supported field
and applicable intake. Do not treat every source attached to an advisor as
support for all of that advisor's claims.

Render a direct link to the actual record, article or official document beside
each corresponding fact/reason in the comparison table and advisor brief.
Use the observed evidence `final_url`, `source_url` or `url`, with a short
source title. A footer source list or an internal evidence anchor may supplement
these links but cannot replace them. A database homepage is not the source for
a specific grant, eligibility requirement or deadline.

Only HTTP(S) URLs may become external report links; escape labels/attributes
and retain simple styling. Missing IDs, unmatched evidence, unknown facts or
absent concrete URLs are marked `待核验` / `来源待补`; never synthesize a URL or
borrow an unrelated source to make the field look verified. A real accessible
link does not by itself upgrade an unknown, stale, conflicting or blocked claim.

### Medical evidence comparison

Candidates use `evidenceProfile`; advisor records use `evidence_profile`
(camelCase or snake_case keys are both accepted by `normalizeMedicalEvidenceProfile`).
The projection contains:

- `researchQuestionFit` `{status: direct|partial|adjacent|weak|insufficient_information, reasons, sourceIds}`
  (legacy `scientificFit` statuses are mapped: strong→direct, mismatch→weak).
- `researchRouteContinuity` `{status: sustained_core|active_emerging|new_expansion|occasional_participation|unclear, reasons, sourceIds}`.
- `piRoleConfidence` `{status: verified|probable|emerging|identity_unresolved, level: A|B|C|D, reasons, sourceIds}`.
- `evidenceSufficiency: strong|adequate|sparse|conflicted`; `currentActivity: active|recent_signal|unclear|apparently_inactive_in_checked_scope`.
- `identity` (current institution / department / position, official profile URL,
  research positioning, doctoral supervision link, name variants, identifiers,
  `affiliationAsOf`).
- `researchMainline` (`longTermQuestion`, `continuingThemes`, `newDirections`,
  `researchObjects`, `methods`, `recentShift`, `participationOnlyWorks`,
  `representativeWorks[{title, year, venue, doi, url, verifiedRole, relationToMainline, isPreprint, sourceIds}]`,
  `backSearchWindow`).
- `collaborationNetwork` (`depth: 1`, `coreCollaborators[{name, currentInstitution, currentPosition, ownCoreDirection, collaborationEvidence: [{type, title, year, url, sourceIds}], sourceIds}]`,
  `edges[{type: coauthorship|shared_project|shared_grant|shared_trial, target, count, years, sourceIds}]`,
  `researchNeighbors[{type: citation|co_citation|bibliographic_coupling|semantic_similarity|related_papers}]`,
  `heuristics`).
- `latestSignals` (`latestPapers`, `preprints`,
  `projects[{title, projectId, fundingBody, piRole, period, status, amount, amountUnit, amountBasis, source, sourceIds}]`,
  `registries`, `trials`).
- `doctoralTrajectory` (`firstAuthorProfiles[]`, `labWebsites[]`, `searches[]` as defined in investigation-contract.md, `currentDoctoral[]`, `formerDoctoral[]` with
  supervision evidence / degree or year / topic / outputs / first destination /
  latest public role / information date, `graduateProgram`, `emergingPiNote`,
  `sampleLimitation`).
- `formalRecords[]`, `fitBoundary`, `keyUnknowns[]`, `nextVerification[]`.

Every sub-item carries `sourceIds` into shared evidence. Removed and never
projected: `trainingFit`, `resources`, `researchFunding`, `doctoralFunding`,
`doctoralOutcomes`, `trainingEnvironment`, `supportedRisks`, `overallScore`,
`qualityScore`, `mentoringSuccess`, `placementRate` (`REMOVED_MEDICAL_PROFILE_KEYS`).
Older stored records keep these keys untouched. Doctoral samples distinguish
doctoral students from postdocs / residents / masters; no graduation, placement
or success rate is ever computed.

Advisor records additionally carry `pi_evidence_level: A|B|C|D`,
`discovered_via: research_seed|map_seed|collaboration|research_neighbor|official_roster|unknown`,
`network_round`, `back_search {window, sourceIds}` and, after a merge,
`source_task_ids[]`.

In medical mode `fit`, `profileMatch`, `overallMatch` are null;
`competitiveness` is unknown. Display order is `researchQuestionFit` →
`researchRouteContinuity` → stable name; it is never a PI quality ranking and
citations, h-index, prestige, grant totals and network centrality do not
participate. Strong but sparse evidence stays pending.

To exclude an exact opportunity for a hard constraint, ineligibility or closure,
use the applicable `hardConstraintEvidence`, `eligibilityEvidence`, or
`opportunityEvidence`: `{status: "verified", advisorProgramId: "real-row-id",
intake: "matching intake when specified", sourceIds: ["ev-id"]}`. Without this
claim-specific current evidence, keep the condition unknown. Discovery never
asserts personal eligibility; historical vacancy closure cannot close a new intake.

Medical `outputs/ranking.json` uses an envelope, not a bare array:

```json
{
  "rankingMode": "evidence_profile",
  "confirmedRevision": 1,
  "confirmedFingerprint": "the-current-investigation-confirmation-fingerprint",
  "rankings": []
}
```

Copy the revision and fingerprint from the current, explicitly confirmed
investigation. The underlying Detective result must bind to that same snapshot.
Changing the medical scope invalidates both comparison and application-material
readiness; confirming and rerunning Detective alone does not make an older ranking
current. Re-evaluate against the new results before offering targets for materials.
Existing general-mode ranking arrays remain compatible.

## Program records

Store school/program facts once:

```json
{
  "program_id": "university-program-degree-intake",
  "school_name": "",
  "qs_overall": {"value": null, "edition": "", "status": "not_checked"},
  "program_name_zh": "",
  "program_name_en": "",
  "degree": "",
  "intake": "",
  "program_url": "",
  "application_pathway": "supervisor_led|committee_led|advertised_position|structured_program|unknown",
  "opportunity_status": "verified_open|signal_only|unknown|verified_closed",
  "deadline": {"value": "", "status": "not_checked"},
  "tuition": {"value": null, "currency": "", "period": "", "status": "not_checked"},
  "scholarships": {"value": "", "status": "not_checked"},
  "application_materials": {"value": "", "status": "not_checked"},
  "rp_requirement": {"value": "", "status": "not_checked"},
  "last_verified_at": null,
  "source_ids": [],
  "missing_fields": []
}
```

Keep variable requirements as multiline text; do not invent Boolean columns.
Application pathway and opportunity status require current official evidence;
they remain `unknown` when the route or opening cannot be established.

## Advisor records

```json
{
  "advisor_id": "institution-advisor",
  "name": "",
  "school": "",
  "department": "",
  "title": "",
  "homepage": "",
  "scholar_url": "",
  "email": "",
  "research_directions": [],
  "recent_papers": [],
  "fit_scores": {},
  "weighted_fit": null,
  "recruiting_status": "open|closed|unknown",
  "advisor_contact_requirements": {"value": "", "status": "not_checked"},
  "selected_section_results": {},
  "risk_flags": [],
  "source_ids": []
}
```

## Run-local files (medical)

`runs/<run-id>/` holds per-run, non-authoritative material:

- `provider-capabilities.json` — routes, run mode and credential status words
  written by `provider-capabilities.mjs`; never secret values.
- `subagents/<task_id>.json` — subagent outputs (schema in
  investigation-contract.md); only the merge script reads them into `outputs/`.
- `merge-report.json` — validation errors, duplicates, conflicts, gaps and
  dropped removed fields for that merge.

Evidence statuses are `verified`, `partial`, `not_found`, `not_checked`,
`inaccessible`, `conflict`, `stale`, `not_applicable` (`EVIDENCE_STATUSES`).

## Cache and freshness

- Reuse a current URL/extraction that supports the needed field.
- Query only `missing_fields`, `stale` fields, and conflicts.
- Recheck recruiting/contact requirements per application run.
- Recheck deadline, tuition, scholarship, and materials for the named intake.
- Refresh QS only when the requested edition changes.
- Never repeat program-level browsing for advisors in the same program.

### 动态查询完成记录（兼容增补）

基金 `projectSearches[]` 可增 `requiresInteraction` 与 `interactionAttempts[]`（provider/tool/checkedAt/url/outcome/reason/sourceIds）。NSFC 动态查询必须填写。对应 evidence 增 `interaction_required`、`query_submitted`、`filters_confirmed`、`results_loaded`、`pagination_complete`、`result_count`；布尔字段按实际观察填写，result_count 是完整结果数。保留 page_state、complete_results、searched_sources。静态空框架不能证明查无。详见 [交互执行规则](browser-research-policy.md#动态基金库查询必须执行)。旧记录兼容，不推断完成交互；合并保留尝试与结果证据。
