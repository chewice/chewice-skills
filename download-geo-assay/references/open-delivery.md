# 开放格式与按样本交付合同

正式产物位于 `deliverables/<sample_id>/`。`processed/<GSM>/` 是转换与审计工作目录；整个样本包验证完成后才原子改名进入正式目录。`.staging/` 中的包尚未交付。只有 `.complete`、`checksums.sha256` 与当前样本审计相符，才可交给下游。

## 格式

- sc/snRNA：`matrix/raw_feature_bc_matrix/{matrix.mtx.gz,features.tsv.gz,barcodes.tsv.gz}`。矩阵为 Matrix Market coordinate integer general，行是 features，列是 barcodes，值是未归一化非负计数。features 为 ID、名称、类型三列，barcodes 为一列，无表头。可附 filtered 三件套，须证明 barcode 子集及对应计数一致。
- velocity：附 `velocity/{spliced,unspliced,ambiguous}.mtx.gz` 与 features/barcodes 文本。三层维度及标识顺序一致，各层非零元素数可不同。loom 不作为必需文件。
- bulk：每 GSM 输出 `processed/<GSM>/counts/counts.tsv.gz`，正式包内为 `counts.tsv.gz`。第一列 `gene_id`，计数列为 `count` 或显式 `unstranded/forward/reverse`。未知方向可同时保留三列，provenance 标明 unknown，不能伪装为已确认方向。用 `export_star_counts.py --root . --gsm GSM... --strandedness unknown` 从该 GSM 的 STAR 输出导出。全局合并矩阵仅为附加产物。
- 芯片明确指定的可审计强度产物：按 GSM 的 TSV/TSV.gz，含唯一 feature/probe/CpG ID 和明确数值列。仅获取 CEL/IDAT 时保留 raw；不借转换之名执行 RMA 或下游统计。
- 每包包含 `sample.tsv`、`provenance.json`、`validation.json`、`checksums.sha256`、`.complete`。provenance 包含下载实际对象/quality class、精确输入、工具版本、参考组装及注释、计数策略、矩阵方向和缺失值约定。

R/Python 可用通用 gzip、TSV、JSON、Matrix Market 读取器导入，不要求创建 Seurat/AnnData 对象。qs、RDS、pickle、h5ad、loom 等不作为正式包的必需产物；如需作为分析缓存，在工作目录另外保存。

## 样本归属

`metadata/sample_units.tsv` 列为 `gsm,sample_id,library_id,assignment_status`。`resolved` 表示已确认归属；`library_only` 表示仅确认文库身份。未提供映射时以 GSM 作为文库单元交付并明确 `library_only`，不声称 GSM 必然等于生物学样本。pooled/ambiguous 状态不能被自动拆成虚构的样本；多个文库映射同一 sample_id 时先明确汇总/分包方案，不覆盖现有包。

## 正式转换流程

1. 全部成员原料下载验证完成后，运行 `artifact_integrity.py --root . --gsm GSM...`，记录来源合同与每个输入文件的 SHA256。
2. 执行该 GSM 的转换脚本。`conversion_provenance.tsv` 的 input_files/input_fastq 必须精确列出全部输入，包括所有 runs、mates 和适用技术 reads；不能用通配符或 SRR 子串代替。
3. 写入 provenance 的 `reference`（组装、注释及可追溯版本）和 `counting_strategy`（例如 exon/intron、UMI、链方向及 cell calling）。这些选择由实际分析决定，工具不猜测。
4. `audit_processed_outputs.py --root . --gsm GSM...` 全量读取产物，并核对转换前后输入未变，生成内容绑定的 processed receipt。`--structure-only` 只做诊断，结果是 STRUCTURE_ONLY，不能授权交付或删除。
5. `publish_sample.py --root . --gsm GSM...` 生成并校验开放格式包，再原子发布。
6. Mode B 才调用 `apply_storage_policy.py --root . --gsm GSM... --confirm-delete`。每次删除前检查当前产物、正式包、来源/样本映射和审计是否仍一致。

`run_queue.py` 已依此顺序调用。旧项目没有输入 receipt 时不能补写一个 PASS 冒充转换前证据；保留 raw，重新核实并执行转换后生成新证据。
