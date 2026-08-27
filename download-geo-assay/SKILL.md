---
name: download-geo-assay
description: 按 GEO assay 和来源对象分流，规划、下载、续传、校验并转换公共组学原始数据；在逐 GSM/文库的标准产物与 provenance 审计通过后，按预先确认的存储策略释放对应 raw。用于 GSE/GSM/GPL、SRA/SRR、ENA、CNCB-NGDC、FASTQ/SRA、CEL、IDAT、配额恢复和有限存储下的滚动转换。不要用来下载 GEO series matrix/logcounts，或执行 DESeq2、RMA、GO/KEGG、Seurat/Scanpy、ATAC/ChIP 下游分析。
---

# Download GEO Assay

固定主线：

```text
下载来源对象并校验
→ 转换为分析输入/标准产物
→ 审计产物与 provenance
→ 按已授权策略删除对应 raw
```

SRR 是下载单元；GSM 或建库文库是转换、审计和释放 raw 的原子单元。没有标准产物、成员 run 不完整、产物审计失败或删除未获前置授权时，均不得删除 raw。

## 渐进路由

始终先读：

- [references/gates.md](references/gates.md)：不变量、停止条件与人机决策边界。
- [references/manifest-schema.md](references/manifest-schema.md)：状态文件和证据合同。

根据已判定的 assay 只读一个匹配的 assay reference：

| Assay | Reference |
|---|---|
| bulk RNA-seq | [references/assays/bulk-rnaseq.md](references/assays/bulk-rnaseq.md) |
| sc/snRNA-seq | [references/assays/scrna.md](references/assays/scrna.md)，需要时再读 `starsolo-read-geometry.md` |
| Affymetrix/Illumina expression array、methylation array | [references/assays/array.md](references/assays/array.md) |
| ATAC-seq、ChIP-seq、miRNA-seq 等 raw-only | [references/assays/raw-only-seq.md](references/assays/raw-only-seq.md) |

再根据实际来源只读一个匹配的 source reference：

| 来源 | Reference |
|---|---|
| NGDC/GSA 或 INSDC 镜像 | [references/sources/ngdc.md](references/sources/ngdc.md) |
| ENA submitted/generated FASTQ | [references/sources/ena.md](references/sources/ena.md) |
| NCBI SRA、source bucket、ODP、Lite | [references/sources/ncbi-sra.md](references/sources/ncbi-sra.md) |
| GEO supplementary、GPL、SOFT/MINiML | [references/sources/geo-supplement.md](references/sources/geo-supplement.md) |

不要为了“完整阅读”同时加载全部 assay/source reference。路由和校验必须实际读取 `assay_capability.yaml` 与 `source_capability.yaml`，不能仅把它们当文档。

## 执行顺序

1. 用 `scripts/scaffold_project.py` 新建项目。assay、最终产物和 raw 去留均可先为 `pending`；不要替用户提前承诺删除。
2. 获取最小必要元数据并运行 `detect_assay.py`。自动探测参考文件、endpoint、工具能力、read length、quota 和文件系统可用空间。
3. 只询问无法可靠推导的选择：最终产物、raw 去留、可用预算、明确来源偏好、是否接受 SRA Lite、是否授权自动恢复。用 `record_storage_policy.py` 写入确认。
4. 探测来源并运行 `select_sources.py`。先按保真度与下游需求选对象类别，再选传输 endpoint。用户明确指定来源时必须服从；NGDC 只是在 `auto` 模式下的有效镜像偏好。
5. 先以一个 GSM/文库做 pilot，并运行 `audit_manifest.py` 做峰值预算。预算取项目上限、working/temporary 上限、用户 quota 和文件系统可用空间中的最严约束。
6. 下载并校验该单元全部 runs，转换为该 assay 的标准产物；用带 `--gsm`/`--unit` 的 `audit_processed_outputs.py` 审计结构、样本覆盖、输入映射和 provenance。
7. 仅当存储策略已确认且 release 证据原子写入后，才用 `apply_storage_policy.py --gsm ... --confirm-delete` 删除该单元 raw。随后处理下一个单元。
8. 每个 GSE 只生成一份中文 `reports/report.html`，同时保留 TSV/JSON 审计证据。

长任务使用项目 Pixi 环境与 detached tmux。先验证 pilot，再扩大并发或进入滚动下载—转换—释放。

## 强制边界

- provenance 与 transport 分开记录。Phred 分布只能提示质量是否简化，不能证明文件来自作者提交。
- SRA Lite 是 `SIMPLIFIED` quality class，必须显式 opt-in；不得伪装为 full-quality archive。
- raw-only assay，或 CEL/IDAT 尚未指定可审计转换产物时，不具备 raw 删除资格。
- STAR 一次保留全部 GeneCounts 列；未知链特异性保持 `unknown/pending`，不得自动定为 unstranded。
- 代理是可选 transport 配置。凭据不得写入 TSV、HTML 或明文日志。
- watchdog 默认只记录快照，不自动重启。自动恢复需要显式授权、持久预算并且能证明产生新进展。
- 不热改活动脚本。此 Skill 的新行为只用于新建项目；现有项目已复制的脚本与活动队列不自动迁移。

本 Skill 到“可审计的标准分析输入”为止，不扩展到统计分析或生物学解释。
