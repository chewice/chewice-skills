# download-geo-assay

按 GEO assay 分流，安全检查、下载、校验和记录公共组学原始数据（RNA-seq FASTQ/SRA、Affymetrix CEL、Illumina/甲基化 IDAT），并按用户确认的存储策略管理 raw files 生命周期。

主要特性：

- 下载前先判定 `assay_type` / `raw_file_type` / `workflow`；测序与芯片走不同获取分支，混合 assay 暂停。
- 下载前强制确认是否长期保存 raw files；不允许默认选择。
- 测序 run 优先使用有效的 NGDC 数据，必要时回退 ENA 或 NCBI。
- 芯片走 GEO supplementary（CEL/IDAT），并保存 GPL 与 probe 注释。
- 使用 pixi、detached tmux、原子下载和完整性审计支持长任务。
- 新项目使用 GSE 级 `raw/`、`temporary/`、`processed/`、`annotation/`、`qc/` 目录；每个 GSM 仍独立存放。
- Mode A 将 raw files 保留在 `raw/`；Mode B 仅在转换产物验证通过后删除 `temporary/` 中的 raw files。
- 每个 GSE 生成唯一的中文报告：`reports/report.html`。
- 完整 MultiQC 内容内嵌于单个 HTML；机器所需的 TSV、JSON、log 和 marker 继续保留。
- 测序项目自动汇总样本级 STARsolo `GeneFull_Summary.csv`，生成跨样本 TSV 并纳入统一 HTML。
- 报告中的目录和数据来源均显示相对于 GSE 根目录的路径。
