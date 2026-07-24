# Notion and Git Contract

## Authority

| Content | Authority |
| --- | --- |
| Code, lock files, full handoffs, reports, evidence details | Git |
| Task priority and human approval | Notion after configuration |
| Summary project state | Synchronize only without conflict |

## Portfolio hierarchy

Use `ProjectYYYY` for the adoption year. Reserve `00｜Research OS Control` for
shared databases. Project and output pages use `NN｜title`, where `NN` is at
least two digits.

- Allocate with `max(existing)+1` among direct children.
- Start projects and project outputs at `01`; reserve project ordinal `00`.
- Never renumber pages, fill gaps, or reuse deleted ordinals.
- Identify pages by stable metadata, not title alone.
- Treat malformed titles, duplicate ordinals, duplicate stable IDs, or a
  matching title without the expected marker as conflicts.

Number `project-adopt`, every meaningful `session-close`, and explicit
`milestone` or `full-state` outputs. Keep Tasks, Questions, Decisions and
Evidence as shared database records linked from output pages.

## Review-first behavior

Generate JSON under:

```text
work/notion_sync/
├── pending/
├── applied/
├── conflicts/
└── superseded/
```

The CLI does not call Notion. Schema `0.3.0` payloads include source hashes, a
Git commit when available, `notion_target`, allocation policy, stable IDs and
explicit operations. Treat pending payloads as immutable.

An Agent may apply a reviewed payload through Notion MCP only after explicit
authorization. It must:

1. Read the pending payload and verify current source hashes.
2. Read the exact portfolio and current direct children.
3. Reuse pages only when the stable ID matches exactly.
4. Allocate missing ordinals using the declared append-only policy.
5. Apply only the listed operations and preserve unrelated content.
6. Read back titles, parents, stable metadata and database IDs.
7. Move the payload to `applied/` with `application.applied_at_utc`, page IDs,
   assigned ordinals and the read-back result.

Move stale or replaced payloads out of `pending/` without editing them in
place. Store the immutable original plus a separate reason/receipt under
`superseded/` or `conflicts/`.
