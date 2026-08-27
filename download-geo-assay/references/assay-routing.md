# Assay 分流（兼容入口）

`detect_assay.py` 按 GSM 识别 modality，并实际读取 `assay_capability.yaml` 写出 `workflow` 与 `capability_reference`。混合 GSE 保留逐 GSM 分流；后续只加载当前 GSM 对应的 assay reference 和实际 source reference。

Mode B 把 raw 写入 `temporary/GSM*/`；Mode A 写入 `raw/GSM*/`。raw-only capability 不允许 Mode B。不得把 CEL/IDAT 送入 `download_run.sh`，也不得把 ATAC/ChIP/miRNA 套用 RNA 标准产物。
