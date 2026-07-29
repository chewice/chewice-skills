# Research Project OS

Research Project OS 是一个面向 Codex 的研究项目管理 Skill，用于为计算研究建立轻量、可恢复且可审计的工作框架。

它帮助研究项目统一管理：

- 由研究者维护的研究目的与问题队列。
- 最小化的 Agent 上下文和跨会话交接。
- 基于 Pixi 的可复现运行环境。
- 按研究问题组织的探索任务、运行凭据和人工审核归档。
- 独立的分析流程与中文 HTML 报告。

## 仓库结构

- `research-project-os/`：可安装的 Skill、CLI 和 Python 实现。
- `docs/`：架构与验收说明。
- `scripts/`：安装辅助脚本。
- `tests/`：单元测试、契约测试和冒烟测试。

## 验证

```bash
pixi run lint
pixi run test
pixi run smoke
pixi run validate-skill
```

所有修改操作默认采用 dry-run；只有显式指定 `--apply` 后才会写入项目。
