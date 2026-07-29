# Harness

长期保留四个根控制文件：

| File | Owner | Purpose |
| --- | --- | --- |
| `AGENTS.md` | repository | 稳定规则 |
| `QUESTIONS.md` | human | 项目目的、I/O 限制、FAQ 与问题路线 |
| `CURRENT_HANDOFF.md` | Agent | 当前状态、限制与恢复入口 |
| `project_manifest.yaml` | CLI | machine paths 与 policy |

Agent 与 CLI 不得修改 `QUESTIONS.md`。每次替换 handoff 时归档旧版本。`start`
只组装四个控制文件、当前 task metadata 与 README；没有 task-specific 理由时，
不加载旧报告、旧 receipts 或 archive snapshots。

先运行 `inspect`，再 dry-run `init` 或 `adopt`。接管已有项目时保留现有 paths、
data、Git history、README、instructions、questions、handoff、manifest 和 ignore
rules。使用 atomic writes，apply 前重新验证 source，拒绝隐式 overwrite。
legacy files 只作为 unused warning 保留，不自动删除。

只允许一个根级 `pixi.toml` workspace 或启用 Pixi 的根 `pyproject.toml`，以及
一个受 Git 跟踪的根 `pixi.lock`；根 `.pixi/` 必须被 ignore。拒绝嵌套
workspace、lock 和 `.pixi/`。package-only manifests 可以存在，但不得拥有自己的
lock 或 environment。`inspect` 与 `audit` 不求解或迁移 dependencies。

执行分析时使用：

```text
rpos run --input <path>... --output <task-relative-path>... \
  [--cwd <project-relative-path>] [--apply] -- <command>...
```

对每个声明文件及声明目录中的所有 regular files，在执行前后计算完整 SHA-256；
拒绝 symlink。task-local receipt 保存完整 stdout/stderr、exit code、cwd、Git
status、根 Pixi hashes 和 output hashes。输入改变、命令失败、输出缺失或输出越界
均是 violation；即使命令无法启动，也要保存失败 receipt。

详细证据只保留在 task receipts 与不可变 manifests。根
`work/audit/lifecycle.jsonl` 只保存精简 append-only events。不得自动 stage、
commit、push、修改 source data、暴露 credentials 或向外部系统同步。

生成的 `AGENTS.md` 要求遵循第一性原理。说明和 handoff 默认中文，专业术语与
machine values 保持原样。遵守：
`You may use superpowers, but do not write any spec or plan.`，且 superpowers
不得绕过 human ownership、approval、dry-run、audited execution 或安全限制。
