# Current question: TODO_QUESTION
# Start a new R session from the project root; run directory initialization once.
setwd("scripts")
getwd()
.libPaths()

library(Matrix)

## Read the expression matrix ====
data_path <- "../data"
fn <- file.path(data_path, "TODO_COUNTS.rds")
counts <- readRDS(fn)

class(counts)
dim(counts)
counts[
  seq_len(min(5, nrow(counts))),
  seq_len(min(5, ncol(counts))),
  drop = FALSE
]

## Read sample metadata ====
# Inspect fields and records needed for sample alignment.
fn <- file.path(data_path, "TODO_METADATA.tsv")
meta <- read.delim(fn, check.names = FALSE)

class(meta)
head(meta)
names(meta)
