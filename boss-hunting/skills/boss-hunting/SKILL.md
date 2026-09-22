---
name: boss-hunting
description: >
  Find and compare doctoral advisors using public evidence. Supports medical and
  biomedical research discovery without a CV, application screening with real
  applicant background, and the existing general advisor workflow. Use when
  the user asks Boss Hunting to discover advisors, compare research and training
  fit, or resume an advisor search. Skill development requests do not start a search.
---

# Boss Hunting

This is the named entry to the existing workflow, not a separate system. Read
[Advisor Pipeline](../advisor-pipeline/SKILL.md) and follow its mode-specific
references. Use the same `project.json`, shared records, builders and confirmation
gates. The `advisor-pipeline` path remains a compatible entry for existing projects.

For medicine, collect only missing information in this order: medical field;
disease/mechanism, research approach and training goals; regions and applicable
entry routes; discovery and evidence comparison. Do not infer existing experience
from desired training. Exploration does not require a CV or an invented program.

Default to the actual host's web tools, following their current schema: a GPT
host's built-in web/search tools (`web.run`, `web_search`, or an exposed
equivalent), or under Wisp Science its browser tools (`browser_setup`,
`web_open_tab`, `web_scan`, `web_execute_js`, `web_screenshot`,
`web_save_assets`). Use official static pages/APIs as fallback and an already
available interactive browser only when dynamic JS/forms require it. Follow the
pipeline capability detection and evidence rules; built-in web retrieval is
`static_web`, and Wisp Science browser retrieval is `browser` with
`retrieval_provider: wisp_science_browser` — neither proves that Browser Use is
installed.
Public browsing does not authorize deep investigation of unconfirmed targets,
personal uploads, messages, applications, installations or paid services. Application materials retain their
original exact-target, real-CV and explicit-confirmation gates.

Use the repository's Pixi environment (`platforms = ["linux-64"]`) for executable
tasks. Follow the pipeline bootstrap instructions when copying these shared
Skills into a project. The main research deliverable is a simple HTML report in
`outputs/`, named for the discipline and research direction; generate it from the
shared records with `advisor-pipeline/scripts/build_advisor_report.mjs`. Excel
exports are supplementary.
Place direct source links alongside the corresponding research, funding,
training, eligibility, deadline and comparison claims. Resolve them from shared
evidence IDs; do not rely only on a source list at the end. Missing or unknown
sources remain pending verification, and external links use safe HTTP(S) URLs.
