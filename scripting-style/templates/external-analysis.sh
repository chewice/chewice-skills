#!/usr/bin/env bash
set -euo pipefail

# State the external analysis and its project-relative inputs.
reference_dir="references/TODO_REFERENCE"

# First explicit sample block.
sample_id="TODO_SAMPLE_A"
input_dir="inputs/TODO_SAMPLE_A"
output_dir="derived/TODO_ANALYSIS/TODO_SAMPLE_A"
mkdir -p "$output_dir"

TODO_TOOL \
  --reference "$reference_dir" \
  --input "$input_dir" \
  --output "$output_dir"

# Inspect the tool's real scientific output before changing parameters or continuing.

# Optional second block: keep it only when another known sample should remain independently readable.
sample_id="TODO_SAMPLE_B"
input_dir="inputs/TODO_SAMPLE_B"
output_dir="derived/TODO_ANALYSIS/TODO_SAMPLE_B"
mkdir -p "$output_dir"

TODO_TOOL \
  --reference "$reference_dir" \
  --input "$input_dir" \
  --output "$output_dir"

# Keep only outputs used by review or downstream analysis.
