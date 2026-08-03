# Templates 与 CSS

默认模板位于 `assets/templates/report.html`，默认样式位于 `assets/css/report.css`。保持语义化 HTML、`lang="zh-CN"`、UTF-8、响应式宽度和可打印样式。

模板只负责表达，不包含研究结论。不得在模板中读取项目文件、运行分析或改变审核状态。所有动态内容先转义；Markdown renderer 禁止 raw HTML。

修改模板或 CSS 时同时检查：

- 标题、来源与审核提示清晰；
- heading 层级连续；
- 表格与图片在窄屏和打印模式可读；
- 不依赖网络字体、远程脚本或外部 CSS；
- assets 使用报告目录内的相对路径。

Human 自定义模板必须明确指定，不得自动从 `docs/template/` 发现或同步。
