# Notebook analysis

Read only for `.ipynb` targets. A notebook records interactive scientific decisions, not a Python application wrapped in JSON. Apply the core limits on current needs, no speculative recovery or legacy adapters, and visible scientific choices. Adapt headings/comments to the user/project language.

## Identify the language, then work by cells

Inspect `kernelspec`, `language_info`, and source cells. `.ipynb` does not imply Python. Preserve the actual kernel and use its syntax; clarify a metadata/source conflict rather than silently converting languages. Set a new notebook's kernel to the task's language. The provided template is Python only.

Use the notebook directory as the working directory for all relative input/output paths. Verify the kernel launch location, then set and display the directory in the first code cell. Initialize once. Python uses `os.chdir(...)` with an explicit relative target and `print(Path.cwd())`, using `"."` if already there; do not rely on absent `__file__`. R uses `setwd(...)`, `getwd()`, and `.libPaths()` before packages; retain `setwd(".")` if appropriate, and display library paths without changing them. Do not guess editor defaults or add directory discovery.

Each cell advances an observable piece of the analysis. Use only needed parts of this sequence:

`question/inputs → dependencies → read and inspect → prepare scientific inputs → representative fit or comparison → diagnostics → recorded choice → dependent analysis → useful save → interpretation`

Do not impose a fixed cell count. Cells should allow a researcher to rerun a coherent step and inspect its output.

Use Markdown headings naming actual analysis steps, or clear existing cell comments. Keep scientific rationale and observations to examine in short explanations. Execution instructions such as “reuse the kernel” or “continue after inspection” belong here, not in routine output comments. One step can span adjacent computation and display cells; do not require a title for each cell or manufacture chapters.

Within a cell, leave one blank line between input preparation, transformation, inspection, and saving groups. Keep related statements adjacent; do not split by line count or space every statement. Wrap arguments, pipes, and plot layers according to the actual language. Names such as `df`, `seu`, `ref`, and `p` remain valid when clear.

Execute the current cell in the same kernel and inspect output before dependent cells. Do not use `Run All` to cross unresolved groups, thresholds, or methods. Continue without per-cell approval when evidence is sufficient. After upstream changes, rerun affected cells instead of using stale results; record dependencies so the notebook can be replayed without hidden session objects.

## Keep comparison and selection distinct

Keep candidates and diagnostics adjacent, with selection after comparison. Only add a sweep when the task actually compares candidates. This is structural pseudocode, not a method or parameter default:

```python
candidate_values = [...]  # Candidates justified for the current analysis.
candidate_results = {}

for value in candidate_values:
    # Fit or transform with this candidate and collect comparable diagnostics.
    ...
```

Display metrics/plots in the next cell and record the later choice with its rationale. Distinguish exploratory selection from prespecified settings and preserve meaningful negative or failed comparisons. When undecided, use Markdown or a comment to state the specific question and omit/comment out dependent calls. Do not pass `None`/`NA` onward or invent an optimum or diagnostics.

Do not prefill scientific cutoffs, top-N, model settings, or defaults from habit. Use confirmed values, evidence-based comparisons, or a visible pending decision. Do not enumerate unrequested defaults, switches, seeds, sampling sizes, or extra diagnostics for apparent completeness. Set figure dimensions/resolution only to suit the current figure.

If a requested output still lacks an estimand, comparison unit, test, or grouping, keep that decision visible. Do not choose a standard method merely for a runnable notebook. Explain a conceptual gap when a later result does not actually depend on a supposed upstream choice; do not invent dataflow.

Newly authored code cells start with `execution_count: null` and empty `outputs`; never fabricate outputs or execution history. Preserve existing user outputs unless clearing or rerunning was requested; do not treat stored outputs as newly verified evidence.

## Extract only stable computations needed now

When a transformation/model still needs understanding, run one representative item in a cell and inspect relevant intermediate results or controls. Extract a small per-item function only after behavior is stable and current repetition needs it. Keep biological groups, candidates, cutoffs, and interpretation in the visible analysis. Distinct method/dataset branches can remain in separate cells/notebooks when clearer.

Do not add CLI entrypoints, YAML config loaders, runners, pipeline state, retries, or completion markers. Honor current explicit contracts without creating compatibility branches. Correct an owned cause and known consumers instead of adding cells that rename old fields, probe old paths, or silently substitute a layer or method to conceal defects. Necessary scientific identifier mapping or explicit format conversion remains valid.

## Save and inspect for a purpose

Save expensive fits only when later diagnosis or interpretation needs them. Explain that use near saving/reloading, and verify relevant inputs/settings still match before reuse. Do not create a cache orchestration system. Follow current formats and relative object/state-specific filenames; saving every cell is unnecessary. Protect raw inputs and meaningful negative evidence when retiring obsolete execution paths.

Use tools appropriate to the kernel and object: R may use base plots, ggplot2, or package methods; Python uses its current libraries. Keep plot preparation, display, and saving in adjacent cells without a general wrapper.

After reading, show actual local contents, not just shape or a loaded message: table `.head()`, array slices, R `head()`, or appropriately sized matrix slices. Never densify a whole sparse object for display. Python displays only its final bare expression implicitly; use `display()`/`print()` for multiple results in a cell. Use the equivalent actual R display behavior for R kernels.

Inspect `class()` in R or `type()`/`.dtypes` in Python after loading, extraction, or conversion when type matters. Do not apply all checks everywhere. After key transformations, show the contents, summaries, or diagnostics that guide the next decision. Concise assertions for actual scientific requirements, such as matching observation IDs or a required layer, are justified before an error occurs; do not build generic validation or silently repair scientific inputs.

Save only outputs useful for current science, review, handoff, or replay. An operational completion cell is unnecessary; an honest unresolved scientific question may be more useful.
