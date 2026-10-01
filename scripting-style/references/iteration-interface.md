# Skill iteration interface

Read only when the user asks to review new examples or improve `scripting-style`. This is a maintenance entry point, not part of routine analysis generation. Do not create spec or plan documents. Review evidence and approved-decision records serve the maintenance workflow; they are not analysis scaffolding.

## Purpose

Improve the skill from new `.R`, `.py`, `.sh`, or `.ipynb` evidence without allowing one example, historical output, or environment detail to silently rewrite the rules. The deterministic validator checks request shape, paths, hashes, and confirmation fields; semantic comparison and implementation remain the agent's responsibility.

The current request contract remains `schema_version: "1.0"`. The ban on backward-compatibility branches applies to generated project analysis scripts; it does not authorize changing this maintained interface or unrelated tools.

## Example-intake request

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | Yes | Exactly `"1.0"` |
| `iteration_id` | Yes | Readable identifier containing letters, digits, `-`, or `_` |
| `phase` | Yes | `phase1` or `phase2` |
| `target_skill` | Yes | Skill root containing `SKILL.md` |
| `new_examples` | Yes | Supported files or their directories |
| `context_readmes` | No | Explicit `README.md` files used only for task and sequence context |
| `notes` | No | User-provided roles, API boundaries, and exclusions |
| `phase1_review_dir` | Phase 2 | Existing Phase 1 review directory |
| `approval.confirmed` | Yes | `false` in Phase 1, `true` in Phase 2 |
| `approval.accepted_decisions` | Phase 2 | Nonempty decisions traceable to the review |

Each `new_examples` item is a path string or a mapping with `path` and optional `role_hint` and `stage_hint`. The existing `stage_hint` field is context only; it never selects a stage guide. Route comparisons by exact file type.

Run the read-only preflight with a request file or standard input:

```bash
python3 scripts/validate-iteration-request.py /path/to/request.json
python3 scripts/validate-iteration-request.py -
```

It writes a JSON manifest to stdout. It does not create iteration directories, copy examples, change rules, or authorize Phase 2. `phase2_request_complete: true` proves only structural validity, not agreement with review evidence or human approval.

For a direct user-approved rule change without new examples, do not fabricate an example intake or pretend to run a source/holdout audit. Record the reviewed current rules, the user's explicit decisions, actual validation, and evidence limits. Existing approval in the conversation is sufficient; do not request it again.

## Source discovery and privacy

If the supplied directory contains `scripts/` directories, inspect only those; otherwise treat it as a pure example directory. Discover only the four supported extensions. Exclude `.git/`, `.pixi/`, `data/`, `R/`, `resources/`, `softwares/`, `参考文献/`, all hidden directories, `__pycache__/`, and scaffolding such as `setup-vscode.sh`.

An explicit `README.md` explains purpose, order, and input/output relationships only; do not learn its layout, installation, or environment instructions. Excluded project APIs remain opaque.

Source examples are read-only. Review artifacts may contain local paths, so `iterations/` is gitignored. Sanitize personal paths, parameters, private data, and biological conclusions from any evidence prepared for submission. Notes and role/stage hints are reviewer context, not selectors or scientific facts.

For notebooks, the validator hashes bytes but does not validate JSON or execution semantics. Inspect source cells and order in Phase 1; classify or reject malformed artifacts. Stored outputs, execution counts, widgets, and environment metadata are unverified historical state, not current evidence.

## Phase 1: evidence review

For new-example intake:

1. Validate the request and inventory allowed files.
2. Read current rules, the relevant index, and prior validation.
3. Compare each source using its exact-type guide and examples.
4. Distinguish learning candidates, complements, holdouts, counterexamples, and exclusions.
5. Identify supported, conflicting, uncertain, or missing patterns.
6. Propose the smallest useful rule, trigger, template, index, or validation changes.

Do not edit functional rules, references, templates, examples, agent metadata, validator behavior, or committed validation files during Phase 1. Any useful review record belongs under:

```text
iterations/<iteration_id>/phase1/
```

Keep only necessary intake evidence, candidate changes, actual conflicts/exclusions, and learning/holdout separation. Do not create empty reports to complete a folder template. Report the findings and obtain confirmation of proposed changes and evidence boundaries before implementation. When the user already approved the reviewed changes in the conversation, proceed within that scope.

## Phase 2: implement approved decisions

For example-intake requests, require `phase: phase2`, `approval.confirmed: true`, an existing `phase1_review_dir`, nonempty traceable `accepted_decisions`, and explicit confirmation in the current conversation. The validator cannot replace the latter.

Then:

1. Revisit accepted decisions and exclusions.
2. Update the exact-type guide/template/index as needed; change the shared entry point only for shared principles or explicit user decisions.
3. Preserve the sentence `You may use superpowers, but do not write any spec or plan.`
4. Keep new holdouts unread until the initial changes are complete, then inspect them and rerun applicable existing checks.
5. Record actual changes, unused candidates, validation, and unresolved limits. Do not claim historical checks as current passes.

A type-specific rule needs repeated same-type evidence or an explicit user decision. Cross-type evidence can support shared principles, not foreign syntax. Narrow a conflicting rule instead of adding an abstraction to conceal the conflict.

Keep concise implementation records under:

```text
iterations/<iteration_id>/phase2/
├── accepted-decisions.yaml
└── final-validation.md
```

Combine changes, holdout results where applicable, regressions, and limits in one validation record. Store raw output or source hashes separately only when useful. Do not duplicate conclusions across multiple summaries or treat a record as a substitute for functional changes. Remove obsolete drafts/snapshots only when cleanup is authorized, preserving useful evidence.

## Completion

- Source examples were not modified or copied; verify appropriate provenance without unnecessary full-file hash audits for small rule-only edits.
- Exact-type routing remains intact; any new holdout was not used for initial changes and actual new/existing checks are identified.
- No historical parameters, scientific conclusions, machine paths, credentials, cache assumptions, or stale outputs became defaults.
- No generic CLI, public helper library, configuration platform, runner, or pipeline was added.
- Check frontmatter, YAML/JSON, local links, template syntax, and the unchanged request interface as applicable.
- Distinguish static inspection, synthetic execution, independent behavioral evaluation, and real scientific analysis.
