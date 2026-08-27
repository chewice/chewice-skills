# `download-geo-assay` 技能改良方案（审核稿）

- 日期：2026-08-27（在 08-24 稿上增补错误课表、前置决策包、归档对象层级；同日对齐 D3 / §7.4 / 课表「代理」：主备代理、协议分工具、切备用须重启、网络报错入 log）
- 性质：改造合同 / skill 改善建议，供人工审核。 **本文不是 skill 正文。** 本次只改本文，不改 `~/.codex/skills/download-geo-assay`，不改正在跑的脚本，不重启队列。落地须你批准 §10 后再动手。
- 来源：
  1. 本项目三套 GEO（GSE102556 / GSE208338 / GSE53987）下载与转换
  2. 你提供的 `watchdog.log`（2026-07-18–07-23，另一项目 GSE213982 流水线；用来泛化 TLS / ENA 卡住 / 盲目重启，不是本 GSE 的进度表）

闸门正文只写可复用规则。具体 GSE/SRR 只放 §12 附录。

---

## 1. 已拍板


| #   | 议题                  | 决定                                                                   |
| --- | ------------------- | -------------------------------------------------------------------- |
| 1   | 子 skill 放置          | **只放在** `download-geo-assay` **包内**，不注册多个顶层 skill                    |
| 2   | sc 与 sn             | **共用一份** `subskills/assays/scrna/SKILL.md`                           |
| 3   | ATAC / ChIP / miRNA | **维持** `other-seq` 合集，默认 **只下载**，不默认 STAR/STARsolo                   |
| 4   | 用户说「改 NCBI」         | **必须 NGDC 文件 endpoint 探测失败**（并写入 `fallback_reason`）后才允许换源；口头指定不能跳过探测 |
| 5   | 进度 log 字段           | **暂不写入本方案**；你提供字段后再做阶段 D                                             |
| 6   | 主 SKILL 与文件树如何对齐    | **暂不选择**（见 §10）                                                      |


新增原则（本次完善，待你确认后写入 skill）：

- **所有需要人工选择的事项必须在第一次长下载开始前问完并写入决策表。** 下载中途不得因「数据类型不确定 / 要不要 Lite / 换不换源」停下来等人。缺选择 = 不得开队列。
- 运行中的 bash 脚本 **禁止热改**；改下载器后另开会话，或等当前样本退出。
- 进度快照与自动重启必须分开；自动重启有上限，达上限后停并等人。

---



## 2. 要解决的问题

当前 skill 虽有 `assay_capability.yaml`，实际仍是 **一份 SKILL.md + 一堆 references 同时进上下文**。一次任务会把芯片 CEL、bulk FASTQ、NGDC/ENA/NCBI、aria2/prefetch、STAR、tmux、watchdog 搅在一起。

中途停下来问人，会把已经跑了几小时的队列挂死（Lite 与 `.sra` 混淆、配额、热改脚本都发生过）。

目标：

1. **先分数据类型（assay），再分数据库（source）**
2. YAML 表驱动，一次只加载 **一个 assay 子 skill + 一个 source 子 skill**
3. **前置决策包**（§4）一次问完；闸门只检查「表里有没有答案」，不再现场发明选项
4. 错误按类处理：能自动恢复的不打扰人；不能恢复的停在边界并等人，不盲重启

---



## 3. 目标结构

对外仍只有一个 skill 名：`download-geo-assay`。

```text
download-geo-assay/
  SKILL.md                         # Router：分流、前置决策包、禁止项（短）
  assay_capability.yaml
  source_capability.yaml
  references/gates.md              # 闸门全文 + 可泛化错误课表
  references/human-decisions.md    # 下载前必须填完的选择清单
  subskills/assays/{bulk-rnaseq,scrna,microarray,other-seq}/SKILL.md
  subskills/sources/{ngdc,ena,ncbi-sra,geo-supplement}/SKILL.md
```

硬规则：

1. 未写入 `metadata/assay_routing.tsv` 与 `metadata/human_decisions.tsv` 前，禁止打开任何 `subskills/sources/`，也不得开始下载。
2. 一次只 Read **一个** assay 子 skill + **一个** source 子 skill。
3. 混合 GSE 拆成执行单元 `(workflow, modality)`：各自存储、tmux、日志。芯片不等 STAR index。
4. 未轮到的子 skill 当作不存在。
5. **禁止在正在执行该脚本的进程上改同一** `.sh`**。**

测序源默认顺序：**NGDC → ENA → NCBI**。换源必须有探测失败记录。芯片只走 `geo-supplement`。

NCBI 测序对象再分一层（前置选好优先级，运行时只执行，不再问）：

1. 作者提交文件（S3 `sra-pub-src-*` 上的 FASTQ/BAM 等；**src-1 与 src-2 都要探**，不能只探 `sra-pub-run-odp`）
2. ODP / 规范化完整 `.sra`（HEAD 必须 200，且不是 delete-marker）
3. 仅当人类在决策表里 **允许 Lite 作为末路** 时才接受 `.sralite`
4. ENA FASTQ（含 generated）：不得因「generated」标签直接否定；须按 **逐碱基 Phred 是否真实变化** 判定（§7.7）

---



## 4. 前置决策包（下载前一次问完）

缺任何一项，Router **停止**，不得进入 prefetch / CEL 下载。答案写入 `metadata/human_decisions.tsv`（按执行单元一行）。下载过程中只许执行，不许再弹出选择题。


| ID  | 问什么                                                                                            | 谁必须答        | 不允许的中途行为                      |
| --- | ---------------------------------------------------------------------------------------------- | ----------- | ----------------------------- |
| D1  | 每个 assay 的 raw 去留、转换产物                                                                         | 每个执行单元      | 下到一半才问 Mode A/B               |
| D2  | 项目临时占用上限 **以及** 系统用户配额是否 ≥ 该上限                                                                 | 全部          | 只改项目数字、不核对 `quota`            |
| D3  | 主 HTTP(S) 一条 + 备 HTTP(S) 一条；NCBI/ENA 走 HTTP(S)、国内源是否直连、**aria2 禁止 socks5 `all_proxy`**；切代理必须重启对应 tmux | 每源可以不同      | 队列跑着改 `proxy.env` 不重启；把 MD5/404/Lite 当代理故障去切备用 |
| D4  | 本机 FASTA/GTF/STAR/STARsolo/index：沿用或重建（含染色体名）                                                  | 仅需转换的测序     | 芯片为此暂停                        |
| D5  | 链特异性：unstranded / forward / reverse / **锁定为 unknown→先 unstranded，队列结束后再核对三列**                  | bulk        | 队列中途停下来改 stranded             |
| D6  | `sjdbOverhang` 算法：RunInfo `max(readLength)-1`，第一批 FASTQ 不符则 **先重建 index 再扩大队列**（这是计划内步骤，不是新选择） | bulk        | 用平台名猜 101 bp                  |
| D7  | 测序归档偏好：提交文件 → 完整 `.sra` →（可选）Lite → ENA FASTQ+质量检验                                             | 测序单元        | Lite 来了才问「能不能用」               |
| D8  | 若某 run **只有 Lite**：跳过该 run / 等完整对象 / 用 Lite / 走 ENA 并做质量检验后决定是否重比对                             | 测序单元        | 默认收下 Lite 当正式结果               |
| D9  | 预取超前量（建议 3 个转换单位）与「转换成功即释放」                                                                    | 不保留 raw 的单元 | 无上限预取把盘打满                     |
| D10 | 进度：只写快照 / 允许自动拉起；自动拉起上限（建议 3 次且必须有新完成单位）                                                       | 全部          | watchdog 在 pipeline 未建立时盲重启   |
| D11 | 正轨后是否脱钩 Agent                                                                                  | 全部          | 试跑 `EXIT:0` 当完成               |
| D12 | 主队列进行中，是否允许 **旁路** 对单个已完成样本用更好的源重转（另开 tmux，不热改主脚本）                                             | 测序          | 为单个 run 杀掉主队列                 |


「unknown」也必须写成锁定策略（例如 D5），不能把 unknown 留成「以后再说」。

---



## 5. YAML 分流（示意）

`assay_capability.yaml` 增加 `subskill`、`allowed_sources`、`gates`。`source_capability.yaml` 增加探测、代理提示、fallback。测序 NCBI 子 skill 必须实现：`sra-pub-src-1` **与** `sra-pub-src-2` 前缀探测、ODP HEAD、拒绝未授权 Lite。

用户指定「改 NCBI」：仍先 NGDC probe；失败原因属于允许集合才写 `fallback_reason`。

---



## 6. Router 关卡顺序

```text
脚手架 → 元数据 → detect_assay → assay_routing.tsv
  → 【停】填完 human_decisions.tsv（§4 全表）
  → 只打开当前 assay 子 skill（芯片跳过 D4–D8 中不适用项）
  → 只打开当前 source 子 skill（按已锁定优先级探测，不现场改优先级）
  → 试跑 / 第一批校验（计划内；不符则按已锁定规则重建 index，不再问新题）
  → 正轨后：剩余队列 + 快照 log；允许脱钩
  → 旁路重转仅当 D12=是，且另开 tmux
  → 报告 / 按转换单位释放后的终扫
```

---



## 7. 闸门（写入 `references/gates.md`）



### 7.1 正轨后再 tmux 脱钩

试跑 `EXIT:0` 不算数据集完成。正轨 = 源已锁定 + 第一批校验通过 + 跑的是剩余队列 + 临时占用能靠「转换单位释放」压在配额下。

#### 转换成功后释放

配额 = `temporary/` **任意时刻占用上限**（含预取缓存），不是 raw 总量预算。释放单位 = 转换并审计通过的单位。无转换产物不得选「不保留 raw」。终扫不能当唯一释放路径。预取超前量受 D9 约束。

须同时核对 **系统用户配额**（`quota`）。项目表写成 700 GiB 而系统 soft/hard 仍约 573/592 GiB 时，以系统配额为准，并在前置包 D2 拦下。

### 7.2 进度快照 ≠ 自动重启

- 快照 log：固定间隔，不重启进程。字段待你提供（阶段 D）。
- 自动拉起：仅当「工作 tmux 已死」且「未达重启上限」且「本轮有新的完成单位或明确可续传文件」。
- `watchdog.log` 所证：同一 `NEW_ERROR` 反复刷历史行 ≠ 新事故；`pipeline=missing` 连拉三次仍无新完成样本时必须 `ALERT` 并停手（你这份 log 在第三次后 withheld，这一条要保留）。
- 完成判据 = 产物文件 + 完成标记，不是重启次数。



### 7.3 提速分层

国内镜像要有文件 endpoint。可并行预取；谨慎并行解包；不要并行基因组定量。配额不够时并行会先打满盘。

### 7.4 代理拓扑（前置 D3）

决策表一次填齐，运行中只执行，不再问「换不换代理」。

1. **主一条、备一条**：都写成 HTTP(S) 地址（例 `http://host:port`）。主代理出现 **连接失败 / TLS eof / 代理认证（407）** 时改走备用；切备用必须 **重启该下载 tmux**，旧 session 会继续用旧环境。
2. **按工具锁协议**：NCBI / ENA 用 HTTP(S)；国内镜像（NGDC 等）按表决定是否直连、不走海外 VPN。**aria2 禁止** socks5 `all_proxy`（会直接解析失败，与有没有备用代理无关）。
3. **什么不算代理故障、不准切备用**：MD5 失败、404 / delete-marker、只有 Lite、配额满。这些走对应闸门，不换 IP。
4. **log 必须写明**：当前用的是主还是备、工具名（curl / aria2 / prefetch）、错误码（如 curl 35/56、HTTP 407）、是否已切换。禁止只写 `exit=1`。

### 7.5 本机参考（前置 D4）

GRC + GENCODE + 染色体名对齐。排除 10x index、RefSeq `NC_*` + GENCODE `chr*`。`versionGenome` 是 index 格式号。

### 7.6 链特异性与 overhang（前置 D5–D6）

不用平台名猜读长。unknown → 先 unstranded 是 **已锁定策略**，不是中途选择题。

### 7.7 归档对象与质量（前置 D7–D8）

运行时探测顺序（有文件才用，没有则下一步），**不再问人**：

1. `aws s3 ls` / HEAD：`s3://sra-pub-src-1/<SRR>/` 与 `s3://sra-pub-src-2/<SRR>/`（提交 FASTQ/BAM 等）
2. ODP 完整 `.sra`：`https://sra-pub-run-odp.s3.amazonaws.com/sra/<SRR>/<SRR>`，HEAD 必须 200，**404 + delete-marker 视为不存在**
3. `prefetch --type sra`；出现 `.sralite` 则删除 Lite，不把它当 `.sra`
4. 仅当 D8 允许：ENA FASTQ（含 generated）

ENA / 提交 FASTQ 用作正式输入前，先做隔离目录校验，**不覆盖**已有转换结果：

- 提供方 MD5（或记录 multipart ETag 不能当文件 MD5）
- read 数、paired 是否等 n、read length
- quality：对足够多碱基做 Phred 直方图

判定：

- 多个 Q 档（如 Q20–Q41）有实质质量、不是单一 Q → **真实逐碱基 quality**，可作首选原始输入；旧 Lite 结果改名为遗留目录，正式结果改用该 FASTQ，并写 `download_source`
- 几乎全是统一 Q30、reject 为 Q3、distinct Q 极少 → **与 Lite 无本质差别**，不重跑比对
- 不得因 ENA 标成 generated 就直接丢掉

旁路重转：主队列继续；另开 tmux；禁止热改主 `download_run.sh`。

### 7.8 热改与会话隔离

Bash 边跑边改同一文件，后续行号错位会出现 `syntax error near unexpected token`（`path` / `done` / `)` 都见过）。正确做法：改完 `bash -n`，**新** tmux 跑剩余队列；当前样本用的是旧 inode，等它退出。

试跑脚本、剩余队列、watchdog、旁路重转：**分文件、分 tmux 名、分 log**。

---



## 8. 错误课表（可泛化；写入 `references/gates.md` 的故障节）

格式：现象 → 本次如何处理 → 正确（以后 skill 应做的）。


| 类               | 现象                                                                   | 本次处理                          | 正确处理                                                                                                  |
| --------------- | -------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| 注意力             | 芯片与 RNA-seq、ENA 与 NCBI 同一上下文                                         | 事后拆开执行                        | 先分流；一次只开一个 assay + 一个 source                                                                          |
| 选择滞后            | 链特异性 / 参考 / 源 / Lite 在下载中才问                                          | 中途停、改代理、改 NCBI                | **§4 前置包**；unknown 也要锁成策略                                                                             |
| 代理              | socks5 `all_proxy`；中途 215→217                                        | 改 env；部分旧 tmux 仍用旧代理          | 前置 D3 + §7.4：主/备 HTTP(S) 各一条；国内源是否直连；aria2 禁用 socks5 `all_proxy`；仅连接/TLS/407 可切备用并重启对应 tmux；log 写清主或备、工具、错误码、是否已切换；MD5/404/Lite 不切代理 |
| 芯片入口            | NCBI FTP TLS/502                                                     | 改 GEO CGI                     | 芯片默认 GEO download CGI，FTP 失败不作为唯一入口                                                                   |
| GPL             | `annot.gz` 下架；`family.soft.gz` 极大                                    | 人上传 platform SOFT             | 禁止 family.soft；只拉 platform-only；缺失则 **下载前** 向人要文件/链接                                                  |
| 参考配对            | RefSeq `NC_*` vs GENCODE `chr*`；10x v44                              | 人要求重建 v47/M36                 | 前置盘点；配对失败不得 genomeGenerate                                                                            |
| overhang        | 用 HiSeq 猜 100                                                        | RunInfo→49/99，seqkit 复核       | 锁定算法；第一批不符则重建 index 再扩大（计划内）                                                                          |
| 源探测             | NGDC 无文件仍优先                                                          | 回退 ENA 再 NCBI                 | 探测文件 endpoint；写 `fallback_reason`                                                                     |
| ENA 完整性         | aria2 MD5 失败、TLS eof（本任务 + `watchdog.log`）                           | 改 NCBI Toolkit；隔离坏文件          | 不得拼接不同远端；换源；TLS 反复失败达上限则停并换源/换代理，不空转                                                                  |
| 试跑误判            | 2-run 脚本 `EXIT:0` 当成下完                                               | 人问「为何结束」后开剩余队列                | 试跑与全量分脚本；正轨定义写进闸门 1                                                                                   |
| 语法              | `case` 的 `)`；热改导致 `path`/`done`                                      | 修脚本并重启 continue               | `bash -n`；禁止热改正在跑的脚本                                                                                  |
| prefetch 锁      | 与 `download_run` 抢同一 SRR 目录                                          | 独立 `prefetch_cache/`          | 缓存目录与工作目录分离                                                                                           |
| 预取膨胀            | 超前量无上限，缓存 263 GB                                                     | 人允许后清空；成功转换即删该单位缓存；超前 ≤3      | D9；转换成功释放；系统配额打满时先删预取                                                                                 |
| 双配额             | 项目 500→700 GiB，系统仍 ~573 GiB                                          | `fasterq` Disk quota exceeded | D2 必须系统配额 ≥ 项目上限                                                                                      |
| 空 monitor       | tmux 里只有 `sleep`                                                     | 快照改写文件 / pane                 | 快照写 `monitor_latest.txt`；pane 要打印，不能只 sleep                                                           |
| watchdog 盲重启    | 本 GSE 11:40 `pipeline=missing` 连拉；`watchdog.log` 里同一 ERROR 循环后 ALERT | 人停监测、看 continue.log           | 历史 ERROR 不当新事故；3 次无新完成则停；快照 ≠ 重启                                                                      |
| Lite 当 SRA      | 只认 `.sra`，NCBI 给 `.sralite` 则 Terminal failure                       | 一度收下 Lite 跑完 STAR             | 探测 ODP/src；未授权则拒绝 Lite；D8 事先选好                                                                        |
| ODP 404         | 用户给的 odp URL 为 delete-marker                                         | 未下载 Lite；探 src-1/src-2        | 必须探 src-1 **和** src-2；404 不是「没有提交文件」                                                                  |
| 提交 FASTQ        | src-2 空、src-1 有原始 R1/R2                                              | 旁路下载并做质量检验                    | 正式源写成提交 FASTQ；Lite 结果改遗留目录；主队列不中断                                                                     |
| generated FASTQ | 标签像「不原始」                                                             | 用 Phred 直方图判定                 | 真实多档 Q → 可作首选；统一 Q30/Q3 → 不重比对                                                                        |
| 双 STAR          | 旁路重转与主队列同时 STAR                                                      | 未完成（脚本写入被打断）                  | D12；主队列正在 STAR 时旁路等待或降线程，避免抢内存                                                                        |


自动可做、不必问人：续传、`vdb-validate`、跳过已有产物、转换成功后删该单位 temporary、预取命中、HEAD 200 才拉 ODP。

必须停并等人：前置包缺项、系统配额不足、自动拉起达上限、源对象全部 404 且 D8 未覆盖、GPL 注释入口失效且无人提供 SOFT。

---



## 9. 各子 skill 注意力边界


| 文件                          | 只装什么                         | 禁止装什么                       |
| --------------------------- | ---------------------------- | --------------------------- |
| Router                      | 分流、前置决策包、一次只开两份              | fasterq 参数、CEL CGI、STAR 命令行 |
| `bulk-rnaseq`               | GeneCounts、index、D5–D8、按单位释放 | CEL、STARsolo 几何             |
| `scrna`                     | STARsolo / 10x / 可选 velocity | bulk GeneCounts             |
| `microarray`                | CEL/IDAT、GPL、禁止 family.soft  | NGDC、STAR                   |
| `other-seq`                 | 只下载；无产物则禁止「不保留 raw」          | 默认 STAR/STARsolo            |
| `ngdc` / `ena` / `ncbi-sra` | 探测、下载器、代理、归档层级、质量判定          | 芯片 CGI                      |
| `geo-supplement`            | GEO CGI、platform SOFT        | `probe_ngdc`、`download_run` |


---



## 10. 实施阶段


| 阶段            | 内容                                                  | 不做       |
| ------------- | --------------------------------------------------- | -------- |
| **A. 合同**     | YAML、Router、`gates.md`、`human-decisions.md`、子 skill | 不改正在跑的队列 |
| **B. 对齐**     | detect 输出带 `subskill`；修正不存在的脚本名                     | 同上       |
| **C. 闸门**     | 未填 `human_decisions.tsv` 不得 `download_run`；按转换单位删除  | —        |
| **D. 进度 log** | 等你给字段；与 watchdog 重启拆开                               | 不默认盲重启   |


第 6 条未选择：方案 I 一次写齐 vs 方案 II 先收回主 SKILL。选定前 **不修改 skill 文件**。

---



## 11. 明确不做

- 不把子 skill 做成多个顶层 skill
- 不把 ATAC 做成分析流水线；microarray 不做 RMA
- 不下载 series matrix / family.soft
- 不在 other-seq 无产物时「不保留 raw」
- 不把 `watchdog.log` 的完成数当成当前 GSE102556 进度（那是另一项目）
- 不中断用户未要求停止的主队列
- 选定 §10 第 6 条之前不改 skill 包

---



## 12. 附录：本次实例（不写进闸门原文）

用来核对泛化是否覆盖。


| 实例                                                                                                                         | 对应条款           |
| -------------------------------------------------------------------------------------------------------------------------- | -------------- |
| GSE102556 Mode B、配额 500→700 GiB、系统仍 ~573 GiB，prefetch 263 GB 顶满                                                            | §7.1 D2 D9     |
| 人 50 bp / 鼠 100 bp → overhang 49/99                                                                                        | D6             |
| 链特异性 unknown → 先 unstranded                                                                                                | D5             |
| NGDC 无文件 → ENA MD5 → NCBI Toolkit                                                                                          | 源探测            |
| 代理 215→217；aria2 + socks5                                                                                                  | D3 §7.4        |
| 不用 10x v44；不用 RefSeq FASTA + GENCODE GTF                                                                                   | D4             |
| GPL family.soft；annot 下架后人传 SOFT                                                                                           | 芯片短规则          |
| `first_batch` 2 run 正常结束 ≠ 341 GSM                                                                                         | §7.1           |
| GSE102556 `watchdog.log` 11:40 盲重启                                                                                         | §7.2           |
| 项目根 `watchdog.log`（GSE213982）：TLS eof、ENA 卡住、`all_proxy` 解析失败、`syntax error`、`pipeline=missing` 三次后 ALERT                  | §7.2 §7.4 §7.8 |
| `download_run` 热改导致 `unexpected token path`                                                                                | §7.8           |
| SRR5961855 `.sralite`；ODP 404 delete-marker；`sra-pub-src-2` 空、`src-1` 有 BA89_57 R1/R2；Phred 多档 Q41… → 应作正式输入，Lite STAR 改遗留 | §7.7           |
| 两芯片 CEL 不等人类 STAR                                                                                                          | 混合 GSE 拆单元     |


