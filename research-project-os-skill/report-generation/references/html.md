# HTML 报告

使用根 workspace 执行：

```bash
pixi run generate-report --project /path/to/project \
  --question Q-001
pixi run generate-report --project /path/to/project \
  --question Q-001 --apply
```

默认输出到 `reports/<Q-ID>/report.html`。唯一合格 Artifact 自动选择；存在多个合格候选时用一个或多个 `--artifact A-NNN` 明确报告范围。

报告按设计边界、Claim-Evidence 综合、Observed Evidence、Inference/Qualified Claims、Uncertainty/Applicability、Next Decisive Test 和简洁 provenance 组织，不整篇复制 BRIEF/RESULT。Markdown raw HTML 禁用；HTTPS citation 可保留，远程图片、危险 URL、缺失资源和项目外路径拒绝。显式引用的本地资源复制到报告 `assets/`。

默认 dry-run 只显示输入、输出与资源计划。`--apply` 后写入 HTML 和 build metadata；输出存在时停止，只有 Human 明确提供 `--overwrite` 才重建。写入后立即运行报告校验。
