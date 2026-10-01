# Bash analysis scripts

Read only for `.sh` targets. Bash records needed external commands and project inputs; it is not a cross-dataset scheduler for exploratory R/Python analysis. Apply the core rules against speculative design, legacy compatibility, and concealed scientific changes. Adapt comments to user/project language.

## Write the actual command sequence

Use the `.sh` directory as the working directory. From the project root, enter `scripts/` with `cd scripts` and display it with `pwd`; use `cd .` when already there. Initialize once; do not search for the directory or probe old locations. Inputs, outputs, and project tool paths are relative to this directory, with variables near their commands.

A useful shape is:

`shebang and proportionate shell safety → current input/tool variables → explicit sample/analysis step → inspect real output before another step`

Keep options with scientific or computational meaning beside the command. Use arrays or line continuation only when they improve readability of the actual invocation.

Name each block for the current analysis step, such as “Align reads” when alignment is already specified, not “Current external tool step.” Do not add methods to fill out headings. Comments explain input meaning, analysis rationale, or output use; instructions about selecting blocks remain in this guide.

Within a step, leave one blank line between input/path preparation, the tool call, and output inspection. Keep related assignments together. Do not split by fixed line count or space every line. Wrap long commands by argument and indent continuation lines; never insert a blank line inside a continued command. Shell assignments remain `name=value`, with no spaces around `=`.

A multiline command is one execution unit. After it completes, inspect real output according to its type: use `head` for a relevant text table or the R/Python session for a scientific binary object. A comment does not pause the shell. Run the current block and examine output before writing/executing dependent blocks; do not use whole-script execution, repeated Python processes, or `for dataset ...; Rscript ...` to bypass scientific decisions. Confirmed mechanical repetition can use a simple loop.

Do not copy flags merely because examples use them, or expand every default, resource option, logging setting, and post-processing stage. If an omitted option creates scientific ambiguity, leave a specific unresolved question or obtain the missing decision instead of silently accepting a default. Use only options justified by the current command and task.

Quoting, `mkdir -p`, and `set -euo pipefail` are reasonable shell safeguards; they do not authorize an execution framework. Do not claim all source examples use them.

## Keep explicit sample blocks when useful

For a few known samples with confirmed inputs and settings, repeated blocks can make differences readable. This example shows organization, not authorization to run every block during exploration:

```bash
sample_id="sample_a"
input_dir="../data/sample_a"
output_dir="../results/current-step/sample_a"
mkdir -p "$output_dir"

analysis_tool \
  --input "$input_dir" \
  --output "$output_dir"

sample_id="sample_b"
input_dir="../data/sample_b"
output_dir="../results/current-step/sample_b"
mkdir -p "$output_dir"

analysis_tool \
  --input "$input_dir" \
  --output "$output_dir"
```

Use a loop only when the same command is established for the explicit sample list and differences remain visible. Do not add a dispatcher, config parser, registry, or completion discovery to reduce repetition. Extract a small common invocation only when actual drift has become a problem; keep scientific settings visible.

## Preserve scientific boundaries

Candidate commands or expensive optional stages may remain as clearly explained manual blocks during a real comparison. They are not a reason to create execution modes. Once obsolete, retire their executable paths while retaining meaningful comparison evidence.

Downstream scientific files are valid outputs. `.done` markers, pass tables, registries, automatic completed-directory discovery, retries, and dashboards are not default analysis products. Reuse saved results only when their relevant inputs/settings still match.

Validate current inputs when missing or mismatched inputs could mislead the analysis; do not build speculative `if` chains. Do not suppress a tool failure with `|| true`, silently select another tool, or search legacy locations to keep execution going. Fix the actual cause within scope and update known callers. Required explicit format conversions remain valid; wrappers that conceal broken producers or obsolete interfaces do not.

Do not copy destructive cleanup, machine paths, installation, credentials, or environment activation from examples into an analysis. Protect source inputs and unrelated work.
