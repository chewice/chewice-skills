# Reporting

report authoring 与 scientific computation 必须分离。analysis scripts 只产生 tables
和 figures；叙述以 Markdown 语法传给共享 Python API 或 `report-build` CLI。默认只写出
HTML 与 `.build.yaml`，不额外保存 Markdown。只有 human 明确要求 Markdown，或需要保留
可编辑 source 时，才使用持久 `.md` 文件模式。

Python API 是唯一实现，仅供 harness automation 与 tests 复用；analysis scripts
不得 import。若 package 未安装到当前 environment，通过已解析的 `SKILL_ROOT`
显式设置 `PYTHONPATH` 后运行 harness automation：

```bash
PYTHONPATH="$SKILL_ROOT" pixi run --locked \
  --manifest-path "$SKILL_WORKSPACE/pixi.toml" python build_harness_report.py
```

Python 调用：

```python
from pathlib import Path

from research_project_os.reporting import (
    ReportBuild,
    ReportKind,
    build_report_text,
    validate_report,
)

result: ReportBuild = build_report_text(
    source_text=report_markdown,
    source_base=Path("explore/P0-QC-example"),
    output=Path("explore/P0-QC-example/report.html"),
    project_root=project_root,
    kind=ReportKind.EXPLORE,
    asset_mode="embed",
)
```

CLI 默认从 stdin 接收 Markdown，`--source-base` 是本地图片和链接的解析基准：

```text
rpos report-build --stdin --source-base explore/P0-QC-example \
  --output explore/P0-QC-example/report.html --kind explore [--apply]
rpos report-build --stdin --source-base reports \
  --output reports/final.html --kind release [--apply]
```

先运行一次不带 `--apply` 的 dry-run，并向 stdin 提供完全相同的内容；确认后再加
`--apply`。若明确需要 Markdown 产物，先保存 `.md`，再使用兼容模式：

```text
rpos report-build --source explore/P0-QC-example/report.md \
  --output explore/P0-QC-example/report.html --kind explore [--apply]
```

Markdown frontmatter 必须包含：

```yaml
schema_version: "1.0.0"
kind: explore | release
language: zh-CN
title: "中文标题"
task: "P0-QC-example"       # explore
snapshots: ["...@v001"]    # release
run_receipts: ["runs/RUN-.../receipt.yaml"]
```

Explore 固定章节为 `研究问题`、`输入与方法`、`结果`、`限制`、
`结论与下一问题`、`可复现信息`。Release 固定章节为 `项目目的`、
`输入与方法`、`主要结果`、`限制`、`结论`、`可复现信息`。可以在核心章节之间
增加领域章节，但不得删除核心章节。

renderer 使用 `markdown-it-py` 并关闭 raw HTML。默认嵌入 bundled CSS 与本地
images。拒绝 `file://`、绝对本地路径、path traversal、symlink、缺失资源、
executable URL schemes 和 remote images；普通 HTTPS citations 可以保留为 link。
非图片资源使用经过验证的 project-relative link，并进入 build manifest。

输出必须是 deterministic、UTF-8、`lang="zh-CN"` 的 semantic HTML，并包含
print styles。HTML 与 `.build.yaml` 使用 atomic write。manifest 记录 renderer 与
schema version、source/output/assets SHA-256、相关 run receipts、Git commit 与根 Pixi
lock hash。inline build 会把准确的 Markdown 原文以 base64 编码内嵌在 HTML 的隐藏
`template` 中，并在 manifest 记录 source metadata、heading contract、source hash 与
completeness result，因此不额外落盘 `.md` 也能恢复原文并完成 archive/release 审计。release 只有在
source contract 无 placeholder、resources hashes 仍匹配、pipeline sources 验证通过且
正式报告位于 `reports/` 时才有效。
