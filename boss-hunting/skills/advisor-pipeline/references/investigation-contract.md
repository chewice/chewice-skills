# Detective selection and result contract

Read this reference only for Detective selection, confirmation, execution,
result validation, or migration.

## Draft versus authorization

Checkbox/menu changes update only `investigation.draft`. Network research and
community-cache operations require a current non-empty confirmed snapshot:

```json
{
  "investigation": {
    "draft": {
      "selectedAdvisorProgramIds": [],
      "selectedSections": [],
      "communitySources": {"requested": false},
      "revision": 1,
      "updatedAt": "ISO-8601"
    },
    "confirmed": {
      "selectedAdvisorProgramIds": [],
      "selectedSections": [],
      "communitySources": {"consented": false, "consentedAt": null},
      "revision": 1,
      "confirmedAt": "ISO-8601",
      "fingerprint": "sha256",
      "source": "user_confirmed"
    }
  }
}
```

The confirmed revision and fingerprint must match the current draft. A draft,
count, professor name, or Top N instruction is not authorization.

Schema 9+ also stores `sourcePolicy: public_only|community_allowed` and
`researchScopeFingerprint` in both draft and confirmed snapshots. Medical defaults
to public_only. None of the five medical modules is community-relevant, so
medical projects never request community files or trigger community consent;
`communityRefreshEligibility` reports `不需要社区资料` even under
`community_allowed`. General legacy confirmations retain their original
fingerprint semantics.

Medical mode/field/disease-question/target/background/degree/intake/constraint
changes update the research-scope fingerprint and invalidate prior confirmation.
This does not erase previous findings. Normalize project metadata before checking
confirmation. Browser availability and permission never substitute for this gate.

Section catalogs come from `getDetectiveSectionCatalog(project)` and defaults
from `defaultDetectiveSections(project)` in project-contract.mjs; Web and CLI
must use that shared catalog:

- Generic projects: the 11-item catalog (`GENERIC_DETECTIVE_SECTIONS`) with the
  three legacy defaults; `COMMUNITY_SECTION_IDS` apply only here.
- Medical projects (schema 10): the five-module catalog
  (`MEDICAL_DETECTIVE_SECTIONS`), all selected by default —
  `identity_research_positioning` (A), `research_mainline_5y` (B),
  `collaboration_network` (C), `latest_signals_projects` (D),
  `doctoral_trajectory` (E). `confirm_investigation.mjs` rejects generic
  section IDs for medical projects.

Schema 10 migration: a medical `investigation.confirmed` snapshot that still
lists generic section IDs (for example `recent_research`,
`resources_career_support`) is kept as historical data but the project returns
to draft with the five medical modules; medical drafts with generic IDs are
re-scoped the same way. `medicalProfile.currentSkills` / `desiredTraining` are
deleted during migration.

After displaying the exact summary and receiving explicit confirmation, run:

```bash
node .agents/skills/advisor-pipeline/scripts/confirm_investigation.mjs \
  --root "$PWD" --confirmed-by-user \
  --advisor-id advisor-program-id \
  --section identity_current_role --community no
```

Use repeated or comma-separated exact IDs/sections. The script validates IDs
against `outputs/candidates.json`, writes a backup, and creates the revision-
bound fingerprint. Never set `confirmed` by hand.
`--source-policy public_only` explicitly retains the medical public scope;
`--source-policy community_allowed --community yes` is only for a separately
requested and user-confirmed extension. Unmapped advisor discovery records do not
enter this exact advisor-program confirmation path.

For schemaVersion 3 migration, non-empty selections without a real
`detective-results.json` remain draft-only. A real non-empty legacy Detective
artifact may be restored only as `source: legacy_artifact`; old checkbox
consent alone does not prove community authorization.

## Detective result artifact

`outputs/detective-results.json` is complete only when it belongs to the
confirmation that launched it:

```json
{
  "confirmedRevision": 3,
  "confirmedFingerprint": "sha256 of confirmed snapshot",
  "generatedAt": "ISO-8601",
  "selectedSections": ["identity_current_role"],
  "communitySources": {"consented": false},
  "results": [
    {
      "advisorProgramId": "advisor-program-id",
      "name": "Real Name",
      "sections": {
        "identity_current_role": {
          "status": "completed",
          "summary": "...",
          "sourceIds": []
        },
        "work_style_pressure": {
          "status": "not_completed",
          "summary": "why it could not be completed"
        }
      },
      "evidenceCount": 0
    }
  ],
  "evidenceCount": 0,
  "evidenceCoverage": 0
}
```

Every confirmed advisor needs a row. Every selected section needs a conclusion
or explicit `not_completed` reason. Missing keys, old revisions, or old
fingerprints are unfinished, not completed.

## Medical subagent outputs and merge

Medical deep dives may be split across subagents (Seed Scouts, Identity
Resolver, Trajectory Mappers, Network Expander, Regional Project Investigator,
Doctoral Trajectory Investigator, Evidence Auditor). Each writes exactly one
run-local file `runs/<run-id>/subagents/<task_id>.json`:

```json
{
  "task_id": "identity-001",
  "agent_role": "identity_resolver",
  "scope": {"module": "identity_research_positioning", "advisor_id": "…", "network_round": 0, "discovered_via": "research_seed"},
  "findings": [{"entity": "advisor_id", "claim": "…", "claim_type": "fact", "status": "verified|partial|not_found|not_checked|inaccessible|conflict|stale|not_applicable", "fields_supported": ["current_institution"], "source_ids": ["s1"], "excerpt": "…", "reading_depth": "detail", "page_locator": "…"}],
  "new_entities": [{"entity_type": "advisor|evidence", "advisor_id": "…", "identifiers": {"orcid": "…"}}],
  "conflicts": [{"entity": "advisor_id", "field": "current_institution", "claims": ["…", "…"]}],
  "gaps": ["…"],
  "queries_executed": ["…"],
  "sources_checked": [{"source_id": "s1", "url": "https://…", "final_url": "https://…", "page_title": "…", "accessed_at": "ISO-8601", "retrieval_method": "static_web|official_api|browser", "retrieval_provider": "…", "retrieval_tool": "…", "extraction_status": "success|partial|blocked|failed"}]
}
```

`verified` findings must cite `source_ids` that exist in `sources_checked`.
Subagents never write `outputs/`. The Main Agent runs
`merge_subagent_findings.mjs --root <project> --run-id <run-id> [--dry-run]`,
which validates every file, refuses files containing a credential value,
deduplicates advisors (`advisor_id` / ORCID / OpenAlex id) and evidence
(URL + entity + fields + claim), converts field disagreements and declared
conflicts into `status: conflict` evidence with
`resolution: pending_main_agent_adjudication`, strips removed fields, and
writes `outputs/advisor_records.json`, `outputs/evidence.json` and
`runs/<run-id>/merge-report.json` under the project file lock.

## 医学报告：逐位基金检索（兼容增补）

此项是默认最小交付，不以用户 prompt 是否提及基金为条件，也不以另选深查维度为前提。每位纳入报告的导师都需展示实际检索过程；明确排除、受阻或未完成也须逐位说明，不得静默省略。

`evidenceProfile.latestSignals.projectSearches[]`（兼容 snake_case）记录：

```json
{"database":"NIH RePORTER","query":"姓名变体 + 机构；实际筛选条件","checkedAt":"2026-09-23","scope":"当前在研及2021-09-23至2026-09-23项目","status":"not_found","sourceKind":"official_database","limitations":"仅所列姓名与机构范围","sourceIds":["该导师的检索证据ID"]}
```

- `status`: `found` / `not_found` / `inaccessible` / `partial` / `not_checked`。未找到仅指实际查过的范围。
- `sourceKind`: `official_database` 或 `supplementary`；公告、搜索引擎等为补查。未记录类别不推断为官方检索。
- 每条必须记录库名、姓名与机构查询、日期、范围、状态、限制及 sourceIds。完成官方检索需对应导师的可访问 URL 证据，found 对应 verified，not_found 对应 not_found；受阻、缺字段、缺证据均保留未完成提示。
- `projects[]` 保留已发现项目；空数组不代表完成检索。旧记录无需迁移即可导出部分报告。
- 增量合并只追加项目与检索记录、补空字段、合并来源引用；同一项目字段冲突保留原值并写 conflict，其他研究事实不被替换。历史受阻记录保留；主 Agent 核实后可明确整理有效检索记录，不能静默删除限制。
- evidence 的可选 `citation_label` 是人类可读来源名；与 `page_title`、`accessed_at`、`source_updated_at` 一同保留。任职核对日期与网页日期独立。

## 博士指导增补字段

在 `evidenceProfile.doctoralTrajectory` 增加下列兼容字段（亦接受 snake_case），复用 `evidence.json`，不另建事实源：

- `firstAuthorProfiles[]`: `{personId, name, identityStatus, publicRole, identitySourceIds, researchSummary, summarySourceIds, sourceIds, papers[]}`。`personId` 是消歧后稳定身份键；同名未确认者使用不同键。`identityStatus: verified` 和独立身份来源才支持展示 publicRole，否则显示身份待核实。不得从共同署名自动生成博士生身份。
- `papers[]`: `{title, doi, url, date, year, firstAuthorRole, advisorRole, roleStatus, sourceIds}`。角色分别使用 `first_author|co_first_author` 与 `corresponding_author|co_corresponding_author`；`roleStatus: verified` 需已读署名依据。sourceIds 引用共享 evidence_id（不是查询工具的局部 source_id）。方向总结的 summarySourceIds 必须来自符合条件的论文。
- `labWebsites[]`: `{url, title, relationshipStatus, status, sourceIds, pages[]}`；`relationshipStatus: verified` 需网站归属依据。`pages[]`: `{url, title, status, accessedAt, updatedAt, limitations, sourceIds}`。页面更新时间缺失不以访问时间代替。
- `searches[]`: `{kind, database, query, checkedAt, windowStart, windowEnd, status, limitations, sourceIds}`；kind 为 `corresponding_papers|lab_website`，status 为 `found|not_found|inaccessible|partial|not_checked`。`checkedAt` 用 YYYY-MM-DD；论文窗口截至此日并向前五年（闰日按二月末日），明确保存实际起止日期。不同窗口、未知日期或边界年份待核实的论文保留为线索，不冒充近五年画像。

增量合并按 personId、论文 DOI/URL、网站 URL、查询类型与日期关联，缺少人物身份键只对完全相同记录去重，绝不按姓名合并。补空字段、合并来源与新增论文，已有标量冲突保留原值并进入 conflict，须主 Agent 裁决；不覆盖既有博士生记录。HTML 和 Excel 投影保留导师级新补查，不能被旧申请记录遮住。首次补入人物记录时即保存必要身份和署名核验状态；更新冲突不静默升级为 verified。
