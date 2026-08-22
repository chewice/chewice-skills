---
name: download-geo-assay
description: 按 GEO assay 分流检查、规划、下载、续传、校验和记录公共组学原始数据（RNA-seq FASTQ/SRA、Affymetrix CEL、Illumina/甲基化 IDAT），并按用户确认的存储策略管理 raw files 生命周期。当 Codex 需要下载或核验 GSE/GSM/GPL、SRA/SRR、ENA 或 CNCB-NGDC 数据、判定 assay workflow、确认是否长期保存原始文件、恢复中断传输、区分作者提交与数据库生成产物、按 GSM 建立 raw/temporary/processed 目录，或从测序 reads 生成 STARsolo/RNA velocity 输入时使用。测序 run 优先使用有效 NGDC 镜像；长任务使用 pixi 和 detached tmux；生成单文件中文 HTML 报告并保留可审计的机器证据。
---

# 安全下载 GEO assay 原始数据

## 执行约定

将元数据发现、assay 分流、存储策略确认、传输、转换和分析视为相互独立的关卡。accession 集合、assay workflow、存储策略和最终数据产品未明确前，不得开始大规模传输。测序数据的默认最终产品为可直接分析的 FASTQ。除非用户明确要求，否则不要下载 GEO logcounts 或标准化表达矩阵。不要引入 Seurat object、Scanpy object、RData 或 Python pickle。

统一数据模型：Study → Donor → Sample (GSM) → raw assay file。

使用 pixi 管理环境，并在 `pixi.lock` 中锁定解析后的工具版本。长时间下载和处理必须在 detached tmux 会话中运行。默认每 1800 秒监测一次，并按 sample/run、阶段、错误、字节数和剩余空间报告进度。

每个 GSE 只生成一份面向用户的报告：`reports/report.html`。将 TSV、JSON、log 和 status marker 作为机器证据保留，不把它们视为额外的人类报告。报告标题、摘要、状态和解释使用简体中文；accession、chemistry、provenance、read structure 等专业术语可保留英文。

在报告和目录说明中使用相对于 GSE 根目录的路径，例如 `metadata/sample_metadata.tsv`、`raw/GSM*/fastq/`、`raw/GSM*/CEL/`、`temporary/GSM*/fastq/`、`processed/GSM*/matrix_10x/`、`annotation/platform_annotation/`、`qc/`、`reports/logs/`。不得写入项目绝对路径。每个报告章节都要列出其机器数据来源的相对路径。

使用内置命令前先设置 helper 路径：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/download-geo-assay"
```

使用 `scripts/scaffold_project.py` 创建数据集目录结构；`--retain-raw-files` 必填，无默认值。创建元数据表之前，先阅读 `references/manifest-schema.md`。存储策略细节阅读 `references/storage-policy.md`。assay 分流阅读 `references/assay-routing.md`。

## 1. 介绍并解析数据集

下载前：

1. 根据 GEO、SRA 和 ENA 官方元数据解析 GSE -> Donor -> GSM ->（测序则 SRX -> SRR / BioProject）的关系。
2. 说明研究标题、目的、物种、组织/疾病、设计、分组、assay、平台（GPL）、文库策略和 chemistry（如可获得）。
3. 运行 `scripts/detect_assay.py`，写入 `metadata/assay_routing.tsv`。混合 workflow 的 GSE 必须暂停。
4. 测序：统计预期 GSM 和 SRR 数量，识别拆分为多个 run 或 lane 的 GSM；检查 R1/R2/I1/I2 与技术 read 结构，必须结合 read 长度和实验元数据。
5. 芯片：记录 GPL、array type、probe annotation version；Affymetrix 原始文件为 `CEL`/`CEL.gz`，Illumina 表达与甲基化为 `IDAT`。
6. 判断下游真正需要 FASTQ、BAM、SRA、CEL、IDAT 还是作者原始提交字节。STARsolo、重新比对和 RNA velocity 通常需要 FASTQ。
7. 将研究介绍保存到 `metadata/study_metadata.tsv`，donor 保存到 `metadata/donor_metadata.tsv`，标准化 sample 元数据保存到 `metadata/sample_metadata.tsv`，平台保存到 `metadata/platform_metadata.tsv`，多值 characteristics 保存到 `metadata/sample_characteristics.tsv`；测序再写入 `metadata/expected_runs.tsv`；刷新 `reports/report.html`。

当 GEO、ENA 和 SRA 对预期 run 集合的记录不一致时，不得静默继续。将差异写入预检报告并暂停，直至解决。

```bash
pixi run --locked python "$SKILL_DIR/scripts/detect_assay.py" --root .
```

## 1b. 强制确认存储策略

大规模传输开始前必须主动询问：

> 是否需要长期保存下载后的原始 assay 文件（FASTQ/SRA/CEL/IDAT）？

选项只有：

- A. 保存 raw files（`retain_raw_files=true`）
- B. 不保存 raw files，仅保留转换后的分析结果（`retain_raw_files=false`）

不允许默认选择。记录用户选择：

```bash
pixi run --locked python "$SKILL_DIR/scripts/record_storage_policy.py" \
  --root . --gse <GSE> --retain-raw-files true|false \
  --assay-type RNA-seq|microarray|methylation \
  --raw-file-type FASTQ|CEL|IDAT
```

Mode A：raw files 发布到 `raw/GSM*/fastq/`、`raw/GSM*/sra/`、`raw/GSM*/CEL/` 或 `raw/GSM*/IDAT/`，不允许自动删除。测序 `final_product` 可以是 `fastq`、`sra` 或 `matrix_velocity`；芯片可以是 `CEL`/`IDAT` 或 `intensity`/`processed`。

Mode B：未确认转换产品前不得下载。测序必须 `final_product=matrix_velocity`；芯片必须 `intensity` 或 `processed`。raw files 只进入 `temporary/GSM*/`，转换并验证成功后由 `scripts/apply_storage_policy.py` 删除。禁止下载完成后立即删除。

缺少 `metadata/storage_policy.tsv` 时不得运行 `download_run.sh` 或 `download_geo_supplement.py`。

## 1c. 芯片补充文件

Affymetrix / Illumina / methylation 不走 SRA。将 GEO supplementary 清单写入 `metadata/supplement_files.tsv` 后：

```bash
pixi run --locked python "$SKILL_DIR/scripts/download_geo_supplement.py" \
  --root . --file-type CEL
```

Affymetrix 发布路径：`raw/GSM*/CEL/GSM*.CEL.gz`（Mode B 为 `temporary/GSM*/CEL/`）。同时保存 `annotation/platform_annotation/probe_to_gene_mapping.tsv`。

## 2. 判定 provenance 并优先使用 NGDC

仅 `workflow=sra` 进入本节。选择文件前阅读 `references/provenance-routing.md`。

逐个检查预期 run 在 `https://ngdc.cncb.ac.cn/gsa/browse/` 中对应的 GSA 或 INSDC run 记录。必须探测实际的 `download*.cncb.ac.cn` 文件 endpoint，不能只检查 browse 页面。运行：

```bash
pixi run --locked python "$SKILL_DIR/scripts/probe_ngdc.py" \
  --input metadata/expected_runs.tsv \
  --output reports/ngdc_coverage.tsv
```

按 run 应用以下优先级：

1. CRA/CRR accession优先使用 NGDC 原生 GSA 作者文件。
2. SRR accession 优先使用有效的 NGDC INSDC 镜像 SRA。
3. ENA 作者提交 FASTQ 可用时选用；否则使用 ENA 生成的 FASTQ。
4. 最后才回退到 NCBI SRA Toolkit。

不能仅因其他线路更快而替换可用且有效的 NGDC run。仅当 run 缺失、没有文件 endpoint、连续三次不可达，或未通过大小/完整性/read 数校验时回退。每个非 NGDC 选择都必须记录 fallback reason。

使用 `scripts/select_sources.py` 生成 `metadata/source_manifest.tsv`，然后进行校验：

```bash
pixi run --locked python "$SKILL_DIR/scripts/select_sources.py" \
  --expected metadata/expected_runs.tsv \
  --ngdc reports/ngdc_coverage.tsv \
  --ena metadata/ena_runs.tsv \
  --output metadata/source_manifest.tsv

pixi run --locked python "$SKILL_DIR/scripts/audit_manifest.py" \
  --root . --manifest metadata/source_manifest.tsv
```

始终回答：“这些是作者上传的原始字节，还是公共数据库转换后的版本？”只能使用 schema 中定义的 provenance 值。特别注意：NGDC INSDC `.sra` 标记为 `NGDC_MIRROR_SRA`；由 `fasterq-dump` 生成的 FASTQ 标记为 `ARCHIVE_GENERATED_FASTQ`。

## 3. 原子化下载与校验

每个 GSM 使用独立子目录，位于 `raw/`、`temporary/` 或 `processed/` 之下。每个 run/lane 保持文件分离。下载阶段不要合并 run。

对 source manifest 的每一行运行 `scripts/download_run.sh <project-root> <SRR>`。在 detached tmux 中启动 sample 循环。下载器必须：

- 读取 `metadata/storage_policy.tsv` 决定发布目录；
- 使用 run 级锁；所有未提交文件仅写入 `temporary/GSM*/work/<run>/staging/`；
- 仅当 `.part`、aria2 piece map、resume metadata 和当前 source fingerprint 一致时续传；
- 发布方提供预期字节数时必须核对；
- ENA 文件必须核对提供方 MD5；
- FASTQ 运行 `gzip -t`，SRA 运行 `vdb-validate`；
- 在 R1/R2/I1/I2 整组校验通过后使用发布 journal 提交；
- Mode A 发布到 `raw/GSM*/fastq/` 或 `raw/GSM*/sra/`；Mode B 发布到 `temporary/GSM*/fastq/`，不得写入 `raw/`；
- 最终产品为 FASTQ 时对 SRA 运行 `fasterq-dump --split-files`；
- 在 staging 中原子压缩和校验转换后的 FASTQ；
- 已知 CB/UMI geometry 时校验配对记录数、expected spots 和 barcode read 最短长度；
- 向 `metadata/download_manifests/<GSM>.tsv` 追加可审计记录；
- 将累计 attempt/resume、逐文件 checksum 和 integrity method 写入机器证据；
- 仅保留具有有效 piece map 和匹配 resume metadata 的 partial。

校验已有 FASTQ 时直接使用 `scripts/validate_fastq_pair.py`。不得将“HTTP 请求成功”或“大小一致”视为充分证据。

## 4. 生成统一 HTML 报告

运行：

```bash
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" \
  --root <GSE-dir>
```

默认输出为 `<GSE-dir>/reports/report.html`。报告必须整合 study/sample/platform metadata、assay 分流、存储策略、预检、NGDC coverage、source routing、provenance、下载与转换完整性、FastQC/MultiQC、STARsolo/velocity、工具版本和清理状态。

MultiQC 使用项目内临时 HTML 时，运行：

```bash
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" \
  --root <GSE-dir> \
  --multiqc-html <GSE-dir>/reports/multiqc_data/embedded_multiqc.html \
  --consume-multiqc
```

仅在统一报告原子写入成功后删除明确指定的临时 MultiQC HTML；保留 MultiQC 的 JSON/TSV 数据。对旧项目，可读取已有 Markdown/TSV 报告并纳入 HTML，但不得自动删除旧文件。

## 5. 监测与恢复

在独立 detached tmux 会话中运行 `scripts/watchdog.sh <project-root> [interval-seconds]`。修改失败任务前阅读 `references/recovery-playbook.md`。

对可重复出现的网络或完整性错误最多安全恢复三次，预算持久化到
`reports/status/<run>.transfer.json`。`terminal_failed` 出现后 watchdog 必须停止；
不得通过重启 tmux 清零预算。不得热修改活动脚本；先停止任务、校验语法，再重新
启动。统一 CRLF 换行，并校验 TSV 数值字段，避免格式问题伪装成 read count 错误。

## 6. 可选 STARsolo 与 velocity 分支

仅当用户要求矩阵、重新比对、RNA velocity，或测序选择 Mode B 时进入此分支。阅读 `references/starsolo-read-geometry.md`。芯片数据不走 STARsolo。

- 明确记录参考物种和版本。
- 使用同一个锁定 STAR 版本建立并运行 STAR index。
- 保留原实验的 chemistry、CB/UMI geometry 和 whitelist；不得把所有数据集统一“升级”为一种 chemistry。
- 指定 STARsolo 输入顺序前，核实 barcode/cDNA 的实际角色。
- Mode A 从 `raw/GSM*/fastq/` 读取；Mode B 从 `temporary/GSM*/fastq/` 读取。
- 按 GSM 分组已校验的 run，同时保留 run provenance。
- 输出写到 `processed/GSM*/matrix_10x/` 与 `processed/GSM*/velocity/`。
- velocity 分析中，将 `Gene`、`GeneFull` 和 `Velocyto` 作为独立 STAR 参数传入，并校验 raw/filtered 10x 矩阵以及 spliced、unspliced、ambiguous 和 loom 输出。
- 每个 sample 保留 STARsolo `GeneFull_Summary.csv`。全部 sample 完成后运行 `scripts/summarize_starsolo.py --root <GSE-dir>`，生成一行一个 GSM 的 `reports/starsolo_summary.tsv`。
- 汇总至少展示 Estimated Number of Cells、valid barcode、sequencing saturation、genome/GeneFull mapping、fraction reads in cells、reads/UMI/gene per cell。明确区分 `EmptyDrops_CR` 实际回收细胞数和 `nExpectedCells` 算法先验。
- 将工具、版本、输入 FASTQ 和输出 matrix 写入 `reports/conversion_provenance.tsv`。
- 重新运行 `scripts/build_report.py`，在统一 HTML 中展示分数据集统计、跨样本分布和逐 GSM 指标；不得用 MultiQC 的 STAR alignment 表替代 STARsolo Summary。

清理前运行 `scripts/audit_final_outputs.py --root <GSE-dir>`。

## 7. 清理与交付

先运行 `scripts/audit_download_evidence.py --root <GSE-dir>`。若发生转换，再运行 `scripts/audit_final_outputs.py`。然后运行 `scripts/audit_storage_policy.py --root <GSE-dir>`。

- Mode A：保留 `raw/` 中的 FASTQ、SRA、CEL 或 IDAT；可删除 `.part`、`.aria2` 和 `temporary/*/work`。不得调用删除 raw files 的脚本。
- Mode B：仅当 download-evidence、final-output 和 storage-policy 审计均通过后，运行 `scripts/apply_storage_policy.py --root <GSE-dir>`。该脚本是删除 raw files 的唯一入口。
- 不得清理未完成或未经审计的 sample。
- 清理后再次生成 `reports/report.html`，并确认其中不存在项目绝对路径。

报告：

- 预期与实际 GSM、SRR 数量，以及 assay_type / raw_file_type / workflow；
- 存储策略、validation_status 与 deletion_status；
- NGDC available/missing/invalid 和 fallback 数量（仅测序）；
- 作者提交产品与数据库生成产品的分类；
- 多 run/lane 与 read role 检查结果；
- 保留产品路径、总大小、完整性状态及已执行的清理。
