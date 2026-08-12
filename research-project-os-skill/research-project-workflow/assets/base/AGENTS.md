# Repository Instructions

## Language

- 面向 human 的说明默认使用中文。 
- 专业术语、code、paths、commands、IDs 和 machine-readable values 等agent方便识别的内容保持英文。

## Reasoning

- 遵循第一性原理、奥卡姆剃刀原理

## Superpowers

- You may use superpowers, but do not write any spec or plan.

## Research workflow

- 以 `Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test` 组织科研分析。
- 根 `CURRENT_HANDOFF.md` 是 project router；只读取 Context Map 声明的局部 Handoff，不递归发现其他上下文。
- `QUESTIONS.md` 只保存索引；BRIEF 是事前设计的事实源，RESULT 是事后证据与推断的事实源，Handoff 只引用而不复制。
- 保留 null、negative、contradictory 与 inconclusive evidence；technical validation、scientific support、Human approval 和 implementation reuse 不相互替代。
- 用户已明确请求的项目内、非覆盖、可恢复写入无需二次确认；mutating script 仍默认 dry-run，覆盖、删除、Git mutation 和外部写入必须获得明确授权。
- 具体分析脚本使用 `scripting-style` Skill；Pixi 环境创建、迁移、审查或诊断使用 `pixi-environment-builder` Skill，项目只允许根级 Pixi workspace。
