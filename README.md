# download-geo-sra-safely

用于安全检查、下载、校验和记录 GEO、SRA、ENA 与 CNCB-NGDC 公共测序数据的 Codex skill。

主要特性：

- 按 run 优先使用有效的 NGDC 数据，必要时回退 ENA 或 NCBI。
- 使用 pixi、detached tmux、原子下载和完整性审计支持长任务。
- 每个 GSM 使用独立目录，并保留多 run/lane 与 provenance。
- 每个 GSE 生成唯一的中文报告：`reports/report.html`。
- 完整 MultiQC 内容内嵌于单个 HTML；机器所需的 TSV、JSON、log 和 marker 继续保留。
- 自动汇总样本级 STARsolo `GeneFull_Summary.csv`，生成跨样本 TSV 并纳入统一 HTML。
- 报告中的目录和数据来源均显示相对于 GSE 根目录的路径。
