#!/usr/bin/env bash
set -euo pipefail

# 当前外部工具步骤
# TODO：说明本段目的、已确认的输入，以及运行后需要检查的科学产物。
# 探索时只运行当前命令块；检查真实输出后再添加下一块。
input_dir="inputs/TODO_SAMPLE"
output_dir="derived/TODO_ANALYSIS/TODO_SAMPLE"
mkdir -p "$output_dir"

# 按工具实际契约替换调用；不要仅因范例存在就增加 options。
TODO_TOOL \
  --input "$input_dir" \
  --output "$output_dir"

# TODO：按真实产物格式查看局部内容或诊断，不只检查退出码和文件存在。
# 不自动追加另一个样本或调用 Rscript 批跑未探索的数据集。
