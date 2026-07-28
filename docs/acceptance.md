# Acceptance

- Release `0.5.0`；manifest 与 payload schema 保持 `0.3.0`。
- CLI modes、dry-run/apply、adopt preservation、handoff、evidence 和 Notion
  contracts 保持通过测试。
- `root_workspace` 检测两种根 manifest；嵌套 workspace、lock、`.pixi/` 失败，
  package-only manifest 服从配置。
- 根 `pixi.lock` 被 Git 跟踪；根 `.pixi/` 可缺失且不得被跟踪。
- Skill metadata、bounded scan、idempotency、安装 symlink 和 boundary evals
  全部通过自动验证。
- 分析类 profile 创建 `explore/`、`archive/`、`pipeline/`；task name 使用唯一
  `P<order>-<core>-<summary>`，且未获 human direction approval 不得创建。
- 根目录 `QUESTIONS.md` 由 human 维护、Agent 默认只读；一次只允许处理一个
  current question，并最多保留一个未归档、未取消的 explore task。
- explore task 生成 narrative `README.md`，code 默认按执行顺序线性组织，保留
  intermediate results；单次逻辑不强制函数化，模块化推迟到 pipeline。
- 每个 explore 与 pipeline code file 使用文件顶部中文 outline 和对应编号中文
  section/cell headings；按 workflow 语义切分，code identifiers 保持英文。
- archive 保留 explore source、自动追加 `vNNN`、拒绝覆盖并可 hash verify；
  pipeline 只接受获批 snapshot，release 前拒绝 runtime 依赖 explore/archive。
