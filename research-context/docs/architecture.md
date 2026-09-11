# Architecture

本 Skill 在用户已有项目中维护一份可恢复的 `context.md`，并规范 Main Agent 与
Sub-agent 的交接。目录、编号和记录模板不进入本框架；具体分析方法和 runtime
也不进入本框架。

工作环为：明确问题 → 按需读取 → 执行与核验 → 理解观察 → 更新上下文。
委派、方案比较和请求人的决定只在需要时加入，不是固定 Stage Gate。

遵循第一性原理与 Occam's razor：先明确科学问题、数据生成过程、比较对象与推断
单位，再选择足以改变判断的最小分析。

## Source of truth

`context.md` 是压缩后的当前状态，不是证据数据库。实际依赖某个结果时，读取被
引用的产物与说明。详细设计、分析过程与证据由项目已有文件承载。

默认入口是用户指定的路径；未指定时为已有的 `doc/context.md`。入口缺失时不自动
创建。Main Agent 统一维护该摘要；Sub-agent 只返回建议更新项。

## Skills 与实现边界

```text
research-context
├── SKILL.md
├── references/{context,delegation,decisions}.md
├── agents/openai.yaml
└── evals/evals.json
```

具体分析代码交给 `scripting-style`，Pixi 环境建设交给 `pixi-environment-builder`。
本仓库不包含报告生成 Skill；不默认产出正式 Report。

## 安全

- 安装脚本默认 dry-run；`--apply` 才写入 discovery links。
- 不自动创建或覆盖用户项目文件。
- 技术检查通过不等于科学结论成立；人的决定不能替代科学依据。
