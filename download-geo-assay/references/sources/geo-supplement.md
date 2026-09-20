# GEO supplementary 与平台元数据

- sequencing raw、CEL、IDAT 走 GEO supplementary 时，验证下载内容不是 HTML/错误页，并记录文件名、大小、校验和与 GSM/GPL 归属。
- 不下载 series matrix 或 logcounts 作为本 Skill 的原始输入。
- GPL/platform 元数据优先最小官方端点：GPL self/full、platform-only MINiML/SOFT 或精确 supplementary；失败后回退官方 family SOFT/MINiML 并提取目标平台。
- fallback 需要记录首选 endpoint 的失败证据和实际采用的官方 endpoint。一次大文件故障不是永久禁用 family 文件的理由。
- HEAD、GET、GPL fallback 统一使用指定代理；代理失败不直连，凭据不得进入 manifest、report 或日志。
- 来源对象留在 staging，响应长度、提供方摘要、完整 gzip/归档读取均通过后才发布。裸 CEL/IDAT 缺少提供方摘要时记 `UNVERIFIED`，不能只靠本地 MD5 写 PASS。
- 续传绑定 ETag/Last-Modified、最终 URL 与总长度，严格验证 Content-Range。远端忽略 Range 时重写 staging，不拼接。
- 解包前拒绝路径越界、链接和同名目标冲突，预留展开空间；按 GSM 持久化完成记录，发布 journal 保留可恢复事务。旧 raw 和旧 PASS 不被失败尝试覆盖。

GPL 配置 `platform_unknown_size_limit_bytes` 默认 8 MiB：仅用于无 Content-Length 的响应，在预留有界空间后接收；完整平台结构仍须验证。已知长度的 family 按项目预算接收，不受这个未知长度上限限制。可显式设置 `platform_max_download_bytes` 限制所有平台传输，`platform_max_uncompressed_bytes` 默认 2 GiB 限制平台解码；超限保留失败与 fallback 证据，不发布残缺文本。
