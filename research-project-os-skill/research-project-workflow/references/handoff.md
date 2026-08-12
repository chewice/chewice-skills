# 分层 Context Handoff

## 原则

Handoff 是可恢复的 context router，不是科研事实数据库。BRIEF 保存事前设计，RESULT 保存事后证据与推断；Handoff 只引用 active IDs、最后验证点、阻塞和 next decisive action，不复制问题、设计、结果或完整历史。

## 根 Project Router

每个项目只有一个根 `CURRENT_HANDOFF.md`，metadata 至少包含 `Updated` 与 `Active context`。其 `Context Map` 表固定为：

```text
Context | Scope | Active question | Current artifact | Checkpoint | Blocker | Next decisive action | Handoff
```

单项目只保留 `root` 行，`Scope` 为 `.`，`Handoff` 为 `CURRENT_HANDOFF.md`。大型项目只有在子项目确需独立恢复上下文时才新增 context 行；不要预先拆分。根文件另含 `Cross-context Dependencies` 与 `Required Reads`，用于声明跨子项目约束及项目级最小读取入口。

## 局部 Context

局部 Handoff 位于 Context Map 声明的 Scope 内，只包含：

- `Context`、`Scope`、`Updated`
- `Active question`、`Current artifact`
- `Last verified checkpoint`、`Blocker`、`Next decisive action`
- `Dependencies`
- `Required Reads`

创建局部 context：

```bash
pixi run record-project new-context \
  --project /path/to/project --context cohort-a --scope subprojects/cohort-a
pixi run record-project new-context \
  --project /path/to/project --context cohort-a --scope subprojects/cohort-a --apply
```

Context 使用稳定 slug，Scope 与 Handoff 必须是项目内相对路径。默认 dry-run；`--apply` 才在同一计划中一致创建局部 Handoff 并更新根 Context Map，拒绝覆盖、重复 context、scope 逃逸或与现有声明冲突。Q-ID 保持项目级唯一；A-ID 在各 Question 内递增，因此由 Q-ID/A-ID 组合唯一标识 Artifact。

## 恢复与更新

恢复时依次读取根 `AGENTS.md`、根 `CURRENT_HANDOFF.md`，再读取 Active context 行声明的局部 Handoff（root 行不重复读取）和 `Required Reads`。只在当前动作需要时读取 active BRIEF/RESULT；不得递归发现或扫描未声明的 `CURRENT_HANDOFF.md`。

切换 context 前，先写清当前 `Checkpoint`/`Last verified checkpoint`、`Blocker` 与 `Next decisive action`，再更新 `Active context`。new-question/new-artifact 至少正确更新目标 Context Map 行；局部 context 同时更新其局部 Handoff。跨 context 依赖写入根 `Cross-context Dependencies`，局部仅引用与自身有关的依赖。

Validator 只检查根 Context Map 声明的 Handoff 路径、scope containment、ID 引用和必要字段；不得递归发现局部 Handoff。`structure_consistent` 不表示 checkpoint 已被科学验证。Handoff 不使用 Workstream 状态机，也不设固定字数；删除不能改善恢复的信息即可。
