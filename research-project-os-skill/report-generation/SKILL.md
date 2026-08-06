---
name: report-generation
description: 当用户要求“生成研究报告”“输出 HTML 报告”“把审核结果整理成报告”“生成 PDF”或“验证报告”时，应使用此 Skill 从已审核研究内容生成 `reports/` 交付物。
---

# 报告生成

## 范围

将 Human 已审核的 `BRIEF.md`、一个或多个审核通过的 `RESULT.md`、`results/<Q-ID>/`、必要 Pipeline 说明和 Human 指定要求整理为正式报告。`results/` 是分析事实与机器可读产物；`reports/` 是面向 Human 的表达和交付。

## 输入门槛

- 读取目标 Question 的 BRIEF、明确指定的 Artifact RESULT 和必要资源。
- 确认 BRIEF 已有 Human review，所有 RESULT 状态均为“审核通过”。
- 不默认扫描其他 Question、旧 Artifact、全部 Pipeline 或 `docs/template/`。

## 按需加载

- HTML 生成：读取 [`references/html.md`](references/html.md)。
- PDF 请求：读取 [`references/pdf.md`](references/pdf.md)。
- 模板或样式调整：读取 [`references/templates.md`](references/templates.md)。
- 报告校验：读取 [`references/validation.md`](references/validation.md)。

## 边界

所有写入默认 dry-run，只有显式 `--apply` 后写入。不得隐式覆盖输出、修改 `QUESTIONS.md`、BRIEF/Artifact 状态、批准结果、修改 Pipeline、执行 Explore，或把未经审核内容表述为正式结论。报告不是唯一科学事实源；事实仍以审核记录和 `results/` 为准。

未满足审核门槛、输入冲突、资源越界、renderer 不可用或验证失败时停止，不生成看似成功的交付物。
