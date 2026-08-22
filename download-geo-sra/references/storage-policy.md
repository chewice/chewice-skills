# 原始测序数据存储策略

在大规模传输开始前确认并记录存储策略。不允许默认选择。详细状态机供下载、转换、删除和审计脚本共同遵守。

## 关卡

1. 解析数据集并写入 expected runs。
2. 询问用户：是否长期保存 FASTQ/SRA？选项只有 A / B。
3. 运行 `scripts/record_storage_policy.py` 写入 `metadata/storage_policy.tsv`。
4. Mode B 必须确认 `final_product=matrix_velocity` 和转换参数后，才运行 `download_run.sh`。
5. 缺少或非法的 storage policy 时，`download_run.sh` 必须退出。

## 取值

| 字段 | 允许值 |
|---|---|
| `retain_raw_fastq` | `true` / `false` |
| `storage_mode` | `retain` / `delete_after_validation` |
| `validation_status` | `pending` / `conversion_pending` / `validated` / `failed` / `not_applicable` |
| `deletion_status` | `not_applicable` / `pending` / `deleted` / `blocked` |
| `deletion_time` | ISO-8601 或空 |

Mode A：`retain_raw_fastq=true`，`storage_mode=retain`，`deletion_status=not_applicable`。FASTQ 发布到 `raw/GSM*/fastq/`。禁止自动删除。

Mode B：`retain_raw_fastq=false`，`storage_mode=delete_after_validation`，`deletion_status` 初始为 `pending`。FASTQ 只发布到 `temporary/GSM*/fastq/`，不得写入 `raw/`。删除只能由 `scripts/apply_storage_policy.py` 执行。

## 删除前验证

Mode B 删除 FASTQ 前必须同时满足：

- `reports/final_output_audit.tsv` 每个 GSM 均为 `PASS`
- `reports/conversion_provenance.tsv` 覆盖每个 GSM：工具、版本、输入 FASTQ 相对路径、输出 matrix 相对路径
- matrix 文件存在、可读、非空，gene/sample 数量与审计一致

禁止：下载完成后立即删除 FASTQ，或假设 matrix 正常。转换失败时保留 `temporary/` FASTQ 与日志，将 `deletion_status` 设为 `blocked`。

## 审计清单

`scripts/audit_storage_policy.py` 至少检查：

1. `metadata/storage_policy.tsv` 存在且字段合法
2. 用户选择已记录（`retain_raw_fastq` 与 `storage_mode` 一致）
3. Mode B 若已删除，删除发生在 `validation_status=validated` 之后，且 `reports/storage_deletion_log.tsv` 非空
4. Mode B 删除后 `processed/GSM*/matrix_10x/` 仍在，`temporary/GSM*/fastq/` 中不再有 FASTQ
5. Mode A 不得删除：`raw/GSM*/fastq/` 或 `raw/GSM*/sra/` 仍在，`deletion_status=not_applicable`

## 禁止事项

- 不引入 Seurat object、Scanpy object、RData 或 Python pickle
- 不默认下载 GEO processed expression matrix 或作者标准化矩阵
- 不得把应用层清理脚本之外的 `rm` 当作删除入口
