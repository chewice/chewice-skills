# Manifest 与状态 schema

项目根为 `<output-root>/GEO/<GSE>/`。新项目的能力表快照位于 `config/`；已生成项目不自动迁移。

## 关键路径

```text
config/{assay_capability.yaml,source_capability.yaml}
metadata/{assay_routing.tsv,expected_runs.tsv,source_manifest.tsv,storage_policy.tsv,acquisition_config.tsv}
metadata/download_manifests/<GSM>.tsv
raw/<GSM>/{fastq,sra,CEL,IDAT}/
temporary/<GSM>/{fastq,sra,CEL,IDAT,work}/
processed/<GSM>/...
deliverables/<sample_id>/{matrix,counts.tsv.gz,sample.tsv,provenance.json,validation.json,checksums.sha256,.complete}
reports/{conversion_inputs,processed_receipts,release_journals}/<GSM>.json
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
- `conversion_provenance.tsv`：每 GSM 一行，至少含 `gse,gsm,tool,tool_version,input_fastq,output_matrix,validated_at`；测序正式交付还需 `reference,counting_strategy`；`input_files` 可作为兼容扩展。输入必须覆盖该 GSM 全部成员 runs。
- `processed_output_audit.tsv`：每 GSM 的结构、样本覆盖和状态；支持 `--gsm/--unit` 增量更新。

## `storage_release.tsv`

每 GSM/文库一行，记录成员 runs、最终产物、policy 确认时间、download/conversion/processed 三门状态、精确候选路径/bytes/MD5、`release_status=blocked|ready|released` 和释放时间。

`ready` 必须在删除前原子落盘；删除前再次比对候选 fingerprint。`storage_deletion_log.tsv` 逐文件记录实际删除。没有 release 与 deletion 两层证据，不得把 assay 聚合状态置为 deleted。

## 报告边界

每 GSE 只有一份中文 `reports/report.html`。所有报告显示项目相对路径，禁止写入代理凭据或绝对私有路径。TSV/JSON/log 是机器证据，不算额外人类报告。

## 内容绑定与交付

`conversion_inputs/<GSM>.json` 在转换前保存完整来源合同、样本映射、下载记录和精确输入 paths/bytes/SHA256。`processed_receipts/<GSM>.json` 将同一合同、provenance 与全套产物校验和绑定。任一文件或归属改变使旧 PASS 失效。

`release_journals/<GSM>.json` 在首次 unlink 前保存原始候选及 receipt 指纹，逐文件持久化删除结果；中断恢复只处理原事务剩余文件，新出现文件或变化产物阻断恢复。TSV 是摘要，JSON journal 是逐文件恢复依据。

正式格式与流程见 `open-delivery.md`；STRUCTURE_ONLY 不等于 PASS，旧 TSV PASS 不提供删除权限。

## 获取运行时配置与状态

| 配置 | 默认值 | 含义 |
|---|---|---|
| `download_workers` | 2 | 队列同时获取的 run 数 |
| `download_connections` | 4 | 每文件最大连接数 |
| `conversion_workers` | 1 | 仅允许 1；展开、压缩、assay 转换共用槽位 |
| `max_same_error_attempts` | 3 | 同类错误的持久重试上限 |
| `retry_delays_seconds` | `0;30;120` | 逐次退避秒数 |
| `storage_check_interval_seconds` | 1 | 运行中空间检查间隔 |
| `min_headroom_bytes` | 10 GiB | 磁盘和预算安全余量 |
| `proxy_env_file` | 空 | 可信本地代理环境文件路径 |
| `require_proxy` | true | 外网必须经过指定代理 |

显式命令参数/`GEO_SRA_*` 环境覆盖优先于项目配置，未指定时使用默认值。`GEO_SRA_PROXY_ENV` 优先于项目的代理文件；不要将凭据写进此 TSV。脱敏后的设置写入 `reports/status/acquisition_config.effective.json`。

`acquisition_runtime.json` 保存预留、所属进程身份、启动时间和父子关系。进程退出前不得手动删除此账本。`<RUN>.ready.json` 记录获取成功的来源对象路径、大小、摘要和来源身份；`acquired` 仅允许进入转换阶段。AWS `awaiting_identity` 表示传输与原生校验通过、尚待来源身份复核，不是 PASS。

下载 manifest 与 complete marker 均需 `acceptance_fingerprint`，覆盖 layout、expected spots、CB/UMI、read roles、final product 和合同版本。合同变化使旧 PASS 失效，应重验已有对象，不直接重新传输。source fingerprint 继续绑定来源对象身份；它不包含代理和脚本内容。

supplement manifest 还记录 `integrity_methods,response_bytes,etag,last_modified,expected_bytes,expected_md5,member_of,member_name,source_fingerprint`。归档成员绑定已验证来源归档；本地摘要只用于防变更，不作为来源完整性的唯一证据。`UNVERIFIED` 不允许进入转换/发布验收门。
