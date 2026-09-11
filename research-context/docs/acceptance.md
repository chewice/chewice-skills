# Acceptance

## 科研合同

- 工作围绕当前研究问题展开，并能说明为什么做、什么观察会改变判断、下一步是什么。
- 遵循第一性原理与 Occam's razor；解释力与证据相当时优先额外假设更少的解释。
- 观察、解释与人的决定分别表达；null、negative、contradictory 与 inconclusive
  evidence 不被丢弃。
- 技术检查通过不等于科学结论成立。
- 不默认产出正式 Report。

## 上下文与恢复

- 项目只维护一份 `context.md`；未指定时约定入口为已有的 `doc/context.md`。
- 入口缺失时不自动创建文件或目录；能开展的工作继续，并标明尚未持久化的状态。
- 摘要不能替代被引用证据；冲突按输入/输出、解释、人的决定分类处理。
- Main Agent 维护摘要；Sub-agent 不直接编辑共享摘要。
- 没有 Sub-agent 时 Main Agent 直接开展同样工作。

## 自动化与安全

- 不 scaffold、不分配 Q-ID/A-ID、不生成 BRIEF/RESULT 模板。
- 覆盖、删除、Git/外部写入仍需 Human 明确决定。
- 用户已授权任务内，维护已有摘要无需二次确认。

## 仓库完成条件

- 根 `AGENTS.md` 的 `Language`、`Environment` 与总原则受逐字回归测试保护。
- 可安装 Skill 仅为 `research-context`。
- 仓库只有根级 Pixi workspace；无嵌套 lock 或被跟踪的 `.pixi/`。
- Skill 的 Codex/Agents discovery 路径可解析到当前源码。
- `pixi run lint`、`pixi run test`、`pixi run smoke` 与 `pixi run validate-skill` 全部通过。
