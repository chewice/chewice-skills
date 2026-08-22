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
| `sra` | `RNA-seq` / `ATAC-seq` / `ChIP-seq` / `miRNA-seq` / `sequencing` | `FASTQ` | `raw/GSM*/fastq/` 或 `raw/GSM*/sra/` |
| `affymetrix` | `microarray` | `CEL` | `raw/GSM*/CEL/` |
| `illumina` | `microarray` | `IDAT` | `raw/GSM*/IDAT/` |
| `methylation` | `methylation` | `IDAT` | `raw/GSM*/IDAT/` |

Mode B 将上述目录替换为 `temporary/GSM*/...`。禁止写入 Seurat/Scanpy/RData/pickle。

## 判定规则

1. 存在 SRR/run，或 `library_strategy`/`technology` 指向高通量测序 → `workflow=sra`，`raw_file_type=FASTQ`。`assay_type` 按证据细分：RNA-seq/transcriptome → `RNA-seq`；ATAC-seq → `ATAC-seq`；ChIP-seq → `ChIP-seq`；miRNA-seq → `miRNA-seq`；仅有测序平台证据 → `sequencing`。不得把 ATAC/ChIP 标成 `RNA-seq`。
2. `GPL570` 及已知 Affymetrix 表达芯片，或平台名含 Affymetrix/GeneChip/U133 → `affymetrix` / `CEL`。
3. 450K/EPIC 等甲基化芯片 → `methylation` / `IDAT`。
4. Illumina BeadChip 表达芯片 → `illumina` / `IDAT`。

不能只依据 GPL 数字猜测测序平台：HiSeq/NovaSeq 的 GPL 仍走 `sra`。10x Genomics 无其他文库证据时标 `RNA-seq`。

STARsolo / velocity 只适用于有 10x/droplet scRNA 证据的 `sra` 样本。ATAC-seq、ChIP-seq、miRNA-seq、bulk RNA-seq 即使 `workflow=sra` 也不要默认 STARsolo。

芯片补充文件、probe 注释和解包规则见 `references/array-download.md`。
