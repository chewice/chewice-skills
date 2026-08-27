# Bulk RNA-seq

- release 单元是 GSM/文库；同一 GSM 的全部 runs 必须共同下载、转换和审计。
- 标准产物是带 `gene_id` 和 GSM 样本列的非负整数 count matrix。gene ID 必须唯一；不得用只有文件存在或非空代替审计。
- 参考基因组与注释必须版本相容并记录来源、版本和校验和。
- `sjdbOverhang` 从权威 read length 推导，并用 pilot FASTQ 的真实 read length 复核；不能仅凭 accession 或固定常数猜测。
- STAR `--quantMode GeneCounts` 一次产生 unstranded、forward、reverse 三列。建库方向未知时保留三列和 `unknown/pending` 状态，先用建库信息和代表性样本判定，再选择最终矩阵列。
- conversion provenance 必须覆盖该 GSM 全部成员 runs/FASTQ，并记录工具与版本、参考对象和输出。
- 只有 `gene_count_matrix` 审计通过且已确认 Mode B 时可以释放对应 raw；BAM 属于可选中间/产物，不自动替代 count matrix。
