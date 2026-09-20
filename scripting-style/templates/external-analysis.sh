#!/usr/bin/env bash
set -euo pipefail

# 工作目录：从项目根启动 scripts/analysis.sh；已在文件目录时改为 cd .，只运行一次。
cd scripts
pwd

# 当前外部工具步骤
# TODO：说明目的及运行后要查看的产物，只选择当前命令块运行。
input_dir="../data/TODO_SAMPLE"
output_dir="../results/TODO_STEP/TODO_SAMPLE"
mkdir -p "$output_dir"

TODO_TOOL \
  --input "$input_dir" \
  --output "$output_dir"

# 检查真实产物后再决定下一步；文本表可直接 head，二进制对象在 R/Python 会话中查看。
