# Acceptance

- Release `0.6.0`；新 manifest schema `0.4.0`，只读兼容 legacy `0.3.0`。
- 单一 Research 模板；不存在 profile 或 Notion CLI。
- scaffold/adopt 非破坏、mutation dry-run、atomic apply、无隐式 Git 操作。
- 四个根控制文件遵守 human/Agent/CLI ownership。
- 生成的 `AGENTS.md` 强制先读四个根控制文件与当前 task，并明确
  QUESTIONS、handoff 和 superpowers 边界。
- 一次只有一个 unresolved explore task；task 名和本地 artifact layout 合法。
- `run` 完整记录输入前后、输出、命令、日志、Git 与 Pixi hashes；violation 阻止 archive。
- archive 不可变且可独立验证；pipeline runtime 不依赖 explore/archive。
- analysis scripts 保持线性、可读、中文 outline，不含 HTML/CSS/rendering。
- Markdown API 与 CLI 生成确定性中文 HTML，检查章节、资源、链接和 build manifest。
- lint、unit、smoke、Skill validator、installation symlink 与 forward tests 全部通过。
