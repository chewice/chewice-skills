# Assay 转换

本 Skill 负责把 raw assay 转成可长期保存、软件无关的标准数据产品。不运行 DESeq2、GO/KEGG、聚类或生物学解释。

先读 `assay_capability.yaml`。只生成该 modality 声明的 output / optional。转换前确认 STAR index 与 GTF（或用户指定的替代参考），这些资源由用户提供或事先构建，下载流程不现场生成人类基因组 index。

输入一律来自 Mode A 的 `raw/GSM*/fastq/` 或 Mode B 的 `temporary/GSM*/fastq/`。产物写入 `processed/`。工具、版本、输入、输出写入 `reports/conversion_provenance.tsv`。

## bulk RNA-seq → `gene_count_matrix`

默认：STAR `--quantMode GeneCounts`，再合并为 gene × sample 矩阵。

```text
FASTQ → STAR → ReadsPerGene.out.tab → processed/gene_count_matrix.tsv
```

1. 确认 `ref.star_index` 与 `ref.gtf`。index 需已用同一 GTF 构建。
2. 按文库链特异性选择 ReadsPerGene 列：`unstranded`=第 2 列，`forward`=第 3 列，`reverse`=第 4 列（Illumina TruSeq stranded 常用 reverse）。
3. 每个 GSM 的 STAR 输出可留在 `processed/GSM*/counts/`。
4. 运行 `scripts/merge_star_counts.py --root . --strandedness unstranded|forward|reverse`。
5. 默认不保存 BAM。用户明确要求时才写入 `processed/GSM*/alignment/*.bam` 并建索引。
6. 不要跑 DESeq2、enrichment、megadepth/bigWig。

替代工具（用户指定时）：STAR + featureCounts，或 Salmon。不要同时把多种定量结果都写成“最终矩阵”，选一种写入 provenance。

Mode B 的 `final_product` 为 `gene_count_matrix`。

## scRNA-seq / snRNA-seq → `matrix_10x`

抽象步骤是 single-cell counting，当前默认实现为 STARsolo：

```text
FASTQ → STARsolo → matrix.mtx.gz + features.tsv.gz + barcodes.tsv.gz
```

输出目录：`processed/GSM*/matrix_10x/`（raw 与 filtered triplet）。几何判定阅读 `references/starsolo-read-geometry.md`。未来可换成 Cell Ranger 或 kallisto bustools，Skill 只验收 10x triplet。

velocity 仅为 optional：只在用户要求、或 Mode B 的 `final_product=matrix_velocity` 时生成 `processed/GSM*/velocity/`。bulk / ATAC / ChIP / 芯片不得生成 velocity。

## 芯片 / 甲基化

本 Skill 只下载 CEL/IDAT 并管理文件。不做 RMA、quantile、probe 重注释或下游分析。GEO/厂商提供的 probe 映射可保存到 `annotation/platform_annotation/`，这是文件管理不是分析。

芯片 Mode B 仅当用户指定转换工具、版本和输出路径后才下载；产物记为 `intensity` 或 `processed`。

## ATAC / ChIP / miRNA / 未细分测序

`assay_capability.yaml` 未声明 conversion 时，Mode A 可停在 FASTQ/SRA。Mode B 在用户指定转换产品前暂停，不要套用 STARsolo。
