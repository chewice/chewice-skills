# NCBI SRA

- `sra-pub-src-1` 与 `sra-pub-src-2` 是选择性收录的 source-submission buckets。两者都应探测；缺失只表示该 bucket 没有对象，不能推出该 run 没有完整归档对象。
- SRA Open Data Program/ondemand 对象是 full-quality normalized SRA。探测必须验证精确 key、成功状态和非零大小。
- 常规 `prefetch` 使用 resolver/cache，并记录最终对象路径与实际类型。下载后若发现 `.sralite` 或 Lite 标记，必须分类为 `SRA_LITE/SIMPLIFIED`。
- SRA Lite 会把每条 read 的质量简化为 Q30 或 Q3。它必须显式 opt-in；未授权时移入隔离或停止，不进入转换，更不能记为 full-quality。
- `fasterq-dump` 的 working/scratch 预算按 SRA accession 大小约 8–10 倍规划，并纳入 FASTQ 展开、转换 scratch、processed、lookahead 和安全余量。
- Phred 检查只能辅助识别简化质量，不能替代官方对象类型和 resolver provenance。
