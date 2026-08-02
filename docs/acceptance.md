# Acceptance

- Release `0.7.1`；manifest schema `0.4.0`，只读兼容 legacy manifest `0.3.0`
  与 split-layout `QUESTIONS.md`。
- 单一 Research 模板；不存在 profile 或 Notion CLI。
- scaffold/adopt 非破坏、mutation dry-run、atomic apply、无隐式 Git 操作。
- 四个根控制文件遵守 human/Agent/CLI ownership。
- `QUESTIONS.md` 每个 Q-ID 只有一个固定 block；五种状态合法、current 唯一、answered
  必须选择合法 review decision 并包含 review date、compact reviewed outcome 与
  evidence；其他状态—审核组合按模板固定选项校验，legacy split layout 只读兼容。
- 新 scaffold 的 `QUESTIONS.md` 在 Project purpose 前提供 Filling guide，解释填写顺序、
  每种 Status、每种 Review decision 与 review 字段用途。
- 生成的 `AGENTS.md` 强制先读四个根控制文件与当前 task，要求遵循第一性原理，并明确
  QUESTIONS、handoff 和 superpowers 边界。
- 一次只有一个 unresolved explore task；task 名和本地 artifact layout 合法。
- `run` 完整记录输入前后、输出、命令、日志、Git 与 Pixi hashes；violation 阻止 archive。
- archive 不可变且可独立验证；pipeline runtime 不依赖 explore/archive。
- analysis scripts 优先减少函数封装和工程化代码，保持线性、可读、中文 outline，
  不含 HTML/CSS/rendering。
- inline Markdown API 与 CLI 默认只生成确定性中文 HTML 和 build manifest；显式 source
  模式才保留 Markdown，并继续检查章节、资源与链接。
- lint、unit、smoke、Skill validator、installation symlink 与 forward tests 全部通过。
