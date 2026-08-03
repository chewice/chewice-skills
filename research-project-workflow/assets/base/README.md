# {{PROJECT_NAME}}

本项目采用轻量研究工作流组织 Question、Explore、Pipeline、结果与报告。

## 控制文件

- `AGENTS.md`：长期有效规则。
- `QUESTIONS.md`：Question 索引。
- `CURRENT_HANDOFF.md`：唯一默认状态入口。
- `docs/questions/<Q-ID>/BRIEF.md`：问题工作依据。
- `explore/<Q-ID>/<A-ID>/RESULT.md`：Explore 结果与 Human review。

## 目录

- `docs/references/`：文献、官方资料与数据资源说明。
- `docs/template/`：Human 主动提供且仅在显式引用时读取的参考代码。
- `docs/methods/`、`docs/runbooks/`：复用方法与操作流程。
- `explore/`、`pipeline/`：探索与正式分析流程。
- `results/`、`reports/`：机器可读事实与面向 Human 的交付。
- `logs/`、`configs/`、`tests/`：日志、稳定配置和测试。

所有写入默认先预览；Human 审核决定不得由自动化替代。
