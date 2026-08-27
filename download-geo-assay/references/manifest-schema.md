# Manifest 与状态 schema

项目根为 `<output-root>/GEO/<GSE>/`。新项目的能力表快照位于 `config/`；已生成项目不自动迁移。

## 关键路径

```text
config/{assay_capability.yaml,source_capability.yaml}
metadata/{assay_routing.tsv,expected_runs.tsv,source_manifest.tsv,storage_policy.tsv,acquisition_config.tsv}
metadata/download_manifests/<GSM>.tsv
raw/<GSM>/{fastq,sra,CEL,IDAT}/
temporary/<GSM>/{fastq,sra,CEL,IDAT,work}/
processed/<GSM>/... 或 processed/gene_count_matrix.tsv
reports/{download_integrity_audit.tsv,processed_output_audit.tsv,conversion_provenance.tsv,storage_release.tsv,storage_deletion_log.tsv,report.html}
```

## `storage_policy.tsv`

每个 assay/modality 一行：

```text
gse assay_type modality raw_file_type retain_raw_files storage_mode
final_product source_preference allow_sra_lite confirmed_at
validation_status deletion_status deletion_time
```

`source_preference=auto|ngdc|ena|ncbi|geo`。`allow_sra_lite=true|false`。旧文件缺少新增列时按 `final_product=pending`、`source_preference=auto`、`allow_sra_lite=false` 兼容读取；缺 `confirmed_at` 的旧策略不能授权新删除。

scaffold 可暂不创建该文件。真正下载前必须确认 raw 去留和必要选择；Mode B 必须有能力表允许的非 raw 标准产品。

## `acquisition_config.tsv`

key/value 表，至少可记录 `max_project_bytes`、`max_temporary_bytes`、`min_headroom_bytes`、可探测时的 `user_quota_bytes`、`source_preference`、`allow_sra_lite`、`auto_restart` 与 `max_auto_restarts`。默认 `auto_restart=false`。

## `source_manifest.tsv`

每个 run 一行，保留既有 accession、layout、expected spots 和 NGDC 探测字段，并增加：

```text
selected_source selected_provenance object_class quality_class transport_endpoint
selected_urls selected_bytes selected_md5 read_roles final_product
selection_evidence selection_reason fallback_reason
```

`fallback_reason` 仅兼容旧读取；新选择以 evidence/reason 解释。object/provenance/quality 必须与 `source_capability.yaml` 一致。transport endpoint 不作为 provenance。

## 下载与转换证据

- `<GSM>.tsv`：逐 run 的实际对象分类、文件路径、bytes/MD5、验证方法和完成时间。NCBI resolver 若实际得到 Lite，必须记录 `SRA_LITE/SIMPLIFIED`。
- `conversion_provenance.tsv`：每 GSM 一行，至少含 `gse,gsm,tool,tool_version,input_fastq,output_matrix,validated_at`；`input_files` 可作为兼容扩展。输入必须覆盖该 GSM 全部成员 runs。
- `processed_output_audit.tsv`：每 GSM 的结构、样本覆盖和状态；支持 `--gsm/--unit` 增量更新。

## `storage_release.tsv`

每 GSM/文库一行，记录成员 runs、最终产物、policy 确认时间、download/conversion/processed 三门状态、精确候选路径/bytes/MD5、`release_status=blocked|ready|released` 和释放时间。

`ready` 必须在删除前原子落盘；删除前再次比对候选 fingerprint。`storage_deletion_log.tsv` 逐文件记录实际删除。没有 release 与 deletion 两层证据，不得把 assay 聚合状态置为 deleted。

## 报告边界

每 GSE 只有一份中文 `reports/report.html`。所有报告显示项目相对路径，禁止写入代理凭据或绝对私有路径。TSV/JSON/log 是机器证据，不算额外人类报告。
