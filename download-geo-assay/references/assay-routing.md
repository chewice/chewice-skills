# Assay 分流

下载前运行 `scripts/detect_assay.py`，按 GSM 判定 workflow。混合 workflow 的 GSE 必须暂停。

## 输出

`metadata/assay_routing.tsv`：

```text
gse
gsm
gpl
assay_type
raw_file_type
workflow
evidence
```

| workflow | assay_type | raw_file_type | 原始文件目录 |
|---|---|---|---|
| `sra` | `RNA-seq` | `FASTQ` | `raw/GSM*/fastq/` 或 `raw/GSM*/sra/` |
| `affymetrix` | `microarray` | `CEL` | `raw/GSM*/CEL/` |
| `illumina` | `microarray` | `IDAT` | `raw/GSM*/IDAT/` |
| `methylation` | `methylation` | `IDAT` | `raw/GSM*/IDAT/` |

Mode B 将上述目录替换为 `temporary/GSM*/...`。禁止写入 Seurat/Scanpy/RData/pickle。

## 判定规则

1. 存在 SRR/run，或 `library_strategy`/`technology` 指向高通量测序 → `sra`。
2. `GPL570` 及已知 Affymetrix 表达芯片，或平台名含 Affymetrix/GeneChip/U133 → `affymetrix` / `CEL`。
3. 450K/EPIC 等甲基化芯片 → `methylation` / `IDAT`。
4. Illumina BeadChip 表达芯片 → `illumina` / `IDAT`。

不能只依据 GPL 数字猜测测序平台：HiSeq/NovaSeq 的 GPL 仍走 `sra`。

## Affymetrix 额外产物

- `metadata/platform_metadata.tsv`：GPL、array type、annotation version。
- `annotation/platform_annotation/probe_to_gene_mapping.tsv`：probe 到 gene 的映射。
- CEL 文件保存为 `GSM*.CEL` 或 `GSM*.CEL.gz`。

芯片补充文件清单写入 `metadata/supplement_files.tsv` 后，运行 `scripts/download_geo_supplement.py`。
