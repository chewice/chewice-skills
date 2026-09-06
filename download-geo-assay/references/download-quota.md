# 峰值预算与滚动转换

预算以 GSM/文库为单位，同时计入来源对象、FASTQ 展开、`fasterq-dump` scratch、转换 scratch、processed 产物、下一单元预取和安全余量。SRA 转 FASTQ 时按 accession 约 8–10 倍 scratch 预留。

`audit_manifest.py` 比较项目上限、working/temporary 上限、可用空间和已知用户 quota，采用最严限制。若当前单元峰值不满足，不能启动下一单元。Mode B 逐单元下载、转换、审计和 release，不以“整批已下载”作为删除门。

`user_quota_bytes` 表示配置的项目总预算；`quota(1)` 检测值表示文件系统对该用户的剩余预算，两者独立比较，不能相互替代。`df` 仍单独约束可用空间。`--gsm` 只对即将运行的 GSM 评估峰值，并保留全 manifest 元数据检查。

预取默认 `prefetch_ahead_runs=0`；启用后的预取容量计入峰值，完整文件、Lite、未完成 cache 目录均占 slot。用户把项目上限改大不能消除底层硬配额。未知来源大小须先补探测/保守预算，不能把空 `selected_bytes` 当成该 run 不占空间。

逐 GSM release 在共同持有 run/cache 锁时，将该 GSM 的 FASTQ、已关联 run 的 prefetch archive 与旧 work archive 一并列入精确候选、校验和和删除日志；其他 GSM 的 cache 不在候选内。转换或审计失败时保留 raw 与 temporary/logs。
