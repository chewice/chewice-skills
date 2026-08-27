# Raw-only sequencing

ATAC-seq、ChIP-seq、miRNA-seq 以及未定义标准转换产品的 sequencing assay，在本 Skill 边界内只负责获取、校验和记录 FASTQ/SRA。

- 不为了获得删除资格而伪造 count matrix 或引入下游分析流水线。
- `assay_capability.yaml` 中 `workflow: raw_only` 且 `standard_products: []` 时，存储策略只能保留 raw；Mode B 必须被校验器拒绝。
- 如果未来需要释放 raw，应在另一个明确的分析合同中定义可审计标准产物，再升级能力表和行为测试；不能由单次项目临时放宽。
