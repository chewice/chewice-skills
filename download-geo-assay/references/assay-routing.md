# Assay 分流

下载前运行 `scripts/detect_assay.py`，按 GSM 判定 `workflow` 与 `modality`。混合 assay 写入分流表，然后按 assay 分别记录存储策略并走对应获取分支。不要把芯片 GSM 丢进 `download_run.sh`。仅在 `--reject-mixed` 时退出。

读 `assay_capability.yaml` 决定该 modality 允许哪些转换产物。

## 输出

`metadata/assay_routing.tsv`：

```text
gse
gsm
gpl
assay_type
modality
raw_file_type
workflow
evidence
```

| workflow | assay_type | modality | raw_file_type | 原始文件目录 |
|---|---|---|---|---|
| `sra` | `RNA-seq` | `bulk_rnaseq` / `scRNAseq` / `snRNAseq` | `FASTQ` | `raw/GSM*/fastq/` 或 `raw/GSM*/sra/` |
| `sra` | `ATAC-seq` / `ChIP-seq` / `miRNA-seq` / `sequencing` | `atac` / `chip` / `mirna` / `sequencing` | `FASTQ` | 同上 |
| `affymetrix` | `microarray` | `microarray` | `CEL` | `raw/GSM*/CEL/` |
| `illumina` | `microarray` | `microarray` | `IDAT` | `raw/GSM*/IDAT/` |
| `methylation` | `methylation` | `methylation` | `IDAT` | `raw/GSM*/IDAT/` |

Mode B 将上述目录替换为 `temporary/GSM*/...`。禁止写入 Seurat/Scanpy/RData/pickle。

## 判定规则

1. 存在 SRR/run，或 `library_strategy`/`technology` 指向高通量测序 → `workflow=sra`，`raw_file_type=FASTQ`。`assay_type` 按证据细分。RNA-seq 再分 modality：single-nucleus → `snRNAseq`；single-cell / 10x / droplet → `scRNAseq`；其余 → `bulk_rnaseq`。不得把 ATAC/ChIP 标成 `RNA-seq`。
2. `GPL570` 及已知 Affymetrix 表达芯片，或平台名含 Affymetrix/GeneChip/U133 → `affymetrix` / `CEL`。
3. 450K/EPIC 等甲基化芯片 → `methylation` / `IDAT`。
4. Illumina BeadChip 表达芯片 → `illumina` / `IDAT`。

不能只依据 GPL 数字猜测测序平台：HiSeq/NovaSeq 的 GPL 仍走 `sra`。

转换规则见 `references/conversion.md`。芯片补充文件见 `references/array-download.md`。
