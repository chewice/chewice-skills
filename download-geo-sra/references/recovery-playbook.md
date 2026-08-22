# 传输中断与恢复手册

## 不变量与状态机

每个 run 依次经过 `preflight -> transfer/prefetch -> converting -> validating ->
publishing -> complete`。`reports/status/<run>.transfer.json` 是跨进程状态，
`reports/status/<run>.complete` 仅在最终 manifest 原子写入后生成。

- 下载与转换只写 `temporary/GSM*/work/<run>/staging/`。
- Mode A 最终 FASTQ/SRA 属于 `raw/GSM*/`；Mode B 转换前 FASTQ 属于 `temporary/GSM*/fastq/`。
- 最终目录中的文件必须属于已校验的发布事务。
- 同一 run 由 `flock` 串行化。
- R1、R2 和适用的 I1/I2 作为一个 run 事务校验；任一文件失败都不得发布。
- `publish.json` 记录每个 staged/final 路径、字节数和 MD5。进程在改名间退出时，
  下一次运行逐项复核后继续提交。

## 可信断点

aria2 partial 仅在以下三项同时存在且一致时续传：

1. `<file>.part`；
2. `<file>.part.aria2` piece map；
3. `<file>.part.resume.json`，其中 source fingerprint 与当前 manifest 一致。

source fingerprint 覆盖 source、URL、expected bytes、provider MD5、read role 和最终
产品。可获得时还比较 ETag、Last-Modified 和远端 Content-Length。任一稳定标识变化，
将旧断点移到 `temporary/GSM*/work/<run>/quarantine/`，从零开始；不得拼接不同远端对象。

aria2 每次调用只尝试一次。外层默认最多三次同类错误，并将次数写入 transfer JSON；
因此 tmux 或 watchdog 重启不会重置预算。默认退避由
`GEO_SRA_RETRY_DELAYS=0,30,120` 控制。

## 故障分类

| 类别 | 行为 |
|---|---|
| `network_interrupted` | 保留可信 partial，按预算续传 |
| `checksum_or_integrity` | 隔离完整但损坏的文件，从零重下 |
| `remote_changed` | 立即停止，重新核对 endpoint/manifest |
| `disk_or_conversion` | 立即停止，检查空间和 fasterq size check |
| `conversion_failure` | 立即停止，保留 SRA 与日志 |
| `read_validation` | 立即停止，核对 expected spots、layout 和 read role |

三次相同可恢复错误或任一不可安全重试错误将状态设为 `terminal_failed`。watchdog
看到该状态必须停止，不得循环启动 pipeline。

## NCBI prefetch

`prefetch` 的工作目录跨重试保留，使 SRA Toolkit 自身恢复缓存。只有出现完整
`.sra` 且 `vdb-validate` 失败时才隔离该文件；不得因普通 TLS/网络失败清空 cache。

## 人工恢复与换源

1. 阅读 `reports/status/<run>.transfer.json` 和对应 log。
2. 解决磁盘、metadata 或 endpoint 问题。
3. 若继续同一 source，保留可信 partial；需要新的三次预算时，先人工审计错误原因，
   再归档该 transfer JSON。
4. 若换源，重新运行 source selection/audit。新的 fingerprint 会归档旧状态并隔离
   不匹配断点。
5. 不要手工把 `.part` 政名为最终文件，不要热修改活动脚本。

## 清理关卡

仅当每个预期 run 均有 PASS download manifest、匹配的 complete marker、直接终端
文件审计且没有活动事务时清理。执行 `audit_download_evidence.py --deep` 与
`audit_storage_policy.py` 后，才删除 `.part`、`.aria2`、resume metadata 或 work。
FASTQ 删除只允许 `apply_storage_policy.py` 在 Mode B 且 matrix 验证通过后执行。
