# {{PROJECT_NAME}}

本项目采用问题驱动的科研分析架构：

`Question → Study Design → Evidence → Inference → Qualified Claim → Next decisive test`

## 事实源

- `QUESTIONS.md`：Question 的机械索引。
- `docs/questions/<Q-ID>/BRIEF.md`：事前研究问题与 Study Design。
- `explore/<Q-ID>/<A-ID>/RESULT.md`：事后 Evidence、Inference 与 Human review。
- `AGENTS.md`：跨 Question 长期有效规则。

BRIEF 不保存事后结果，RESULT 不改写事前设计。null、negative、contradictory 与 inconclusive evidence 和支持性 evidence 同样保留。technical validation、scientific support、Human approval 与 implementation reuse 分别记录。

## 分层上下文

根 `CURRENT_HANDOFF.md` 是 project router。单项目只使用 `root` context；大型项目在子项目确需独立恢复时，才按 Context Map 声明的 Scope 创建局部 `CURRENT_HANDOFF.md`。Handoff 只保存 active IDs、checkpoint、blocker、next decisive action 和 Required Reads，不复制 BRIEF/RESULT。

## 按需结构

Scaffold 只建立根控制层。Question、Artifact、局部 context、pipeline、results、reports、logs、configs 与参考资料目录在首次真实需要时创建。具体分析脚本由 `scripting-style` Skill 管理；Pixi 环境由 `pixi-environment-builder` Skill 管理。

所有 mutating script 默认 dry-run 并拒绝覆盖。用户明确请求的项目内、非覆盖、可恢复写入无需重复确认；覆盖、删除、Git mutation 或外部写入仍需明确授权。
