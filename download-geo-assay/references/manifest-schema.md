# Manifest 与项目 schema

## 数据集目录

使用 `<output-root>/GEO/<GSE>/`。如果未指定输出根目录，则使用 `<current-directory>/GEO/<GSE>/`。

```text
GEO/GSE123456/
├── README.md
├── metadata/
│   ├── study_metadata.tsv
│   ├── donor_metadata.tsv
│   ├── sample_metadata.tsv
│   ├── platform_metadata.tsv
│   ├── assay_routing.tsv
│   ├── sample_characteristics.tsv
│   ├── srr_gsm_mapping.tsv
│   ├── expected_runs.tsv
│   ├── ena_runs.tsv
│   ├── source_manifest.tsv
│   ├── supplement_files.tsv
│   ├── acquisition_config.tsv
│   ├── storage_policy.tsv
│   └── download_manifests/
│       └── GSM000001.tsv
├── raw/
│   └── GSM000001/
│       ├── fastq/
│       ├── sra/
│       ├── CEL/
│       └── IDAT/
├── temporary/
│   └── GSM000001/
│       ├── fastq/
│       ├── CEL/
│       ├── IDAT/
│       └── work/
│           └── SRR000001/
├── processed/
│   └── GSM000001/
│       ├── matrix_10x/
│       └── velocity/
├── annotation/
│   └── platform_annotation/
│       └── probe_to_gene_mapping.tsv
├── qc/
├── reports/
│   ├── logs/
│   ├── status/
│   │   ├── SRR*.transfer.json
│   │   └── SRR*.complete
│   ├── fastqc/
│   ├── multiqc_data/
│   ├── report.html
│   ├── preflight_audit.tsv
│   ├── ngdc_coverage.tsv
│   ├── download_integrity_audit.tsv
│   ├── final_output_audit.tsv
│   ├── conversion_provenance.tsv
│   ├── storage_deletion_log.tsv
│   ├── storage_policy_audit.tsv
│   └── tool_versions.tsv
├── scripts/
├── pixi.toml
└── pixi.lock
```

仅创建最终产品需要的目录。运行日志不是表达矩阵 `logcounts`，必须保留。

## 路径与层级约定

所有路径均以单个 GSE 根目录为基准：

| 层级 | 相对路径 | 内容 |
|---|---|---|
| GSE 项目 | `.` | 单个数据集的完整获取和处理项目 |
| 元数据 | `metadata/` | study、donor、sample、platform、assay、run、ENA、source 与 storage policy |
| 下载证据 | `metadata/download_manifests/<GSM>.tsv` | 每个 GSM 的已校验下载记录 |
| Mode A FASTQ | `raw/GSM*/fastq/` | 长期保存的 R1/R2/I1/I2 |
| Mode A SRA | `raw/GSM*/sra/` | 需要保留时的归档文件 |
| Mode A CEL | `raw/GSM*/CEL/` | Affymetrix CEL / CEL.gz |
| Mode A IDAT | `raw/GSM*/IDAT/` | Illumina 表达或甲基化 IDAT |
| Mode B raw | `temporary/GSM*/fastq/` 等 | 仅供转换的临时 raw files，验证后删除 |
| 平台注释 | `annotation/platform_annotation/` | probe_to_gene_mapping 等 |
| QC | `qc/` | 芯片或测序 QC 中间文件 |
| 临时工作区 | `temporary/GSM*/work/<run>/` | staging、`.part`、SRA 转换和断点 |
| 10x 矩阵 | `processed/GSM*/matrix_10x/` | raw/filtered feature-barcode matrix |
| RNA velocity | `processed/GSM*/velocity/` | spliced、unspliced、ambiguous 与 loom |
| 统一报告 | `reports/report.html` | 唯一面向用户的中文 HTML |
| 机器证据 | `reports/*.tsv` | preflight、coverage、download、final、storage audit |
| STARsolo 汇总 | `reports/starsolo_summary.tsv` | 每个 GSM 一行的 cell calling、mapping、saturation 与计数指标 |
| QC 数据 | `reports/fastqc/`、`reports/multiqc_data/` | 供统一报告读取的机器数据 |
| 日志与状态 | `reports/logs/`、`reports/status/` | 原始日志和完成 marker |

HTML 中显示上述项目相对路径。从 `reports/report.html` 链接文件时，实际 href 使用 `../metadata/...` 等浏览器相对地址。不得将 GSE 根目录的绝对路径写入报告。

## 报告展示层

`reports/report.html` 是唯一面向用户的报告。它由 `scripts/build_report.py` 原子生成，使用 UTF-8 和内联 CSS/JS，不依赖 CDN。完整 MultiQC HTML 以内嵌 iframe 保存到该文件；成功内嵌后删除临时 MultiQC HTML，但保留 JSON/TSV 等机器数据。

以下文件继续使用 TSV/JSON/log 等机器可读格式，因为下载、恢复和审计脚本依赖它们：

- `metadata/*.tsv`
- `metadata/download_manifests/*.tsv`
- `reports/*_audit.tsv`
- `reports/ngdc_coverage.tsv`
- `reports/starsolo_summary.tsv`
- `reports/conversion_provenance.tsv`
- `reports/storage_deletion_log.tsv`
- `reports/logs/*`
- `reports/status/*`

旧项目中的 `GSM*/fastq/`、`GSM*/matrix_10x/` 和 `GSM*/download_manifest.tsv` 可被审计脚本只读回退识别；新项目不得创建这些路径。

旧项目中的 `reports/dataset_overview.md`、`reports/preflight_summary.md` 和 `reports/ngdc_mirror_audit.md` 可被纳入统一报告，但生成器不得自动删除它们。

## `storage_policy.tsv`

整个 GSE 一行，在大规模传输前由用户确认后写入：

```text
gse
assay_type
raw_file_type
retain_raw_files
storage_mode
validation_status
deletion_status
deletion_time
```

| 列 | 允许值 |
|---|---|
| `assay_type` | `RNA-seq`、`ATAC-seq`、`ChIP-seq`、`miRNA-seq`、`sequencing`、`microarray`、`methylation`；未判定前可空或 `pending` |
| `raw_file_type` | `FASTQ`、`SRA`、`CEL`、`IDAT`；未判定前可空或 `pending` |
| `retain_raw_files` | `true` 或 `false`，不得留空，不得默认；兼容旧列 `retain_raw_fastq` |
| `storage_mode` | `retain` 或 `delete_after_validation`，必须与 `retain_raw_files` 一致 |
| `validation_status` | `pending`、`conversion_pending`、`validated`、`failed`、`not_applicable` |
| `deletion_status` | `not_applicable`、`pending`、`deleted`、`blocked` |
| `deletion_time` | 删除完成时的 ISO-8601，否则留空 |

Mode A 的 `deletion_status` 必须是 `not_applicable`。Mode B 初始为 `pending`，仅在转换产物验证通过并由 `apply_storage_policy.py` 删除 temporary raw files 后变为 `deleted`。

## `conversion_provenance.tsv`

每个完成转换的 GSM 一行：`gse`、`gsm`、`tool`、`tool_version`、`input_fastq`、`output_matrix`、`validated_at`。路径使用项目相对路径，分号分隔。测序把 FASTQ 写在 `input_fastq`；芯片可把 CEL/IDAT 路径写在同一列，或额外提供 `input_files`。`output_matrix` 对芯片表示 intensity/processed 产物路径。

## `storage_deletion_log.tsv`

每个被删除的 FASTQ 一行：`gse`、`gsm`、`srr`、`path`、`bytes`、`md5`、`validation_report`、`deleted_at`。`path` 为项目相对路径。没有该日志不得将 `deletion_status` 设为 `deleted`。

## `expected_runs.tsv`

每个预期 run 一行：

| 列 | 要求 |
|---|---|
| `gse` | `GSE` accession |
| `gsm` | 所属 `GSM` accession |
| `srx` | Experiment accession（如可获得） |
| `srr` | 唯一的 `SRR`/`ERR`/`DRR`/`CRR` run accession |
| `run_alias` | 原始 run alias |
| `lane` | 从 metadata/文件名解析的 lane，或留空 |
| `library_layout` | `PAIRED` 或 `SINGLE` |
| `read_structure` | 已知结构，例如 `R1:28,R2:91`；不得猜测 |
| `expected_spots` | 每个逻辑 mate 的预期记录数 |
| `cb_length` | 单细胞数据的 barcode 长度，或留空 |
| `umi_length` | UMI 长度，或留空 |

将换行统一为 LF。数值字段只能包含数字或留空。即使某数据源缺少部分 run，也必须保留完整预期 run 集合。

## `ena_runs.tsv`

尽可能保留 ENA 报告中的原始字段。数据源选择至少需要：

```text
run_accession
submitted_ftp
submitted_bytes
submitted_md5
fastq_ftp
fastq_bytes
fastq_md5
fastq_file_role
sra_ftp
sra_bytes
sra_md5
read_count
library_layout
```

以分号分隔的 URL/byte/MD5/role 数组长度必须一致。仅当同一 endpoint 支持 HTTPS 时，才将裸 FTP host 路径转换为 `https://`。

## `ngdc_coverage.tsv`

每个预期 run 一行：

```text
gse
gsm
srx
srr
ngdc_browse_url
ngdc_run_page
ngdc_status
ngdc_url
ngdc_file_type
ngdc_bytes
expected_spots
probe_attempts
probe_message
```

允许的 `ngdc_status` 值：

- `available`：endpoint 返回稳定且大于零的 Content-Length。
- `missing`：所有已解析/候选 endpoint 均返回 not found。
- `invalid`：endpoint 存在，但 metadata/大小无效。
- `unreachable`：网络/TLS/server 故障导致无法判定。
- `not_probed`：尚未执行网络探测。

## `source_manifest.tsv`

每个 run 一行：

```text
gse
gsm
srx
srr
run_alias
lane
library_layout
read_structure
expected_spots
cb_length
umi_length
ngdc_status
ngdc_run_page
ngdc_url
ngdc_bytes
selected_source
selected_provenance
selected_urls
selected_bytes
selected_md5
read_roles
final_product
fallback_reason
```

允许的 `selected_source`：

- `ngdc_gsa`
- `ngdc_insdc`
- `ena_submitted`
- `ena_fastq`
- `ncbi_sra`

允许的 `selected_provenance`：

- `AUTHOR_SUBMITTED`
- `GSA_AUTHOR_SUBMITTED`
- `NGDC_MIRROR_SRA`
- `ARCHIVE_NORMALIZED_SRA`
- `ARCHIVE_GENERATED_FASTQ`
- `AUTHOR_SUBMITTED_BAM`
- `GEO_PROCESSED`

允许的测序 `final_product`：`fastq`、`sra`、`matrix_velocity`。芯片 Mode A 可为 `CEL` 或 `IDAT`；芯片 Mode B 为 `intensity` 或 `processed`。`source_manifest.tsv` 只用于 `workflow=sra`。

`selected_urls`、`selected_bytes`、`selected_md5` 和 `read_roles` 使用分号分隔数组。角色为 `SRA`、`R1`、`R2`、`I1`、`I2`、`BAM` 或 `OTHER`。每个非 NGDC 选择都必须填写 `fallback_reason`。

## `sample_metadata.tsv`

每个 GSM 一行，至少保留：

```text
gse
gsm
title
organism
tissue
condition
treatment
donor_subject
sex
age
batch
library_strategy
library_source
library_selection
platform
instrument_model
chemistry
srx_list
srr_list
run_count
lane_count
read_structure
ngdc_coverage
provenance
selected_source
final_product
expected_bytes
status
notes
```

不要将任意 GEO characteristics 扁平化为会丢失信息的列。将其保存到 `sample_characteristics.tsv`，字段为 `gse`、`gsm`、`key`、`value` 和 `source_order`。

## 每个 GSM 的 `metadata/download_manifests/<GSM>.tsv`

仅当 run 达到通过校验的终态后追加一行。Mode B 删除 FASTQ 后此文件仍保留，作为下载证据。

```text
gse
gsm
srr
source
provenance
final_product
urls
expected_bytes
observed_bytes
expected_md5
observed_md5
expected_spots
observed_r1
observed_r2
validation
completed_at
retained_files
retained_bytes
retained_md5
integrity_methods
attempt_count
resume_count
source_fingerprint
```

先写入临时文件，再原子改名。不得用完成记录代替对其引用文件的实际检查。

`retained_files` 使用项目相对路径；`retained_bytes` 和 `retained_md5` 与其按位置
一一对应。旧项目缺少新增列时仍可执行兼容审计，但新事务必须写齐这些列。

## `<run>.transfer.json`

每个 run 的持久恢复状态至少包含：

```text
run
source_fingerprint
phase
status
attempt_count
resume_count
bytes_resumed
error_counts
error_class
last_error
created_at
updated_at
```

`status` 为 `in_progress`、`retryable_failed`、`terminal_failed` 或 `complete`。
该 JSON 原子写入，是 watchdog 判断是否允许自动恢复的机器证据。
