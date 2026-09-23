---
name: boss-hunting
description: >
  Find and compare doctoral advisors using public evidence. Supports medical and
  biomedical research discovery from a scientific question alone (no CV, grades
  or applicant ability), application screening with real applicant background,
  and the existing general advisor workflow. Use when the user asks Boss Hunting
  to discover advisors, map a research direction's PIs and collaboration
  network, compare research-question fit, or resume an advisor search. Skill
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
orchestration: Seeds → PI validation → five-year back-search → collaboration
network → saturation → shortlist → five-module deep dive (A identity and
research positioning, B five-year mainline, C collaboration network, D latest
signals and projects, E doctoral trajectory). Exploration never invents a
program, intake or candidate ID.

Default to the actual host's web tools, following their current schema: a GPT
host's built-in web/search tools (`web.run`, `web_search`, or an exposed
equivalent), or under Wisp Science its browser tools (`browser_setup`,
`web_open_tab`, `web_scan`, `web_execute_js`, `web_screenshot`,
`web_save_assets`). Use official static pages/APIs as fallback and an already
available interactive browser only when dynamic JS/forms require it. Follow the
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
