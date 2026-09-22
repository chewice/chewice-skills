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
