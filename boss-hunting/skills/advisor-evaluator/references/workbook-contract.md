# Application-ready workbook contract

The primary deliverable is a concise HTML report named by discipline/direction:
`outputs/{topic}-导师调研.html`, generated directly from shared records with
`node skills/advisor-pipeline/scripts/build_advisor_report.mjs --project-root <project>`
(adjust the installed skills prefix). Excel remains an optional structured
companion. The report uses the same medical comparison rules, a real-project
table, individual advisor briefs, linked claim evidence, and audit limitations.
It requires no external website assets or browser package. Re-exporting reads
local records and does not repeat the investigation.

In the HTML comparison and each information section, place direct, concrete
source links beside each study, resource, research grant, doctoral funding
claim, training outcome, eligibility condition, deadline and comparison reason.
Resolve each item's `sourceIds` / `source_ids` through the shared evidence
records using the field-level rules in
`../../advisor-pipeline/references/core-data-contract.md`. Show short linked
source titles; do not leave the reader to locate the relevant source only in a
page-end list or follow only an internal evidence anchor. Keep the full evidence
section for dates, excerpts and limitations.

Use observed specific record/document URLs with HTTP(S) only and escaped
labels/attributes. Unknown or unsupported items retain `待核验` / `来源待补`;
do not fabricate links, substitute a database homepage or attach an unrelated
advisor source. Preserve the simple content-first layout.

For the general application workflow create `advisor_application_ready_YYYYMMDD.xlsx`.
Medical discovery exports `advisor_research_discovery_YYYYMMDD.xlsx`; medical
application comparison may use `advisor_medical_comparison_YYYYMMDD.xlsx`.
All three shipped builders keep their `--input` / `--output` CLI and select
the medical sheets from `input.project` (or `input.config`, or top-level)
`domainProfile: medical`, `evaluationMode: evidence_profile`, `searchMode`.

## Medical evidence profile

The medical path exports shared facts through `medical-workbook.mjs`. It does
not calculate, import, or display the general fit/profile/overall score or
reach/match/safer quotas. `rank` is only `display_order`; `rankingMode` is
`evidence_profile`, and any score compatibility fields remain `null`.

- Discovery accepts `advisorRecords` / `advisor_records` projected from
  `outputs/advisor_records.json`, with unique real `advisor_id`; the
  `1_医学方向探索` sheet is an advisor view. It never invents program, intake,
  or `advisorProgramId`. The selector also derives `outputs/discovery-view.json`
  from these records; this view is not an application-material target list.
- Real mapped `candidates` / `applicationRows` / `advisors` use the separate
  program comparison sheet. Application rows require `advisorProgramId`.
  One advisor with two real programs/intakes remains two rows.
- Columns cover current role/homepage; disease/mechanism, research approach,
  scientific question; scientific fit and desired training support; recent
  studies; actual program, degree, intake, route, rotation and contact rules;
  eligibility and opportunity; resource access levels; separate research
  funding and doctoral funding; doctoral outcomes and sample limits; training
  environment; unknowns, supported risks, next verification, sources and dates.
- Exploration application fields say `本次未核验`. Missing numeric values are
  blank, never zero. Missing section results remain `not_checked`; selecting
  a section does not prove it was researched.
- `evidenceProfile.scientificFit.status` is `strong`, `partial`, `adjacent`,
  `mismatch`, or `insufficient_information`; `trainingFit.status` is
  `supported`, `partial`, or `unknown`. Each includes reasons and source IDs.
  Existing researched records use the `evidence_profile` projection spelling.
- `comparisonGroup` is `actionable`, `needs_verification`, `follow_up`, or
  `not_applicable`. Sort by supported scientific/desired-training relevance,
  then stable name. Evidence coverage and prior numeric scores do not sort.
  Strong relevant sparse records stay pending; budget-deferred records are
  distinct from explicit inapplicability.
- Eligibility, hard constraints and open/closed claims require their matching
  `eligibilityEvidence` / `hardConstraintEvidence` / `opportunityEvidence`:
  verified status, source IDs and this exact `advisorProgramId`; an intake
  in the evidence must match the row. Otherwise they remain pending/unknown.
  An old closed advert cannot close a different intake. Discovery does not
  certify personal eligibility.
- Sources include claim type, supported fields, status, title, URL, source
  update/access dates, intake, excerpt/locator, read depth, retrieval method,
  extraction status, same-source group and limitations. Verified HTTP(S)
  URLs are clickable exporter-authored hyperlinks. External cell text is
  never accepted as a formula or as a serialized formula object.

General `ranking.json` keeps its existing array, `{rankings: [...]}`, and
`{ranking: [...]}` compatibility. A current medical comparison uses an envelope:
`{rankingMode: "evidence_profile", confirmedRevision, confirmedFingerprint,
rankings: [...]}`, tied to the current investigation confirmation. Each medical
row uses real candidate IDs and the mode/display semantics above. Old or
unstamped medical rankings remain visible as historical traces but cannot
supply current ordering, eligibility, or application-material targets.
Advisor-only exploration may export without a ranking and never contributes
fake IDs to this material-selection artifact.
The HTML exporter merges a current confirmed evaluation into the matching
candidate by ID, preserving real advisor/program/degree/intake identity. Its
updated research/training reasons, risks, unknowns and next actions appear in
both the comparison and the advisor brief. Unknown or repeated evaluation IDs
and identity changes are rejected. The comparison shows readable reasons and
evidence links rather than raw source-ID objects.

The following sheets and scoring rules describe the preserved **general**
workflow only.

## Row grain

Each primary row represents one real:

`school × program × degree/intake × advisor`

Do not collapse multiple programs for one advisor into one ambiguous row.

## Sheet 1: 申请就绪总表

Use these columns:

1. 申请优先级
2. 学校名称
3. QS 综合排名
4. QS 版本
5. 专业名称（中文）
6. Program Name (English)
7. 学位与申请季
8. 专业链接
9. 申请截止日期
10. 学费
11. 奖学金项目
12. 申请要求及材料
13. RP 字数要求
14. 导师姓名
15. 导师研究方向（论文）
16. 导师邮箱
17. 导师官网链接
18. 导师招生与联系要求
19. 研究匹配分
20. 履历匹配分
21. 综合匹配分
22. 申请定位
23. 硬条件状态
24. 硬条件依据
25. 申请路径
26. 机会状态
27. 建议下一步
28. 客观申请可行性
29. 背调结论
30. 风险与信息缺口
31. 最后核实日期
32. 关键官方来源

Use multiline cells for application materials, scholarships, advisor
requirements, research, backcheck findings, and gaps.

## Other sheets

- `2_研究匹配与选择`: research/profile/overall scores, hard conditions,
  pathway, opportunity, action, fit evidence, and user selections.
- `3_背调证据`: selected section, finding, evidence strength, conflict state,
  URL, and access date.
- `4_申请来源与时效`: field-level official sources, dates, and stale/missing
  fields.
- `5_配置与说明`: user constraints, selected sections, scoring weights,
  evidence rules, and disclaimers.

## Scoring

- Keep research fit numeric and auditable.
- Keep unknown scores blank; do not coerce them to zero.
- Hard failures, objective ineligibility, and verified-closed opportunities are
  excluded before any score. Unknown hard conditions remain pending.
- Treat `reach`/`match`/`safer` as portfolio labels, not admission probability.
- Keep objective feasibility categorical and show failure reasons.
- Score only Detective dimensions that the user selected consistently for the
  compared advisors.
- Do not treat `not_found` as zero.
- Do not normalize away a severe verified risk. Display it separately even
  when the total score is high.
- Anonymous leads cannot directly change a score without independent
  corroboration.

## Formatting

- Freeze the primary header and the first identifying columns.
- Enable filters.
- Use conditional formatting for feasibility and risk.
- Store dates, ranks, tuition numbers, and scores as typed values when known.
- Keep source URLs as plain text.
- Verify formula cells and scan for Excel errors before delivery.
