# NCBI SRA

- `sra-pub-src-1` 与 `sra-pub-src-2` 是选择性收录的 source-submission buckets。两者都应探测；缺失只表示该 bucket 没有对象，不能推出该 run 没有完整归档对象。
- SRA Open Data Program/ondemand 对象是 full-quality normalized SRA。探测必须验证精确 key、成功状态和非零大小。
- 常规 `prefetch` 使用 resolver/cache，并记录最终对象路径与实际类型。下载后若发现 `.sralite` 或 Lite 标记，必须分类为 `SRA_LITE/SIMPLIFIED`。
- SRA Lite 会把每条 read 的质量简化为 Q30 或 Q3。它必须显式 opt-in；未授权时移入隔离或停止，不进入转换，更不能记为 full-quality。
- `fasterq-dump` 的 working/scratch 预算按 SRA accession 大小约 8–10 倍规划，并纳入 FASTQ 展开、转换 scratch、processed、lookahead 和安全余量。
- Phred 检查只能辅助识别简化质量，不能替代官方对象类型和 resolver provenance。

## 正式执行路径

先用 `probe_ncbi.py --expected metadata/expected_runs.tsv --output metadata/ncbi.tsv` 探测两个 source buckets 与精确 ODP key，再把 `--ncbi metadata/ncbi.tsv` 交给 `select_sources.py`。source buckets 的提交 FASTQ/BAM 有不同 read roles，不能凭任意一个对象存在就用作配对 FASTQ。保留整份探测表，Lite 的后续替换依据也来自这里。

下载时先检查 staging 与独立 `temporary/prefetch_cache/<SRR>/<SRR>.sra`，只有 `vdb-validate` 通过的完整 archive 才复用；这一步在 ODP 网络请求之前。否则检查完整 ODP 对象。HEAD 200 可走 HTTP；`000`、超时、TLS、403、5xx 都是状态不明，不能当作缺失，也不能据此启动 prefetch。

`ncbi_odp.py` 在 HEAD 状态不明时通过 `aws s3api list-objects-v2 --no-sign-request` 查精确 `sra/<SRR>/<SRR>` key 与正数字节数。这是 `aws s3 ls` 人工检查的结构化实现：不会把前缀相同的别的 run 当作当前对象。列举成功则 `aws s3 cp` 到独立 cache 的 `.aws.part`，校验退出码、字节数、`vdb-validate` 及下载前后的 ETag/大小等身份后，才原子改名为 `.sra`。ETag 用作对象身份，不当作通用 MD5。证据保存在 `reports/status/<SRR>.odp.json` 并纳入下载 manifest。

只有 HEAD 404 或明确的 `x-amz-delete-marker: true` 才允许进入 prefetch/Lite 分支；空列表、AWS 失败或缺少 AWS CLI 均保留 `unreachable`，按持久预算停止。新 scaffold 已包含 `awscli`。旧项目须先检查 `aws --version`，并在项目环境准备该工具。

AWS fallback 不承诺跨进程续传：旧 partial 保留并计入磁盘占用，新 copy 从独立文件开始。预算耗尽后先检查空间和旧 partial，再显式恢复；不能自动反复归档预算重试。已完整校验的 cache 始终优先于 HEAD/AWS/prefetch；已有 terminal 状态仍需先按恢复手册归档，缓存存在不自动解除失败状态。

ODP 缺失时用 `prefetch --type sra --max-size u`，实际返回 Lite 并不等于传输失败。只有已有 `allow_sra_lite=true` 且已确认 ODP 缺失时才接纳校验通过的 Lite；完整归档始终优先。未获授权的 Lite 保留等待决策，不反复删除重下。现场对 Lite 的许可不能默认套用到所有新项目。

预取器同样复用已校验的 Lite cache：本轮确认 ODP 缺失后，有授权则记为 ready，无授权则保留并停止该 run 的预取；两者都不重复调用 prefetch。若完整 ODP 已可用则优先完整对象，状态不明时仍不得接纳 Lite。

`download_run.sh` 把实际类型原子写入 staging 的 `<SRR>.object.tsv`，发布恢复前重新读取，最终 manifest 使用 `SRA_LITE/SIMPLIFIED` 与 `replacement_note`。不能因 staging 统一文件名为 `.sra` 而改写成 full-quality；旧 staging 缺少身份记录时须人工核查，不能靠文件名推定。

无 provider MD5 时不虚构校验和：`vdb-validate` → `fasterq-dump --size-check only` → 实际转换 → gzip CRC → FASTQ 结构和 R1/R2 条数、已知 `expected_spots` 校验；本地 MD5 用于后续损坏检测。元数据 spots 与实际生物学 read 数若不适配该 layout，先厘清再重试。

## 可选、有上限的预取

在 `acquisition_config.tsv` 设 `prefetch_ahead_runs=1..3` 后，可运行一次：

```bash
python scripts/prefetch_ahead.py --root . --current-run SRR...
```

该工具仅预取选中 NCBI archive 来源的后续 run，独立 cache、同一 run/cache 锁、持久三次预算；cache 已满时 idle，跳过当前 run。它也遵守 ODP 分流：完整 cache 优先，AWS 确认存在则 copy，明确缺失且来源为 ncbi_sra 才 prefetch；状态不明时保留失败证据，不绕过主下载器的规则。其预算是独立的 `<SRR>.prefetch.json`，不会被 transfer 的 archive-retry 重置。保留完整文件、Lite 和 partial，主下载器接管时仍重新校验类型与 ODP 条件。每次调用是有界的一轮，不自行启动循环、tmux 或 watchdog。若配置了代理文件，在新会话先加载环境，再调用 Python 预取器；该工具自行清除 `all_proxy/ALL_PROXY`。不并行第二个 STAR。

格式与来源依据：[NCBI SRA formats](https://www.ncbi.nlm.nih.gov/sra/docs/sra-data-formats/)、[NCBI AWS download](https://www.ncbi.nlm.nih.gov/sra/docs/sra-aws-download/)。

传输语义：[AWS HeadObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html)、[AWS ListObjectsV2 CLI](https://docs.aws.amazon.com/cli/latest/reference/s3api/list-objects-v2.html)、[AWS s3 cp](https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html)。
