# Scaffold

## 读取范围

只读取目标目录浅层结构、已有 `AGENTS.md`、已有根级 `pixi.toml` 与 `pixi.lock`。不得扫描 `docs/template/` 或研究结果。

## 初始化与接管

使用根 workspace 执行：

```bash
pixi run scaffold-project --project /path/to/project
pixi run scaffold-project --project /path/to/project --apply
```

默认输出计划，不写入。空目录与已有项目使用同一非破坏性流程：创建缺失的稳定父目录和根控制文件，保留所有已有路径。仅在 Human 明确要求且提供 `--overwrite` 时覆盖普通模板；任何情况下均不得覆盖已有 `AGENTS.md`、`QUESTIONS.md`、`CURRENT_HANDOFF.md`、`README.md`、`pixi.toml` 或 `.gitignore`。

## 稳定结构

创建 `AGENTS.md`、`QUESTIONS.md`、`CURRENT_HANDOFF.md`、`README.md`、根级 Pixi 与 `.gitignore`，以及 `docs/questions/`、`docs/references/{papers,official,datasets}/`、`docs/template/`、`docs/methods/`、`docs/runbooks/`、`explore/`、`pipeline/`、`results/`、`reports/`、`logs/`、`configs/`、`tests/`。

只创建父目录，不创建 Q-ID、A-ID、结果或报告实例。不得生成 Question、Pipeline 实现、Git commit，或修改已有研究产物。

## 文件放置

- Question 依据放入 `docs/questions/<Q-ID>/BRIEF.md`。
- Human 明确提供的参考代码只放入 `docs/template/`，且仅在显式 `@` 时读取。
- 跨 Question 已复用的方法放入 `docs/methods/`；恢复和人工操作流程放入 `docs/runbooks/`。
- Explore 临时产物留在 Artifact；审核后稳定配置进入 `configs/`，机器可读结果进入 `results/`。

应用后运行 `pixi run validate-project --project /path/to/project`。验证失败时不得宣称脚手架完成。
