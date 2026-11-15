# R analysis

Read only for `.R` targets. Learn paths, naming, spacing, previews, and plotting expression from same-type examples, not their scientific methods, parameters, or conclusions. Follow the core rules on current inputs only, no speculative recovery, visible scientific decisions, and preserving evidence. Example comments are English; adapt them to the user/project language.

## Enter from the script directory

Start with `setwd()`, `getwd()`, and `.libPaths()`, then load packages and data. Display library paths without changing them. Set the target from the actual launch location; for `scripts/analysis.R` launched from the project root:

```r
setwd("scripts")
getwd()
.libPaths()

library(Matrix)

data_path <- "../data"
```

If already in the script directory, use `setwd(".")`. Initialize once, then reuse the session; rerunning `setwd("scripts")` could enter a nested directory. Do not guess the script location, discover project roots, probe old paths, or copy machine paths. All input, intermediate, output, and project API paths are relative to the script directory.

Keep the filename near the read. `fn` is useful for sequential reads; use `counts_file` or `metadata_file` when multiple paths must coexist. A short `readRDS(file.path(...))` is also valid; do not rewrite existing code merely to standardize syntax.

```r
## Read sample metadata ====
# Inspect available fields before choosing sample alignment and groups.
fn <- file.path(data_path, "metadata.tsv")
meta <- read.delim(fn, check.names = FALSE)

class(meta)
head(meta)
names(meta)
```

Use actual project inputs and readers. `data/`, `output/`, and `results/` are examples, not a mandatory directory layout. Create directories only when writing there is needed.

At a read or conversion boundary, make the object's meaning visible where needed: what a row represents, the identifier, units, matrix orientation, or a known downstream format. Show the relevant columns or a small component before using unfamiliar contents; a wide table's full `head()` may obscure the fields that matter. Clear names and familiar structures need no repetitive explanation.

## Analysis-step headings and spacing

One section serves an actual analysis step. Preserve a nearby convention such as `## Title ====`, `# Title ----`, or another clear delimiter; use `## Title ====` when there is no precedent. Within a step, a short model, tissue, or cohort label can locate a branch without creating another formal section. Titles state analysis content, not instructions such as “Continue after inspection.” Short comments such as “Build the design matrix” or “Add gene annotations” can orient the reader to a local scientific operation; they need not each explain why. Add input meaning, scientific rationale, observations to examine, or downstream use where informative. Do not repeat a clear title or translate each function's syntax. A brief inline comment can clarify an unfamiliar scientific field or unit.

Leave one blank line between sections and between small operation groups within a section. Input preparation, transformation, inspection, and saving are possible group boundaries, not four required subdivisions in every step. Keep consecutive calls serving one operation together, such as fitting the same model or adding annotations to the same plot; leave a blank line when the operation or analysis object changes. Do not space every line, split by line count, or add large banners. Space operators and commas normally; wrap long calls by argument and put pipe steps or plot layers on separate lines. Do not impose numbering or checkpoint labels.

When dependencies permit, keep one model, tissue, or cohort's calculation, inspection, and output close together. Do not reorganize clear local sequences into global “all calculations,” “all checks,” and “all saves” regions merely for uniformity. Bring branches together where an actual comparison needs them. See [compact analysis blocks](r-style-comparisons.md#compact-analysis-blocks) for an example of this reading order, short labels, and spacing.

Place comments where the reader needs the information:

| Location | Useful content when needed |
|---|---|
| File entry | Current question or responsibility, necessary upstream input, and main handoff; keep it brief. |
| Before an operation | Local purpose, a non-obvious rule, or the reason for a choice. A short action cue is sufficient when it aids navigation. |
| Beside an expression or parameter | Units, direction, row/column meaning, or index correspondence. |
| After inspecting output | Actual observation, its limits, and a resulting decision. For unexecuted code, leave a specific pending question instead of a conclusion. |
| At a save | Object state and known consumer, human handoff, or recomputation cost, unless already clear nearby. |

These are placement choices, not required comment slots. Retain explanations of subtle exclusions and information loss; do not expand syntax narration or copy project history into each block. Refresh affected comments when code changes.

The following illustrates layout, assuming fields have been inspected and sample IDs are unique and fully matched. It does not authorize adding alignment to unrelated tasks:

```r
## Align expression columns and sample metadata ====
# Keep group labels in the same order as expression columns.
sample_ids <- colnames(counts)
sample_index <- match(sample_ids, meta$sample_id)

meta <- meta[sample_index, , drop = FALSE]

head(meta)
identical(meta$sample_id, sample_ids)
```

Use names understandable in context, including `counts`, `exprSet`, `meta`, `seu`, `ref`, `obj`, `fit`, `res`, `p`, and `fn`. Avoid meaningless `tmp1`/`tmp2` chains, not all short names. Reuse a name as an object develops; use separate names when preserving a baseline or comparison matters. Do not rename stored object fields merely for style.

## Preview real contents and types

After reading, show actual contents before choosing the next step. Use checks appropriate to the object, not every check on every object:

```r
# This slice assumes the inspected matrix has at least five rows and columns.
class(counts)
dim(counts)
counts[1:5, 1:5]

head(meta)
table(meta$group, useNA = "ifany")

seu
head(seu@meta.data)
```

Inspect `class()` when an object is first encountered, converted, or its type affects the next operation. For Seurat or lists, inspect relevant components such as `Assays(seu)`, `Layers(seu)`, or local metadata; do not expand everything. Verify fields such as `meta$group` against the actual data first.

Adapt slices to small matrices:

```r
counts[
  seq_len(min(5, nrow(counts))),
  seq_len(min(5, ncol(counts))),
  drop = FALSE
]
```

For sparse objects, preview a small slice directly; convert only that slice if needed. Never densify the whole object for display or create a general preview helper. After filtering, merging, conversion, or fitting, inspect the contents, summary, or plot needed for the next decision. Interactive `View()` is optional, not a required noninteractive step.

Distinguish three purposes: a preview helps a person understand the object or decide what follows; an assertion stops a concrete invalid state; a saved record serves a known consumer or review. A successful assertion does not show the contents, and a plausible preview does not enforce an invariant. Use only what the task needs; do not turn every check into all three or print every iteration of a confirmed batch. For batch replay, use `print()` where a relevant display would otherwise be lost inside a loop or function.

## Keep choices and execution visible

Write reading, inspection, trials, comparison, and analysis at the top level. During exploration, run the current line or selection, inspect its output, then write and execute dependent code. Section delimiters do not pause a script. Reuse one session instead of repeatedly reloading objects with `Rscript`; after upstream changes, rerun affected downstream blocks and retain explicit dependencies for replay. Once inputs, methods, and parameters are confirmed, a complete script or simple loop may replay the analysis with existing checks and explicit stopping conditions; stop affected work on violations instead of changing methods.

Keep grouping, thresholds, model choices, and evidence near first use. Example defaults are not evidence. Leave specific unresolved questions as comments and omit or comment out dependent calls; never select the first level automatically or pass `NA` to a model just to complete the script. Continue when evidence supports the choice; ask only for consequential unresolved scientific tradeoffs.

If a repeated computation is not yet understood, run one representative case inline first. Only then extract a stable local computation, conversion, or repeated plot into a small function or loop when current reuse warrants it. Parallel sample/method blocks can remain separate when clearer. Repetition twice does not mandate abstraction.

For a style refactor involving wrappers, fixed switches, or dense long blocks, read [R style comparisons](r-style-comparisons.md). A function body pasted into the main script may still retain unnecessary aliases, `list()` layers, or an `if` branch whose flag is fixed for this analysis. Simplify those only after checking their use and the current execution contract; keep actual model comparisons and supported restart modes.

For a crowded block, first consider local operation groups and short cues, then meaningful intermediate objects that expose a transformation worth inspecting. Consider a narrow function when its computation has a stable responsibility and extraction reduces repetition or the state a reader must track. Consider a separate script only for a real independent question, consumer, expensive recomputation/replot boundary, or human handoff. These are progressively stronger options, not a required sequence or a mandate to split long code. Avoid aliases that merely rename an unchanged object and splitting that forces more navigation than it saves.

For a substantial custom function with a confirmed need across scripts or projects, and when extraction is within the requested scope, use an ordinary `.R` file in that project's root `R/` directory. A style-only request does not itself authorize moving code into `R/`. Keep local helpers before and near their first use. Document purpose, parameters, and return value before `name <- function(...)`. Do not create `DESCRIPTION`, `NAMESPACE`, roxygen scaffolding, or load it with `library()`. From `scripts/downstream`, for example, use `source("../../R/helpers.R")`. Data paths inside the function remain relative to the analysis working directory, not the helper file. Do not invent a shared-library path or extract code for merely possible reuse.

For a nontrivial helper, make important external dependencies and side effects clear too. Prefer explicit arguments for changing data or settings when that clarifies the call; a local closure can legitimately capture a fixed object if the dependency is evident. Do not hide selection or method changes inside IO helpers. When splitting files, establish a sufficient handoff that can be read in a fresh session; preserve the population used by whole-set checks, ordering, missingness, and current scientific choices. Do not serialize every temporary object to recreate a workspace.

Use concise checks for scientific invariants even before a failure occurs. For example, after alignment where matching sample order is required:

```r
stopifnot(identical(meta$sample_id, colnames(counts)))
```

Do not add broad `tryCatch()`, retry, old-reader fallback, guessed fields, or silent sample removal. Fix the actual owned cause and affected callers; report out-of-scope boundaries. Preserve meaningful failed and negative results without retaining obsolete executable branches.

## Plot directly with the appropriate tools

Use base plots, ggplot2, or object-specific methods such as `DimPlot()`, `FeaturePlot()`, `plotPCA()`, and `plotMA()` as appropriate. Heatmaps and networks may use their relevant packages. Do not wrap everything in a single plotting interface.

For ggplot, assign `p`, display it, and adjust directly with layers such as `labs()` or `theme()`. Use existing project composition tools when needed. Set dimensions, resolution, and colors for the current figure, not from example defaults. With a previously created and inspected ggplot object:

```r
out_path <- "../output"
dir.create(out_path, showWarnings = FALSE, recursive = TRUE)
fn <- file.path(out_path, "sample_overview.pdf")

ggsave(fn, plot = p, width = 6, height = 4, units = "in")
```

These dimensions illustrate saving syntax, not a standard. Use appropriate devices for base or package plots, such as `pdf(fn)` followed by plotting and `dev.off()`. Do not force incompatible objects through `ggsave()`.

## Save for a concrete scientific use

Apply the shared saving and overwrite criteria in `SKILL.md`. Match `saveRDS()` with `readRDS()`, `qs::qsave()` with `qs::qread()`, and `save()` with `load()`. Name the object and stage, such as `sample_A.annotated.rds` or `comparison_A.markers.tsv`.

Use an explicit destination directory such as `out_dir` or `out_path`, retaining clear existing names. Define it at the relevant step or shared setup and create it before the first write that needs it; do not repeat directory creation for each result. Keep a concrete filename beside the write. Both `fn <- file.path(out_dir, "result.tsv")` followed by a writer and `file.path()` directly inside that writer are valid. Use `plot_file` or another descriptive path name when several paths coexist. Meaningful `paste0()` filenames inside actual sample or method loops are also valid; do not require literal filenames or a separate path variable for every output.

Separate saving from the preceding calculation with a blank line. A short save call may stay on one line; expand a crowded call by arguments so the object, path, and writer options are easy to scan. A short save comment is optional when the purpose is already clear. Extract substantive result assembly before saving, but do not create aliases solely to rename an unchanged object. For a few fixed outputs, prefer direct object-to-file calls over `get()` or a generic export loop. Preserve necessary chunked writes and external tools' output-prefix contracts. Keep the existing writer and serialization settings, including separators, quoting, missing-value representation, row/column names, compression, and append behavior; readability alone does not justify changing them.

For example, with an already prepared table and an existing destination directory:

```r
write.table(
  markers,
  file.path(out_dir, "all-markers.tsv"),
  sep = "\t", quote = FALSE, row.names = FALSE
)
```

This illustrates direct saving, not a requirement to switch an existing writer to `write.table()` or rename its file.

```r
## Save the annotated object for review ====
out_path <- "../output"
dir.create(out_path, showWarnings = FALSE, recursive = TRUE)
fn <- file.path(out_path, "sample_A.annotated.rds")

saveRDS(seu, fn)
```

A later session can reestablish the same relative path, read the object, and inspect `seu` and `head(seu@meta.data)` before use.

Saving fewer files does not necessarily simplify the analysis. A shared table that several stages read, replace, and rewrite introduces state dependencies; use it only for a current project need, not as the default for diagnostics. Keep ordinary previews in the session and retain only meaningful handoffs or review evidence. Separate recomputation from replotting only when there is a real use, with the plot's required inputs available at that boundary.

## Review the reading and modification path

For a substantial style refactor, trace representative reader tasks: locate the input and its meaning; explain a consequential object change; find the choice to edit and its affected downstream work; identify who uses a saved result; and, if supported, resume or replot from the documented handoff. Inspect helper dependencies and whether comments arrive before the ambiguity they resolve. Do not add missing capabilities just to complete this review. Evaluate behavior preservation separately, including ordering, missingness, failure behavior, and supported execution modes; parsing, equal results, line counts, and comment counts do not establish readability.
