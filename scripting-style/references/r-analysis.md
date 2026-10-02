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

## Analysis-step headings and spacing

One section serves an actual analysis step. Preserve a nearby convention such as `## Title ====`, `# Title ----`, or another clear delimiter; use `## Title ====` when there is no precedent. Titles state the analysis content, not instructions such as “Continue after inspection.” Short comments explain input meaning, scientific rationale, an observation to examine, or downstream use. Do not repeat clear titles or narrate syntax.

Leave one blank line between sections and between small operation groups within a section: input preparation, transformation, inspection, and saving. Keep closely related statements adjacent. Do not space every line, split by line count, or add large banners. Space operators and commas normally; wrap long calls by argument and put pipe steps or plot layers on separate lines. Do not impose numbering or checkpoint labels.

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

## Keep choices and execution visible

Write reading, inspection, trials, comparison, and analysis at the top level. Run the current line or selection, inspect its output, then write and execute dependent code. Section delimiters do not pause a script. Reuse one session instead of repeatedly reloading objects with `Rscript`; after upstream changes, rerun affected downstream blocks and retain explicit dependencies for replay.

Keep grouping, thresholds, model choices, and evidence near first use. Example defaults are not evidence. Leave specific unresolved questions as comments and omit or comment out dependent calls; never select the first level automatically or pass `NA` to a model just to complete the script. Continue when evidence supports the choice; ask only for consequential unresolved scientific tradeoffs.

If a repeated computation is not yet understood, run one representative case inline first. Only then extract a stable local computation, conversion, or repeated plot into a small function or loop when current reuse warrants it. Parallel sample/method blocks can remain separate when clearer. Repetition twice does not mandate abstraction.

For a substantial custom function with a confirmed need across scripts or projects, use an ordinary `.R` file in that project's root `R/` directory. Document purpose, parameters, and return value before `name <- function(...)`. Do not create `DESCRIPTION`, `NAMESPACE`, roxygen scaffolding, or load it with `library()`. From `scripts/downstream`, for example, use `source("../../R/helpers.R")`. Data paths inside the function remain relative to the analysis working directory, not the helper file. In another project, place the needed file under that project's `R/`; do not invent a shared-library path or automatic lookup. Do not extract it for merely possible future reuse.

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

Intermediate saves support expensive-result review, later plotting, human-edited handoff, or another analysis fragment. Follow current project formats: `saveRDS()`/`readRDS()`, `qs::qsave()`/`qs::qread()`, or `save()`/`load()`. Name the object and stage, such as `sample_A.annotated.rds` or `comparison_A.markers.tsv`; avoid generic `result` or `final_final` defaults.

Allow reruns to overwrite the analysis's existing generated files. Write directly with `saveRDS()`, `write.table()`, `ggsave()`, or the appropriate writer; use a documented overwrite argument only when that writer requires it. Do not prepend `stopifnot(!file.exists(fn))`, stop when an output already exists, or wrap saving in `if (!file.exists(fn))` so a rerun silently retains stale results. Do not add timestamped filenames, backup copies, or overwrite confirmation by default. Keep scientific validity assertions, such as sample-order checks; the existence of an old generated output is not a scientific validity failure. Protect raw inputs, human-edited source tables, unrelated files, and explicitly protected records as specified in the core rules.

```r
## Save the annotated object for review ====
out_path <- "../output"
dir.create(out_path, showWarnings = FALSE, recursive = TRUE)
fn <- file.path(out_path, "sample_A.annotated.rds")

saveRDS(seu, fn)
```

A later fragment/session can read the same relative `fn` and inspect `seu` and `head(seu@meta.data)`. Do not automatically save and immediately reload. Reestablish the path after a session restart and verify relevant inputs/settings before reusing expensive results. Keep intermediate artifacts distinct from original inputs; never overwrite raw data. Save final tables, figures, or objects near their analysis or a meaningful stage boundary, only when useful. No mandatory output bundle, completion summary, or state system.
