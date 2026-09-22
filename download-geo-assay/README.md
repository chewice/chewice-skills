# download-geo-assay

## 用途

面向 GEO/SRA/ENA/NGDC 公共组学原始数据的获取与交付。按 assay 和来源对象分流，以 SRR 为下载单元、GSM/文库为转换与 raw 释放单元，在有限存储下执行：

```text
下载并校验 → 记录输入指纹 → 转换 → 审计 → 发布开放格式样本包 → 按授权释放 raw
```

支持 bulk RNA-seq 的基因计数、sc/snRNA-seq 的开放格式矩阵，以及 FASTQ/SRA、CEL/IDAT 原始文件获取。ATAC-seq、ChIP-seq、miRNA-seq 和默认芯片路径只获取、校验 raw。不负责 GEO series matrix/logcounts，也不执行 DESeq2、RMA、Seurat/Scanpy、GO/KEGG 或 ATAC/ChIP 下游分析。

## 运行必需依赖

执行前需要可加载本目录 [SKILL.md](SKILL.md) 的 Agent、可写的独立下载项目目录，以及足够容纳下载、展开和转换峰值的磁盘空间。仅阅读技能说明不需要安装分析软件。

| 使用范围 | 必需依赖或输入 |
|---|---|
| 随附脚本的运行平台 | Linux x86_64，或相应的 WSL Linux 环境；脚本使用 Bash、`flock`、POSIX 文件锁和常用 GNU 工具。当前 scaffold 的 Pixi 平台为 `linux-64` |
| 项目环境与路由 | Pixi；生成的环境固定 Python `>=3.12,<3.13`；PyYAML 用于读取 assay/source 能力表 |
| 产物审计、发布与 raw 释放 | NumPy、SciPy；审计脚本直接导入它们，执行审计前必须可用 |
| 外网元数据、探测与下载 | 用户指定的可用 HTTP(S) 代理；通过 `GEO_SRA_PROXY_ENV`、项目 `proxy_env_file` 或已有代理环境变量提供。代理失败时暂停，不能自动直连 |
| 测序文件的 HTTP 传输 | `curl`、`aria2c`（Pixi 包名 `aria2`）；压缩使用 `pigz`，缺少时回退 `gzip` |
| NCBI SRA 路径 | SRA Toolkit（`prefetch`、`vdb-validate`、需要 FASTQ 时的 `fasterq-dump`）；ODP 精确对象查询和 S3 回退使用 AWS CLI |
| bulk / sc/snRNA 矩阵转换 | STAR / STARsolo、匹配的参考 FASTA/GTF/index；单细胞还需明确 read geometry 和适用的 barcode whitelist；项目自行准备并审核逐 GSM 转换脚本 |
| 特定功能 | BAM 校验需 `samtools`；启用 FASTQ 质控需 FastQC，汇总质控需 MultiQC；长期终端会话可使用 `tmux` |

[scaffold_project.py](scripts/scaffold_project.py) 会在下载项目内生成 `pixi.toml`，包含以上工具以及 `seqkit`、`h5py`、`loompy` 等预置包。预置包不代表所有路径都使用它们；正式开放格式交付不要求 Seurat、AnnData 或 loom，也没有通用必需的 R 包。具体转换所需的额外依赖按项目确认，环境安装和配置变更先说明再执行。

## 如何使用

将本目录作为 skill 加载后，用自然语言给出 accession、输出目录、来源偏好、代理配置位置、存储预算和目标产物。例如：

> 使用 $download-geo-assay，为 GSE123456 准备原始数据下载。输出到指定数据目录，项目预算 500 GiB，代理读取我提供的环境文件。先判定 assay、来源和必需依赖，保留 raw；确认配置后先跑一个 GSM 的 pilot。

需要滚动释放 raw 时，明确提出“标准产物审计与发布通过后，允许删除对应 GSM 的 raw”；尚未决定的目标或策略保持 `pending`。Lite 必须单独明确允许。

1. 按 [SKILL.md](SKILL.md) 读取必需规则，再只加载匹配的 assay/source 文档。运行时读取 [assay_capability.yaml](assay_capability.yaml) 和 [source_capability.yaml](source_capability.yaml)。
2. 使用 scaffold 建立项目，补齐样本、run、来源与 assay 路由元数据，确认代理、存储策略和参考对象。用户指定来源优先，自动模式才应用镜像偏好。
3. 在确认环境变更后锁定项目依赖。请求矩阵时，先准备 `convert_gsm.sh` 等项目转换脚本；此文件不会由 skill 自动生成，缺少时队列在下载前停止。
4. 先运行 pilot 并检查实际产物，再执行剩余队列。测序入口见 [queue-execution.md](references/queue-execution.md)；CEL/IDAT 使用 [download_geo_supplement.py](scripts/download_geo_supplement.py)，不套用测序队列。
5. 核对全部预期 GSM 的状态、下载证据、转换产物和存储策略，更新中文 `reports/report.html`。pilot 完成或队列退出 0 不代表全集完成。

从本 skill 根目录可查看脚本参数；下列命令不下载数据、不安装环境：

```bash
python3 scripts/scaffold_project.py --help
```

确认输出目录后，创建项目的示例为：

```bash
python3 scripts/scaffold_project.py --gse GSE123456 \
  --output-root /path/to/data --max-project-gib 500
```

scaffold 在 `GEO/GSE123456/` 下生成项目骨架和环境定义，目标产物与 raw 策略默认仍为 `pending`。后续操作在生成的项目内进行。

## 交付与运行边界

正式交付为按样本独立的 MEX/TSV、JSON 和 SHA256 清单，详见 [open-delivery.md](references/open-delivery.md)。原始数据保留模式同时保留已获取的 raw；滚动释放模式只在前置授权、完整成员 run、转换审计与正式包发布全部满足后释放 raw。raw-only assay 或未指定可审计产物的 CEL/IDAT 不具备删除资格。

默认两个下载 worker、每文件四个连接、一个转换 worker；SRA 展开、压缩和 assay 转换共用转换槽位。软件存储预算配合运行中检查，不等于文件系统硬配额。watchdog 默认不启动、不自动重启；可选 NCBI 预取默认关闭，上限为 3 个 run。中断恢复先复用有完整性证据的 cache，保留不完整文件和持久重试记录，详见 [recovery-playbook.md](references/recovery-playbook.md)。

技能更新只用于新建项目；不会自动替换现有项目已复制的脚本，也不热改活动队列。
