# 测序 run 的原子下载与校验

仅 `workflow=sra` 时阅读。芯片 / 甲基化走 `scripts/download_geo_supplement.py`，不要套用本节。中断恢复细节见 `references/recovery-playbook.md`。

## 布局

每个 GSM 使用 `raw/`、`temporary/` 或 `processed/` 下的独立子目录。每个 run/lane 保持文件分离。下载阶段不要合并 run。

对 `metadata/source_manifest.tsv` 的每一行运行：

```bash
scripts/download_run.sh <project-root> <SRR>
```

在 detached tmux 中启动 sample 循环。

## 下载器必须

- 读取 `metadata/storage_policy.tsv` 决定发布目录；
- 使用 run 级锁；所有未提交文件仅写入 `temporary/GSM*/work/<run>/staging/`；
- 仅当 `.part`、aria2 piece map、resume metadata 和当前 source fingerprint 一致时续传；
- 发布方提供预期字节数时必须核对；
- ENA 文件必须核对提供方 MD5；
- FASTQ 运行 `gzip -t`，SRA 运行 `vdb-validate`；
- 在 R1/R2/I1/I2 整组校验通过后使用发布 journal 提交；
- Mode A 发布到 `raw/GSM*/fastq/` 或 `raw/GSM*/sra/`；Mode B 发布到 `temporary/GSM*/fastq/`，不得写入 `raw/`；
- 最终产品为 FASTQ 时对 SRA 运行 `fasterq-dump --split-files`；
- 在 staging 中原子压缩和校验转换后的 FASTQ；
- 已知 CB/UMI geometry 时校验配对记录数、expected spots 和 barcode read 最短长度；
- 向 `metadata/download_manifests/<GSM>.tsv` 追加可审计记录；
- 将累计 attempt/resume、逐文件 checksum 和 integrity method 写入机器证据；
- 仅保留具有有效 piece map 和匹配 resume metadata 的 partial。

校验已有 FASTQ 时直接使用 `scripts/validate_fastq_pair.py`。不得将「HTTP 请求成功」或「大小一致」视为充分证据。

## 监测

在独立 detached tmux 会话中运行 `scripts/watchdog.sh <project-root> [interval-seconds]`。

对可重复出现的网络或完整性错误最多安全恢复三次，预算持久化到 `reports/status/<run>.transfer.json`。`terminal_failed` 出现后 watchdog 必须停止；不得通过重启 tmux 清零预算。不得热修改活动脚本；先停止任务、校验语法，再重新启动。统一 CRLF 换行，并校验 TSV 数值字段，避免格式问题伪装成 read count 错误。
