# download-geo-assay

按 GEO assay 分流，安全检查、下载、校验和记录公共组学原始数据（bulk/sc/snRNA-seq FASTQ/SRA、Affymetrix CEL、Illumina/甲基化 IDAT），并按 assay 分别管理 raw files 生命周期。

主要特性：

- 下载前先判定 `assay_type` / `modality` / `raw_file_type` / `workflow`；测序与芯片走不同获取分支。
- 多个 assay 时分别确认是否长期保存 raw files，不使用全局默认。
- 下载前询问最大临时存储配额；Mode B 分批转换以免占满磁盘。
- 测序 run 优先使用有效的 NGDC 数据，必要时回退 ENA 或 NCBI。
- 芯片走 GEO supplementary（CEL/IDAT）；zip 中只解出 CEL/IDAT。不做芯片 normalization。
- bulk RNA-seq 可将 FASTQ 转为 `gene_count_matrix`（STAR GeneCounts）；默认不保存 BAM，不跑 DESeq2。
- sc/snRNA-seq 可将 FASTQ 转为 10x matrix；velocity 仅在用户要求时生成。
- 使用 pixi、detached tmux、原子下载和完整性审计支持长任务。
- Mode A 将 raw files 保留在 `raw/`；Mode B 仅在转换产物验证通过后删除 `temporary/` 中对应 assay 的 raw files。
- 每个 GSE 生成唯一的中文报告：`reports/report.html`（获取、转换与存储状态）。
