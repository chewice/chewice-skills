# Manifest 与项目 schema

## 数据集目录

使用 `<output-root>/GEO/<GSE>/`。如果未指定输出根目录，则使用 `<current-directory>/GEO/<GSE>/`。

```text
GEO/GSE123456/
├── metadata/
│   ├── study_metadata.tsv
│   ├── sample_metadata.tsv
│   ├── sample_characteristics.tsv
│   ├── srr_gsm_mapping.tsv
│   ├── expected_runs.tsv
│   ├── ena_runs.tsv
│   └── source_manifest.tsv
├── GSM000001/
│   ├── fastq/
│   ├── sra/
│   ├── work/
│   ├── matrix_10x/
│   ├── velocity/
│   └── download_manifest.tsv
├── reports/
│   ├── logs/
│   ├── status/
│   ├── fastqc/
│   ├── multiqc_data/
│   ├── report.html
│   ├── preflight_audit.tsv
│   ├── ngdc_coverage.tsv
│   ├── download_integrity_audit.tsv
│   ├── final_output_audit.tsv
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
| 元数据 | `metadata/` | study、sample、run、ENA 与 source manifest |
| GSM sample | `GSM*/` | 每个 GSM 的独立目录 |
| run FASTQ | `GSM*/fastq/` | 按 SRR 分开的 R1/R2/I1/I2 |
| SRA | `GSM*/sra/` | 需要保留时的归档文件 |
| 临时转换 | `GSM*/work/` | `.part`、SRA 转换和中间文件 |
| 10x 矩阵 | `GSM*/matrix_10x/` | raw/filtered feature-barcode matrix |
| RNA velocity | `GSM*/velocity/` | spliced、unspliced、ambiguous 与 loom |
| 统一报告 | `reports/report.html` | 唯一面向用户的中文 HTML |
| 机器证据 | `reports/*.tsv` | preflight、coverage、download、final audit |
| STARsolo 汇总 | `reports/starsolo_summary.tsv` | 每个 GSM 一行的 cell calling、mapping、saturation 与计数指标 |
| QC 数据 | `reports/fastqc/`、`reports/multiqc_data/` | 供统一报告读取的机器数据 |
| 日志与状态 | `reports/logs/`、`reports/status/` | 原始日志和完成 marker |

HTML 中显示上述项目相对路径。从 `reports/report.html` 链接文件时，实际 href 使用 `../metadata/...` 等浏览器相对地址。不得将 GSE 根目录的绝对路径写入报告。

## 报告展示层

`reports/report.html` 是唯一面向用户的报告。它由 `scripts/build_report.py` 原子生成，使用 UTF-8 和内联 CSS/JS，不依赖 CDN。完整 MultiQC HTML 以内嵌 iframe 保存到该文件；成功内嵌后删除临时 MultiQC HTML，但保留 JSON/TSV 等机器数据。

以下文件继续使用 TSV/JSON/log 等机器可读格式，因为下载、恢复和审计脚本依赖它们：

- `metadata/*.tsv`
- `GSM*/download_manifest.tsv`
- `reports/*_audit.tsv`
- `reports/ngdc_coverage.tsv`
- `reports/starsolo_summary.tsv`
- `reports/logs/*`
- `reports/status/*`

旧项目中的 `reports/dataset_overview.md`、`reports/preflight_summary.md` 和 `reports/ngdc_mirror_audit.md` 可被纳入统一报告，但生成器不得自动删除它们。

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

允许的 `final_product`：`fastq`、`sra`、`matrix_velocity`。

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

## 每个 GSM 的 `download_manifest.tsv`

仅当 run 达到通过校验的终态后追加一行：

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
```

先写入临时文件，再原子改名。不得用完成记录代替对其引用文件的实际检查。
