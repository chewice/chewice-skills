# 局部辅助函数片段

仅在函数门槛成立时复制以下片段。它们展示函数边界，不提供项目专属算法。

## R：重复保存同类图

适用：同一脚本需要用一致尺寸保存多张已经生成的图。

```r
save_plot <- function(plot, filename, width, height) {
  ggplot2::ggsave(
    filename = filename,
    plot = plot,
    width = width,
    height = height,
    dpi = 300
  )
}

save_plot(qc_plot, qc_file, width = 7, height = 5)
save_plot(result_plot, result_file, width = 9, height = 6)
```

不要把分组、颜色、生物学标签或输出 stem 隐藏成函数内部默认值。

## R：逐 feature 的窄模型单元

适用：明确需要对多个 feature 执行同一种拟合，且科学参数由调用处提供。

```r
fit_one_feature <- function(feature_values, pseudotime, model_formula) {
  model_data <- data.frame(
    feature = feature_values,
    pseudotime = pseudotime
  )
  stats::lm(model_formula, data = model_data)
}

feature_models <- lapply(
  feature_names,
  function(feature_name) {
    fit_one_feature(
      feature_values = expression_matrix[feature_name, ],
      pseudotime = cell_pseudotime,
      model_formula = feature ~ pseudotime
    )
  }
)
```

实际任务应在主线显式说明 feature 集合、模型选择、cutoff 和多重检验。

## Python：重复转换同构记录

适用：文件中的多条记录需要相同的窄格式转换。

```python
def convert_record(record: dict[str, str], required_keys: tuple[str, ...]) -> str:
    missing = [key for key in required_keys if key not in record]
    if missing:
        raise ValueError(f"Missing keys: {missing}")
    return "\t".join(record[key] for key in required_keys)


required_keys = ("feature_id", "feature_name")
output_lines = [convert_record(record, required_keys) for record in records]
```

不要为一次转换增加 class、registry、plugin 或配置对象。

## 删除函数的信号

- 函数只调用一次且内联更容易读；
- 函数名只能用 `run_all`、`process_data` 一类模糊词描述；
- 大多数参数是隐藏的科学默认值；
- 为理解主线必须频繁跳进函数体；
- 函数开始创建额外 wrapper 或跨文件 helper。
