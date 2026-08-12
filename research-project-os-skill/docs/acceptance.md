# Acceptance

## 科研合同

- 主流程明确实现 `Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test`。
- BRIEF 只记录事前设计；RESULT 只记录事后 Evidence 与 Inference，不以技术运行成功代替科学支持。
- Hypothesis/falsifier、estimand/inference unit、evidence eligibility、uncertainty、Claim–Evidence、
  acceptance/stopping criteria 均有明确位置。
- Provenance、planned deviation、observed evidence、technical/scientific validation、alternative
  explanation、applicability boundary 和 next decisive test 均有明确位置。
- Null、negative、contradictory 与 inconclusive evidence 不被丢弃或改写成正结论。
- Human approval、scientific support 与 implementation reuse 为三个独立判断。

## 上下文与恢复

- 根 `CURRENT_HANDOFF.md` 作为 project router，保留 Active context、Context Map、跨上下文依赖和 Required reads。
- 小项目只需 `root` context；子项目 Handoff 按需创建且必须由 Context Map 显式声明。
- Handoff 只引用 BRIEF/RESULT，不复制科学事实；Validator 不递归发现未声明上下文。
- “总结工作”只更新发生变化的 canonical record 与相关 Handoff，不批量改写无变化文件。

## 自动化与安全

- Scaffold 默认 dry-run，只建立最小控制文件，不预建空业务目录、不生成 Q/A 实例或固定 Pixi 环境。
- Question/Artifact 的 ID、模板、时间戳、索引和上下文由单个计划一致更新，已有目标不会被覆盖。
- 用户已明确请求的项目内 non-destructive bookkeeping 不需要二次确认。
- 科学结论与 review、覆盖或删除、Git/Notion/外部写入仍需 Human 明确决定。
- Validator 只声明 `structure_consistent`，并显式报告 `scientific_validity: not_evaluated`。
- 旧结构在 non-destructive adoption 中只产生 warning。

## 报告与交付

- 报告围绕 Research Question、design boundary、Claim–Evidence、Inference、uncertainty、
  applicability 和 next decisive test 组织，不整篇拼接治理文档。
- 未关闭 Question 的报告标记为阶段性；多 Artifact 的冲突不得被静默合并。
- 报告保留 source anchor、输入和资源 hash；报告仍是上游审核记录的派生物。
- PDF renderer 未配置时明确失败，不创建伪输出。

## 仓库完成条件

- 根 `AGENTS.md` 的 `Language`、`Environment` 与总原则受逐字回归测试保护。
- 生成项目的 Language、Reasoning 与 literal Superpowers contract 受回归测试保护。
- 两个 Skill 共用唯一根级 Pixi workspace；无嵌套 lock 或被跟踪的 `.pixi/`。
- 两个 Skill 的 Codex/Agents discovery 路径均可解析到当前源码。
- `pixi run lint`、`pixi run test`、`pixi run smoke` 与 `pixi run validate-skill` 全部通过。

## 从旧结构迁移

Adoption 保留既有文件并报告差异，不自动删除 archive、旧 manifest、历史 Handoff 或项目自有目录。
只有在某个 Question/Artifact 再次进入工作时，才将仍有效的设计、证据和 provenance 人工归入新
BRIEF/RESULT；无法证明来源的内容标为待确认。完成只读验证和可恢复备份后，再由 Human 单独决定
是否清理旧结构。
