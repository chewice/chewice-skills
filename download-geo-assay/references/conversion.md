# Assay 转换（兼容入口）

先由 `assay_capability.yaml` 路由，只读 `assays/` 下匹配的 reference。

- bulk：`assays/bulk-rnaseq.md`
- sc/snRNA：`assays/scrna.md`
- CEL/IDAT：`assays/array.md`
- ATAC/ChIP/miRNA/raw-only：`assays/raw-only-seq.md`

未知 strandedness 保持 pending，STAR GeneCounts 三列都保留；转换与 release 以 GSM/文库而非 SRR 为单位。
