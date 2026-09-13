# [问题] 用一句话写当前脚本要回答的问题，以及上游对象来自哪里。

# 若项目约定从脚本目录运行，在 library 前进入该目录；已在则跳过。
# 不要把某个仓库里的 setwd("scripts/...") 字符串当成通用默认值。
# setwd("TODO_SCRIPT_DIR")
getwd()
.libPaths()

# 沿用目标项目的 section 和路径约定；删除不适用块。
library(TODO_PACKAGE)

data_path <- file.path("TODO_DATA")
out_path <- file.path("TODO_OUTPUT")
dir.create(out_path, showWarnings = FALSE, recursive = TRUE)

fn <- file.path(data_path, "TODO_COUNTS")
counts <- read.delim(fn, check.names = FALSE)
dim(counts)
counts[1:5, 1:5]

fn <- file.path(data_path, "TODO_METADATA")
metadata <- read.table(fn, header = TRUE, sep = "\t")
dim(metadata)
head(metadata)
# 嵌套 readRDS(file.path(...)) 仍允许；逐行会话优先先赋 fn。

# [检查点] 只查看会影响下一步判断的结构、分组或质量信息。
# table(metadata$TODO_GROUP)

# [可选：具体试做] 仅在随后要批量化且方法仍待理解时，先跑一个代表性对象。
representative_id <- "TODO_REPRESENTATIVE_ID"
# representative_result <- TODO_METHOD(counts, representative_id)
# representative_result

# [可选：比较] 仅在任务确实要选择参数或方法时，保留候选结果和诊断。
# 短匿名函数可以保留；不要把整段分析包进 named function。
candidate_values <- numeric()
candidate_results <- lapply(candidate_values, function(value) {
  # TODO_METHOD(counts, candidate_value = value)
})

# [可选：决策点] 运行并检查候选结果后再填写；没有比较时删除本块。
# 若用户指向项目内参数来源，起始值写在调用附近，并标明不是已验证最优。
selected_value <- NA_real_

# [可选：批量扩展] 只有代表性案例被理解后，才提取稳定技术核或循环。
# analysis_result <- TODO_DOWNSTREAM(counts, metadata, selected_value)

# [可选：保存证据] 只保存当前复查或下游真正需要的产物。
# saveRDS(analysis_result, file.path(out_path, "TODO_RESULT.rds"))

# [可选：待判断] 只有分析叙事需要时，运行后记录观察、局限或下一问。
