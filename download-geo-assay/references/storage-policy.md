# 原始 assay 文件存储策略

不同 assay 的 raw 大小和用途不同，不能使用一个全局 `retain_raw_files`。在 `detect_assay.py` 之后，对每个 modality 单独询问并各写一行。

## 关卡

1. 解析数据集并判定 assay / modality。
2. 按 assay 询问是否长期保存 raw files（Y/N）。不允许默认，也不把脚手架占位值当成最终选择。
3. 询问最大临时存储（见 `references/download-quota.md`）。
4. 运行 `scripts/record_storage_policy.py` upsert 到 `metadata/storage_policy.tsv`。
5. Mode B 必须确认**该 modality 允许的**转换产品后才下载：
   - `bulk_rnaseq`：`gene_count_matrix`
   - `scRNAseq` / `snRNAseq`：`matrix_10x`；velocity 可选，对应 `matrix_velocity`
   - 芯片 / 甲基化：`intensity` 或 `processed`
   - ATAC / ChIP / miRNA：用户未指定则暂停，不要默认 STARsolo
6. 缺少或非法的 storage policy 时，下载脚本必须退出。

## 取值

每个 assay 一行：

| 字段 | 允许值 |
|---|---|
| `assay_type` | `RNA-seq` / `ATAC-seq` / `ChIP-seq` / `miRNA-seq` / `sequencing` / `microarray` / `methylation`，未判定前可空或 `pending` |
| `modality` | `bulk_rnaseq` / `scRNAseq` / `snRNAseq` / `atac` / `chip` / `mirna` / `sequencing` / `microarray` / `methylation` |
| `raw_file_type` | `FASTQ` / `SRA` / `CEL` / `IDAT` |
| `retain_raw_files` | `true` / `false`（兼容旧列 `retain_raw_fastq`） |
| `storage_mode` | `retain` / `delete_after_validation` |
| `validation_status` | `pending` / `conversion_pending` / `validated` / `failed` / `not_applicable` |
| `deletion_status` | `not_applicable` / `pending` / `deleted` / `blocked` |
| `deletion_time` | ISO-8601 或空 |

Mode A：`retain_raw_files=true`，raw 发布到 `raw/GSM*/`。禁止自动删除该 assay 的 raw。

Mode B：`retain_raw_files=false`，raw 只进 `temporary/GSM*/`。删除只能由 `scripts/apply_storage_policy.py` 执行，且只作用于该 assay 的 GSM。

## 删除前验证

Mode B 删除前必须同时满足：

- 测序：`reports/processed_output_audit.tsv` 对应 GSM 为 `PASS`，转换产物存在、可读、非空
- 芯片：转换产物存在且 `reports/conversion_provenance.tsv` 覆盖每个 GSM
- provenance 覆盖每个待删 GSM：工具、版本、输入相对路径、输出相对路径

禁止：下载完成后立即删除 raw files。转换失败时保留 `temporary/` 文件与日志，将该 assay 的 `deletion_status` 设为 `blocked`。

## 审计清单

`scripts/audit_storage_policy.py` 至少检查：

1. `metadata/storage_policy.tsv` 存在且每行字段合法
2. 每个 assay 的用户选择已记录（`retain_raw_files` 与 `storage_mode` 一致）
3. Mode B 若已删除，删除发生在 `validation_status=validated` 之后，且删除日志非空
4. Mode B 删除后 processed 产物仍在，该 assay 的 `temporary/` raw 已不在
5. Mode A 不得删除：对应 assay 文件仍在 `raw/`

## 禁止事项

- 不引入 Seurat object、Scanpy object、RData 或 Python pickle
- 不默认下载 GEO processed expression matrix 或作者标准化矩阵
- 不运行 DESeq2 / GO / KEGG
- 不得把应用层清理脚本之外的 `rm` 当作删除入口
