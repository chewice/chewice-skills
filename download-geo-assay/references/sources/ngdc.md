# NGDC/GSA

- 区分 GSA 作者提交对象与 NGDC 的 INSDC/SRA 镜像对象；transport 都可为 NGDC HTTPS，但 provenance 不同。
- 探测需记录 endpoint、HTTP 状态、content length/实际大小、校验信息和时间。只有有效、非空且类型合理的对象才能入选。
- 用户明确指定 ENA/NCBI 等来源时，不得用 NGDC 默认偏好覆盖。`auto` 模式下，有效 NGDC endpoint 可因传输稳定性优先于同类对象的其他 endpoint。
- 先按 object class 的保真度与下游兼容性选择，再在同类对象中比较 endpoint；不能因镜像更快而降级为 Lite 或 processed object。
- DNS、TLS、403、404、超时、校验失败分别记录，不把所有失败压成“NGDC 不可用”。
