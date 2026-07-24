---
name: download-geo-sra-safely
description: 安全检查、规划、下载、续传、校验和记录 GEO/GSE/GSM、SRA/SRR/SRX/PRJNA、ENA 及 CNCB-NGDC GSA/INSDC 公共测序数据。当 Codex 需要下载或核验 GSE/SRA 数据、恢复中断传输、区分作者提交文件与数据库生成的 FASTQ/SRA/BAM、检查 R1/R2/I1/I2 或多 run/lane 结构、按 GSM 建立独立目录，或从公共原始 reads 生成 STARsolo/RNA velocity 输入时使用。有效且可用的 NGDC 镜像 run 优先于 ENA 或 NCBI；长任务使用 pixi 和 detached tmux；生成单文件中文 HTML 报告并保留可审计的机器证据。
---

# 安全下载 GEO/SRA

## 执行约定

将元数据发现、传输、转换和分析视为相互独立的关卡。accession 集合和最终数据产品未明确前，不得开始大规模传输。默认最终产品为可直接分析的 FASTQ。除非用户明确要求，否则不要下载 GEO logcounts 或标准化表达矩阵。

使用 pixi 管理环境，并在 `pixi.lock` 中锁定解析后的工具版本。长时间下载和处理必须在 detached tmux 会话中运行。默认每 1800 秒监测一次，并按 sample/run、阶段、错误、字节数和剩余空间报告进度。

每个 GSE 只生成一份面向用户的报告：`reports/report.html`。将 TSV、JSON、log 和 status marker 作为机器证据保留，不把它们视为额外的人类报告。报告标题、摘要、状态和解释使用简体中文；accession、chemistry、provenance、read structure 等专业术语可保留英文。

在报告和目录说明中使用相对于 GSE 根目录的路径，例如 `metadata/sample_metadata.tsv`、`GSM*/fastq/`、`reports/logs/`。不得写入项目绝对路径。每个报告章节都要列出其机器数据来源的相对路径。

使用内置命令前先设置 helper 路径：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/download-geo-sra-safely"
```

使用 `scripts/scaffold_project.py` 创建数据集目录结构。创建元数据表之前，先阅读 `references/manifest-schema.md`。

## 1. 介绍并解析数据集

下载前：

1. 根据 GEO、SRA 和 ENA 官方元数据解析 GSE -> GSM -> SRX -> SRR 与 BioProject 的关系。
2. 说明研究标题、目的、物种、组织/疾病、设计、分组、assay、平台、文库策略和 chemistry（如可获得）。
3. 统计预期 GSM 和 SRR 数量，识别拆分为多个 run 或 lane 的 GSM。
4. 检查作者提交文件名和数据库生成文件名中的 R1/R2/I1/I2 与技术 read 结构。必须结合 read 长度和实验元数据，不能只依据文件名。
5. 判断下游工作真正需要 FASTQ、BAM、SRA 还是作者原始提交字节。STARsolo、重新比对和 RNA velocity 通常需要 FASTQ。
6. 将研究介绍保存到 `metadata/study_metadata.tsv`，标准化 sample 元数据保存到 `metadata/sample_metadata.tsv`，多值 characteristics 保存到 `metadata/sample_characteristics.tsv`，完整预期 run 集合保存到 `metadata/expected_runs.tsv`；再刷新 `reports/report.html`。

当 GEO、ENA 和 SRA 对预期 run 集合的记录不一致时，不得静默继续。将差异写入预检报告并暂停，直至解决。

## 2. 判定 provenance 并优先使用 NGDC

选择文件前阅读 `references/provenance-routing.md`。

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

每个 GSM 使用独立目录，每个 run/lane 保持文件分离。下载阶段不要合并 run。

对 source manifest 的每一行运行 `scripts/download_run.sh <project-root> <SRR>`。在 detached tmux 中启动 sample 循环。下载器必须：

- 仅写入 `.part` 和 aria2 控制状态；
- 发布方提供预期字节数时必须核对；
- ENA 文件必须核对提供方 MD5；
- FASTQ 运行 `gzip -t`，SRA 运行 `vdb-validate`；
- 仅在校验通过后原子改名；
- 最终产品为 FASTQ 时对 SRA 运行 `fasterq-dump --split-files`；
- 原子压缩转换后的 FASTQ；
- 已知 CB/UMI geometry 时校验配对记录数、expected spots 和 barcode read 最短长度；
- 向 `GSM*/download_manifest.tsv` 追加可审计记录；
- 仅当存在有效 aria2 piece map 时保留失败的 partial。

校验已有 FASTQ 时直接使用 `scripts/validate_fastq_pair.py`。不得将“HTTP 请求成功”或“大小一致”视为充分证据。

## 4. 生成统一 HTML 报告

运行：

```bash
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" \
  --root <GSE-dir>
```

默认输出为 `<GSE-dir>/reports/report.html`。报告必须整合 study/sample metadata、预检、NGDC coverage、source routing、provenance、下载与转换完整性、FastQC/MultiQC、STARsolo/velocity、工具版本和清理状态。

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

对可重复出现的网络或完整性错误最多安全恢复三次。第三次发生相同错误后停止并报告。不得热修改正在被 sample 进程读取的 shell 脚本；先停止任务、校验语法，再重新启动。统一 CRLF 换行，并校验 TSV 数值字段，避免格式问题伪装成 read count 错误。

## 6. 可选 STARsolo 与 velocity 分支

仅当用户要求矩阵、重新比对或 RNA velocity 时进入此分支。阅读 `references/starsolo-read-geometry.md`。

- 明确记录参考物种和版本。
- 使用同一个锁定 STAR 版本建立并运行 STAR index。
- 保留原实验的 chemistry、CB/UMI geometry 和 whitelist；不得把所有数据集统一“升级”为一种 chemistry。
- 指定 STARsolo 输入顺序前，核实 barcode/cDNA 的实际角色。
- 按 GSM 分组已校验的 run，同时保留 run provenance。
- velocity 分析中，将 `Gene`、`GeneFull` 和 `Velocyto` 作为独立 STAR 参数传入，并校验 raw/filtered 10x 矩阵以及 spliced、unspliced、ambiguous 和 loom 输出。
- 每个 sample 保留 STARsolo `GeneFull_Summary.csv`。全部 sample 完成后运行 `scripts/summarize_starsolo.py --root <GSE-dir>`，生成一行一个 GSM 的 `reports/starsolo_summary.tsv`。
- 汇总至少展示 Estimated Number of Cells、valid barcode、sequencing saturation、genome/GeneFull mapping、fraction reads in cells、reads/UMI/gene per cell。明确区分 `EmptyDrops_CR` 实际回收细胞数和 `nExpectedCells` 算法先验。
- 重新运行 `scripts/build_report.py`，在统一 HTML 中展示分数据集统计、跨样本分布和逐 GSM 指标；不得用 MultiQC 的 STAR alignment 表替代 STARsolo Summary。

清理前运行 `scripts/audit_final_outputs.py --root <GSE-dir>`。

## 7. 清理与交付

先运行 `scripts/audit_download_evidence.py --root <GSE-dir>`。

- 最终产品为 FASTQ：保留 FASTQ，删除 SRA、`.part`、`.aria2` 和 work。
- 最终产品为 SRA：保留通过校验的 SRA。
- 最终产品为 matrix/velocity：仅当 download-evidence 和 final-output 审计均通过后，才删除 SRA、FASTQ 和 work。
- 不得清理未完成或未经审计的 sample。
- 清理后再次生成 `reports/report.html`，并确认其中不存在项目绝对路径。

报告：

- 预期与实际 GSM、SRR 数量；
- NGDC available/missing/invalid 和 fallback 数量；
- 作者提交产品与数据库生成产品的分类；
- 多 run/lane 与 read role 检查结果；
- 保留产品路径、总大小、完整性状态及已执行的清理。
