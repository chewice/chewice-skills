# 当前问题：TODO_QUESTION；上游对象：TODO_UPSTREAM。
# 沿用项目的路径与分段约定；每次选择当前段运行，检查输出后再继续。

# 读取并检查表达矩阵 ----
# 查看行列标识和部分数值，为后续样本对齐提供依据。
# 本例假设输入是矩阵 RDS；根据实际格式替换读取调用。
counts_path <- file.path("inputs", "TODO_COUNTS.rds")
counts <- readRDS(counts_path)
dim(counts)
# 小矩阵按实际尺寸调整范围；稀疏矩阵直接取局部，不转换整个对象。
counts[1:5, 1:5]

# 读取并检查样本信息 ----
# 先看实际字段与记录，再决定分组和对齐方式。
metadata_path <- file.path("inputs", "TODO_METADATA.tsv")
metadata <- read.delim(metadata_path, check.names = FALSE)
head(metadata)
names(metadata)

# 根据观察继续分析 ----
# TODO：检查上面的真实输出后，在这里写入下一步及其依据。
# 只预告尚未明确的方向；不预填分组、阈值或模型，不执行依赖未决选择的调用。
# 若任务确实需要比较候选，先运行比较并展示诊断，再追加选定结果的下游段。
# 在关键变换后展示相关内容或诊断；只在有复查或下游用途时保存结果。
