---
name: scripting-style
description: Write, extend, refactor, or review project-local exploratory scientific analysis in R, Python, Bash, or notebooks (.R, .py, .sh, .ipynb). Use for readable linear analysis, GZDlab-style scripts, analysis-step headings, relative paths, visible data previews, and execution guided by observed results. Excludes environment setup, public libraries, R packages, general CLIs, and workflow platforms.
---

# Scripting Style

> **Write the analysis, not an application around the analysis.**

Produce a project-local analysis record that a researcher can read, run, inspect, and modify in analysis order. User-specified same-type references take precedence over indexed GZDlab examples for writing style; neither supplies scientific methods, parameters, or conclusions.

During exploration: **write the current fragment → execute a line, selection, or cell → inspect real output → decide and write the next step.** Once inputs and methods are confirmed, deterministic batch replay is allowed.

These instructions use English. Generated headings, comments, and explanations follow the user's language and project conventions; English skill instructions do not require English analysis comments.

## Entry

1. Identify the exact target type and read only its full guide:
   - `.R`: [R analysis](references/r-analysis.md)
   - `.py`: [Python analysis](references/python-analysis.md)
   - `.sh`: [Bash analysis](references/bash-analysis.md)
   - `.ipynb`: [Notebook analysis](references/notebook-analysis.md); identify its actual kernel and source language first.
2. For edits, read the target and nearby **same-type** scripts. For ordinary fixes, preserve clear local conventions and keep changes local. For an explicit style refactor, read the user's same-type reference and follow the requested reading order; minimal diff must not preserve the structure being corrected. Keep scientific choices and current execution contracts intact, and update affected callers when changing an owned interface.
3. For new code, optionally select at most one same-type primary and one useful complement from the [example index](examples/example-index.yaml), only when the user supplies a source root or it clearly resolves from the workspace. Do not guess `<SOURCE_ROOT>`, search the user's machine, or copy source paths, parameters, environment details, or conclusions. If unavailable, use the type guide and disclose that examples were not read.
4. Read [API boundaries](references/api-usage-boundary.md) only when calling an API supplied by the user or project.
5. Discuss unresolved scientific choices briefly in conversation when needed. Do not create unsolicited spec, plan, checklist, or workflow documents. When the user explicitly requests an analysis plan, task prompt, or handoff document, provide only that deliverable at the requested level of detail. Do not turn it into a prerequisite for unrelated analysis work or treat a plan-only request as authorization to execute it.

Read [public source notes](references/public-repo-patterns.md) only for supplementary source evidence or skill iteration. Do not routinely browse every source. Never derive one file type's concrete style from another: R sections, Python CLI conventions, Bash scheduling, and notebook cells are not interchangeable.

## Choose the smallest sufficient analysis

- Define what the current script receives, computes, and supplies downstream. Implement confirmed needs; do not build configuration systems, runners, registries, retries, or pipelines for imagined reuse. A requested reusable tool is a separate scope.
- **Reuse suitable upstream products.** Prefer official or previously validated processed inputs when their provenance, version, identifiers, and scientific definition meet the task. Check compatibility at entry; do not recreate upstream analysis merely to start from raw data. Rebuild when inputs are missing, incompatible, scientifically changed, or explicitly requested. Previously verified facts need renewed investigation when relevant inputs/settings change or conflicting evidence appears.
- Reuse must respect the project's declared provenance boundary. When the project requires a chain starting from first-party releases, rebuild legacy intermediates once from those releases; subsequent steps may reuse the resulting validated products without repeating upstream work. Author-published processed data can satisfy the first-party requirement. Do not impose this project-specific requirement on every analysis.
- **Keep only necessary transformations.** Read usable formats directly. Convert or rename for a known consumer, a scientific operation, or a clearer representation of the current objects; do not materialize every design term as another table or processing stage. Keep assumptions and information loss visible.
- **Check concrete scientific conditions.** Protect alignment, unique keys, matrix orientation, required layers, and comparison validity even before a failure occurs. Use concise assertions for violations that could silently invalidate results. Exploratory previews inform decisions; persistent evidence supports a specific review or downstream need. Performing a check does not require saving a report.
- **Resolve actual exceptions locally.** Apply the direct, established operation first and investigate unresolved or conflicting records separately. Retain whole-set checks where exceptions could collide with accepted records. Do not add speculative recovery, guessed inputs, broad exception suppression, or automatic repairs. Never silently drop samples, impute values, or switch layers or methods merely to finish.
- **Fix owned causes and current callers.** Remove obsolete interfaces and path probing within scope rather than adding compatibility glue. Report opaque or out-of-scope mismatches. A shorter example does not justify missing dependencies, swallowed failures, or omitted scientific choices.

These restrictions govern generated analysis code, not unrelated infrastructure or this skill's existing request schema. Simplicity limits incidental machinery, not the scientific scope requested by the user.

## Working directory and paths

- Use the current script/notebook directory as the working directory. Inputs, intermediate archives, final outputs, and project API paths are relative to it, not machine-specific absolute paths.
- R starts explicitly with `setwd()`, `getwd()`, and `.libPaths()`, before loading packages or data. `.libPaths()` displays library paths; do not modify them by default. Set the relative target from the actual launch location; keep `setwd(".")` if already in the script directory.
- Use each language's ordinary directory operations once at session entry. Reuse the session and objects; do not repeatedly change directories or add root-discovery functions.
- Keep paths near their reads/writes and use the project's existing formats. Names identify the object, processing state, or purpose; ensure saved outputs match downstream reads.

## Code, results, records, and temporary files

- Follow the project's established layout. Where none exists, use `scripts/` for reproducible analysis code, `output/` for its products, `records/` for necessary maintenance and historical evidence, `tmp/` for disposable work, and `output/run_logs/` for console logs. Create only locations needed by the current task; these conventions do not authorize migration or cleanup.
- Keep results traceable to formal code and declared inputs. This is a responsibility mapping, not one script per output file: multiple products, shared inputs, and scientific validation tables are legitimate. Keep project-authored replay code in the formal analysis, not in result folders. Preserve upstream source bundles and their supplied layout.
- Classify auxiliary code by what it does, not its extension or original purpose. If a one-off repair changes a formal result, incorporate the necessary transformation into the formal analysis within the authorized scope; retain useful historical evidence. If incorporation is outside scope, report the remaining replay dependency. Replay must not require a manual repair in `records/` or preexisting content in `tmp/`. A formal script may create and consume its own scratch files during a run.
- Keep necessary repair history, acceptance checks, and execution snapshots in `records/` or the existing evidence location. Preserve historical snapshots as evidence; update current executable entry points when authorized. Records are not disposable, a second analysis pipeline, or a duplicate project-status system. Retain only evidence with a concrete purpose.
- Use `tmp/` only for rebuildable working copies, caches, scratch computations, and one-off editing/checking helpers whose loss does not remove the sole source of a result or needed evidence. Work intended to survive cleanup belongs in the established durable location. Do not clear files while a task uses them; cleanup still requires applicable authorization.
- Put console output and execution diagnostics in the existing run-log location. Preserve external-tool logs that must stay with their output prefix. Structured acceptance or PASS/FAIL tables are validation evidence, not console logs; keep maintenance checks with their records and scientific validation products with their analysis outputs. Do not automatically add status files, README files, or a report bundle because a script ran.
- For an authorized move, inspect callers, working directories, relative reads/writes, and dependencies before moving files; distinguish historical production paths from current replay paths. Static syntax and path checks establish only those properties, not numerical reproduction or scientific validity. Honor a code-only or no-rerun request.
- Preserve existing Git ignore policy, especially ignored analysis outputs. Without a project policy, recommend ignoring `output/` and `tmp/`; retain valuable code and small records under version control when appropriate, excluding large evidence explicitly. Directory guidance alone does not authorize changing Git settings or adding ignored outputs.

## Analysis-step headings and within-step spacing

- Headings identify the actual analysis step and its responsibility, such as “Align expression columns and sample metadata” or “Filter low-expression genes.” Name only steps present and scientifically determined. Do not prefill a whole workflow or impose bioinformatics stages on another discipline.
- Make the current operation clear through its heading and short comments about input meaning, purpose, evidence to inspect, or downstream use. Keep necessary limitations and human decisions beside the affected operation; reference detailed history instead of repeating it. Do not repeat a clear heading or narrate syntax line by line. Agent instructions such as “run in sections” belong in the skill, not routine script comments.
- Within a step, separate input preparation, transformation, inspection, and saving into small groups with **one blank line between groups**. Split a nested expression when it combines distinct analysis steps or hides an intermediate result worth inspecting; keep simple expressions compact. Wrap by arguments, operators, or plot layers rather than character count alone. Do not space every statement or impose fixed block lengths.
- Small operation groups usually need spacing, not separate headings. Preserve clear project delimiters; do not mandate numbering, fixed chapters, or checkpoint/decision-point labels.

## Execute from evidence and preserve replay

- Sections are selectable analysis units, not function boundaries. Execute the current fragment in one R/Python session or notebook kernel, reusing upstream objects. An ordinary interactive process is enough; do not create a runner or service for it.
- Inspect actual output before deciding and executing dependent steps. Continue autonomously when evidence is sufficient; ask only when a consequential scientific choice remains unresolved. Discussing a possible direction does not authorize implementing steps that depend on unknown results.
- Interactive inspection is required at unresolved scientific decision points, not at every line of an already approved analysis. Once inputs, methods, and parameters are confirmed, allow complete scripts, simple loops, or deterministic batch replay with the existing checks and explicit stopping conditions. If an expected condition fails, stop the affected branch and dependent work and report it; do not silently change methods to continue.
- Headings and comments do not pause execution. Do not use `Run All`, repeated `Rscript` calls, Bash dataset loops, or fresh temporary Python processes to bypass unresolved choices. Confirmed mechanical repetition and external tool calls can still use direct loops or commands.
- After an upstream filter or parameter changes, rerun affected downstream work. Reuse saved results when their relevant inputs and settings still match.
- Keep explicit dependencies, current valid code, and the rationale needed for sequential replay. Do not depend on objects that exist only in an unrecorded interactive session. Write valuable experiments back into the analysis or a concise research record.
- Retire obsolete execution paths within the authorized scope, while preserving original inputs, meaningful failed attempts, negative findings, and selection evidence. Historical evidence need not remain executable code; version history or a short record can preserve it. Never delete unrelated work as “cleanup.”
- For code-only requests, leave previews and concrete pending questions without claiming execution. If tools cannot support inspection at unresolved decision points, report the limitation; batch replay can verify a confirmed workflow but is not evidence of completed exploration.

## Keep scientific choices visible

Keep only the useful parts of this chain; do not manufacture empty stages:

`question → concrete trial → inspection/comparison → judgment → stable repetition → saved evidence → interpretation/limitations/next question`

- Show objects and transformations in actual execution order. After loading, display a small real slice, table head, or relevant component before transforming it; dimensions or a “loaded” message alone are insufficient. Inspect type after loading, component extraction, or conversion when it matters. Preview large/sparse objects locally without densifying the entire object or creating a general preview helper.
- After consequential transformations, show the content, summary, or diagnostic needed for the next decision. Do not print every object or apply the same checks everywhere.
- Paths and prespecified methods may precede reading. Verify data-dependent fields, levels, and model terms against the loaded object; do not overwrite actual fields to match a paper or prior expectation. Keep confirmed settings near use without reopening settled choices merely for completeness.
- Compare methods or parameters only when the question requires it. Inspect comparable evidence and record the selection rationale; distinguish an exploratory starting proposal from a fixed method and retain meaningful negative results.
- Use observations to assess method applicability, not to repeatedly tune prespecified thresholds until the desired positive result appears. A change to the scientific question, test family, or correction scope is a method change to discuss, not a style simplification.
- When a scientific parameter is genuinely unresolved, use evidence to decide or state the concrete pending question and omit dependent calls. Do not invent values from habit or pass `NA`/`None` placeholders onward.
- Do not enumerate unrequested defaults, algorithm switches, random seeds, or plot sampling settings for apparent completeness. Scientific choices need a reason; plot dimensions, units, and necessary resolution may be set near saving to suit the current figure.
- An output name does not authorize a method. If its estimand, comparison unit, test, grouping, or model remains undecided, keep that decision visible rather than silently choosing a standard method to make the script runnable.
- Do not fabricate dataflow. If a requested later analysis does not actually use an earlier choice, explain the conceptual gap and retain the correct handoff rather than connecting unrelated objects.
- Record conclusions, limitations, and next questions only after inspecting real results. Otherwise mark the specific interpretation as pending.

## Minimal useful structure

Design steps default to sections in one readable analysis, not one file per requirement. Split scripts only for a real boundary: independently used inputs/outputs, substantial computation, current reuse, or human handoff. Do not prescribe a fixed number of scripts or stages.

Keep substantive operations at the top level, with scientific choices near use and needed helpers before their first call. Do not wrap the whole analysis in `main()` or `run_analysis()`. Inspect a representative case before extracting an unfamiliar repeated calculation. Similar blocks alone do not require abstraction; separate sample/method blocks may be clearer. Extract a narrow stable calculation when current reuse or maintenance drift justifies it.

Judge helpers by responsibility and what the caller can see. Narrow parsers, numerical kernels, parallel workers, and stable plotting components can remain functions. Keep sample selection, feature identity, statistical choices, and interpretation visible rather than concealing them in a “prepare” or “save” helper. Existing package and opaque project APIs retain their documented boundaries.

After inlining, simplify redundant aliases, containers, and switches, checking for variable collisions. Remove alternatives only when the current execution contract makes them obsolete; preserve genuine comparisons, resume modes, useful intermediate objects, and scientific checks.

Use understandable names, including ordinary short names and scientific abbreviations. Keep plot preparation, plotting, display, and saving visible. Choose base plotting, ggplot2, package methods, or other appropriate tools by object and purpose; do not impose a plotting/saving wrapper. Show a plot before making a decision based on it.

Save for a downstream input, expensive result worth reusing, human handoff, or necessary review/reproduction evidence. Ordinary intermediate objects and diagnostic previews can stay in the session. Avoid immediate save/reload without a consumer and redundant serialization of usable inputs. When saving overlapping evidence, combine it where useful; exception tables need a concrete review purpose. Do not require a table/figure/object bundle, `run_summary`, `validation_pass`, or status files.

Make each saved result locally readable: show the result object, destination directory, filename, and relevant writer options at the saving step. Complete substantive filtering, merging, or summarization before the write call; retain simple path construction or column selection inline when clear. Do not add object-name lookup, output registries, or generic save wrappers merely to unify a few fixed outputs. Keep genuine per-sample loops and streaming writes when needed. A saving-style refactor preserves existing filenames, resolved paths, formats, writer options, write order, and append/overwrite behavior unless the user requests a change. Follow the exact-type guide for syntax and spacing.

Reruns replace the current analysis's generated outputs at their intended paths by default, including intermediate files, result tables, and figures. Do not add output-nonexistence guards, skip writes merely because a file exists, or generate timestamped copies, backups, or overwrite prompts by default. Use the writer's normal replacement behavior or its documented overwrite option when needed; do not add blanket directory deletion. This permission covers generated outputs, not raw inputs, human-edited source tables, unrelated files, or explicitly protected research records. Preserving meaningful evidence does not require preserving every superseded output file; honor an explicit no-overwrite requirement when present.

## Project and API boundaries

Treat provided APIs as opaque capabilities: prepare known inputs, call the documented interface, inspect returns, and save needed results. Do not inspect excluded internals, copy implementations, guess behavior, or rewrite an API without authorization. Do not automatically build environments, editor settings, public libraries, or packages. Never copy source-example package installation, session clearing, path guessing, or scientific pipelines into a new script. Source examples remain read-only.

## Templates

Use only for a new file without a closer same-type project precedent:

- [R](templates/linear-analysis.R)
- [Python](templates/linear-analysis.py)
- [Bash](templates/external-analysis.sh)
- [Notebook](templates/linear-analysis.ipynb)

Remove irrelevant blocks and replace every question, input, tool, and heading placeholder, including the Bash analysis-step title. Script templates enter `scripts/` from the project root; use `.` when already in the file directory. The notebook assumes its kernel starts in that directory and uses Python, not R. Templates provide initialization and reading/preview or a current tool call, not predetermined later stages. Use the type guide for purposeful saving and plotting. Adapt comment language to the user/project.

## Skill iteration

Read the full [iteration interface](references/iteration-interface.md) only when asked to review examples or improve this skill. Routine analysis does not load the maintenance workflow.

For new-example intake, Phase 1 reviews evidence without changing functional rules; Phase 2 implements approved decisions, exclusions, holdouts, and rule changes. A direct user-approved rule change without new examples does not require fabricated Phase 1 intake or holdouts. Validate in proportion to the affected behavior under the iteration interface; an existing approval does not need repeating. The request validator is read-only and cannot authorize edits. Keep current request-schema behavior separate from the prohibition on legacy branches in generated analysis code.

## Final check

- What current scientific question, necessary computation, or explicit deliverable does this step support? Remove additions with no current purpose.
- What correctness guarantee, error detection, or reproduction evidence would be lost by removing it? Merge or remove it when there is no concrete loss; retain necessary scientific checks and meaningful evidence.
- Has upstream data, software, or an existing verification already resolved the same issue? Reuse it when its relevant inputs and rules still match; rerun only affected work after changes.
- Does this intermediate file have a known consumer or enough recomputation cost to justify saving? Otherwise keep the object in the session.
- Does this abstraction make the method and reading order clearer, with inputs, paths, dependencies, scientific choices, inspection, and saving visible? If it hides key choices, use direct code.
- Does simplification preserve the input provenance, samples, feature identities, statistical question, and correction scope? Discuss scientific changes as method changes; never invent methods, results, or execution claims to complete a refactor.

If not, restore the visible analysis and remove machinery that has no current scientific purpose.

For a style refactor, report behavior preservation and readability separately: parsing or numerical equivalence does not establish readable analysis. Review the actual reading path and retained helper boundaries; function counts, line counts, and heading counts are not acceptance criteria.
