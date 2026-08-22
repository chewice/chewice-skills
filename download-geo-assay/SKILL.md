---
name: download-geo-assay
description: 按 GEO assay 分流后检查、规划、下载、续传、校验和记录公共组学原始数据（RNA-seq/ATAC-seq/ChIP-seq FASTQ/SRA、Affymetrix CEL、Illumina/甲基化 IDAT），并按用户确认的存储策略管理 raw files 生命周期。当用户要求下载或核验 GSE/GSM/GPL、SRA/SRR、ENA、CNCB-NGDC、判定 assay workflow、确认是否长期保存原始文件、恢复中断传输、区分作者提交与数据库生成产物、按 GSM 建立 raw/temporary/processed 目录，或从 10x 测序 reads 生成 STARsolo/RNA velocity 输入时使用。测序 run 优先使用有效 NGDC 镜像；芯片走 GEO supplementary；长任务使用 pixi 和 detached tmux；每个 GSE 只生成一份中文 HTML 报告。不要用本技能下载 GEO series matrix、logcounts，或对已有矩阵做 Seurat/Scanpy 分析。
---

# 安全下载 GEO assay 原始数据

将元数据发现、assay 分流、存储策略确认、传输、转换和分析视为相互独立的关卡。accession 集合、assay workflow、存储策略和最终数据产品未明确前，不得开始大规模传输。

统一数据模型：Study → Donor → Sample (GSM) → raw assay file。测序默认最终产品为可直接分析的 FASTQ。除非用户明确要求，否则不要下载 GEO logcounts 或标准化表达矩阵，也不要引入 Seurat object、Scanpy object、RData 或 Python pickle。

使用 pixi，并在项目 `pixi.lock` 中锁定工具版本。长时间下载和处理必须在 detached tmux 中运行，默认每 1800 秒监测一次。

每个 GSE 只生成一份面向用户的报告：`reports/report.html`。TSV/JSON/log/status marker 是机器证据，不是额外人类报告。报告使用简体中文；accession、chemistry、provenance、read structure 可保留英文。路径一律相对 GSE 根目录，不得写入项目绝对路径。每个报告章节列出其机器数据来源的相对路径。

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/download-geo-assay"
```

若当前仓库就是本 Skill，则 `SKILL_DIR` 为本目录。表结构阅读 `references/manifest-schema.md`。

## 关卡顺序

不要跳步，也不要在分流前把芯片项目的 `final_product` 写成 `fastq`。

1. 询问是否长期保存 raw files（A/B，与 assay 无关）。不允许默认。
2. `scaffold_project.py --retain-raw-files true|false`。分流前 `final-product` 可为 `pending`；Mode B 必须先有该 assay 允许的转换产品。
3. 发现官方元数据并填表（阅读 `references/metadata-discovery.md`）。
4. `detect_assay.py`（阅读 `references/assay-routing.md`）。混合 workflow 暂停。
5. `record_storage_policy.py` 补齐 `assay_type` 与 `raw_file_type`。
6. 按单一 `workflow` 进入 3a 或 3b。
7. 统一报告 → 审计 → 按存储策略清理。

| workflow | 进入 | 不要做 |
|---|---|---|
| `sra` | `references/provenance-routing.md` 与 `references/sra-download.md` | 不要用 GEO supplementary 当测序原始 reads；不要对 ATAC/ChIP/bulk/miRNA 默认 STARsolo |
| `affymetrix` / `illumina` / `methylation` | `references/array-download.md` | 不要跑 `probe_ngdc.py`、`download_run.sh`、STARsolo |

## 1. 脚手架与数据集解析

```bash
pixi run --locked python "$SKILL_DIR/scripts/scaffold_project.py" \
  --gse <GSE> --retain-raw-files true|false --final-product <product>
```

`--retain-raw-files` 必填。Mode A 测序常用 `fastq` / `sra`；芯片为 `CEL` / `IDAT`。Mode B 仅在转换产品已明确时使用：10x/droplet RNA 为 `matrix_velocity`；芯片为 `intensity` / `processed`。ATAC-seq、ChIP-seq、miRNA-seq、bulk RNA-seq 的 Mode B 若用户未指定转换产品，暂停。

下载前：

1. 按 `references/metadata-discovery.md` 解析 GSE → Donor → GSM →（测序则 SRX → SRR / BioProject）。
2. 说明研究标题、目的、物种、组织/疾病、设计、分组、assay、GPL、文库策略和 chemistry（如可获得）。
3. 写入 `study_metadata.tsv`、`donor_metadata.tsv`、`sample_metadata.tsv`、`platform_metadata.tsv`、`sample_characteristics.tsv`；测序写 `expected_runs.tsv`，芯片写 `supplement_files.tsv`。
4. 运行分流并刷新报告：

```bash
pixi run --locked python "$SKILL_DIR/scripts/detect_assay.py" --root .
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" --root .
```

`assay_type=RNA-seq` 只在有 RNA-seq/transcriptome 证据时使用。ATAC-seq、ChIP-seq、miRNA-seq 或仅有测序平台证据时分别写对应类型或 `sequencing`，`workflow` 仍为 `sra`。不得把 HiSeq/NovaSeq 的 GPL 猜成芯片。GEO、ENA、SRA 对预期 run 集合不一致时写入预检并暂停。

## 2. 记录存储策略

大规模传输前必须已有用户选择：

> 是否需要长期保存下载后的原始 assay 文件（FASTQ/SRA/CEL/IDAT）？

- A. 保存 raw files（`retain_raw_files=true`）
- B. 不保存 raw files，仅保留转换后的分析结果（`retain_raw_files=false`）

```bash
pixi run --locked python "$SKILL_DIR/scripts/record_storage_policy.py" \
  --root . --gse <GSE> --retain-raw-files true|false \
  --assay-type <assay_type> --raw-file-type FASTQ|SRA|CEL|IDAT
```

Mode A 发布到 `raw/GSM*/`。Mode B 未确认转换产品前不得下载；raw files 只进 `temporary/GSM*/`，删除入口只能是 `scripts/apply_storage_policy.py`。缺少 `metadata/storage_policy.tsv` 时不得运行 `download_run.sh` 或 `download_geo_supplement.py`。细节见 `references/storage-policy.md`。

## 3a. 测序分支（`workflow=sra`）

选择文件前阅读 `references/provenance-routing.md`。探测 NGDC 文件 endpoint，不能只看 browse 页：

```bash
pixi run --locked python "$SKILL_DIR/scripts/probe_ngdc.py" \
  --input metadata/expected_runs.tsv --output reports/ngdc_coverage.tsv
pixi run --locked python "$SKILL_DIR/scripts/select_sources.py" \
  --expected metadata/expected_runs.tsv \
  --ngdc reports/ngdc_coverage.tsv \
  --ena metadata/ena_runs.tsv \
  --output metadata/source_manifest.tsv
pixi run --locked python "$SKILL_DIR/scripts/audit_manifest.py" \
  --root . --manifest metadata/source_manifest.tsv
```

优先级：原生 GSA → 有效 NGDC INSDC SRA → ENA 作者 FASTQ / ENA 生成 FASTQ → NCBI SRA Toolkit。不能因更快而替换可用且有效的 NGDC run。始终回答：这些是作者上传的原始字节，还是数据库转换后的版本？NGDC INSDC `.sra` = `NGDC_MIRROR_SRA`；`fasterq-dump` 输出 = `ARCHIVE_GENERATED_FASTQ`。

下载、续传、校验阅读 `references/sra-download.md`。对 manifest 每一行在 detached tmux 中运行 `scripts/download_run.sh <project-root> <SRR>`。监测与恢复阅读 `references/recovery-playbook.md`，并用 `scripts/watchdog.sh <project-root> [interval-seconds]`。

STARsolo / RNA velocity **仅当** 用户要求矩阵、重新比对或 velocity，或测序 Mode B，**并且** 有 10x/droplet scRNA 证据。阅读 `references/starsolo-read-geometry.md`。ATAC-seq、ChIP-seq、miRNA-seq、bulk RNA-seq 不要默认 STARsolo。Mode A 从 `raw/GSM*/fastq/` 读，Mode B 从 `temporary/GSM*/fastq/` 读；输出到 `processed/GSM*/matrix_10x/` 与 `processed/GSM*/velocity/`。全部 sample 完成后运行 `scripts/summarize_starsolo.py --root <GSE-dir>`，再刷新 HTML。清理前运行 `scripts/audit_final_outputs.py --root <GSE-dir>`。

## 3b. 芯片 / 甲基化分支（`workflow=affymetrix|illumina|methylation`）

阅读 `references/array-download.md`。记录 GPL、array type、probe annotation version。将 CEL/IDAT 清单写入 `metadata/supplement_files.tsv` 后：

```bash
pixi run --locked python "$SKILL_DIR/scripts/download_geo_supplement.py" \
  --root . --file-type CEL|IDAT
```

`--file-type` 必须与 `raw_file_type` 一致。Mode A 发布到 `raw/GSM*/CEL/` 或 `raw/GSM*/IDAT/`；Mode B 为 `temporary/GSM*/`。同时保存 `annotation/platform_annotation/probe_to_gene_mapping.tsv`。

## 4. 统一 HTML 报告

```bash
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" --root <GSE-dir>
```

报告整合 study/sample/platform metadata、assay 分流、存储策略、预检、（测序）NGDC/source/provenance、下载完整性、（如有）FastQC/MultiQC 与 STARsolo、工具版本和清理状态。项目内临时 MultiQC HTML 仅在统一报告原子写入成功后由 `--consume-multiqc` 删除；保留 JSON/TSV。不得自动删除旧 Markdown/TSV 报告。

## 5. 清理与交付

先运行 `scripts/audit_download_evidence.py --root <GSE-dir>`。若发生转换，再运行 `scripts/audit_final_outputs.py`。然后运行 `scripts/audit_storage_policy.py --root <GSE-dir>`。

- Mode A：保留 `raw/` 中的 FASTQ、SRA、CEL 或 IDAT；可删除 `.part`、`.aria2` 和 `temporary/*/work`。不得调用删除 raw files 的脚本。
- Mode B：三项审计均通过后，才运行 `scripts/apply_storage_policy.py --root <GSE-dir>`。
- 不得清理未完成或未经审计的 sample。清理后再次生成 `reports/report.html`，并确认其中没有项目绝对路径。

报告中写明：预期与实际 GSM/SRR（测序）或 CEL/IDAT 数量、assay_type / raw_file_type / workflow、存储策略与 deletion 状态、（测序）NGDC/fallback 与 provenance 分类、多 run/lane 与 read role、保留产品路径、总大小、完整性与已执行的清理。
