# 元数据发现

在 `detect_assay.py` 和大规模传输之前阅读。目标是填官方元数据表，不是下载表达矩阵。

## 允许的来源

- GEO series/sample/platform SOFT 或 MINiML
- GEO supplementary **文件清单**（只记 CEL/IDAT/FASTQ/SRA 等 raw assay 文件）
- ENA `filereport`（`result=read_run`）
- SRA RunInfo / BioProject 关系
- NGDC GSA browse 仅用于后续测序路由，不能代替 GEO/ENA 的 expected run 集合

## 禁止当原始 assay 下载

- `GSE*_series_matrix.txt.gz`、GEO logcounts、RMA/quantile 标准化矩阵
- 作者上传的 Seurat/Scanpy/RData/pickle
- 仅含 processed expression 的 supplementary

这些最多记入 `notes`，provenance 为 `GEO_PROCESSED`，默认排除。

## 建议抓取顺序

1. 用 GSE 取 series SOFT / MINiML，解析每个 GSM 的标题、organism、characteristics、GPL、library 字段和 supplementary 文件名。
2. 测序：从 SOFT 的 SRA/BioProject 关系或 ENA filereport 展开 GSM → SRX → SRR。每个 SRR 一行写入 `metadata/expected_runs.tsv`。GEO、ENA、SRA 的 run 集合不一致时写入 `reports/preflight_audit.tsv` 并暂停。
3. 芯片 / 甲基化：不要找 SRR。把每个 GSM 的 CEL/IDAT（或仅含这些文件的 zip）写入 `metadata/supplement_files.tsv`。
4. 平台：用 `download_geo_platform.py --root . --gpl GPL... --gse GSE...` 先取最小 GPL self/full，失败后自动走官方 family fallback；再写入 `metadata/platform_metadata.tsv`（GPL、title、technology、array type、annotation version）。probe 映射来自 GEO platform SOFT 或厂商注释，不要手编。
5. 多值 characteristics 放到 `metadata/sample_characteristics.tsv`，不要压扁成会丢信息的单列。
6. 运行 `scripts/detect_assay.py --root .`，再按 SKILL.md 更新 `storage_policy.tsv`。

ENA filereport 至少保留 `references/manifest-schema.md` 中 `ena_runs.tsv` 所需字段。仅当同一 endpoint 支持 HTTPS 时，才把裸 FTP 路径改成 `https://`。

## 常用入口（按 accession 替换）

- GEO series SOFT：`https://ftp.ncbi.nlm.nih.gov/geo/series/GSE<nnn>nnn/GSE<id>/soft/`
- GEO sample supplementary：SOFT 中 `!Sample_supplementary_file_*`，或 `https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM<nnn>nnn/GSM<id>/suppl/`
- ENA filereport：`https://www.ebi.ac.uk/ena/portal/api/filereport?accession=<BioProject|SRR>&result=read_run`

具体 URL 以官方目录为准，缺文件时记录到预检，不要改下 series matrix。
