# 下载配额与分批转换

FASTQ 在转换前可能占满磁盘。大规模传输前询问用户本次允许的最大临时存储，不允许默认、也不写死固定值。

```text
请选择本次允许使用的最大临时存储空间：
A. 100 GB
B. 500 GB
C. 1 TB
D. 自定义
```

写入 `metadata/acquisition_config.tsv` 的 `max_temporary_bytes`（也可用 `scripts/record_storage_policy.py --max-temporary-gib <N>`）。`max_project_bytes` 仍是项目总上限。

## 规则

- 配额按用户机器实际情况设定。
- 下载下一批之前，估算待拉文件的 `expected_bytes` 之和；超过剩余配额则暂停并报告。
- Mode B 使用分批转换，使 `temporary/` 占用始终低于配额：

```text
batch 1: 下载 FASTQ → 转换 → 审计 processed → 删除该批 temporary raw
batch 2: 重复
```

- 删除入口只能是 `scripts/apply_storage_policy.py`（或按 GSM 子集调用）；转换失败时保留该批 temporary 与日志。
- Mode A 的 raw 计入项目总上限，但不因配额被删除。
