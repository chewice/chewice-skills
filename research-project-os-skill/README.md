# 研究项目工作流 Skills

本仓库提供两个面向 Codex 的协作 Skill，为计算研究建立轻量、可恢复且可审核的工作框架。

## Skills

- `research-project-workflow`：管理脚手架、Question/BRIEF、Explore/RESULT、
  Human review、Pipeline promotion、Handoff 和“总结工作”。
- `report-generation`：从已审核研究内容生成并验证 `reports/<Q-ID>/report.html`。
  PDF 保留扩展契约，当前版本不捆绑 renderer。

## 仓库结构

- `research-project-workflow/`、`report-generation/`：可安装 Skills。
- `docs/`：架构、迁移与验收说明。
- `scripts/`：双 Skill 安装辅助脚本。
- `tests/`：单元测试、契约测试和冒烟测试。

两个 Skill 共用唯一根级 Pixi workspace，不包含嵌套 `pixi.toml`、`pixi.lock`
或 `.pixi/`。

## 验证

```bash
pixi run lint
pixi run test
pixi run smoke
pixi run validate-skill
```

所有修改操作默认采用 dry-run；只有显式指定 `--apply` 后才会写入。脚手架不会
预建虚假 Q-ID/A-ID，不会自动 commit/push，也不会扫描 `docs/template/`。
