# download-geo-assay 现场踩坑与迭代备忘

- 日期：2026-09-05
- 来源任务：`02.MDD_DLPFC_Bulk_Meta-analysis`（GSE102556 bulk RNA-seq Mode B + GSE208338 / GSE53987 Affymetrix CEL）
- 真正 skill 包：`~/.codex/skills/download-geo-assay`
- 性质：把这次下载里真实发生过的坑、中断、失败，以及后来有效的处理，整理成**可泛化**条目，供下次改 skill 时对照。不是表达分析结果，也不替代 `data/GEO_three_datasets_plan.md`。
- 约定：本文只记录已发生的事实与已拍板的处理。未选定的 skill 包结构（例如是否拆 `subskills/`）不在这里改文件。

---

## 1. 这次任务里 skill 实际碰到的形状

| 项 | 现场事实 |
|---|---|
| 混合 assay | 一次会话同时处理 bulk RNA-seq 与两套芯片。注意力会被 CEL、STAR、ENA、NCBI 搅在一起。 |
| GSE102556 | 341 GSM / 343 SRR，人 263 + 鼠 78。Mode B：`gene_count_matrix`，不长期留 FASTQ。全集 FASTQ 约 1.70 TiB。 |
| 芯片两套 | GSE208338 169 CEL、GSE53987 205 CEL，Mode A 留 `raw/GSM*/CEL/`。相对测序，芯片路径短、坑少。 |
| 数据源探测 | NGDC 无可用文件 endpoint（503/404，`ngdc_missing` 248、`ngdc_unreachable_after_3_attempts` 95）→ 曾走 ENA FASTQ → 用户改 NCBI/SRA Toolkit。 |
| 转换 | STAR 2.7.11b GeneCounts；人 `sjdbOverhang=49`，鼠 `99`；链特异性先 unstranded。 |
| 控盘 | 用户临时配额先 500 GiB 后 700 GiB；系统盘硬上限约 573/592 GiB。真正控盘的是「每个 GSM 转换通过后立刻删 FASTQ / prefetch cache」，不是全集结束后再 `apply_storage_policy.py`。 |

到 2026-09-04 22:28 重启时：STAR **270 / 341**（人 263/263，鼠 7/78），队列因 `SRR5956344` prefetch 三次失败停住。

---

## 2. 中断时间线（只列打死队列或改过规则的事件）

| 时间 | 现象 | 直接原因 | 处理 |
|---|---|---|---|
| 2026-08-23 11:40 | 第一批 ENA FASTQ 几乎立刻报错 | `all_proxy=socks5://...` 被 aria2 当成 `--all-proxy`；随后 ENA TLS 被对端掐断 | `source proxy.env` 后 **`unset all_proxy ALL_PROXY`**；NCBI/ENA 只用 HTTP(S) |
| 2026-08-23 18:54 | 用户以为全集下完 | `first_batch_fastq_star.sh` 只跑 2 个 GSM 做 seqkit，`EXIT:0` / `first_batch_done` | 试跑成功 ≠ 全集完成；必须另开剩余队列 |
| 2026-08-23 20:54 | `fasterq-dump` `Disk quota exceeded(122)` | 用户配额 500 GiB，系统硬配额更小；prefetch 无上限把 `temporary/` 打满 | 升项目配额不够；要按 GSM 立刻删 FASTQ，prefetch 超前上限 ≤3 |
| 2026-08-24 19:17 | `CONTINUE_EXIT:1`，`SRR5961855` | prefetch 三次后仍无可用原始 `.sra`（NCBI 给 Lite） | 后改：先探 `sra-pub-src-1/2` 与 ODP；ODP 无完整 `.sra` 才允许校验过的 Lite |
| 2026-08-25 13:09 | `CONTINUE_EXIT:2` syntax error | **热改正在跑的 `download_run.sh`** | 先停 tmux → `bash -n` → 新开会话。禁止热改活动脚本 |
| 2026-08-31 07:52 / 14:02 | `SRR5962007` / `SRR5962014` terminal_failed | 代理 `10.10.10.217` 对 ODP `SSL_ERROR_SYSCALL`；prefetch 三次拒收 Lite | 换代理必须新开 tmux。ODP HEAD 必须是 200 才算有完整 `.sra` |
| 2026-09-01 / 09-02 | `SRR5962025`、`SRR5962058` 整队停 | ODP 404 + NCBI `prefetch --type sra` 仍给 `.sralite`；当时脚本只认 `.sra` | 用户拍板：先用校验过的 Lite，写 `provenance=SRA_Lite`；src-1 提交 FASTQ 以后可换 |
| 2026-09-03 22:17 | `Publish journal source fingerprint mismatch` | 改了 `download_run.sh` 后 `SOURCE_FINGERPRINT` 变了，残留 `publish.json` 对不上 | 删该 SRR 的 `work/publish.json` 与陈旧 `transfer.json`，保留已校验 `.sra`，新开 continue |
| 2026-09-04 12:18 | `SRR5956344` `CONTINUE_EXIT:1` | prefetch HTTPS 失败三次；`set -e` 让单 run 失败停掉剩余 70+ GSM | 单 run `terminal_failed` 应隔离，不应杀死整队。后来 prefetch_cache 已有 12 GiB `.sra`，重启即可续 |

`CONTINUE_EXIT:1` 在日志里出现过多次，**不等于**「脚本写坏了」。`set -e` 下 `download_run.sh` 非 0 就会把 `continue_remaining_fastq_star.sh` 整队带停。

---

## 3. 可泛化踩坑（按主题）

每条格式：**现场** → **根因** → **不要再做** → **正确处理** → **建议写进 skill 的位置**。

### 3.1 注意力与关卡：混合 assay 会把下载逻辑搅乱

**现场。** 同一会话里 CEL 下载、GPL 注释、人类/小鼠 STAR index、ENA FASTQ、NCBI prefetch 交替出现。Agent 容易用测序脚本去碰芯片，或反过来。

**根因。** skill 入口没有把「先分 assay、再分数据库」做成硬隔离。`SKILL.md` 现在写了这条，但包内 `subskills/`、`source_capability.yaml`、`references/gates.md` **实际不存在**，Agent 只能读摘要。

**不要再做。** 为「了解全貌」同时打开 microarray 与 bulk、ENA 与 NCBI 的 playbook。

**正确处理。**

1. `detect_assay.py` 写出 `metadata/assay_routing.tsv` 之前，不打开任何 source 文档、不开下载。
2. 每个 `(workflow, modality)` 各自问存储策略、各自 tmux、各自日志。
3. 芯片 GSM 不等 STAR index；测序 GSM 不走 GEO CEL 下载器。
4. 用户改数据源（例如「改 NCBI」）时：必须先有 NGDC 探测失败记录和 `fallback_reason`，禁止因为「快」就跳优先级。

**写入。** 保留 `SKILL.md` 注意力隔离；补齐缺失的 `references/gates.md` 与 source 子文档，否则摘要无法执行。

---

### 3.2 「正轨」未定义时过早 tmux 脱钩

**现场。** 第一批 2 GSM 的 seqkit 脚本 `EXIT:0` 后，监测会话显示「无 prefetch / fasterq / STAR」，用户问「为什么 18:54 正常结束了」。剩余 339 GSM 还没开。

**根因。** skill 把「长时间任务丢进 tmux」写得太早。试跑成功、watchdog 空转、HTML 报告刷新，都长得像「做完了」。

**不要再做。** 把 `first_batch` / `self_test` / 单个 CEL 试下的 `EXIT:0` 当成全集完成。不要在数据源未锁定时开会自动重启的 watchdog。

**正确处理。正轨 = 同时满足：**

1. 数据源已锁定（本任务：NGDC 失败已写入 → 用户确认 NCBI）。
2. 第一批校验通过（seqkit 读长与 RunInfo 一致；芯片则是 CEL 字节/解压检查）。
3. 跑的是**剩余队列**，不是试跑脚本。
4. Mode B 已能按 GSM 删 FASTQ，且 `temporary/` 低于配额。

正轨之后才 tmux 脱钩。给人看的进度 log 与 watchdog 重启 log 必须分开。用户 `tmux attach` 看不到内容时，进度在**文件日志**里（本任务：`data/reference/logs/gse102556_continue.log`），不是 monitor 会话的空屏。

**写入。** `references/gates.md` 第 1、2 条。明确：试跑脚本必须在文件名和日志里带 `first_batch` / `pilot`，完成句必须写「未开始剩余 N 个 GSM」。

---

### 3.3 代理拓扑：aria2 不能吃 socks5 `all_proxy`

**现场。** 用户给的环境是：

```bash
export https_proxy=http://10.10.10.215:7897 http_proxy=http://10.10.10.215:7897 all_proxy=socks5://10.10.10.216:7897
```

（地址后来 215 → 217 → 216。）aria2 立刻：

```text
Caught Error while parsing environment variable 'all_proxy'
unrecognized proxy format
```

随后 ENA `ftp.sra.ebi.ac.uk` 出现 `Error decoding the received TLS packet` / `TLS connection was non-properly terminated`。

**根因。** 用户习惯把 Clash/VPN 的 HTTP 与 socks5 一起 export。aria2 把 `all_proxy` 解析成 `--all-proxy`，不认 `socks5://`。prefetch / aws / curl 对坏代理的表现又不同：有的慢、有的 `SSL_ERROR_SYSCALL`、有的直连反而 200。

**不要再做。**

- 把用户的 `export` 原样塞进所有下载器。
- 换代理时热改正在跑的脚本或指望旧 tmux 读到新 `proxy.env`。
- 国内镜像还开着海外 VPN（本任务 NGDC 本身就没有文件 endpoint，但规则仍成立）。

**正确处理。**

1. 下载前问清：HTTP/HTTPS 给谁、socks5 给谁、国内源是否直连。
2. 写入 `data/proxy.env`，并固定 `no_proxy=localhost,127.0.0.1`。
3. 脚本 `source` 后：**NCBI/ENA/ODP/aria2/aws 只用 `http_proxy`/`https_proxy`，立刻 `unset all_proxy ALL_PROXY`。**
4. 换代理 = 停对应 tmux → 写 `proxy.env` → `bash -n` → **新开** tmux。不要热补环境变量。
5. 某台代理对 ODP 出现 `SSL_ERROR_SYSCALL` 时，用 HEAD 对比直连。直连 200 说明对象存在、代理坏了；不要把 SSL 失败当成「ODP 没有 `.sra`」。用户若坚持走 HTTP 代理，换一台能 TLS 的，而不是默默改成直连后不记录。

**写入。** `references/gates.md` 第 4 条；`download_run.sh` / 任何 aria2 包装脚本的固定序言。skill 示例里不要再出现「把用户的 all_proxy 原样 export」。

---

### 3.4 数据源优先级：NGDC 空、ENA 不稳、NCBI 才是本任务的主路径

**现场。** `probe_ngdc.py` 对 GSE102556 几乎全是 503/404，没有可下的文件 endpoint。skill 优先级要求 NGDC → ENA → NCBI。ENA FASTQ 在代理下 TLS 不稳。用户明确「改 NCBI/SRA Toolkit」。

**根因。** 「国内镜像更快」被理解成可以跳探测。NGDC 收录项目 ≠ 有可下载 run。ENA 有 MD5，但 TLS 中断后断点不可信。NCBI 原始 `.sra` **没有 provider MD5**。

**不要再做。** 未写 `fallback_reason` 就换源。用「测速」代替优先级。把 GEO series matrix / 作者 logcounts 当 raw。

**正确处理（测序，NCBI 锁定之后）。** 每个 SRR 独立探测，顺序为：

1. `s3://sra-pub-src-1/<SRR>/` **和** `s3://sra-pub-src-2/<SRR>/`：作者提交的 FASTQ/BAM。
2. AWS ODP 完整 `.sra`：`https://sra-pub-run-odp.s3.amazonaws.com/sra/<SRR>/<SRR>`。**HEAD 必须 200。** 404 加上 delete-marker = 对象不存在，不是「再等等」。
3. `prefetch --type sra --max-size u`。
4. 若 ODP 无完整 `.sra`、NCBI 只给 Lite：在 `vdb-validate` 通过的前提下**先用 `.sralite`**，`provenance=SRA_Lite`，并在 `processed/<GSM>/source_record.tsv` 留「src-1 以后可换」的记录。有完整 `.sra` 仍优先 `.sra`。

**写入。** `references/provenance-routing.md` 与 NCBI source 子 skill。当前 `source_capability.yaml` 缺失，优先级只写在散文里，Agent 执行时容易漏 src-1/src-2 和 ODP HEAD=200。

有效 `fallback_reason` 本任务已用：`ngdc_missing`、`ngdc_unreachable_after_3_attempts`。换到 NCBI 后不要把 reason 留空。

---

### 3.5 NCBI Lite ≠ 下载失败；拒收 Lite 会把整队打死

**现场。**

- `SRR5961855`：prefetch 成功但产物是 Lite；脚本只要 `.sra`，三次后 `terminal_failed`。
- `SRR5962025` / `SRR5962058`：ODP 404，`prefetch --type sra` 仍给 `.sralite`。当时 `download_run.sh` 三次拒收，`CONTINUE_EXIT:1`。
- 旁路脚本 `star_SRR5962025_sralite.sh`、`star_SRR5962058_sralite.sh` 证明 Lite 可以 fasterq + STAR。
- `sra-pub-src-1` 上仍有提交 FASTQ（例如 2025=`NAC_212`，2058=`SUBIC_124`，1855=`BA89_57`）。

**根因。** skill / 旧 `download_run.sh` 把「只要 `.sra`」当成完整性策略。NCBI 对部分 run 已经没有完整 archive，只提供 Lite。`--type sra` **不能**保证不是 Lite。prefetch 日志里的 `err: no error ... success` / `retrying` 是工具自己续传，不是任务挂了。

**不要再做。**

- 发现 `.sralite` 就 `rm` 再 prefetch 三次，然后停整队。
- 把 Lite 当最终唯一来源且不记账。
- 热改正在跑的 `prefetch_ahead.sh` 去「顺便」保留 Lite（本任务里 `prefetch_ahead.sh` 仍会 `rm` cache 里的 `.sralite`）。

**正确处理。**

1. HEAD ODP：200 → 下完整 `.sra` 并 `vdb-validate`。
2. 非 200 → prefetch；若只有校验过的 Lite → 收下，写 `SRA_Lite`。
3. 同步记 src-1/src-2 是否还有提交 FASTQ，供以后重转。
4. NCBI `.sra` 无 provider MD5。实际检查链：`vdb-validate` → `fasterq-dump --size-check only` → `gzip -t` → R1/R2 条数 = RunInfo `expected_spots`。
5. 续传后必须跑上述检查；「HTTP 成功」或「文件大小看起来对」不够。

**写入。** NCBI `download_run.sh` 的 `pick_sra_file` / `prefetch_staged`。skill 正文目前的 `download_run.sh` **仍只认 `.sra`**，与现场已拍板的 Lite 策略不一致，这是下一轮必须合入的补丁。

---

### 3.6 `SOURCE_FINGERPRINT` 与热改脚本

**现场。** 2026-09-03 为了收 Lite 改了 `download_run.sh`。重启后立刻：

```text
Publish journal source fingerprint mismatch
CONTINUE_EXIT:1 2026-09-03T22:17:20+08:00
```

同日更早还有两次 **syntax error**（`unexpected token ')'` / `'path'`），都是热改正在被 bash 读取的脚本导致 `CONTINUE_EXIT:2`。

**根因。** `publish.json` / `transfer.json` 把当前脚本算出的 fingerprint 当成「还是同一个远端对象」。改探测顺序、URL 字段、provenance 或 helper 后 fingerprint 变了，但磁盘上的 `.sra` 仍可用。热改则让正在跑的 bash 读到半截文件。

**不要再做。** 对正在跑的 `.sh` 做 StrReplace / 插入函数。不要为了对齐 fingerprint 而重下已经 `vdb-validate` 通过的对象。

**正确处理。**

1. 停 continue 与 prefetch tmux。
2. `bash -n` 所有将要启动的脚本。
3. 若报 fingerprint mismatch：删**该 SRR** 的 `work/publish.json` 和陈旧 `transfer.json`，保留已校验 `.sra` / `.sralite`，再新开 continue。
4. 换代理、改探测逻辑、改 Lite 策略，一律新开 tmux，不热补。

**写入。** `references/recovery-playbook.md` 已有「不要热修改活动脚本」。补一条：**改 `download_run.sh` 等于可能作废所有未 complete 的 publish journal**。watchdog 看到 `terminal_failed` 必须停，不得靠重启清零三次预算；但 fingerprint mismatch 是人工可恢复的本地状态，不应算进「三次网络失败」。

---

### 3.7 Prefetch 与主队列抢锁、把盘打满

**现场。** 为提速并行 prefetch 后：

- 与 `download_run.sh` 抢同一 SRR 的 NCBI cache / `flock`。
- `temporary/prefetch_cache` 一度约 263 GiB，用户问能不能删。
- 系统出现 `Disk quota exceeded(122)`，`fasterq-dump` 写不进去。
- 用户拍板：每完成一个 GSM 的转换就立刻清该 GSM 的 FASTQ 和对应 cache。

**根因。** skill 第 3 条闸门写了「可并行 prefetch；不要并行 STAR」，但没有 **超前上限** 和 **独立 cache 目录**。Mode B 的删除入口在文档里仍是全集级 `apply_storage_policy.py`，与「按 GSM 立刻删」冲突。用户配额（500/700 GiB）可以大于文件系统硬配额。

**不要再做。** 无上限预取。prefetch 写进 `temporary/GSM*/work/<SRR>/` 与主队列同一把锁。等 341 个 STAR 都完再删 FASTQ。把用户说的 700 GiB 当成一定写得进去。

**正确处理。**

1. prefetch 独立目录：`temporary/prefetch_cache/<SRR>/`。
2. 超前最多 N 个完整 `.sra`（本任务 N=3）。cache 达上限则 idle，不要再拉。
3. **跳过主队列正在处理的第一条 SRR。**
4. STAR `ReadsPerGene.out.tab` 通过后：立刻删该 GSM 的 FASTQ、该 SRR 的 cache、残留 `temporary/GSM*`。
5. 开下一批前估算 `expected_bytes`；超过剩余配额（取 **用户配额与 `df`/`quota` 的较小值**）则暂停。
6. 转换失败保留该 GSM 的 temporary 与日志，`deletion_status=blocked`。

**仍未修好的一点。** `prefetch_staged` 当前顺序是：已有 staging → ODP → 才看 cache。2026-09-04 重启 `SRR5956344` 时 cache 里已有约 12 GiB 校验过的 `.sra`，主脚本仍因 ODP HEAD=200 重新 `aws s3 cp`。下一轮应改为：**cache 里 `vdb-validate` 通过的 `.sra` 优先于重新拉 ODP**。

**写入。** `references/download-quota.md` 与 `references/gates.md` 第 3 条。Mode B 的删除规则要从「只能 `apply_storage_policy.py`」改成「**每个已审计 GSM 立即删除**；`apply_storage_policy.py` 只做收尾扫尾」。skill 里还没有 `prefetch_ahead.sh`，应作为可选加速器写入 NCBI source 文档，并带上限与独立 cache。

---

### 3.8 单 run 失败杀死剩余队列

**现场。** `continue_remaining_fastq_star.sh` 使用 `set -e`，对每个 SRR 调 `download_run.sh`。任一 `terminal_failed` 都变成整队 `CONTINUE_EXIT:1`，后面几十个已有 STAR 或可 skip 的 GSM 全部停。

**根因。** 队列脚本把「这个 run 下失败」和「这条流水线坏了」当成同一件事。三次预算用尽后本应 **park 该 SRR、继续下一个 GSM**。

**不要再做。** 用 watchdog 对着 `terminal_failed` 循环拉起同一条 pipeline（会把三次预算清零或空转）。也不要在失败时重跑已经有 `ReadsPerGene.out.tab` 的 GSM。

**正确处理。**

- 有 STAR 产物：`skip_star_done`。
- `terminal_failed`：写入状态、记日志、**继续下一个 GSM**；人工看完再单独重试失败 run。
- 队列退出码：全部完成 0；存在 parked 失败则为 0 但报告里列失败清单，或用 0+sidecar 清单，避免 Agent 把非 0 理解成「脚本崩了必须改语法」。

**写入。** sample 循环 / runner，不要只写在项目脚本注释里。`watchdog.sh` 继续：看到 `terminal_failed` 停止自动重启。

---

### 3.9 STAR index：平台名、旧 index、染色体名、格式号

**现场。**

- 一度准备复用机器上 GENCODE v44 / 10x `GRCh38-2024-A` index，`sjdbOverhang=100`（因为 HiSeq 2000「常见 101 bp」）。
- 用户改为 GRCh38.p14 + GENCODE v47；小鼠 GRCm39 + M36。
- NCBI RefSeq `NC_*` FASTA 配不上 GENCODE `chr*` GTF。
- index 文件里 `versionGenome=2.7.4a` 是格式号，不是 STAR 软件版本（实际 2.7.11b）。
- SRA RunInfo + 第一批 seqkit：人约 50 bp → overhang **49**；鼠约 100 bp → **99**。用户确认后重建，未中断已在跑的错误 overhang 任务，而是新目录重建。

**根因。** skill 转换文档写「下载流程不现场生成人类基因组 index」，但现场经常没有对齐的 index。Agent 会抓最近能用的目录，包括 Cell Ranger。

**不要再做。** 用测序平台猜读长。用 10x Cell Ranger index。用 RefSeq `NC_*` FASTA 配 GENCODE GTF。把 `versionGenome` 当成 STAR 版本。

**正确处理（闸门 5+6）。**

1. 先盘点本机 FASTA / GTF / STAR / STARsolo / index，再问是否沿用。必须对齐 GRC 组装 + GENCODE 版本 + 染色体命名。
2. `sjdbOverhang = max(readLength) - 1`，来源是 RunInfo，第一批 FASTQ `seqkit` 复核；不一致则先重建再转其余样本。
3. 未知链特异性先 unstranded，用 ReadsPerGene 三列核对。
4. 芯片不走 STAR。

**写入。** `references/gates.md` 第 5、6 条已在 `SKILL.md` 摘要出现；`references/conversion.md` 里「不现场生成 index」应改成「未盘点、未询问、未对齐染色体命名前不得生成或复用」。

---

### 3.10 日志噪声 vs 真失败

**现场。** 用户 `tail -f continue.log` 看到满屏 `Completed 256.0 KiB/...` 和 prefetch `err:`，以为一直失败。另一边 `tmux attach -t geo-GSE102556-monitor` 是空的。

**根因。** `aws s3 cp` / aria2 / prefetch 把进度打到同一文件。进度 log 与 watchdog log 混用时，Agent 也会把续传当成停滞。

**不要再做。** 把 `retrying`、`err: no error`、`Completed 256 KiB` 当成任务挂了。不要让用户去 attach 一个只负责 sleep+snapshot 的 monitor 会话找下载进度。

**正确处理。**

- 人类进度：固定间隔快照（本任务曾 15 min / 30 min），字段按用户指定。
- 机器证据：`reports/status/<SRR>.transfer.json`、`*.complete`、STAR `ReadsPerGene.out.tab`。
- `watchdog.log` 只记拉起/停止。默认不要自动开 watchdog。
- 看进度用文件：`gse102556_continue.log` 过滤 `gsm_start|gsm_done|COMPLETE|Terminal failure|CONTINUE_EXIT`。

**写入。** 闸门 2。给一个「进度字段默认集」：当前 GSM/SRR、阶段、已完成 STAR 数、剩余、`temporary/` 占用、`df`、最近一条错误类。

---

### 3.11 芯片路径相对干净，但仍有关卡

**现场。** 两套 CEL 最终齐。GPL5188 注释曾让用户自己下 `.txt` 上传，Agent 需要确认这就是平台注释而不是 series matrix。

**正确处理。** 芯片只走 `download_geo_supplement.py` / GEO FTP。不要把芯片 GSM 丢进 `download_run.sh`。skill 不做 RMA。GPL 注释是文件管理，不是分析。用户提供的 `.txt` 只要来自 GEO 平台页即可，不要改去下 `GPL*_family.soft.gz` 当替代（skill 默认禁止 family.soft）。

---

## 4. 队列退出码与状态机（给下一轮脚本）

本任务实际用过的状态：

| 状态 | 含义 | Agent 该做什么 |
|---|---|---|
| `skip_star_done` | 已有非空 `ReadsPerGene.out.tab` | 不要重下 |
| `in_progress` | 正在 prefetch / fasterq / STAR | 不要并行第二个 STAR；不要热改脚本 |
| `network_interrupted` | 保留 cache 续传 | 未满三次则继续；满三次 → park |
| `terminal_failed` | 三次同类错误或不可安全重试 | **停该 run，继续其他 GSM**；不要 watchdog 循环 |
| fingerprint mismatch | 本地 journal 与当前脚本不一致 | 删 journal，保留已校验对象 |
| `CONTINUE_EXIT:2` | 脚本语法坏了 | 停一切，`bash -n`，修完再开 |
| `CONTINUE_EXIT:1` | 常见是某个 SRR 非 0 且 `set -e` | 先读最后一条 `Terminal failure`，不要当成「整条 skill 坏了」 |
| `first_batch` / 试跑 `EXIT:0` | 试点完成 | 开剩余队列，不要脱钩宣布完成 |

可信断点（ENA/aria2）仍要求 `.part` + `.aria2` piece map + `resume.json` 且 fingerprint 一致。NCBI prefetch 的工作目录跨重试保留；只有完整 `.sra` 且 `vdb-validate` 失败才隔离。普通 TLS 失败不要清空 cache。

---

## 5. 当前 skill 包与现场补丁的差距

这些是迭代时最值得先合的缺口（现场已经踩过，包内尚未对齐）：

| 缺口 | 现场已有 | skill 包现状 |
|---|---|---|
| `references/gates.md` | `SKILL.md` 引用「六个闸门全文」 | **文件不存在** |
| `subskills/`、`source_capability.yaml` | `SKILL.md` 要求一次只加载一个 | **目录/文件不存在** |
| NCBI 探测：src-1/src-2 → ODP HEAD=200 → prefetch → 校验 Lite | 项目 `data/GEO/GSE102556/scripts/download_run.sh` | 包内 `scripts/download_run.sh` 仍只 `prefetch` 要 `.sra` |
| 独立 `prefetch_cache` + 超前 ≤3 | `prefetch_ahead.sh` | 包内无此脚本 |
| prefetch 与主队列跳过当前 SRR | 项目脚本 | 未写 |
| Mode B 按 GSM 立刻删 FASTQ | `continue_remaining_fastq_star.sh` | 文档仍写删除入口只能是 `apply_storage_policy.py` |
| `unset all_proxy` | 项目所有下载脚本序言 | `SKILL.md` 摘要有一句；脚本未强制 |
| 改脚本后清 `publish.json` | 人工处理过 | recovery-playbook 未写 fingerprint mismatch 的本地恢复 |
| 单 run 失败不杀整队 | 未改，仍 `set -e` | runner 不存在 / 未规定 |
| `prefetch_ahead.sh` 仍 `rm` `.sralite` | 已知，约定下次新开 prefetch 时再改 | — |
| cache 优先于重复 ODP 下载 | 未改 | — |

**不要把项目里的 sidecar 脚本（`star_SRR5962025_sralite.sh` 等）原样拷进 skill。** 那是拒收 Lite 时期的权宜。正式路径应是 `download_run.sh` 收下校验过的 Lite。

选定「主 skill 如何对齐现场补丁」之前，不要改正在跑的队列所用脚本。

---

## 6. 建议写入 skill 的补丁优先级

### P0 — 不写进去还会再停整队

1. 补 `references/gates.md`（把本文 §3.2–3.10 的正确处理写成可执行条文，而不是只有 `SKILL.md` 摘要）。
2. NCBI `download_run.sh`：ODP HEAD=200、`pick_sra_file` 接受校验 Lite、`provenance=SRA_Lite`、探测 src-1/src-2。
3. 所有 aria2/aws/prefetch 包装：`source proxy.env` 后 `unset all_proxy ALL_PROXY`；换代理新开 tmux。
4. 禁止热改活动脚本；改 `download_run.sh` 后处理残留 `publish.json`。
5. Mode B：每个 GSM 转换审计通过立即删 FASTQ 与对应 cache；prefetch 超前有上限、独立目录、跳过当前 SRR。
6. 剩余队列：单 run `terminal_failed` park，不 `set -e` 杀整队。试跑 `EXIT:0` 不得表示全集完成。

### P1 — 减少人工救火

1. cache 内已校验 `.sra` 优先于重新拉 ODP。
2. `prefetch_ahead.sh` 保留校验过的 Lite，不再 `rm`。
3. 进度快照字段与「过滤关键词」写进闸门 2，避免 `tail -f` 进度行被当成 error。
4. 配额取用户值与文件系统硬配额的较小值；开下一批前估算。
5. 明确 NCBI 无 provider MD5 时的校验链。

### P2 — 结构（需用户选定后再动包）

1. 是否真的拆 `subskills/assays/*` 与 `subskills/sources/*`。
2. `source_capability.yaml` 是否落地。
3. watchdog 默认关闭；仅正轨后、用户明确要求才开。
4. 芯片 / 测序混合 GSE 的强制拆分执行单元。

---

## 7. 不要写进 skill 的数据集特例

这些是 GSE102556 的事实，泛化时只保留规则、不写死 accession：

- 人 263 / 鼠 78、读长 50/100、overhang 49/99。
- 具体代理 IP `10.10.10.215/216/217:7897`。
- 具体失败 SRR：`SRR5961855`、`2025`、`2058`、`2007`、`2014`、`5956344`。
- sidecar 脚本文件名和 `NAC_212` / `SUBIC_124` / `BA89_57`。
- 项目路径 `02.MDD_DLPFC_Bulk_Meta-analysis`。

对应的规则已经在 §3：按 RunInfo+seqkit 定 overhang；代理写入 `proxy.env`；Lite 在 ODP 缺失时作为记账后的授权 fallback；src-1/src-2 始终先探。

---

## 8. 现场已拍板、迭代时不得回退的决策

1. 不下载 GEO series matrix、FPKM、logcounts；不做 DESeq2 / RMA / GO / Seurat。
2. 混合 assay 必须拆开执行。
3. Mode B 控盘单位是 **GSM**，不是全数据集。
4. NCBI 锁定后：src-1/src-2 → ODP 完整 `.sra` → prefetch → 校验 Lite。
5. 有完整 `.sra` 绝不改用 Lite；无完整 `.sra` 时先用 Lite 往前走，并留下可替换记录。
6. 换代理、改探测、改 Lite 策略：停旧 tmux，校验语法，新开。不热改。
7. 不自动开 watchdog，除非用户明确要求。
8. 选定主 skill 对齐方案前，不改正在跑的队列脚本。
)