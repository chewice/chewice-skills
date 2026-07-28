# Data Lineage

只登记 formal external source、可复用 checkpoint、archive snapshot、pipeline
release、result、report 和进入 evidence 链的 artifact；不要登记每个 temporary
file。保留原始 source name，并区分 tracked metadata 与大型或可重建数据。

## Artifact record template

```markdown
## <artifact ID or path>

- role: external_source | checkpoint | archive_snapshot | pipeline_release | result | report
- produced_by:
- inputs:
- environment_manifest:
- environment_lock:
- validation:
- status:
- evidence_ids:
- limitations:
```

External source 还应记录 source URL、retrieved filename 和可用时的 checksum。
Checkpoint 只有在 downstream workflow 会复用或重算成本较高时才视为 formal
artifact。
