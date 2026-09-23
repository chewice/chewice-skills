---
name: advisor-pipeline
description: >
  Orchestrate Boss Hunting within the existing Advisor Atlas workflow, from
  medical research interests (no CV required for discovery) or a real CV to a
  source-backed shortlist, objective application-feasibility screen,
  user-selected advisor background research, an application-ready final
  workbook, and optional target-specific outreach or Research Proposal
  materials. Use when the user asks to find advisors, run the full advisor
  matching process, resume an application project, or coordinate Finder,
  Detective, Evaluator, and post-evaluation application materials.
---

# Boss Hunting

The original `advisor-pipeline` module remains the compatible orchestrator.
For medical/biomedical work set `domainProfile: medical` and read
[medical-profile.md](references/medical-profile.md). Medical intake is three
steps: medical field → disease / mechanism / scientific question → target
regions. Research objects, scales, paradigm (`researchModes`) and method
preferences are optional and never block. Discovery then runs scientific
question → Seeds → PI validation → collaboration network → five-module deep
dive (see "Medical discovery orchestration" below).
Ask only missing questions; development of this Skill is not an intake request.
Choose `searchMode: discovery|application`; medical discovery needs no CV,
grades, degree, intake, applicant skills or desired training. Application
screening accepts a real CV or sufficient attributed `applicantBackground`.
Use `evaluationMode: evidence_profile`.
Keep existing non-medical behavior below unless a medical branch says otherwise.

Read [medical-sources.md](references/medical-sources.md) (Source Capability
Registry) only for the global core and the selected-region adapters. For public
web research and the credential / provider fallback rules read
[browser-research-policy.md](references/browser-research-policy.md).
Discover actual host tools and default to built-in web/search capabilities
(`backend: builtin_web`; legacy `auto` is also built-in-first). Follow the real
schema for search/open/find/link access; do not assume every host has all actions.
Under Wisp Science, its host browser tools (`browser_setup`, `web_open_tab`,
`web_scan`, `web_execute_js`, `web_screenshot`, `web_save_assets`) are the
interactive-browser route; connect with `browser_setup` first and stop for human
verification when the host asks for it. Official static pages/APIs are fallback
routes. An empty shell or dynamic query form MUST trigger actual interactive
tool discovery and execution (GPT native interactive tools when exposed; Wisp
Browser Use). Static retries never substitute for filling name/institution/date,
submitting, waiting, verifying filters and paginating. Record requiresInteraction,
interactionAttempts and the shared query receipt fields. If no complete tool
route exists, report missing host capability, not site failure; see the mandatory
procedure in browser-research-policy.md.
Record built-in retrieval as `static_web` and Wisp Science browser retrieval as
`browser` with `retrieval_provider: wisp_science_browser`; this does not claim
Browser Use is installed.
Public research is allowed within scope, but installs, paid services and deep
investigation confirmation remain separate. Preserve an explicitly chosen backend.

Run one progressive, resumable workflow:

```text
Intake
  -> Finder broad discovery
  -> Finder research-fit shortlist
  -> Finder objective application feasibility
  -> user selects advisor-program rows and investigation sections
  -> Detective selected-section research
  -> Evaluator and application-ready workbook
  -> user selects exact advisor-program target and material purpose
  -> Research Proposal and/or advisor outreach, in requirement-driven order
```

The final advisor research deliverable is a concise, content-first HTML report
named for the user's academic field/direction. Generate it from shared records
with `node scripts/build_advisor_report.mjs --project-root "$PWD"` using this
skill's script path. It writes `outputs/{topic}-导师调研.html`; do not use a generic
date-only title. Existing Excel exports remain supplemental compatibility
artifacts. A workbook alone does not satisfy the report requirement.
Place specific external source links beside the corresponding studies, funding,
doctoral outcomes, qualifications, deadlines and comparison reasons. Resolve
item-level source IDs through shared evidence; a footer-only bibliography is
insufficient. Missing concrete sources stay explicitly pending verification.

Do not create a late, independent application-requirements scrape. Capture facts
when encountered and fill only shortlist gaps before Detective.

## Shared contract

Read the short `references/data-contract.md` router first, then only the
stage-specific contract it names. Do not load Detective or application-material
schemas during Finder, or Finder schemas during a material-only continuation.

Use:

- `project.json`
- `status.json`
- `outputs/candidates.json`
- `outputs/candidates-excluded.json`
- `outputs/matching-audit.json`
- `outputs/advisor_records.json`
- `outputs/program_records.json`
- `outputs/evidence.json`

The JSON files are authoritative. Markdown state files are resumable human
summaries only.

### Direct CLI project bootstrap

Web-created projects already contain the shared files. When this Skill is used
directly from Codex CLI, Codex Desktop, or Claude Code in a user-created folder,
initialize the same contract before starting if it is missing:

Read `references/core-data-contract.md` for this bootstrap and shared-record
schema.

Run these commands inside the shared Pixi environment: activate it with
`pixi shell --manifest-path /path/to/boss-hunting/pixi.toml`, then
change to the application project directory. Keep the repository available as
the dependency workspace; copied Skills reuse it instead of adding another
package manifest or installing global runtimes. The default platform is Linux
(`linux-64`; use WSL on Windows).

1. Run `node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD"`
   (or the equivalent `.claude/skills/` path). This deterministic initializer
   creates or safely migrates the shared files, writes a timestamped backup
   before normalizing an existing file, and never overwrites existing outputs.
2. Resolve the project's existing CV first: prefer the file referenced by
   `project.json.cv`, then inspect `inputs/` and any explicit CV path already
   supplied in the conversation. Read that CV and any existing application
   notes.
3. Treat CV intake as project-scoped and idempotent. Once a readable CV for the
   current applicant exists, reuse that same file silently in every later
   phase; never ask the user to upload, attach, or paste it again merely because
   another Skill or phase is starting. Only request a replacement when no
   readable CV exists, the stored path is broken, the file is clearly a sample
   or for another applicant, or the user asks to update it. If one material
   needs a fact that the CV does not contain, ask only for that fact rather than
   requesting the whole CV again. A CV is mandatory for generic matching and
   application materials; the medical discovery/application exceptions above
   apply before this CV gate.
4. Collect only the missing Phase 1 inputs; do not make the user repeat facts
   already present in those files.
5. Persist confirmed input using the initializer's `--config input-patch.json` option (a user-input patch, not hand-composed project state). Reuse the repository Pixi Node environment; do not install global runtimes.
6. Validate again with the initializer's `--check` option before research.

Do not hand-compose `project.json`. The initializer leaves unknown user inputs
blank rather than guessing them from unrelated Finder output fields. Empty
structured output arrays are created only when the corresponding file is
missing; demonstration advisors and progress counts are never inserted.

Direct CLI use and Web use are two interfaces over the same project state, not
two different workflows.

## Status

Use:

```json
{
  "schemaVersion": 2,
  "phase": "intake|finder|detective|evaluator|completed",
  "stage": "intake|discovery|research_fit|objective_screen|selection|investigation|ranking|completed",
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

Write real counts from artifacts. Do not populate demonstration values.

## Phase 1: Advisor Finder

For generic projects require a target scope plus a real, readable CV. Research interests and weights
are optional supplements, not replacements for the CV. Persist explicit hard
constraints, `portfolioStrategy`, and the user-selected `shortlistTarget`
(default 10), then invoke Advisor Finder without duplicating its instructions.

Finder performs a fixed low-cost scan for identity/current role, high-level
recent research, representative work, and official recruiting signals. These
facts may later be reused by Detective, but Finder must not pre-run community
reputation, group ecology, work-style, or other selected deep-research sections.

Degree and intake can be supplied after discovery. Require them before Finder
starts the objective application-feasibility pass, then query only missing
official application facts for the shortlist.

Medical discovery instead completes after a real advisor-level exploration
view with a five-dimension evidence profile per PI (research-question fit,
route continuity, PI role confidence, evidence sufficiency, current activity),
the five public-evidence modules, and an explicit seed / network / saturation /
coverage report. Keep unmapped advisors in `advisor_records.json`; do not
invent programs, intakes or candidate IDs to satisfy the application route.
Derive an exploration workbook and the field-named HTML report, then mark
`research_discovery`, with unperformed eligibility checks explicit. A real
program and intake are required only for program-level rows. Moving to
application reuses research facts and fills only the missing inputs.

## Medical discovery orchestration

The Main Agent (this Skill's runner) is the only orchestration owner. It reads
the user's scientific question, plans the seed sub-directions, dispatches
subagents, adjudicates conflicts, runs the deterministic merge and writes the
report. No subagent owns the plan or the authoritative JSON.

Flow (details in `references/medical-profile.md`):

```text
Scientific question
  -> Seed Scouts (parallel per sub-direction): Map Seeds (reviews) + Research Seeds (5-year originals)
  -> PI extraction from Research Seeds (no "last author = PI" rule)
  -> Identity Resolver: OpenAlex / ORCID / official page, pi_evidence_level A–D
  -> Trajectory Mappers: 5-year back-search per PI -> route continuity
  -> Network Expander (max 2 rounds): collaboration edges vs research-neighbor edges
  -> saturation check -> shortlist (display order, not quality ranking)
  -> five-module deep dive A–E -> merge -> {topic}-导师调研.html
```

Subagent roles: Seed Scouts, Identity Resolver, Trajectory Mappers, Network
Expander, Regional Project Investigator, Doctoral Trajectory Investigator,
Evidence Auditor. Schedule them mixed: independent sub-directions and
independent PIs run in parallel; identity resolution precedes back-search and
network expansion for the same PI; the Evidence Auditor runs last.

Write rules:

- Subagents write only `runs/<run-id>/subagents/<task_id>.json` with the fields
  `task_id, agent_role, scope, findings, new_entities, conflicts, gaps,
  queries_executed, sources_checked`. They never touch `outputs/`.
- The Main Agent merges with
  `node scripts/merge_subagent_findings.mjs --root "$PWD" --run-id <run-id>`
  (use `--dry-run` first). The script validates the schema, refuses any file
  containing a credential value, deduplicates advisors by `advisor_id` / ORCID /
  OpenAlex id and evidence by URL + entity + fields + claim, writes field
  disagreements as `status: conflict` evidence, strips removed fields, and is
  the single writer of `outputs/advisor_records.json` and `outputs/evidence.json`
  under the project file lock. It also writes `runs/<run-id>/merge-report.json`.
- Conflicts (for example API affiliation vs official page) stay recorded with
  their as-of dates; the Main Agent adjudicates using the current official
  institution page and says so.

Credentials and providers:

- On first use run `node scripts/first-use.mjs` and show its ordered environment,
  optional-key and prompt guidance. It creates the ignored source-Skill
  credentials template once and never installs dependencies; only the source
  repository holds key values, not copied project Skills.
- Run `node scripts/credentials.mjs --json` and
  `node scripts/provider-capabilities.mjs --project-root "$PWD" --run-id <run-id>`
  at start. Credentials are optional accelerators resolved from the process
  environment, `BOSS_HUNTING_CREDENTIALS_FILE`, the source repository's
  `skills/boss-hunting/credentials.env`, then the legacy OS user config file.
  The source repository is located from the Skill path or a one-time user
  configuration pointer. Never scan project directories for `.env` files or
  ask the user to paste keys into chat.
- Only the status words `configured | unavailable | invalid | capability-limited`
  may appear in prompts, subagent outputs, evidence, logs, HTML or Markdown.
  Secret values never leave the loader.
- Per provider fall back in order: authenticated API → anonymous / keyless
  official API → Browser Use on official public pages → alternative
  authoritative sources. `runs/<run-id>/provider-capabilities.json` records the
  chosen routes and the run mode (`api_enriched | hybrid | public_only |
  browser_fallback`). A missing NCBI key means anonymous E-utilities, not PubMed
  scraping; a missing CiNii App ID means the CiNii / KAKEN websites; a WoS key
  never implies the Expanded tier; Google Scholar is discovery / backcheck
  only. `not_found` in a public database never becomes "the PI has no funding".

Removed from the medical workflow (do not investigate, render or rank on
them; old stored fields stay untouched): training fit / desired training /
applicant skills, lab resources and access tiers, doctoral personal funding
and tuition, training environment / atmosphere / mentoring style, mentoring
success or placement rates, composite quality scores, citation or h-index
ranking, and any resource or student-funding source entries.

Completion tiers for a medical discovery run: `complete` (every shortlisted PI
has all five modules with a result or explicit gap, provider metadata and merge
report saved), `partial` (some modules or PIs unfinished but reported as such),
`blocked` (identity unresolved or every route inaccessible for the required
evidence). Never report a higher tier than the artifacts support.

Generic/application-stage completion requires:

- Real advisor and program records.
- A pathway-classified, hard-constraint-gated research/profile-fit shortlist.
- Deterministic `outputs/matching-audit.json` and preserved excluded candidates.
- Objective feasibility for shortlisted advisor-program combinations.
- `outputs/candidates.json` for the Web UI.

Pause for user selection after the objective screen.

## Selection gate

This is a mandatory interactive gate in both Web and direct CLI use. Finishing
Finder does not authorize Detective research.

Read `references/investigation-contract.md` before confirming or running this
stage. The renderer owns the full option catalog, so do not separately load the
catalog merely to reproduce the menu.

For direct CLI users, perform the following steps in order:

1. Render the menu with the deterministic script, never by hand:

   ```bash
   node .agents/skills/advisor-pipeline/scripts/render_investigation_menu.mjs --root "$PWD"
   ```

   It prints the candidate table (including the stable `advisorProgramId`
   column), the ordered section catalog for the project's mode (11 generic
   sections, or the five medical modules A–E, all selected by default) and the
   current work unit / cost level. Show its output verbatim. You may explain it, but you must
   not reorder, rename, drop, or summarize away any column or row — a
   free-form menu has already shipped without `advisorProgramId`.
2. **Read scope while selecting**: only `project.json`,
   `outputs/candidates.json`, and the dimension catalog. Do not read
   `outputs/advisor_records.json`, `outputs/evidence.json`, previous detective
   results, or the community cache, and make no network requests until the
   user has confirmed.
3. Ask the user to choose exact advisor-program rows by number or stable ID.
   Do not infer the choice from ranking, Top N, or a count.
4. Let the user keep the defaults, add sections, remove sections, select all,
   or select none. If a default section is removed, warn that the background
   check may be incomplete or stale before accepting the removal.
5. The script already prints the Web-equivalent cost level, calculated as
   selected advisor-program rows multiplied by selected sections: `<= 8` is
   low, `9-24` is medium, and `> 24` is high.
6. Medical `investigation.draft.sourcePolicy: public_only` uses public evidence
   only; none of the five medical modules is community-relevant, so no community
   snapshot question or download is triggered for medical projects.
   For generic or explicitly community-enabled investigations, if a community-relevant section listed in the canonical section reference
   is selected, ask separately whether the user consents to downloading and
   parsing third-party community material in this local project. Default to no.
7. Show a final confirmation summary with exact advisor names/programs, exact
   section labels, cost, and community consent. Wait for an explicit confirm or
   modification request.
8. Menu changes are draft-only. After the user explicitly confirms the exact
   summary, run `scripts/confirm_investigation.mjs --confirmed-by-user` with
   every selected advisor-program ID, section ID, and `--community yes|no`.
   This produces a revision-bound `investigation.confirmed` snapshot. Only then
   invoke Advisor Detective.

Use a compact reply format such as:

```text
Advisors: 1,3
Sections: keep defaults + 5,6,10
Community sources: no
```

Do not start Detective while either the advisor selection or section selection
is empty. Never infer selected advisors from Top N when exact user selections
exist.

## Phase 2: Advisor Detective

Invoke Advisor Detective only for exact confirmed IDs and selected sections.

If a reputation-related section is selected and the source policy permits
community research:

- Ask separately for community-source consent.
- Refresh local snapshots only after consent and only when needed.
- Continue other public-source research even when community access is declined
  or unavailable.

Completion requires a result or explicit gap for every selected
advisor-section pair.

## Phase 3: Advisor Evaluator

Invoke Advisor Evaluator using shared structured records. Do not pass a
shallow/medium/high level.

Completion requires:

- Separate research fit, profile match, hard constraints, application pathway,
  opportunity evidence, objective feasibility, and advisor-suitability
  conclusions (generic mode), or the five-dimension evidence profile per PI
  (medical mode) without any total score.
- An application-ready workbook for application mode, or an evidence-profile
  exploration workbook for medical discovery, without fabricated total scores.
- The field/direction-named HTML research report from shared records. Medical
  reports start with the search requirements, then a compact comparison,
  five readable modules per advisor, and “本次查了什么，还缺什么”.
  Keep grant-search records expanded; put source and technical details in
  native disclosure sections. Collaborator profiles contain only identity, current
  appointment, research direction, joint projects and outputs; see the shared
  medical contract for the relaxed single-documented-collaboration rule.
- Source, freshness, missing-field, and risk checks.

## Post-evaluation application materials

Read [references/application-materials-contract.md](references/application-materials-contract.md)
before offering, confirming, researching, downloading, or generating these
materials.

After Evaluator, offer—not silently start—two target-specific Skills:

- `advisor-research-proposal` for an RP, concept note, literature review,
  methods plan, adaptation, or proposal audit.
- `advisor-outreach` for a first email, advertised-position response, follow-up,
  or reply.

Before offering generation as ready, validate the already stored project CV and
applicant name. This is a state check, not a new intake step: when
`project.json.cv` still resolves to the readable CV supplied earlier in the
pipeline, both application-material Skills must reuse it without asking the
user for another upload. If the CV or name is missing, invalid, conflicting,
ambiguous, or looks like a placeholder, pause and ask only for the exact input
needed to repair that condition.
Do not start literature downloads, create applicant-facing files, or substitute
an example identity. An official anonymity rule may keep the name out of an RP,
but does not waive the identity/CV preflight.

Require the user to choose one exact `advisorProgramId`, the material purpose,
and generation order. Do not infer the target from rank 1 or generate a mail merge. Read the
current official advisor/program contact and RP requirements before choosing
the order:

- When a draft RP or concept note is required or useful for first contact, run
  Research Proposal first and let Outreach decide whether to attach it.
- When the first contact is only an availability/route inquiry, draft Outreach
  first and do not manufacture a full RP attachment.
- For an advertised project, follow its document list and selection criteria.

Write post-evaluation artifacts under
`outputs/application-materials/<advisorProgramId>/`. Ranking remains the end of
the three analysis phases, but the Web and CLI expose these as separately
confirmed, artifact-verified continuations. A draft without both literature
classes, advisor/team relationship evidence, locally verified public PDFs,
manifest hashes, and citation-audit IDs
is partial. Never send email or submit the RP.

## Resume behavior

At startup:

1. Read status and structured outputs.
2. Validate schema versions and stable IDs.
3. If the objective screen is complete but selection is absent, resume at the
   interactive selection gate; do not repeat Finder or choose Top N.
4. If a non-empty `investigation.confirmed` snapshot exists and still matches
   the current draft revision/fingerprint, show its compact summary and resume
   the first incomplete research stage unless the user asks to modify it.
   Draft-only or changed selections must return to the final confirmation gate.
5. Reuse current sources.
6. Query only missing, stale, or conflicting fields.
7. If post-evaluation materials exist, resume only the chosen target and
   material; do not regenerate ranking or other targets unless requested.

Never restart the whole workflow merely because an output workbook is missing;
regenerate the workbook from structured state.

## Safety

- Do not send email, submit applications, commit, push, or publish.
- Keep CVs, project state, downloaded community snapshots, credential files and
  generated outputs local and Git-ignored.
- Never print, log or store API key values; report credential status words only.
- Do not treat public accessibility as redistribution permission.
- Do not bundle or commit third-party community snapshot contents.
- Stop and state the missing input instead of inventing application facts.

## Minimal medical report and grant-search evidence

Per-advisor official grant-database searching and its recorded process are mandatory baseline work for every medical report, even when the user never mentions grants. Do not require an extra prompt, a selected Detective section, or a deep-investigation request to include this baseline. Silence is not an exclusion; only an explicit user restriction can narrow it, and each excluded, blocked or unfinished search must still appear with its reason in a partial report.

For a medical report, follow [the shared report contract](../advisor-pipeline/references/medical-profile.md#证据与续跑). Each advisor needs regional official grant-database searches using name variants and institution, covering active and past-five-year projects. Store the actual query, dates, scope, status, limitations and sources in `latestSignals.projectSearches[]`; store found grants in `projects[]`. Supplementary institutional/search-engine pages do not complete a database search. Respect user-selected investigation scope; report missing or blocked searches as partial, never infer “no grants” from empty data. Use descriptive `citation_label` links and separate appointment verification, page access and page update dates. Generate the shared minimalist HTML with five readable modules; do not replace it with custom decorated HTML.

Medical minimum reports also include the [doctoral first-author and lab-website checks](../advisor-pipeline/references/medical-profile.md#博士指导第一作者画像与实验室网站默认最低内容), without an extra user request. Verify the advisor's corresponding/co-corresponding role and first/co-first authors on papers from the past five years; summarize only those joint papers. Seek an attributable lab website and check members/alumni/publications. First authors are not automatically doctoral students; preserve independent identity evidence, dates, sources and search gaps in `doctoralTrajectory`.
