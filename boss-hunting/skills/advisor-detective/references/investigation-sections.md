# Canonical selectable advisor investigation sections

This is the shared Web and direct-CLI option catalog. Use the exact order,
stable section IDs and labels below; mode-specific defaults come from the
shared project-contract catalog. A CLI Agent must display the rendered
catalog rather than asking the user to invent a free-form investigation scope.

## Generic Detective starting defaults

These sections are checked by default when the user reaches Advisor Detective.
Finder may already have low-cost facts for them; Detective must reuse current
evidence and query only missing, stale, or conflicting fields. The user may
uncheck one after seeing a warning that the background check may be incomplete
or stale.

| ID | Label |
| --- | --- |
| `identity_current_role` | 基础身份与当前职位 |
| `recent_research` | 最近三年研究兴趣与方向 |
| `current_projects_recruiting` | 近期项目与招生状态 |

The objective application-feasibility pass is required for shortlisted
advisor-program combinations and remains separate from these background-check
checkboxes.

## Detective selections

| ID | Label | Typical sources |
| --- | --- | --- |
| `research_output_trend` | 研究产出与趋势 | Papers, Scholar, dblp, OpenReview |
| `group_members_outcomes` | 课题组成员及去向 | Lab roster, theses, alumni pages, public profiles |
| `guidance_group_ecology` | 指导环境与组内生态 | Identified accounts, community leads, public discussions |
| `work_style_pressure` | 工作方式与压力 | Identified accounts and carefully labelled community leads |
| `resources_career_support` | 资源、funding、署名与职业支持 | Grants, acknowledgements, alumni outcomes, public accounts |
| `integrity_public_controversies` | 学术诚信与公开争议 | Retractions, corrections, institutions, primary records |
| `international_student_support` | 国际学生支持 | Group roster, alumni outcomes, identified accounts |
| `collaboration_industry_network` | 合作者、产业和职业网络 | Papers, grants, labs, company and university announcements |

## CLI selection menu

Display all options in this exact order:

| No. | ID | Label | Initial state |
| ---: | --- | --- | --- |
| 1 | `identity_current_role` | 基础身份与当前职位 | selected by default |
| 2 | `recent_research` | 最近三年研究兴趣与方向 | selected by default |
| 3 | `current_projects_recruiting` | 近期项目与招生状态 | selected by default |
| 4 | `research_output_trend` | 研究产出与趋势 | not selected |
| 5 | `group_members_outcomes` | 课题组成员及去向 | not selected |
| 6 | `guidance_group_ecology` | 指导环境与组内生态 | not selected |
| 7 | `work_style_pressure` | 工作方式与压力 | not selected |
| 8 | `resources_career_support` | 资源、funding、署名与职业支持 | not selected |
| 9 | `integrity_public_controversies` | 学术诚信与公开争议 | not selected |
| 10 | `international_student_support` | 国际学生支持 | not selected |
| 11 | `collaboration_industry_network` | 合作者、产业和职业网络 | not selected |

Accept concise replies such as `keep defaults + 5,6,10`, `1,2,3,9`, `all`, or
`none`. `none` must pause the workflow because Detective cannot start with zero
sections. Removing options 1, 2, or 3 requires a completeness warning.

## Cost level

Use the same estimate as the Web UI:

```text
work units = selected advisor-program rows * selected sections
low: work units <= 8
medium: work units 9-24
high: work units > 24
```

This is a qualitative time and token warning, not a price quote.

## Community-source consent trigger

The Web flow treats these sections as community-relevant:

- `guidance_group_ecology`
- `work_style_pressure`
- `resources_career_support`

For generic or explicitly `sourcePolicy: community_allowed` research, when any
is selected, ask a separate yes/no question about local third-party
community-source download and parsing. The default is no. Declining does not
remove the section and does not block research from other public sources.

Medical projects never trigger this question: none of the five medical modules
is community-relevant, and medical `sourcePolicy` defaults to `public_only`.
A user must explicitly expand the source policy before the independent
community consent mechanism applies. Browser permission does not bypass either
the candidate/section confirmation or source-policy gate.

## Medical five-module menu

Medical / biomedical projects do not use the generic catalog above. The
renderer (`getDetectiveSectionCatalog`) returns exactly these five public-
evidence modules, all selected by default. Training fit, lab resources,
doctoral personal funding, training environment / atmosphere, applicant
ability and overall quality scores are not selectable and are not investigated.

| No. | ID | Label | Initial state |
| ---: | --- | --- | --- |
| 1 | `identity_research_positioning` | A. 导师身份与当前科研定位 | selected by default |
| 2 | `research_mainline_5y` | B. 近五年科研主线与研究路线 | selected by default |
| 3 | `collaboration_network` | C. 科研合作网络 | selected by default |
| 4 | `latest_signals_projects` | D. 最新公开研究动向与项目支撑 | selected by default |
| 5 | `doctoral_trajectory` | E. 博士培养轨迹 | selected by default |

Module scope (details in
[medical-profile.md](../../advisor-pipeline/references/medical-profile.md)):

| ID | Public-evidence scope |
| --- | --- |
| `identity_research_positioning` | Current institution / department / position, official profile, identifiers and name variants, current research positioning, the minimum doctoral-supervision link (graduate school / doctoral programme / supervisor listing); earlier institutions are preserved as history |
| `research_mainline_5y` | Long-term scientific question, continuing themes, new directions, research objects and methods, recent shift, representative works with verified roles; participation-only works listed separately and not counted as the mainline; five-year back-search window |
| `collaboration_network` | Depth-1 ego network of core collaborators using the repeated-collaboration heuristic; collaboration edges (co-authorship / shared project / grant / trial) kept apart from research-neighbour edges (citation / co-citation / similarity); consortium papers filtered; collaborators are described, never investigated recursively |
| `latest_signals_projects` | Latest papers and preprints (flagged), public project records with the fixed field list (title, project id, funding body, PI role, period, status, published amount + unit), registries and trials; `not_found` in a public database never means "no funding" |
| `doctoral_trajectory` | Verified current and former doctoral students, supervision evidence, topics, outputs, first public destination, latest public role and information date; graduate-programme mapping; no graduation rate, destination rate or training success rate; an emerging PI without graduates is not a negative signal |

Mentoring style, feedback speed, working hours, atmosphere, resources,
personal funding and applicant fit remain out of scope; do not infer them from
lab size, title, names, citations or platform presence. Corrections,
retractions and institutional announcements are recorded as formal records
with source independence preserved.

Legacy medical drafts that still name generic section IDs are re-scoped to the
five modules during normalization; the earlier confirmed snapshot is kept as
history but no longer counts as current confirmation.

## Guidance and group ecology subdimensions

When selected, organize findings under:

1. 人品与边界：尊重、信用、权力边界。
2. 指导与判断力：research guidance、方向稳定性、反馈质量。
3. 工作方式：节奏、push 程度、学生自主性。
4. 资源与回报：funding、算力、署名、推荐信和职业发展是否公平。
5. 组内生态：学生流动、转组或退出、公开可核实的组内体验。

Do not calculate a personality score from anonymous reports. Store supported
findings, conflicting accounts, and unresolved risks.

## Empty values

- Selected and checked with no reliable information: `检查后未找到可靠公开信息`.
- Not selected: `用户未选择复核`.
- Blocked by access or extraction failure: `未完成核验` plus the reason.
- Conflicting accounts: preserve both and mark `存在冲突`.
