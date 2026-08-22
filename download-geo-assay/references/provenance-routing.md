# Provenance 与数据源路由

## Provenance 判定

按实际下载的字节分类，而不是按其代表的生物学内容分类。

| 证据 | 分类 | 含义 |
|---|---|---|
| ENA `submitted_*` 和 `SUBMITTED_FILE` | `AUTHOR_SUBMITTED` | 提交者上传的文件 |
| 原生 GSA/CRA 文件 | `GSA_AUTHOR_SUBMITTED` | 提交到 NGDC GSA 的文件 |
| NGDC INSDC 镜像 `.sra` | `NGDC_MIRROR_SRA` | 镜像归档表示，并非原始 FASTQ 字节 |
| NCBI/ENA `.sra` | `ARCHIVE_NORMALIZED_SRA` | 归档标准化 SRA |
| ENA `GENERATED_FILE` 或 `fasterq-dump` 输出 | `ARCHIVE_GENERATED_FASTQ` | 从归档内容生成的 FASTQ |
| 作者提交的 BAM | `AUTHOR_SUBMITTED_BAM` | 作者比对结果，依赖参考版本 |
| GEO count/logcount/标准化矩阵 | `GEO_PROCESSED` | processed 数据，默认排除 |

不能仅因文件名看似作者原始文件名就判定为 `AUTHOR_SUBMITTED`。数据库展示的 run alias 可能保留原始名称，但实际下载对象仍可能是标准化 SRA。

## 固定数据源优先级

逐个 run 独立应用优先级：

1. CRA/CRR 数据的原生 NGDC GSA 文件。
2. 可用且有效的 NGDC INSDC 镜像 SRA。
3. 可用的 ENA 作者提交 FASTQ，其次为 ENA 生成 FASTQ。
4. NCBI SRA Toolkit。

不能因 NGDC 收录项目就推断其覆盖完整。必须精确比较预期 run 集合与可用 run 集合。

不能仅因测速更快而用 ENA 替代有效的 NGDC run。直连/代理测试可用于诊断可达性，但不能改变优先级。

## 有效的 fallback reason

使用以下值之一：

- `ngdc_missing`
- `ngdc_no_file_endpoint`
- `ngdc_unreachable_after_3_attempts`
- `ngdc_size_invalid`
- `ngdc_vdb_validate_failed`
- `ngdc_read_count_failed`
- `ngdc_metadata_conflict`
- `native_gsa_not_applicable`

必要时可在冒号后追加简短说明。选择 ENA/NCBI 时不得将 reason 留空。

## 产品选择

- 默认：可直接分析的 FASTQ。
- STARsolo、重新比对和 velocity：FASTQ。
- 归档/重新转换：SRA 或作者提交源文件。
- 复用作者比对结果：仅在检查参考与 aligner 兼容性后选择 BAM。
- 当作者原生 FASTQ 与目标分析兼容时优先选择；但用户明确要求 NGDC-first 路由时，有效的 NGDC 镜像仍保持数据源优先级。

当最终产品为 FASTQ，而 NGDC 提供 SRA 时，必须分别说明两个阶段：下载对象 = `NGDC_MIRROR_SRA`；保留的 FASTQ = `ARCHIVE_GENERATED_FASTQ`。
