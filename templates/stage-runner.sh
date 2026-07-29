#!/usr/bin/env bash
set -euo pipefail

# 目标：TODO_STAGE_PURPOSE
# 输入：TODO_INPUT_CONTRACT
# 输出：TODO_OUTPUT_CONTRACT

analysis_script="${1:?Usage: stage-runner.sh ANALYSIS_SCRIPT INPUT OUTPUT_DIR}"
input_path="${2:?Usage: stage-runner.sh ANALYSIS_SCRIPT INPUT OUTPUT_DIR}"
output_dir="${3:?Usage: stage-runner.sh ANALYSIS_SCRIPT INPUT OUTPUT_DIR}"

if [[ ! -f "${analysis_script}" ]]; then
  echo "Analysis script does not exist: ${analysis_script}" >&2
  exit 1
fi

if [[ ! -e "${input_path}" ]]; then
  echo "Input does not exist: ${input_path}" >&2
  exit 1
fi

mkdir -p "${output_dir}"

echo "Starting ${analysis_script}"

case "${analysis_script}" in
  *.R)
    Rscript "${analysis_script}" "${input_path}" "${output_dir}"
    ;;
  *.py)
    python3 "${analysis_script}" "${input_path}" "${output_dir}"
    ;;
  *)
    echo "Unsupported analysis script: ${analysis_script}" >&2
    exit 1
    ;;
esac

echo "Completed ${analysis_script}"
echo "Outputs: ${output_dir}"
