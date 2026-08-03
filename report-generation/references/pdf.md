# PDF

PDF 是可选交付物，不是本版本的默认能力。HTML 始终是规范渲染输入。

当 Human 请求 PDF 时，先运行 capability check。只有根 Pixi workspace 已显式配置并锁定受支持 renderer、中文字体和跨平台验证任务后，才允许从已验证 HTML 生成 `reports/<Q-ID>/report.pdf`。

当前版本不捆绑 PDF renderer。`--format pdf` 必须返回明确的 unavailable 错误，不得创建空文件、伪 PDF 或把浏览器打印成功当作内容验证。不得临时安装系统包、调用未锁定的外部服务或手动修改 `pixi.lock`。

未来实现需要验证：文件存在且具有 PDF header、页数大于零、中文字体可用、链接与图片可解析、输出路径正确，并记录 renderer/version 与来源 HTML hash。
