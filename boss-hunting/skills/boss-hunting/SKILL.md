---
name: boss-hunting
description: >
  Find and compare doctoral advisors using public evidence. Supports medical and
  biomedical research discovery from a scientific question alone (no CV, grades
  or applicant ability), application screening with real applicant background,
  and the existing general advisor workflow. Use when the user asks Boss Hunting
  to discover advisors, map a research direction's PIs and publication trajectories, compare research-question fit, or resume an advisor search. Skill
  development requests do not start a search.
---

# Boss Hunting

On the first use of this installation, before starting research, run
`node ../advisor-pipeline/scripts/first-use.mjs` from this Skill directory
(or the equivalent full path in a copied Skill). Report its actual Pixi,
locked-runtime and Skill checks to the user; a missing environment is a
setup gap, not permission to install packages automatically. If Node itself is
unavailable, check `pixi --version` and `node --version` with the host shell,
explain the missing prerequisite and how to run the first-use check after setup.
Next recommend the optional API keys with their purpose and official request
links from the repository README. Ask the user to fill the one ignored
`skills/boss-hunting/credentials.env` in the source repository manually; never
request key values in chat. Run the credential status check again after they
say it is filled. Once the environment check and API guidance are delivered,
show a concrete first-use `$boss-hunting` prompt containing field, scientific
question and target regions. Missing optional keys do not block public-only
research. If the user already gave those inputs, reuse them rather than asking
for the sample prompt to be sent back. Do this onboarding once per installation
or when the user explicitly asks to check setup, not on every project change.

This is the named entry to the existing workflow, not a separate system. Read
[Advisor Pipeline](../advisor-pipeline/SKILL.md) and follow its mode-specific
references. Use the same `project.json`, shared records, builders and confirmation
gates. The `advisor-pipeline` path remains a compatible entry for existing projects.

For medicine, collect only the three minimum inputs that are missing, in this
order: medical field; disease / mechanism / scientific question; target
regions. Research objects, scales, paradigm and method preferences are optional
and never block. Do not read a CV, transcript, publication list or applicant
ability for discovery, and do not ask for desired training or current skills —
those fields no longer exist. Discovery then follows the pipeline's medical
orchestration: Seeds → PI validation → five-year back-search → saturation → shortlist → three-module research (A identity
and research positioning, B five-year mainline including recent papers/preprints
and journal checks, C corresponding-author papers and author profiles). Exploration never invents a
program, intake or candidate ID.

Default to the actual host's web tools, following their current schema: a GPT
host's built-in web/search tools (`web.run`, `web_search`, or an exposed
equivalent), or under Wisp Science its browser tools (`browser_setup`,
`web_open_tab`, `web_scan`, `web_execute_js`, `web_screenshot`,
`web_save_assets`). When a portal returns an empty shell or requires dynamic forms, immediately
switch to actual interaction; do not finish that source after static attempts alone.
On GPT use an exposed native interactive browser/computer tool first (inspect its
schema; web.run is search/read, not form input). On Wisp use Browser Use:
browser_setup → web_open_tab → web_scan → web_execute_js to fill name variants,
institution and dates, submit, wait, inspect results, paginate and open details.
Discover deferred tools if needed; an already available equivalent browser may be
used with its real provider recorded. Never install a backend automatically.
If no interactive tool exists, report missing host capability distinctly from a
website access failure. Follow [the mandatory interaction procedure](../advisor-pipeline/references/browser-research-policy.md#动态检索交互).
Two static failures do not consume the two distinct interactive attempts allowed.
Stop for CAPTCHA/login requiring human intervention; never bypass them. Follow the
pipeline capability detection and evidence rules; built-in web retrieval is
`static_web`, and Wisp Science browser retrieval is `browser` with
`retrieval_provider: wisp_science_browser` — neither proves that Browser Use is
installed. API credentials are optional accelerators: check them with
`advisor-pipeline/scripts/credentials.mjs --check`, use only the status words,
and never ask the user to paste a key into the chat.
Public browsing does not authorize deep investigation of unconfirmed targets,
personal uploads, messages, applications, installations or paid services.
Application materials retain their original exact-target, real-CV and
explicit-confirmation gates.

Use the repository's Pixi environment (`platforms = ["linux-64"]`) for executable
tasks. Follow the pipeline bootstrap instructions when copying these shared
Skills into a project. The main research deliverable is a simple HTML report in
`outputs/`, named for the discipline and research direction; generate it from the
shared records with `advisor-pipeline/scripts/build_advisor_report.mjs`. Excel
exports are supplementary.
Place direct item-level source links alongside the corresponding papers,
projects, doctoral records, eligibility, deadline and comparison claims. Resolve
them from shared evidence IDs; do not rely only on a source list at the end.
Missing or unknown sources remain pending verification, and external links use
safe HTTP(S) URLs. Display order is never a PI quality ranking, and no total
score, training-fit, resource, personal-funding or training-environment
judgement is produced.

## Medical report scope

Follow [the shared medical report contract](../advisor-pipeline/references/medical-profile.md).
Use three modules: identity; research mainline including recent papers, preprints
and journal-publication checks, plus recent academic conferences/talks;
corresponding-author papers and their authors.
Do not investigate or render collaborator profiles or research grants, and do
not treat missing grant searches as incomplete work. Preserve historical records.
Include past-five-year papers when the advisor's corresponding/co-corresponding
role is verified, regardless of the first author's degree or unknown identity.
Record first/co-first names from the paper; known public roles are optional
context, never an inclusion requirement. Coauthorship alone does not establish
supervision. Check the attributable lab website and record sources and dates.
Generate the shared HTML and supplementary Excel from the same records.

In medical module 02, also search public conferences, forums and seminars from
the past two years. Follow the shared medical contract’s “近期学术会议与演讲”
section: preserve exact talk titles and sources, separate upcoming events, and
distinguish a scheduled speaker from a confirmed delivered talk.
