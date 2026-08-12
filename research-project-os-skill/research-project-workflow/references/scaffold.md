# Scaffold 与 Adopt

## 读取范围

读取目标根目录浅层结构及已有 `AGENTS.md`、`QUESTIONS.md`、`CURRENT_HANDOFF.md`、`README.md`。若存在 Pixi 文件，只识别并保留；不在本流程中设计或改写环境。

## 最小控制层

Scaffold/adopt 只创建缺失的根控制文件：

- `AGENTS.md`
- `QUESTIONS.md`
- `CURRENT_HANDOFF.md`
- `README.md`
- `.gitignore`

业务目录按首次真实需求创建：new-question 创建对应 `docs/questions/<Q-ID>/`；new-artifact 创建对应 `explore/<Q-ID>/<A-ID>/`；局部上下文只在多子项目确有需要时创建。不要预建 references、template、methods、runbooks、pipeline、results、reports、logs、configs 或 tests。

Scaffold 不生成 `pixi.toml`、`pixi.lock` 或 `.pixi/`。需要创建、迁移、审查或诊断 Pixi 环境时调用 `pixi-environment-builder` Skill，并保持项目只有根级 Pixi workspace。

## 命令与 mutation

```bash
pixi run scaffold-project --project /path/to/project
pixi run scaffold-project --project /path/to/project --apply
```

默认只输出计划。用户已明确要求初始化或接管时，计划中的项目内、非覆盖、可恢复创建可直接用 `--apply`，不再请求重复确认。保留所有既有路径与文件；路径冲突或任何覆盖需求均停止。Scaffold 不创建 Q-ID/A-ID、不修改研究产物、不执行 Git 或外部写入。

应用后运行只读 Validator。`structure_consistent: true` 只表示控制层结构一致，不表示研究设计或科学结论有效。

## 文件放置原则

- 事前设计：`docs/questions/<Q-ID>/BRIEF.md`。
- 事后证据：`explore/<Q-ID>/<A-ID>/RESULT.md` 及该 Artifact 明确引用的 code、config、output 或 receipt。
- 已审核实现是否进入 `pipeline/` 是独立的 implementation reuse 决定；不得把 Explore 路径直接当作稳定 runtime。
- Human 主动提供的参考材料只在明确引用时读取；具体分析脚本由 `scripting-style` Skill 约束。
