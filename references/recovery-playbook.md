# 传输中断与恢复手册

## 传输不变量

出现最终文件名，表示所有适用的不变量均已通过：

1. 与发布的字节数一致。
2. 与发布的 MD5/checksum 一致。
3. FASTQ 通过 `gzip -t`，或 SRA 通过 `vdb-validate`。
4. 转换已原子完成。
5. 配对记录数与 expected spots 一致。

进行中的传输写入 `.part`。使用 aria2 时保留 `.part.aria2`，以便信任已完成的分片。缺少 piece metadata 的 partial 文件不能安全续传。

## 常见故障

### TLS/网络中断

- 保留 `.part` 和 `.part.aria2`。
- 仅重试受影响的分片。
- 不要向未跟踪的 partial 追加新数据流。
- 连续三次出现相同故障后停止，并将该线路记录为 unreachable。

### 大小符合预期但 checksum 错误

- 将文件视为损坏。
- 删除 `.part` 及其控制文件。
- 从第 0 字节重新下载。
- 不得仅凭大小一致就提升为最终文件。

### SRA endpoint 不提供 checksum

- 要求稳定且大于零的 Content-Length。
- 原子化下载。
- 要求通过 `vdb-validate` 内部 MD5/一致性检查。
- 要求转换后的 read 数与提供方 `expected_spots` 一致。

### 假性 read count 不一致

- 解析 TSV 前统一 CRLF。
- 对空 tab 字段不要使用会折叠空白的 shell 解析方式。
- 运行 sample 前校验数值字段。
- 将 expected、R1 和 R2 规范为整数后比较。

### R1/R2/I1/I2 角色不明确

- 检查提交文件名、run metadata、read 长度和 chemistry。
- 不能跨平台假设 `_1` 必然是 barcode read 或 biological read。
- technical reads 必须保持分离。
- read 角色仍不明确时，预检必须失败。

### 多 run 或多 lane sample

- 独立校验每个 run。
- 下载阶段保持文件分离。
- 仅在调用分析时按 GSM 对 run 分组。
- 在最终 provenance 中保留参与分析的 SRR 列表。

### 运行期间修改活动脚本

- 干净停止受影响任务。
- 运行 `bash -n` 或相应的语法检查器。
- 从已校验 checkpoint 重新启动。
- 不得热修改活动 Bash 进程之后可能读取的 shell 脚本。

## 清理关卡

仅当满足以下条件时删除源文件：

- 每个预期 run 都有通过校验的 download manifest 记录；
- 用户要求的最终 artifact 存在并通过直接审计；
- 没有活动进程正在使用 `.part`、`.aria2` 或 `.tmp`；
- 清理行为与用户要求的最终产品一致。
