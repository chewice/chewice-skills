#!/usr/bin/env bash
set -euo pipefail

# Launch from the project root; use cd . if already in the script directory.
cd scripts
pwd

# TODO_ANALYSIS_STEP
input_dir="../data/TODO_SAMPLE"
output_dir="../results/TODO_STEP/TODO_SAMPLE"
mkdir -p "$output_dir"

TODO_TOOL \
  --input "$input_dir" \
  --output "$output_dir"
