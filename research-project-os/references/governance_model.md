# Governance Model

## Core rule

Treat Agents as temporary executors and project files as durable memory.

Research Project OS governs lifecycle state; it does not replace specialized
workflows for environments, code organization, data acquisition, scientific
analysis, literature retrieval, or figure export. Register durable outputs
from those workflows here only when they affect provenance, evidence,
decisions, or the next handoff.

## Control layers

| File or directory | Responsibility |
| --- | --- |
| `AGENTS.md` | Mandatory repository-local behavior |
| `project_manifest.yaml` | Machine-readable source-of-truth and path index |
| `docs/ai_context/` | Durable context, policies, tasks, questions, decisions |
| `CURRENT_HANDOFF.md` | Current checkpoint and next minimum action |
| `docs/handoffs/archive/` | Immutable prior checkpoints |
| `reports/evidence_registry.yaml` | Evidence claims, validation, and limits |
| `work/notion_sync/` | Reviewable synchronization queue |

## Standard loop

```text
load context
→ define question and boundary
→ explore
→ create candidate result
→ make execution reproducible
→ validate
→ register evidence
→ approve decisions
→ close session and archive handoff
→ inspect Git diff
→ human-reviewed commit
```

Do not infer scientific truth from a structurally valid project.
