# 当前问题：TODO_QUESTION
# 从项目根启动 scripts/analysis.R；已在脚本目录时改为 setwd(".")。
# 入口只运行一次，后续片段复用当前会话。
setwd("scripts")
getwd()
.libPaths()

library(Matrix)

## 读取表达矩阵 ====
# 本例使用矩阵 RDS；查看类型、标识和数值，再决定如何处理。
data_path <- "../data"
fn <- file.path(data_path, "TODO_COUNTS.rds")
counts <- readRDS(fn)
class(counts)
dim(counts)
counts[seq_len(min(5, nrow(counts))), seq_len(min(5, ncol(counts))), drop = FALSE]

## 读取样本信息 ====
# 先看实际字段和记录，为后续样本对齐提供依据。
fn <- file.path(data_path, "TODO_METADATA.tsv")
meta <- read.delim(fn, check.names = FALSE)
class(meta)
head(meta)
names(meta)

## 根据观察继续分析 ====
# 在此写入当前结果支持的下一步，尚未明确的分组和方法留待判断。
# 需要为下游保留已检查的 meta 时，可在相应片段使用：
# out_path <- "../output"
# dir.create(out_path, showWarnings = FALSE, recursive = TRUE)
# fn <- file.path(out_path, "metadata.checked.rds")
# saveRDS(meta, fn)
