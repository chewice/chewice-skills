# R style comparisons

Read when refactoring wrappers, mechanically inlined analysis, or crowded analysis blocks. The first three fragments assume `measurements` is an already inspected numeric matrix with unique row names. For this teaching task only, the user has explicitly requested excluding rows with missing measurements, computing each remaining row's mean, and saving a table to `row-means.tsv`. This is not a default missing-data policy or a scientific recommendation. The later compact-block example has its own explicit task and inputs.

## A save helper hides the analysis

```r
save_summary <- function(x, path, complete_only) {
  if (complete_only) {
    x <- x[complete.cases(x), , drop = FALSE]
  }
  result <- data.frame(id = rownames(x), mean = rowMeans(x))
  write.table(result, path, sep = "\t", row.names = FALSE, quote = FALSE)
  invisible(result)
}

result <- save_summary(measurements, "row-means.tsv", complete_only = TRUE)
```

The reader must open an export helper to understand which rows contribute and how the statistic is computed. Its name understates its responsibility.

## Removing the function is not enough

```r
x <- measurements
path <- "row-means.tsv"
complete_only <- TRUE

if (complete_only) {
  x <- x[complete.cases(x), , drop = FALSE]
}
result <- data.frame(id = rownames(x), mean = rowMeans(x))
write.table(result, path, sep = "\t", row.names = FALSE, quote = FALSE)
```

The wrapper is gone, but its alias and fixed switch still obscure the concrete task. Here the flag has no caller, command-line override, or supported restart mode. That evidence allows removing it; a similarly named flag in another script might need to remain.

## Present the concrete analysis

```r
## Select complete measurement rows ====
# The requested summary excludes rows with any missing measurement.
complete_rows <- complete.cases(measurements)
table(complete_rows)

complete_measurements <- measurements[complete_rows, , drop = FALSE]

## Calculate mean measurement per row ====
result <- data.frame(
  id = rownames(complete_measurements),
  mean = rowMeans(complete_measurements)
)

head(result)

## Save row means for review ====
write.table(
  result,
  "row-means.tsv",
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)
```

The sample rule, transformation, inspection, and output are visible where the reader needs them. Adapt headings and comments to the user's language. These are fragments, so session initialization and input reading are deliberately omitted.

## Compact analysis blocks

For this separate illustrative task, the requested outputs are per-sample total counts and numbers of genes with nonzero counts, saved separately for two cohorts. `counts_a` and `counts_b` are already inspected gene-by-sample numeric count matrices with unique sample names, nonnegative values, and no missing entries. These assumptions describe this example, not a default missing-data or sample-selection policy. No filtering, normalization, or quality threshold is being chosen.

```r
## Summarize counts by sample ====
# Cohort A
sample_qc_a <- data.frame(
  sample_id = colnames(counts_a),
  total_counts = colSums(counts_a),
  detected_genes = colSums(counts_a > 0)  # Genes with a nonzero count.
)

head(sample_qc_a)

write.table(
  sample_qc_a, "cohort-a-count-summary.tsv",
  sep = "\t", row.names = FALSE, quote = FALSE
)

# Cohort B
sample_qc_b <- data.frame(
  sample_id = colnames(counts_b),
  total_counts = colSums(counts_b),
  detected_genes = colSums(counts_b > 0)
)

head(sample_qc_b)

write.table(
  sample_qc_b, "cohort-b-count-summary.tsv",
  sep = "\t", row.names = FALSE, quote = FALSE
)
```

One heading names the scientific step, short labels locate the cohorts, and the inline comment defines a reported quantity. Calculation, inspection, and saving stay adjacent for each cohort. No extra “calculate,” “inspect,” or “save” headings are needed here. Nor does every operation need a comment: use a short action cue only where it helps the reader follow a change of purpose. Keep simple expressions and related arguments compact rather than spreading every argument onto its own line. If the task instead required comparing cohorts before saving, that dependency would determine the order. This fragment assumes the usual initialized session and script-relative working directory; reruns replace these generated output files.

### Source evidence and limits

The user-selected `Bipolar-Disorder-Transcriptomic-Meta-analysis` repository, revision `20408ad`, informed this layout through static inspection on 2026-10-23. Relevant R passages were `GSE53987.R:62-117` (model branches and short operation cues), `GSE12654.R:70-102` (spacing between local operations), `metaanalysis_blood.R:157-179` (each model's computation and output together), and `enrichment_analysis.R:9-18,58-82` (input-format explanations and local analysis sequences). The example above is newly constructed and does not copy those analyses.

Borrow the reading order and comment placement, not source methods, parameters, session clearing, runtime installation, implicit upstream objects, or historical `#TRUE`/`#FALSE` results. These passages are mixed evidence, not a certification of the repository's correctness or its original execution order. Do not transfer R-specific syntax to other file types. The source is optional reference evidence, not a new dependency or an alternative meaning for the GZDlab index's `SOURCE_ROOT`.

## Keep useful function boundaries

A historical-identifier parser returning a mapping, a numerical kernel reused by a parallel worker, or a shared plotting component can remain a function. State its input and return value near its definition, before first use; keep substantive selection, model, and interpretation choices visible at the call site. A package API need not be copied into the main script. A genuine two-model comparison or supported resume flag must not disappear because one test run exercises only one branch.

Assess two separate outcomes: preserved behavior (including order, missingness, fields, and supported modes) and an understandable reading/modification path. Matching output does not prove readability, and shorter code does not prove equivalence.
