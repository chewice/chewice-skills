# Migration Policy

Run `inspect`, then `adopt` dry-run. Preserve paths, README, `AGENTS.md`,
`.gitignore`, data, environments, and history. Add only the control layer;
profile business directories remain recommendations. Stop on conflicts unless
an explicit control-file overwrite was reviewed. A second dry-run must be
idempotent.

For schema `0.1.0` or `0.2.0`, preserve project/database IDs, add schema `0.3.0`
portfolio fields, and review before writing.

For nested Pixi environments, report paths and evidence. The migration is a
separate authorized workflow:

1. choose one root workspace manifest;
2. group dependencies into root features/environments by compatibility;
3. migrate namespaced tasks with `task.cwd`;
4. regenerate and validate root `pixi.lock`;
5. remove nested manifests, locks, and `.pixi/` only after validation.

Never perform these steps automatically from `inspect`, `init`, `adopt`, or
`audit`.
