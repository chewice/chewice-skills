# 原始 assay 文件存储策略

在大规模传输开始前确认并记录存储策略。不允许默认选择。详细状态机供下载、转换、删除和审计脚本共同遵守。字段面向所有 raw files（FASTQ/SRA/CEL/IDAT），不要写成只针对 FASTQ。

## 关卡

1. 解析数据集并判定 assay（`scripts/detect_assay.py`）。
2. 询问用户：是否长期保存 raw files？选项只有 A / B。
3. 运行 `scripts/record_storage_policy.py` 写入 `metadata/storage_policy.tsv`。
4. Mode B 必须确认**该 assay 允许的**转换产品后，才运行下载脚本：
   - 10x/droplet RNA-seq：`matrix_velocity`
   - 芯片 / 甲基化：`intensity` 或 `processed`
   - ATAC-seq / ChIP-seq / miRNA-seq / bulk RNA-seq：用户未指定转换产品则暂停，不要默认 STARsolo
   Mode A 芯片最终产品可以是 `CEL` / `IDAT`。
5. 缺少或非法的 storage policy 时，下载脚本必须退出。

## 取值

| 字段 | 允许值 |
|---|---|
| `assay_type` | `RNA-seq` / `ATAC-seq` / `ChIP-seq` / `miRNA-seq` / `sequencing` / `microarray` / `methylation`，未判定前可空或 `pending` |
| `raw_file_type` | `FASTQ` / `SRA` / `CEL` / `IDAT`，未判定前可空或 `pending` |
| `retain_raw_files` | `true` / `false`（兼容旧列 `retain_raw_fastq`） |
| `storage_mode` | `retain` / `delete_after_validation` |
| `validation_status` | `pending` / `conversion_pending` / `validated` / `failed` / `not_applicable` |
| `deletion_status` | `not_applicable` / `pending` / `deleted` / `blocked` |
| `deletion_time` | ISO-8601 或空 |

Mode A：`retain_raw_files=true`，`storage_mode=retain`，`deletion_status=not_applicable`。raw files 发布到 `raw/GSM*/fastq/`、`raw/GSM*/sra/`、`raw/GSM*/CEL/` 或 `raw/GSM*/IDAT/`。禁止自动删除。

Mode B：`retain_raw_files=false`，`storage_mode=delete_after_validation`，`deletion_status` 初始为 `pending`。raw files 只发布到 `temporary/GSM*/`，不得写入 `raw/`。删除只能由 `scripts/apply_storage_policy.py` 执行。

## 删除前验证

Mode B 删除 raw files 前必须同时满足：

- 测序：`reports/final_output_audit.tsv` 每个 GSM 均为 `PASS`，matrix 文件存在、可读、非空
- 芯片：转换产物存在且 `reports/conversion_provenance.tsv` 覆盖每个 GSM
- `reports/conversion_provenance.tsv` 覆盖每个 GSM：工具、版本、输入相对路径、输出相对路径

禁止：下载完成后立即删除 raw files，或假设转换产物正常。转换失败时保留 `temporary/` 文件与日志，将 `deletion_status` 设为 `blocked`。

## 审计清单

`scripts/audit_storage_policy.py` 至少检查：

1. `metadata/storage_policy.tsv` 存在且字段合法
2. 用户选择已记录（`retain_raw_files` 与 `storage_mode` 一致）
3. Mode B 若已删除，删除发生在 `validation_status=validated` 之后，且 `reports/storage_deletion_log.tsv` 非空
4. Mode B 删除后 processed 产物仍在，`temporary/` 中不再有 raw files
5. Mode A 不得删除：`raw/` 中对应 assay 文件仍在，`deletion_status=not_applicable`

## 禁止事项

- 不引入 Seurat object、Scanpy object、RData 或 Python pickle
- 不默认下载 GEO processed expression matrix 或作者标准化矩阵
- 不得把应用层清理脚本之外的 `rm` 当作删除入口
