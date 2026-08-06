# 脚本提纲
# 1. 定义同一锚点下的相对输入输出
# 2. 执行窄转换并保存结果
# 相对路径基准：repository / runner working directory

# 1. 定义相对输入输出 ----

input_file <- file.path("inputs", "example.tsv")
output_dir <- "derived"

## 1.1 核验输入契约 ----

if (!file.exists(input_file)) {
  stop("Input does not exist: ", input_file)
}

# 这条普通注释是 negative control，不应成为 document symbol。

# 2. 执行窄转换并保存结果 ----

count_rows <- function(path) {
  length(readLines(path, warn = FALSE))
}

row_count <- count_rows(input_file)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(as.character(row_count), file.path(output_dir, "row-count.txt"))
