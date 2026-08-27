# GEO supplementary 与平台元数据

- sequencing raw、CEL、IDAT 走 GEO supplementary 时，验证下载内容不是 HTML/错误页，并记录文件名、大小、校验和与 GSM/GPL 归属。
- 不下载 series matrix 或 logcounts 作为本 Skill 的原始输入。
- GPL/platform 元数据优先最小官方端点：GPL self/full、platform-only MINiML/SOFT 或精确 supplementary；失败后回退官方 family SOFT/MINiML 并提取目标平台。
- fallback 需要记录首选 endpoint 的失败证据和实际采用的官方 endpoint。一次大文件故障不是永久禁用 family 文件的理由。
- 代理仅在直连不可用且已配置时使用；凭据不得进入 manifest、report 或日志。
