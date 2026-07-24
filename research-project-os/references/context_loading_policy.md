# Context Loading Policy

At session start, load in this order:

1. The nearest applicable `AGENTS.md`.
2. `project_manifest.yaml`.
3. `CURRENT_HANDOFF.md`.
4. The manifest's required context files.
5. Relevant tasks, questions, decisions, and evidence only.
6. Git status.
7. Notion summaries only when synchronization is configured.

Do not load every report, notebook, or archived handoff by default. Use the
manifest and current task to select context. Treat `CURRENT_HANDOFF.md` as a
checkpoint, not a substitute for source evidence.
