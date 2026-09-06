# 逐 GSM 队列

scaffold 生成的 `scripts/run_all.sh` 调用 `run_queue.py`。完成 assay routing、source selection 和存储策略确认后，每次只传一种 modality。该入口处理测序；CEL/IDAT 单独使用 GEO supplementary 下载器。

```bash
# Mode A 仅交付 raw 的示例：先 pilot，再启动剩余队列；已校验的 run 可复用。
bash scripts/run_all.sh --modality bulk_rnaseq --pilot 1
bash scripts/run_all.sh --modality bulk_rnaseq

# 请求标准矩阵时（Mode A/B）：先准备已审核的 GSM 转换脚本。
bash scripts/run_all.sh --modality bulk_rnaseq --convert-script scripts/convert_gsm.sh --pilot 1
bash scripts/run_all.sh --modality bulk_rnaseq --convert-script scripts/convert_gsm.sh
```

`convert_gsm.sh` 是项目按 assay、参考版本和科学选择准备的脚本，参数为项目根目录、GSM；必须覆盖该 GSM 所有 runs，输出标准产物及 `reports/conversion_provenance.tsv`。Skill 不自动猜参考或链特异性。请求标准矩阵产物（无论 raw 是否保留）但没有转换脚本时，队列在任何下载之前停止。

- `terminal_failed` 只 park 当前 GSM，保留 raw 并继续下一 GSM；不会重新开始该 run 的网络预算。同一 GSM 有多个 runs 时，任一失败都不能转换不完整文库。
- 脚本退出 2、锁冲突、未知本地失败或空间检查失败暂停整队，修复后新开会话。已有 terminal 状态须人工检查原因并归档后才能重试。
- 只有 processed 审计和 release 门都通过，才跳过已完成转换。单个非空 `ReadsPerGene.out.tab` 不足以跳过审计或删原料。
- 每个 Mode B GSM 下载 → 输入指纹 → 转换 → 审计 → 开放格式样本包发布 → `apply_storage_policy.py --gsm ... --confirm-delete` → 下一 GSM。该工具就是滚动释放入口，也可用于收尾；不要另写直接 `rm` 绕过它。
- 退出 0 表示本次队列遍历正常结束。`reports/queue_<modality>.tsv` 中有 `parked`、`blocked`、`not_started` 时全集未完成；HTML 会展示此表。`pilot_done` 不能宣称全集完成。
- 每个 GSE 同时只运行一个测序队列，以串行使用 STAR 和审计表。混合 assay 分开日志与会话；watchdog 默认不开，若启用仅监测，不因 parked 样本重启整队。

将队列 stdout/stderr 重定向到 `reports/logs/queue_<modality>.log`；它包含 `gsm_start`、GSM 状态、pilot/queue 结束状态。各下载器细节另见每个 run 的日志。

转换脚本须输出 `open-delivery.md` 指定的每样本开放文件，并记录 `reference,counting_strategy`。正式包在 `deliverables/<sample_id>/`，任何临时对象格式不能代替该包。
