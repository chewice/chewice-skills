# 芯片 / 甲基化获取

仅 `workflow=affymetrix|illumina|methylation` 时阅读。不要运行 `probe_ngdc.py`、`download_run.sh` 或 STARsolo。

## `supplement_files.tsv`

每个待下载文件一行：

```text
gse
gsm
filename
url
file_type
expected_bytes
expected_md5
```

`file_type` 为 `CEL` 或 `IDAT`，必须与 `storage_policy.raw_file_type` 一致。`expected_bytes` / `expected_md5` 有值时，`download_geo_supplement.py` 必须核对。

清单来源见 `references/metadata-discovery.md`。不要把 series matrix、non-normalized txt、RData 写进此表。

## 下载

```bash
pixi run --locked python "$SKILL_DIR/scripts/download_geo_supplement.py" \
  --root . --file-type CEL|IDAT
```

未给 `--file-type` 时，脚本从 `storage_policy.raw_file_type` 或表内唯一 `file_type` 推断。不得把 IDAT 数据集默认成 CEL。

- Mode A：`raw/GSM*/CEL/` 或 `raw/GSM*/IDAT/`
- Mode B：`temporary/GSM*/CEL/` 或 `temporary/GSM*/IDAT/`
- Affymetrix：`GSM*.CEL` 或 `GSM*.CEL.gz`
- 若 supplementary 是 zip/tar，下载后只解出 `*.CEL`、`*.CEL.gz`、`*.idat`、`*.idat.gz`；归档本身留在同一 GSM 目录作为证据。不要解出表达矩阵。

同时保存 `annotation/platform_annotation/probe_to_gene_mapping.tsv`。注释版本必须来自 GEO platform 或厂商文件。

## Mode B

芯片 Mode B 的 `final_product` 只能是 `intensity` 或 `processed`。不要发明 RMA/Seurat/Scanpy 流程。用户未指定转换工具、版本和输出路径前，不得下载，更不得删除 temporary raw files。转换后把工具、版本、输入、输出写入 `reports/conversion_provenance.tsv`，再走 `audit_storage_policy.py` 与 `apply_storage_policy.py`。
