# Array 与甲基化芯片

- Affymetrix CEL、Illumina expression IDAT、methylation IDAT 默认是 raw-only 获取任务；本 Skill 不执行 RMA、归一化、差异分析或甲基化统计。
- platform 元数据优先请求最小范围的 GPL self/full、platform-only MINiML/SOFT 或官方 family 附件。最小端点失败后自动回退到官方 family SOFT/MINiML，再从中提取目标 GPL；不得把一次大文件事故泛化为全局禁用 `family.soft`。
- 记录 endpoint、范围、内容类型、大小、校验与 fallback 原因，避免把 HTML 错误页当平台文件。
- CEL/IDAT 只有在用户明确指定 `intensity`/`intensity_matrix`/`methylation_matrix` 等可审计转换产品、转换已覆盖该 GSM 且产物审计通过时，才具备删除资格。标准文本矩阵需有唯一 `feature_id`/`probe_id`/`cpg_id`、当前 GSM 数值列和完整 conversion provenance；任一缺失均保留 raw。未指定时必须保留 raw。
