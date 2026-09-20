# 峰值预算与滚动转换

`audit_manifest.py` 做事前估算；`acquisition_runtime.py` 在项目共享锁下记录预留，并在运行中检查项目总量、temporary、配置 quota 和文件系统剩余空间。项目内 raw、cache、partial、隔离副本、解包、转换与正式产物均计入实际占用。预留只补足尚未写入的空间，可复用缓存不重复计费；隔离和失败副本不能抵扣新的下载额度。

队列按 GSM 预留来源对象、展开和转换峰值、processed 与正式包的同时占用。默认 SRA 展开预算为来源对象的 18 倍，并保留 fasterq 原生空间预检；可按实测设置 `materialize_peak_bytes`。原样交付 SRA 不预留 FASTQ 展开空间。未知对象大小须先补探测，不能按零字节派发。

新建项目默认 `download_workers=2`、`download_connections=4`、`conversion_workers=1`。并发仍受空间预留约束；当前预算只能容纳一个单元时自动等待，直到在途单元完成并按授权释放 raw。所有在途任务结束仍无空间则返回 `waiting_space`，保留可恢复文件。空间逼近 `min_headroom_bytes` 或预算时停止派发并终止写盘进程，恢复后从持久状态继续。

这是软件预算与提前暂停，不能替代文件系统硬配额。默认每秒检查，写入可能在检查间隔内增加；必须为并发速率及块缓冲留足安全余量。外部用户的写入也可能消耗文件系统空间。`user_quota_bytes` 是配置的总预算；`quota(1)` 事前探测的用户剩余额度与 `df` 仍独立约束，不能互相替代。

独立的受审核转换脚本也应通过受监管入口运行，并使用共享转换锁。下列字节额度须由当前 GSM 的峰值估算提供，不能照抄占位符：

```bash
python scripts/acquisition_runtime.py exec --root . --key convert:GSM123 \
  --project-bytes <预计项目占用总字节> --temporary-bytes <预计临时占用总字节> \
  --path processed/GSM123 --path temporary/GSM123/conversion \
  --temporary-path temporary/GSM123/conversion -- \
  flock reports/status/materialize.lock bash scripts/convert_gsm.sh . GSM123
```

测序队列已自动完成以上监督；CEL/IDAT 下载、归档解包、GPL 和样本发布入口各自申请额度。逐 GSM release 同时持有 run/cache 锁，只删除当前已审核单元的精确候选；转换或审计失败时保留原料与证据。
