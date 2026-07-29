# 脚本说明 ---------------------------------------------------------------
# 目标：TODO_ANALYSIS_QUESTION
# 上游输入：TODO_UPSTREAM_INPUT
# 主要输出：TODO_EXPECTED_OUTPUTS
# 关键生物学决策：TODO_BIOLOGICAL_DECISIONS

# 1. 加载依赖与指定 API -----------------------------------------------

# library(TODO_PACKAGE)
# source("TODO_USER_PROVIDED_API.R")

# 2. 定义输入、输出与主要参数 -----------------------------------------

input_file <- "TODO_INPUT_FILE"
output_dir <- "TODO_OUTPUT_DIR"

# 说明当前数据或研究设计为什么需要这个值；不要照搬历史脚本。
analysis_parameter <- TODO_PARAMETER_VALUE

if (!file.exists(input_file)) {
  stop("Input does not exist: ", input_file)
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# 3. 读取数据 -----------------------------------------------------------

input_data <- TODO_READ_INPUT(input_file)

# 4. 检查数据结构与样本构成 -------------------------------------------

print(dim(input_data))
print(head(input_data))
# TODO: 检查当前步骤真正依赖的列、样本、分组、缺失值或对象结构。

# 5. 必要的数据准备 -----------------------------------------------------

analysis_data <- input_data
# TODO: 只保留当前分析必需的过滤、转换或分组。

# 6. 核心分析 -----------------------------------------------------------

# 保持方法、关键参数和生物学选择在主线中可见。
analysis_result <- TODO_RUN_ANALYSIS(
  analysis_data,
  parameter = analysis_parameter
)

# 7. 关键中间结果检查 ---------------------------------------------------

print(summary(analysis_result))
# TODO: 添加能够支持下一步判断的表格、统计摘要或诊断图。

# 8. 结果整理与可视化 ---------------------------------------------------

result_table <- TODO_TIDY_RESULT(analysis_result)
result_plot <- TODO_PLOT_RESULT(result_table)

# 9. 保存输出 -----------------------------------------------------------

table_file <- file.path(output_dir, "TODO_RESULT_TABLE.csv")
figure_file <- file.path(output_dir, "TODO_DIAGNOSTIC_FIGURE.png")
object_file <- file.path(output_dir, "TODO_ANALYSIS_OBJECT.rds")

write.csv(result_table, table_file, row.names = FALSE)
ggplot2::ggsave(figure_file, result_plot, width = TODO_WIDTH, height = TODO_HEIGHT, dpi = 300)
saveRDS(analysis_result, object_file)

# 10. 完成摘要 ----------------------------------------------------------

message("Analysis completed.")
message("Rows in result table: ", nrow(result_table))
message("Outputs: ", normalizePath(output_dir))
