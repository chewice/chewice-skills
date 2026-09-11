# 问题驱动科研分析 Skill

本仓库提供可复用的 `research-context` Codex Skill：在用户已有的项目结构中，
以研究问题组织工作，维护一份可恢复的 `context.md`，并规范 Agent 交接、证据核验
与信息汇总。研究者保留方向与取舍。

项目脚手架由用户人工构建。本 Skill 不自动创建目录、编号或记录模板，也不要求
`QUESTIONS.md`、BRIEF/RESULT 或分层 Handoff。详细设计、分析过程与证据由项目已有
文件承载；摘要只提供必要入口。

探索遵循第一性原理与 Occam's razor：先明确问题、数据生成过程和推断单位，再选择
能改变判断的最小分析。面向人的说明使用中文；专业术语、路径、命令和文件名保持英文。

不默认产出正式 Report。具体 R/Python/Bash 分析写法可按需使用已安装的
`scripting-style`；Pixi 环境创建或迁移调用 `pixi-environment-builder`。

## 验证

```bash
pixi run lint
pixi run test
pixi run smoke
pixi run validate-skill
```

覆盖、删除、Git mutation 或外部写入仍由 Human 明确决定。用户已授权任务内，维护
已有 `context.md` 无需每次重复询问；入口缺失时不自动创建文件。
