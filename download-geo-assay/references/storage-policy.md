# 存储策略与 raw release

`storage_policy.tsv` 按 assay/modality 记录最终产物、raw 去留、来源偏好、Lite 授权和确认时间。scaffold 可没有该文件；在下载前必须用 `record_storage_policy.py` 写入真实选择。

Mode B 采用逐 GSM/文库 release：全部成员 runs 下载通过 → 标准产物转换 → processed/provenance 审计 → 原子写入 `reports/storage_release.tsv` 的精确候选与校验和 → 只删除当前单元。调用：

```bash
python scripts/audit_processed_outputs.py --root . --gsm GSM...
python scripts/apply_storage_policy.py --root . --gsm GSM... --confirm-delete
```

任一门失败均保留 raw。raw-only assay，以及未指定可审计转换产品的 CEL/IDAT，不具备删除资格。完整不变量见 `gates.md`。
