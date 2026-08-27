# sc/snRNA-seq

- release 单元是一个 GSM/文库的全部 runs，而不是单个 SRR。
- 先从实验和文件元数据判定 barcode/UMI/cDNA read 角色及长度；不能仅按 R1/R2 名称猜测。复杂几何再读 `../starsolo-read-geometry.md`。
- 标准产物是完整 10x 三件套：matrix、features/genes、barcodes。维度、索引范围、features 行数、barcodes 列数和非零计数必须一致，且样本归属明确。
- 可选 velocity 输入只有在 spliced/unspliced/ambiguous 结构和来源均可审计时才算完成。
- 多-run GSM 必须证明所有成员 runs 被纳入同一转换；缺任一 run、read 角色冲突或输入 provenance 不全时保留全部 raw。
- sc 与 sn 的参考和计数策略不可因文件结构相似而互换；记录 intron/exon 选择和参考构建证据。
