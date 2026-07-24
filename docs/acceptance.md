# Acceptance

- Release `0.3.2`；manifest 与 payload schema 保持 `0.3.0`。
- CLI modes、dry-run/apply、adopt preservation、handoff、evidence 和 Notion
  contracts 保持通过测试。
- `root_workspace` 检测两种根 manifest；嵌套 workspace、lock、`.pixi/` 失败，
  package-only manifest 服从配置。
- 根 `pixi.lock` 被 Git 跟踪；根 `.pixi/` 可缺失且不得被跟踪。
- Skill metadata、bounded scan、idempotency、安装 symlink 和 boundary evals
  全部通过自动验证。
