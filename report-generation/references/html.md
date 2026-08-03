# HTML 报告

使用根 workspace 执行：

```bash
pixi run generate-report --project /path/to/project \
  --question Q-001 --artifact A-001
pixi run generate-report --project /path/to/project \
  --question Q-001 --artifact A-001 --apply
```

默认输出到 `reports/<Q-ID>/report.html`。先验证 Question 索引、BRIEF 的 Human review，以及每个指定 RESULT 的“审核通过”状态；不自动选择 Artifact。

报告按问题与范围、证据和方案、审核通过的结果、限制、验证、Human review 与可复现来源组织。原始 BRIEF/RESULT 保持不变。Markdown raw HTML 禁用；HTTPS citation 可保留，远程图片、危险 URL、缺失资源和项目外路径必须拒绝。显式引用的本地资源复制到报告 `assets/`，避免报告依赖 Explore 临时路径。

默认 dry-run 只显示输入、输出与资源计划。`--apply` 后写入 HTML 和 build metadata；输出存在时停止，只有 Human 明确提供 `--overwrite` 才重建。写入后立即运行报告校验。
