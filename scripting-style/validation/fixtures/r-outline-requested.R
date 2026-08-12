# This fixture represents an explicit user request for R OUTLINE sections.
# The syntax is conditional and is not the default section style.

# 1. Read the project input ----

input_file <- file.path("inputs", "example.tsv")
output_file <- file.path("derived", "row-summary.tsv")

analysis_data <- read.delim(input_file)
dim(analysis_data)
head(analysis_data)

# 2. Summarize the observed rows ----

row_summary <- data.frame(
  variable = names(analysis_data),
  missing = vapply(analysis_data, function(x) sum(is.na(x)), integer(1))
)
row_summary

# Save this table only because it is the requested downstream handoff.
dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
write.table(row_summary, output_file, sep = "\t", quote = FALSE, row.names = FALSE)
