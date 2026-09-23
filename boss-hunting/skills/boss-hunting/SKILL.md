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
`web_save_assets`). When a portal returns an empty shell or requires dynamic forms, immediately
switch to actual interaction; do not finish that source after static attempts alone.
On GPT use an exposed native interactive browser/computer tool first (inspect its
schema; web.run is search/read, not form input). On Wisp use Browser Use:
browser_setup → web_open_tab → web_scan → web_execute_js to fill name variants,
institution and dates, submit, wait, inspect results, paginate and open details.
Discover deferred tools if needed; an already available equivalent browser may be
used with its real provider recorded. Never install a backend automatically.
If no interactive tool exists, report missing host capability distinctly from a
website access failure. Follow [the mandatory interaction procedure](../advisor-pipeline/references/browser-research-policy.md#动态基金库查询必须执行).
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

## Minimal medical report and grant-search evidence

Per-advisor official grant-database searching and its recorded process are mandatory baseline work for every medical report, even when the user never mentions grants. Do not require an extra prompt, a selected Detective section, or a deep-investigation request to include this baseline. Silence is not an exclusion; only an explicit user restriction can narrow it, and each excluded, blocked or unfinished search must still appear with its reason in a partial report.

For a medical report, follow [the shared report contract](../advisor-pipeline/references/medical-profile.md#证据与续跑). Each advisor needs regional official grant-database searches using name variants and institution, covering active and past-five-year projects. Store the actual query, dates, scope, status, limitations and sources in `latestSignals.projectSearches[]`; store found grants in `projects[]`. Supplementary institutional/search-engine pages do not complete a database search. Respect user-selected investigation scope; report missing or blocked searches as partial, never infer “no grants” from empty data. Use descriptive `citation_label` links and separate appointment verification, page access and page update dates. Generate the shared minimalist HTML with five readable modules; do not replace it with custom decorated HTML.

For collaborator selection and concise profiles, follow the medical contract: one documented, direction-relevant collaboration may suffice; report only who the scholar is, current appointment, research direction, and concrete joint projects and outputs with links.

Medical minimum reports also include the [doctoral first-author and lab-website checks](../advisor-pipeline/references/medical-profile.md#博士指导第一作者画像与实验室网站默认最低内容), without an extra user request. Verify the advisor's corresponding/co-corresponding role and first/co-first authors on papers from the past five years; summarize only those joint papers. Seek an attributable lab website and check members/alumni/publications. First authors are not automatically doctoral students; preserve independent identity evidence, dates, sources and search gaps in `doctoralTrajectory`.

报告导航与分区：沿用共享 HTML 生成器的五模块卡片及 01–05 编号，使用米白画布、暖白卡片、浅卡其目录及深陶土色链接。桌面左侧垂直居中的紧凑悬浮目录（宽 216px、距左 16px、最大高度 70vh、内部滚动，正文留出空间）可跳到导师和模块，窄屏使用顶部折叠目录。保持离线单文件、系统字体；只允许内置导航脚本的 CSP 哈希，不加载外部框架。基金过程仍默认展开，打印隐藏目录。
