# Migration Policy

Use `adopt` for an existing project.

- Inspect before writing.
- Preserve existing paths, naming, README, AGENTS, environment, and data layout.
- Add missing control files around the project.
- Do not create missing profile analysis, code, data, or output directories;
  list them as recommendations only. Profile directories are created by
  `init`, not by default `adopt`.
- Write merge suggestions for existing AGENTS and `.gitignore` files.
- Record path mappings in `docs/ai_context/project_structure.md`.
- Do not move data, rename scripts, rewrite history, or initialize Git unless
  explicitly requested.
- Run adoption twice; the second dry-run should propose no new files.

If an existing file conflicts with a required control file, stop and ask for a
merge decision instead of overwriting by default.

For manifest schema `0.1.0` or `0.2.0`, preserve existing project and database
IDs, add the `0.3.0` portfolio fields, and require a reviewed migration before
writing the manifest. Fix `portfolio_year` at adoption time. Do not infer a
project ordinal from a title alone; read the annual portfolio and stable IDs.
