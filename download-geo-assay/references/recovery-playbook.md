# 传输中断与恢复手册

## 不变量与状态机

每个 run 依次经过 `preflight -> transfer/prefetch -> converting -> validating ->
publishing -> complete`。`reports/status/<run>.transfer.json` 是跨进程状态，
`reports/status/<run>.complete` 仅在最终 manifest 原子写入后生成。

- 下载与转换只写 `temporary/GSM*/work/<run>/staging/`。
- Mode A 最终 FASTQ/SRA/CEL/IDAT 属于 `raw/GSM*/`；Mode B 转换前 raw files 属于 `temporary/GSM*/fastq/`、`temporary/GSM*/CEL/` 或 `temporary/GSM*/IDAT/`。
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
将旧断点移到 `temporary/GSM*/work/<run>/quarantine/` 并停止；人工核对更新来源后才能重下，不得拼接不同远端对象。

每次外层重试重新检查远端身份，并向 aria2 传递强 ETag 的 `If-Match`，或适用的
`If-Unmodified-Since`。只有 aria2 成功退出且最终校验通过才可发布；磁盘写满或无法
创建文件立即停止，保留 partial。aria2 每秒保存恢复状态。

download manifest 的 `integrity_evidence` 区分 `provider_digest_verified`、
`native_archive_verified`、`format_size_read_count_verified`。gzip CRC 只能证明压缩结构，
不能独自证明下载完整；无提供方摘要时还须匹配预期字节数及 read/spot 数，或通过原生
archive 校验。本地 SHA256 用于后续防变更，不冒充远端提供的摘要。缺少可验证证据时
保留数据并阻断完成，不能承诺证明其与来源逐字节相同。

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

watchdog 默认 `auto_restart=false`，只采集快照。自动恢复必须在
`acquisition_config.tsv` 中显式授权并配置正数 `max_auto_restarts` 持久预算；它只能恢复
曾被观察为 running 的会话。一次授权重启后若完成数没有新进展，再次缺失时必须停止。
日志中早于上次快照的历史错误不算新事故，也不能触发重启。

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
5. 不要手工把 `.part` 改名为最终文件，不要热修改活动脚本。

### 三次预算的显式恢复

`--clear-error` 只清除当前错误显示及 `same_error_count`，**不会清除 `error_counts`**。
后者才是跨进程预算；旧 key 累计三次后，下次失败仍会立即 terminal。这是为了防止
watchdog/continue 无限刷新预算，不应将 clear-error 改为隐式清零。

停止该项目队列与对应 run/预取会话，核实并修复网络或缓存后，运行：

```bash
python scripts/transfer_state.py archive-retry --root . --run SRR123456 \
  --reason '已核实 ODP 对象并修复代理，或已准备通过 vdb-validate 的完整缓存'
```

命令检查 queue/run/cache 锁，保留完整旧 transfer JSON 和恢复理由，再创建新预算。
它不删除 cache、partial、publish journal 或完成证据；已有 complete 的 run 不允许重置。
之后启动原队列入口，下载器优先复用校验通过的 full cache。不要把此命令放进自动重试循环。

`CONTINUE_EXIT:1` 或会话退出仅表示命令失败/停止，不是下载完成。只有成员 run 的
complete marker、download manifest 和样本交付审计相符时才可报告完成。

## 清理关卡

仅当每个预期 run 均有 PASS download manifest、匹配的 complete marker、直接终端
文件审计且没有活动事务时清理。执行 `audit_download_evidence.py --deep` 与
`audit_storage_policy.py` 后，才删除 `.part`、`.aria2`、resume metadata 或 work。
raw 删除只允许 `apply_storage_policy.py --gsm <GSM> --confirm-delete` 在 Mode B 且当前
GSM 全部成员 runs、标准产物、provenance 和正式样本包验证通过后执行。

转换前必须生成 `reports/conversion_inputs/<GSM>.json`，审计后生成
`reports/processed_receipts/<GSM>.json`。旧 PASS 或结构诊断不代替当前文件的完整校验。
发布只在 `deliverables/.staging/<sample_id>/` 内准备，全部校验后原子改名。
raw 释放在首次 unlink 前持久化 `reports/release_journals/<GSM>.json`，每删除一个文件
更新日志。强杀后重跑原命令；恢复只允许日志中的原始候选集，并重新验证产物与样本包，
不得把新出现文件加入旧删除事务。

## Publish fingerprint mismatch 是本地恢复问题

当前 fingerprint 由来源、URL、预期字节数、provider MD5、read role 与最终产品构成，**不包含脚本内容或代理地址**。修改脚本本身不应要求重新下载。现场旧脚本若改变了这些字段或 fingerprint 算法，仍可能留下不兼容 journal。

先停止对应 run 与预取会话，保存该 run 的 `publish.json`、`reports/status/<run>.transfer.json` 和日志，再比较旧新 manifest 的对象身份。只有确认同一对象且已校验时，才能归档陈旧 journal/state 并复用 archive；不是无条件删 journal。保留 archive 的实际 full/Lite 身份记录。部分文件已经发布时，依据 journal 逐项核对 staged/final 的校验和后重建事务，不能丢失发布账本。若远端对象已变，旧对象不得作为新来源复用。

此错误与语法/状态损坏返回本地阻断，不消耗三次网络预算。新脚本先 `bash -n`，之后启动新会话。`terminal_failed` 会在下载器入口被保留，不能仅重启来清零；队列继续其他 GSM，watchdog 则停止自身的自动恢复。
