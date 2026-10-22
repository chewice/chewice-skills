# R style comparisons

Read when refactoring wrappers or mechanically inlined analysis. These fragments assume `measurements` is an already inspected numeric matrix with unique row names. For this teaching task only, the user has explicitly requested excluding rows with missing measurements, computing each remaining row's mean, and saving a table to `row-means.tsv`. This is not a default missing-data policy or a scientific recommendation.

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

## Keep useful function boundaries

A historical-identifier parser returning a mapping, a numerical kernel reused by a parallel worker, or a shared plotting component can remain a function. State its input and return value near its definition, before first use; keep substantive selection, model, and interpretation choices visible at the call site. A package API need not be copied into the main script. A genuine two-model comparison or supported resume flag must not disappear because one test run exercises only one branch.

Assess two separate outcomes: preserved behavior (including order, missingness, fields, and supported modes) and an understandable reading/modification path. Matching output does not prove readability, and shorter code does not prove equivalence.
