---
name: scripting-style
description: Write, extend, refactor, or review project-local exploratory scientific analysis in R, Python, Bash, or notebooks (.R, .py, .sh, .ipynb). Use for readable linear analysis, GZDlab-style scripts, analysis-step headings, relative paths, visible data previews, and execution guided by observed results. Excludes environment setup, public libraries, R packages, general CLIs, and workflow platforms.
---

# Scripting Style

> **Write the analysis, not an application around the analysis.**

Produce a project-local analysis record that a researcher can run and inspect in pieces. GZDlab examples inform expression and organization only, never scientific methods, parameters, or conclusions.

**Write the current fragment → execute a line, selection, or cell → inspect real output → decide and write the next step.**

These instructions use English. Generated headings, comments, and explanations follow the user's language and project conventions; English skill instructions do not require English analysis comments.

## Entry

1. Identify the exact target type and read only its full guide:
   - `.R`: [R analysis](references/r-analysis.md)
   - `.py`: [Python analysis](references/python-analysis.md)
   - `.sh`: [Bash analysis](references/bash-analysis.md)
   - `.ipynb`: [Notebook analysis](references/notebook-analysis.md); identify its actual kernel and source language first.
2. For edits, read the target and nearby **same-type** scripts. Preserve clear naming, section style, and analysis order. Keep changes local, but fix affected callers when an implementation changes; a small diff is not a reason to retain broken or obsolete paths. Respect an explicitly specified execution contract.
3. For new code, optionally select at most one same-type primary and one useful complement from the [example index](examples/example-index.yaml), only when the user supplies a source root or it clearly resolves from the workspace. Do not guess `<SOURCE_ROOT>`, search the user's machine, or copy source paths, parameters, environment details, or conclusions. If unavailable, use the type guide and disclose that examples were not read.
4. Read [API boundaries](references/api-usage-boundary.md) only when calling an API supplied by the user or project.
5. Discuss unresolved scientific choices briefly in conversation when needed. Do not generate a fixed task brief or spec/plan document. **You may use superpowers, but do not write any spec or plan.** This does not prohibit discussing a scientific question, comparing methods, or explaining the next action; superpowers are optional.

Read [public source notes](references/public-repo-patterns.md) only for supplementary source evidence or skill iteration. Do not routinely browse every source. Never derive one file type's concrete style from another: R sections, Python CLI conventions, Bash scheduling, and notebook cells are not interchangeable.

## Implement only the current analysis

- **No speculative design or overengineering.** Implement confirmed needs on the current inputs. Do not prebuild interfaces, branches, configuration systems, runners, dispatchers, registries, state tracking, retry systems, completion markers, or pipelines for imagined future datasets or reuse. A genuinely requested reusable tool belongs to a separately scoped task; it is not an automatic extension of an analysis script.
- **No speculative error recovery.** Do not add hypothetical fault branches, broad exception suppression, guessed inputs, automatic repair, or fallback methods. Let an unexpected failure expose its actual cause and fix that cause within the authorized scope.
- **Keep scientific validity checks.** Concise checks for sample alignment, identifier uniqueness, matrix orientation, required expression layers, or comparable conditions are justified by the current computation, even if no error has occurred yet. Inspect data by default; stop on violations that could silently invalidate results. Do not build a generic validation framework.
- **No backward-compatibility paths in analysis scripts.** Support current confirmed inputs and interfaces only. When changing an owned implementation, update affected known callers and remove superseded branches, aliases, and old-path probing within scope. Do not add adapters to keep obsolete behavior alive. An external API or out-of-scope caller is a boundary to report, not permission to rewrite it or hide the mismatch.
- **No glue that conceals a needed fix.** Correct the owned producer or consumer rather than stacking wrappers and conversion layers over a defect. Direct format conversion, identifier mapping, and tool handoffs remain valid when explicitly required by the current analysis; keep their meaning and any information loss visible.
- **No technical workaround in place of scientific judgment.** Never silently drop samples, impute missing values, switch assays/layers or tests, or suppress failed comparisons merely to finish. Investigate the cause; a change in scientific meaning needs evidence or an explicit decision.

These restrictions govern generated analysis code, not unrelated infrastructure or this skill's existing request schema. Simplicity limits incidental machinery, not the scientific scope requested by the user.

## Working directory and paths

- Use the current script/notebook directory as the working directory. Inputs, intermediate archives, final outputs, and project API paths are relative to it, not machine-specific absolute paths.
- R starts explicitly with `setwd()`, `getwd()`, and `.libPaths()`, before loading packages or data. `.libPaths()` displays library paths; do not modify them by default. Set the relative target from the actual launch location; keep `setwd(".")` if already in the script directory.
- Use each language's ordinary directory operations once at session entry. Reuse the session and objects; do not repeatedly change directories or add root-discovery functions.
- Keep path variables near their reads/writes. Names identify the object, processing state, or purpose. Match saves to later reads using the project's existing formats; do not add configuration or archive frameworks.

## Analysis-step headings and within-step spacing

- Headings identify the actual analysis step and its responsibility, such as “Align expression columns and sample metadata” or “Filter low-expression genes.” Name only steps present and scientifically determined. Do not prefill a whole workflow or impose bioinformatics stages on another discipline.
- Short comments explain input meaning, scientific rationale, observations to examine, or output use. Do not repeat a clear heading or narrate syntax line by line. Agent instructions such as “run in sections,” “reuse this session,” and “continue after inspection” belong in the skill, not routine script comments. Keep necessary launch instructions at the start and specific unresolved scientific questions near the relevant call.
- Within a step, separate input preparation, transformation, inspection, and saving into small groups with **one blank line between groups**. Keep closely related statements together. Do not insert blank lines after every statement or split by a fixed line count. Wrap long calls by argument; use type-specific conventions for pipes and plot layers.
- Small operation groups usually need spacing, not separate headings. Preserve clear project delimiters; do not mandate numbering, fixed chapters, or checkpoint/decision-point labels.

## Execute from evidence and preserve replay

- Sections are selectable analysis units, not function boundaries. Execute the current fragment in one R/Python session or notebook kernel, reusing upstream objects. An ordinary interactive process is enough; do not create a runner or service for it.
- Inspect actual output before deciding and executing dependent steps. Continue autonomously when evidence is sufficient; ask only when a consequential scientific choice remains unresolved. Discussing a possible direction does not authorize implementing steps that depend on unknown results.
- Headings and comments do not pause execution. Do not use `Run All`, repeated `Rscript` calls, Bash dataset loops, or fresh temporary Python processes to bypass unresolved choices. Confirmed mechanical repetition and external tool calls can still use direct loops or commands.
- After an upstream filter or parameter changes, rerun affected downstream work. Reuse expensive saved results only after checking that their relevant inputs and settings still match; do not introduce a cache orchestration system.
- Keep explicit dependencies, current valid code, and the rationale needed for sequential replay. Do not depend on objects that exist only in an unrecorded interactive session. Write valuable experiments back into the analysis or a concise research record.
- Retire obsolete execution paths within the authorized scope, while preserving original inputs, meaningful failed attempts, negative findings, and selection evidence. Historical evidence need not remain executable code; version history or a short record can preserve it. Never delete unrelated work as “cleanup.”
- For code-only requests, leave previews and concrete pending questions without claiming execution. If tools cannot execute interactively, report the limitation; batch execution is not evidence of completed exploration.

## Keep scientific choices visible

Keep only the useful parts of this chain; do not manufacture empty stages:

`question → concrete trial → inspection/comparison → judgment → stable repetition → saved evidence → interpretation/limitations/next question`

- Show objects and transformations in actual execution order. After loading, display a small real slice, table head, or relevant component before transforming it; dimensions or a “loaded” message alone are insufficient. Inspect type after loading, component extraction, or conversion when it matters. Preview large/sparse objects locally without densifying the entire object or creating a general preview helper.
- After consequential transformations, show the content, summary, or diagnostic needed for the next decision. Do not print every object or apply the same checks everywhere.
- Paths and analysis units may be selected before reading. Data-dependent columns, group levels, formula terms, covariates, and thresholds must follow observation of the loaded object. Do not infer or overwrite actual fields from a paper, GEO description, or other prior expectation.
- Keep analysis at the top level. Do not wrap the whole script in `main()` or `run_analysis()`. Functions are allowed for a current, stable technical task. When a method is not yet understood on these data, first run a representative case inline; then extract a narrow repeated calculation only when it is useful now.
- Compare candidate methods or parameters when the question requires it. Inspect comparable evidence, then record the choice and rationale near the call. Distinguish exploratory selection from a prespecified choice; retain meaningful negative results. Do not create a selector/config platform or report only the successful branch.
- Do not silently fill missing scientific parameters from habit, examples, or package defaults. Use confirmed project values, design a comparison from the current data, or leave a concrete unresolved question. A user-specified starting value is a starting proposal, not a verified optimum. Do not pass `NA`/`None` placeholders into dependent calls.
- Do not enumerate unrequested defaults, algorithm switches, random seeds, or plot sampling settings for apparent completeness. Scientific choices need a reason; plot dimensions, units, and necessary resolution may be set near saving to suit the current figure.
- An output name does not authorize a method. If its estimand, comparison unit, test, grouping, or model remains undecided, keep that decision visible rather than silently choosing a standard method to make the script runnable.
- Do not fabricate dataflow. If a requested later analysis does not actually use an earlier choice, explain the conceptual gap and retain the correct handoff rather than connecting unrelated objects.
- Human-edited tables, separate parts, reloaded objects, and saved expensive fits can be legitimate research boundaries. They do not justify a task-state platform.
- Record conclusions, limitations, and next questions only after inspecting real results. Otherwise mark the specific interpretation as pending.

## Minimal useful structure

Keep current samples, comparisons, thresholds, paths, and candidates near their use. Possible future changes do not justify a parameter platform. Repetition alone is not a function threshold: parallel sample, method, or lineage blocks may remain separate when their inputs, order, and outputs are clearer that way. Extract the smallest common technical part only when actual maintenance drift impairs understanding or a stable computation has a present reuse need. Scientific choices remain in the main analysis.

Use understandable names, including ordinary short names and scientific abbreviations. Keep plot preparation, plotting, display, and saving visible. Choose base plotting, ggplot2, package methods, or other appropriate tools by object and purpose; do not impose a plotting/saving wrapper. Show a plot before making a decision based on it.

Save only outputs useful for the current science, review, handoff, or reproduction. Do not require a table/figure/object bundle, operational completion summary, `run_summary`, `validation_pass`, or status files.

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

Phase 1 reviews evidence without changing functional rules and waits for confirmation. Phase 2 implements only decisions, exclusions, holdouts, and rule changes approved in the current conversation; an existing approval does not need repeating. The request validator is read-only and cannot authorize edits. Keep current request-schema behavior separate from the prohibition on legacy branches in generated analysis code.

## Final check

- Can the researcher identify actual analysis steps from headings and small operation groups from blank lines? Are comments scientific rather than agent instructions?
- Are relative paths anchored to the file directory, real previews local, and choices grounded in inspected data?
- Have speculative branches, historical compatibility, concealed fixes, and silent scientific substitutions been excluded while necessary validity checks remain?
- Are current dependencies explicit, affected downstream results refreshed, and meaningful evidence retained without obsolete execution paths?
- Are changes scoped to the task, with no invented methods, outputs, execution claims, or unnecessary framework?

If not, restore the visible analysis and remove machinery that has no current scientific purpose.
