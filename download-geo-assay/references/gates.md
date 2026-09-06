# 不变量、停止条件与决策边界

## 不变量

1. SRR/run 仅是下载单元；GSM/文库才是转换、审计、raw release 的原子单元。
2. 来源对象下载完成必须有大小、校验和或等价完整性证据；HTTP 200 本身不够。
3. provenance 与 transport 分列记录。镜像 endpoint 不会自动改变对象 provenance。
4. raw 删除必须同时满足：前置授权、全部成员 runs 完整、标准产物存在、结构与样本覆盖通过、输入映射/provenance 完整、release 证据已持久化。
5. 任一门失败，只阻断当前单元并保留 raw；不得为推进队列放宽审计。

## 人工选择与自动探测

只向用户确认不能可靠推导且会改变结果的事项：最终产物、raw 去留、预算、明确来源偏好、是否接受 Lite、是否授权自动恢复。

先自动探测 assay、参考文件、endpoint、文件大小与校验和、quota、free space、read length、工具能力和代理是否必要。探测失败时记录证据和停止原因，不要求用户手工提供本可从官方端点获取的元数据。

## 停止条件

- assay 或 GSM/run 映射仍冲突；
- 选中对象的 provenance/quality class 不可判定；
- Lite 未获授权；
- 峰值预算超过项目、temporary/working、quota 或可用空间中的最严限制；
- 成员 run 缺失、下载校验失败或转换输入未覆盖所有 runs；
- processed 产物缺失、样本列缺失、结构/数值审计失败；
- raw 路径不属于当前 GSM，或删除候选在 release 证据落盘后发生变化；
- 自动恢复没有显式授权、没有持久预算，或重启后没有新进展。

停止不等于回滚已经验证的其他 GSM，也不授权修改活动脚本。

## 恢复边界

watchdog 默认只写快照。历史日志中的旧错误不算新事故；只有上次快照后出现的新错误或持续无进展才能改变当前状态。获授权的自动恢复也必须启动新会话，禁止热改正在执行的脚本。

## 六个执行关卡

1. **路由与来源锁定**：先写 `assay_routing.tsv`，再读匹配的来源文档。混合 assay 按 `(workflow, modality)` 分开执行、记录存储策略与日志；CEL 不等待 STAR。来源选择须留探测证据与选择原因，用户明确指定 NCBI 时直接尊重该偏好，不强迫重走已拒绝的来源。
2. **pilot 与剩余队列**：pilot 通过仅表示试点成功，日志须写 `pilot_done` 和“未开始剩余 N 个 GSM”。满足来源已锁定、pilot 校验通过、剩余队列实际启动、Mode B 已跑通逐 GSM release、当前峰值预算通过后，才可脱钩。tmux 可以用于保护 pilot 进程，但不能以空闲会话或退出码 0 宣布全集完成。运行入口见 [queue-execution.md](queue-execution.md)。不自动启动 watchdog。
3. **磁盘与预取**：每个 GSM 前重新审计项目总量、temporary 总量、文件系统剩余空间及可探测硬配额；配置的用户配额不能覆盖更严的文件系统限制。可选预取默认关闭，启用后最多 3 个 run，完整、Lite 和 partial 都占用 slot；独立 cache、共享锁并跳过当前 run。转换失败保留原料，成功审计后立即释放当前 GSM。
4. **代理与重启**：使用 HTTP(S) 代理时清除 `all_proxy/ALL_PROXY`，保留 localhost 的 no_proxy；不打印代理值。脚本仅显式加载 `GEO_SRA_PROXY_ENV` 指定的可信本地环境文件。更换代理或脚本先停对应会话，`bash -n` 后新开会话；旧 tmux 不会自动接收新环境。TLS 错误与 HTTP 403/5xx 属于未探明，不记为对象缺失；获准直连时可比较 HEAD 诊断，并记录实际 transport。
5. **参考对象**：先盘点 FASTA、GTF、STAR 版本和 index 参数，核对组装、注释版本及染色体命名；例如 RefSeq `NC_*` 与 GENCODE `chr*` 不可直接混配。是否复用已有参考需结合用户已确认的版本选择；不默认复用 Cell Ranger index。缺少兼容 index 时可在独立新目录构建，不替换活动任务使用的目录。`versionGenome` 是 index 格式兼容信息，实际软件版本用 `STAR --version` 记录。
6. **读长与方向**：用可靠 read length 推导 `sjdbOverhang=max(readLength)-1`，再由 pilot FASTQ 复核；测序平台和 RunInfo 的平均 spot 长度不能直接代替最大单 read 长度。未知链方向保留 GeneCounts 三列与 `unknown/pending`；可显式标记 unstranded 为临时比较列，但不能把暂用列写成已确认建库方向。

人工进度日志与 `watchdog.log` 分开。默认快照字段：当前 GSM/SRR、阶段、审计通过的转换数、剩余数、parked 数、temporary bytes、文件系统剩余 bytes、最近错误类别。`prefetch err: no error`、`retrying` 和字节进度本身不是失败证据；以退出码、持久状态和产物审计联合判断。
