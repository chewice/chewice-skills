# Acceptance

- 只存在 `research-project-workflow` 与 `report-generation` 两个团队级 Skill。
- 用户可见内容、命令、示例与代码不再包含旧品牌和旧 CLI。
- 两个 Skill 共用唯一根级 Pixi workspace；无嵌套 lock 或 `.pixi/`。
- scaffold 默认 dry-run，`--apply` 后才创建目标父目录与控制文件；不创建 Q/A 实例，
  不覆盖已有控制文件，不执行 Git mutation。
- `AGENTS.md` 的 Language、Reasoning、Superpowers 三段逐字保留。
- `QUESTIONS.md` 只保存五列表格索引；BRIEF、RESULT、Handoff 合同与三套状态域合法。
- Validator 只读检查结构、状态、引用、Human review、promotion 和旧结构。
- 被拒绝 Artifact 保留；只有 Human 审核通过版本可记录 Pipeline promotion。
- “总结工作”使用统一时间戳，不自动批准、关闭、开始下一问题或生成报告。
- report-generation 只读取已审核 BRIEF/RESULT，默认 dry-run，HTML 写入
  `reports/<Q-ID>/report.html`，资源与 metadata 可验证。
- PDF renderer 未配置时明确失败，不创建伪输出。
- 安装器为两个 Skill 分别建立 Codex 与 Agents discovery symlink。
- `pixi run lint`、`pixi run test`、`pixi run smoke` 与
  `pixi run validate-skill` 全部通过。

## 从 0.x 迁移

新版本不读取 `project_manifest.yaml`、旧 Question blocks、task manifest、archive、
release 或 Handoff archive。迁移前保留可恢复备份，然后人工执行：

1. 将每个旧问题压缩为 `QUESTIONS.md` 索引行，并把依据迁入对应 `BRIEF.md`。
2. 将仍有价值的 Explore 版本复制为 `explore/<Q-ID>/<A-ID>/`，用 `RESULT.md` 记录
   状态、验证与 Human review；不要覆盖被拒绝版本。
3. 将审核通过且已复用的实现整理到 `pipeline/`，机器可读产物放入 `results/`。
4. 将当前事实压缩到新的 `CURRENT_HANDOFF.md`，旧历史交由 Git 或外部备份。
5. 删除旧结构前运行新 Validator，逐项确认没有遗失仍需保留的证据。

不提供旧 schema 的长期运行时兼容层。
