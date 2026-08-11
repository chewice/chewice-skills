## Scientific analysis scripts are not applications

For project-internal scientific analysis, default to an **executable analysis record**, not a command-line application.

The main script should expose the scientific workflow directly:

```text
define analysis inputs
→ load data
→ inspect / validate key assumptions
→ perform analysis
→ inspect results
→ save scientifically meaningful outputs
→ make figures
```

Do not automatically wrap this workflow in an application or execution-management layer.

Unless explicitly required, avoid adding:

- `commandArgs()` and custom CLI parsers
- generic `--input`, `--output-root`, `--label`, or `--expected-*` interfaces
- automatic job discovery through completion files
- completion markers
- run-state tracking
- execution summaries
- input-contract tables
- audit tables whose only purpose is to record that validation passed
- generic filesystem orchestration
- pipeline-status vocabulary such as `COMPLETE`, `PASS`, `expected`, or `run state`

These are application/pipeline concerns, not default scientific-analysis concerns.

### Project specificity is allowed

A scientific script may explicitly define project-specific:

- sample IDs
- library IDs
- dataset IDs
- paths
- thresholds
- comparisons
- experimental groups

when these values are part of the current analysis.

For example, this is acceptable:

```r
sample_id <- "HS_BM_P1_cells_2"
input_dir <- "../data/cellranger"
```

and may be preferable to introducing a CLI abstraction.

Do not generalize project-specific constants merely because they could theoretically vary in the future.

**Project specificity is not a code smell when it makes the analysis easier to read and reproduce.**

Generalize only when the same script is genuinely intended to operate as a reusable tool across varying inputs.

---

## Prefer analysis inputs over execution discovery

When the analysis concerns a known set of samples or libraries, prefer defining or reading that biological/experimental set directly.

Prefer:

```r
library_ids <- library_manifest$library_id
```

or, for a fixed project analysis:

```r
library_ids <- c("GSM1", "GSM2", "GSM3")
```

over discovering samples indirectly through execution artifacts such as:

```r
complete_files <- list.files(..., pattern = "complete.tsv")
library_ids <- basename(dirname(complete_files))
```

The set of samples should normally be determined by the **study design or analysis manifest**, not by which upstream jobs happen to have completion markers.

---

## Validation should usually disappear after passing

Validation exists to protect scientific correctness, not to become its own subsystem.

Prefer concise fail-fast checks:

```r
stopifnot(
  !anyDuplicated(metadata$cell_id),
  all(metadata$library_id %in% library_ids)
)
```

After a validation passes, normally continue with the analysis.

Do not automatically create and save objects such as:

```text
input_contract
count_check
run_summary
validation_summary
execution_status
```

unless those objects themselves answer a scientific, QC, provenance, or explicitly requested reproducibility question.

A successful validation usually does not need to become an output file.

---

## Scientific outputs only by default

Default outputs should have an obvious analytical purpose.

Examples:

```text
cell_qc_metrics.tsv
donor_qc_summary.tsv
doublet_evidence_enrichment.tsv
DEG_results.tsv
module_scores.tsv
figures/
```

Avoid default outputs whose primary meaning is operational:

```text
complete.tsv
run_summary.tsv
input_contract.tsv
execution_status.tsv
validation_pass.tsv
```

Keep operational outputs only when the surrounding workflow explicitly requires them.

---

## Keep the analysis close to the top of the script

After dependencies and a short input-definition section, the script should normally enter the scientific analysis quickly.

Do not allow tens or hundreds of lines of:

- argument parsing
- filesystem discovery
- configuration
- validation infrastructure
- execution management

before the first scientifically meaningful calculation.

As a heuristic, if a reader must understand a substantial execution framework before reaching the scientific analysis, reconsider the structure.

---

## Distinguish scientific branching from operational branching

Retain branching when it represents real analytical differences, for example:

```text
human vs mouse
v2 vs v3 chemistry
case vs control
available vs unavailable biological measurement
valid statistical edge cases
```

Be skeptical of branching whose purpose is mainly:

```text
did this job complete?
does this output file exist?
did the user provide this CLI argument?
should we use a fallback path?
which execution mode are we in?
```

Scientific branching belongs in analysis scripts.

Operational branching should only be added when the workflow actually requires it.