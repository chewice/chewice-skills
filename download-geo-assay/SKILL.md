---
name: download-geo-assay
description: 按 GEO assay 分流后检查、规划、下载、续传、校验和记录公共组学原始数据（bulk/sc/snRNA-seq FASTQ、ATAC/ChIP FASTQ/SRA、Affymetrix CEL、Illumina/甲基化 IDAT），并按 assay 分别确认是否长期保存 raw files。当用户要求下载或核验 GSE/GSM/GPL、SRA/SRR、ENA、CNCB-NGDC、判定 assay workflow、按 assay 保存原始文件、设置下载配额、恢复中断传输、区分作者提交与数据库生成产物、按 GSM 建立 raw/temporary/processed 目录，或把 FASTQ 转成 count matrix / 10x matrix / 可选 velocity 输入时使用。测序 run 优先使用有效 NGDC 镜像；芯片走 GEO supplementary；长任务使用 pixi 和 detached tmux；每个 GSE 只生成一份中文 HTML 获取/转换/存储报告。不要用本技能下载 GEO series matrix、logcounts，或做 DESeq2、GO/KEGG、Seurat/Scanpy 分析。
---

# 安全下载 GEO assay 原始数据

定位：GEO 数据发现 + assay 识别 + raw/processed 管理 + assay-specific 转换 + 标准化储存入口。不扩展为完整下游分析 pipeline。

统一数据模型：Study → Donor → Sample (GSM) → raw assay file。先读 `assay_capability.yaml`，只生成该 modality 声明的产物。使用 pixi，长时间任务在 detached tmux 中运行。

每个 GSE 只生成 `reports/report.html`，职责是数据获取、转换和存储状态。不要把 FastQC/MultiQC、STARsolo 分析指标或 DEG 写进该报告。路径一律相对 GSE 根目录。

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/download-geo-assay"
```

若当前仓库就是本 Skill，则 `SKILL_DIR` 为本目录。表结构阅读 `references/manifest-schema.md`。

## 关卡顺序

不要跳步。混合 assay 不要整包暂停，也不要用一个全局 `retain_raw_files`。

1. `scaffold_project.py`（分流前 `final-product` 可为 `pending`）。
2. 发现官方元数据并填表（`references/metadata-discovery.md`）。
3. `detect_assay.py`，再读 `assay_capability.yaml`（`references/assay-routing.md`）。
4. **按 assay** 询问是否长期保存 raw files，写入 `storage_policy.tsv` 多行（`references/storage-policy.md`）。
5. 询问本次最大临时存储（`references/download-quota.md`）。
6. 按每个 GSM 的 `workflow` 进入 3a 或 3b。不得把芯片 GSM 丢进 `download_run.sh`。
7. 按 modality 转换（`references/conversion.md`）。
8. 统一报告 → `audit_processed_outputs.py` → 按存储策略清理。

| workflow | 进入 | 不要做 |
|---|---|---|
| `sra` | `references/provenance-routing.md` 与 `references/sra-download.md` | 不要用 GEO supplementary 当测序原始 reads |
| `affymetrix` / `illumina` / `methylation` | `references/array-download.md` | 不要跑 `probe_ngdc.py`、`download_run.sh`、STAR/STARsolo |

## 1. 脚手架与数据集解析

```bash
pixi run --locked python "$SKILL_DIR/scripts/scaffold_project.py" \
  --gse <GSE> --retain-raw-files true|false --final-product <product>
```

脚手架里的 retain 只是占位，检测 assay 后必须按 assay 重问并 upsert。Mode A 常用 `fastq` / `sra` / `CEL` / `IDAT`。Mode B 必须已有该 modality 允许的转换产品：bulk 为 `gene_count_matrix`；sc/snRNA 为 `matrix_10x` 或 `matrix_velocity`；芯片为 `intensity` / `processed`。ATAC/ChIP/miRNA 的 Mode B 若用户未指定转换产品，暂停。

下载前解析 GSE → Donor → GSM →（测序则 SRX → SRR）。写入 `study_metadata.tsv`、`donor_metadata.tsv`、`sample_metadata.tsv`、`platform_metadata.tsv`、`sample_characteristics.tsv`；测序写 `expected_runs.tsv`，芯片写 `supplement_files.tsv`。然后：

```bash
pixi run --locked python "$SKILL_DIR/scripts/detect_assay.py" --root .
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" --root .
```

`assay_type=RNA-seq` 只在有 RNA-seq 证据时使用，并用 `modality` 区分 `bulk_rnaseq` / `scRNAseq` / `snRNAseq`。不得把 HiSeq/NovaSeq 的 GPL 猜成芯片。GEO、ENA、SRA 对预期 run 集合不一致时写入预检并暂停该测序子集。

## 2. 按 assay 记录存储策略与配额

检测到多个 assay 时逐个询问，例如：

```text
请选择是否保存以下 assay 的 raw files：
1. bulk RNA-seq    Raw format: FASTQ    Y/N
2. single-cell RNA-seq    Raw format: FASTQ    Y/N
3. microarray    Raw format: CEL    Y/N
```

```bash
pixi run --locked python "$SKILL_DIR/scripts/record_storage_policy.py" \
  --root . --gse <GSE> --assay-type <assay_type> --modality <modality> \
  --raw-file-type FASTQ|SRA|CEL|IDAT --retain-raw-files true|false \
  --max-temporary-gib 100|500|1024|<custom>
```

每个 assay 一行。Mode A 发布到 `raw/GSM*/`。Mode B 未确认转换产品前不得下载；raw 只进 `temporary/GSM*/`，删除入口只能是 `scripts/apply_storage_policy.py`。缺少 `metadata/storage_policy.tsv` 时不得运行 `download_run.sh` 或 `download_geo_supplement.py`。

大规模传输前询问最大临时存储：A. 100 GB / B. 500 GB / C. 1 TB / D. 自定义。Mode B 分批下载-转换-删除，使 `temporary/` 低于配额。

## 3a. 测序分支（`workflow=sra`）

选择文件前阅读 `references/provenance-routing.md`。探测 NGDC 文件 endpoint，不能只看 browse 页。优先级：原生 GSA → 有效 NGDC INSDC SRA → ENA 作者 FASTQ / ENA 生成 FASTQ → NCBI SRA Toolkit。

下载、续传、校验阅读 `references/sra-download.md`。对 manifest 中测序行在 detached tmux 中运行 `scripts/download_run.sh <project-root> <SRR>`。监测与恢复阅读 `references/recovery-playbook.md`。

转换阅读 `references/conversion.md`。bulk：STAR GeneCounts → `processed/gene_count_matrix.tsv`，默认不保存 BAM。sc/snRNA：STARsolo → `processed/GSM*/matrix_10x/`；velocity 仅用户要求时生成。ATAC/ChIP/miRNA 不要默认 STAR/STARsolo。参考基因组与 GTF 由用户提供，不在下载关卡构建人类基因组 index。转换后运行：

```bash
pixi run --locked python "$SKILL_DIR/scripts/audit_processed_outputs.py" --root <GSE-dir>
```

## 3b. 芯片 / 甲基化分支

阅读 `references/array-download.md`。本 Skill 只下载并管理 CEL/IDAT，不做 normalization。将清单写入 `metadata/supplement_files.tsv` 后运行 `download_geo_supplement.py --file-type CEL|IDAT`。GEO/厂商 probe 映射可保存到 `annotation/platform_annotation/`。

## 4. 统一 HTML 报告

```bash
pixi run --locked python "$SKILL_DIR/scripts/build_report.py" --root <GSE-dir>
```

报告只保留：数据集、assay/modality、样本、文件与校验、存储策略、转换状态、清理状态。不要内嵌 FastQC/MultiQC 或 STARsolo 分析汇总。

## 5. 清理与交付

先运行 `audit_download_evidence.py`。若发生转换，再运行 `audit_processed_outputs.py`。然后 `audit_storage_policy.py`。

- Mode A（按 assay）：保留对应 `raw/` 文件；可删除 `.part`、`.aria2` 和 `temporary/*/work`。
- Mode B（按 assay）：该 assay 审计通过后才 `apply_storage_policy.py`。
- 不得清理未完成或未经审计的 sample。清理后再次生成 `reports/report.html`。
