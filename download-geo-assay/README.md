# download-geo-assay

一个面向 GEO/SRA/ENA/NGDC 公共组学数据的 Codex Skill。它按 assay 与来源对象分流，在有限存储下以 GSM/文库为单位执行：

```text
下载并校验 → 记录输入指纹 → 转换 → 审计 → 发布开放格式样本包 → 按授权释放 raw
```

核心设计：

- 单一顶层 Router，按需加载 `references/assays/` 与 `references/sources/`。
- `assay_capability.yaml` 和 `source_capability.yaml` 是运行时能力表，由脚本读取。
- 用户明确来源优先；自动模式才使用镜像偏好。
- SRR 是下载单元，GSM/文库是转换与 raw release 单元。
- raw 删除采用“前置授权、验证后自动释放”，任何审计失败均保留 raw。
- scaffold 允许 `pending`，watchdog 默认不启动、不自动重启。
- `run_queue.py` 区分 pilot 与全集，park 失败 GSM，Mode B 逐 GSM 审计并释放；见 `references/queue-execution.md`。
- NCBI 优先复用完整 cache；获授权的 Lite 保留身份与替换依据；可选 `prefetch_ahead.py` 预取上限为 3 个 run。
- 每个 GSE 保持一份中文 `reports/report.html`。

不负责 GEO series matrix/logcounts，也不执行 DESeq2、RMA、Seurat/Scanpy、GO/KEGG 或 ATAC/ChIP 下游分析。

运行环境由 `scripts/scaffold_project.py` 在下载项目内生成 `pixi.toml`，按项目安装和锁定依赖。

正式交付合同见 [references/open-delivery.md](references/open-delivery.md)：每样本独立的 MEX/TSV、JSON、SHA256 清单，可用通用 R/Python 文件读取器导入，无需 Seurat/AnnData 对象。
