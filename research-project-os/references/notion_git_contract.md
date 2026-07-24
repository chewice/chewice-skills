# Notion and Git Contract

Git owns code, locks, full handoffs, reports, and evidence details. Notion owns
cross-project navigation, task priority, and human approval after configuration.

Use `ProjectYYYY`; reserve `00｜Research OS Control`. Number project and output
pages with append-only `NN｜title`: allocate `max(existing)+1`, never fill gaps,
renumber, or reuse deleted ordinals. Match stable IDs, not titles. Malformed
titles or duplicate IDs/ordinals are conflicts.

The CLI writes immutable schema `0.3.0` JSON under
`work/notion_sync/{pending,applied,conflicts,superseded}` and never calls
Notion.

After explicit authorization:

1. verify payload source hashes;
2. read the target portfolio and direct children;
3. reuse only exact stable-ID matches and allocate missing ordinals;
4. apply only listed operations;
5. read back titles, parents, metadata, and database IDs;
6. add the application receipt and move the payload to `applied/`.

Move stale payloads intact to `superseded/` or `conflicts/`; never edit them in
place.
