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

Schema 9 also stores `sourcePolicy: public_only|community_allowed` and
`researchScopeFingerprint` in both draft and confirmed snapshots. Medical defaults
to public_only. Selecting resources or training dimensions in this mode does not
request community files or trigger unrelated community consent. To extend scope,
explicitly select community_allowed and separately request/confirm community use;
the existing cache authorization remains mandatory. General legacy confirmations
retain their original fingerprint semantics.

Medical mode/field/target/training/background/degree/intake/constraint changes
update the research-scope fingerprint and invalidate prior confirmation. This
does not erase previous findings. Normalize project metadata before checking
confirmation. Browser availability and permission never substitute for this gate.
Medical section defaults come from `defaultDetectiveSections(project)` and menus
from `getDetectiveSectionCatalog(project)` in project-contract.mjs; Web and CLI
must use that shared catalog. The default seven sections cover identity, recent
research, current projects, research trajectory, doctoral outcomes, resources,
and collaboration. They do not silently include personality/community research.

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
