---
name: report-generation
description: 当用户要求“生成研究报告”“输出 HTML 报告”“生成 PDF”“综合审核结果”或“验证报告”时，应使用此 Skill 将已审核研究证据综合为问题驱动的 `reports/` 交付物；PDF 请求触发 capability check。
---

# 报告生成

## 范围

从已审核的事前 `BRIEF.md` 与事后 `RESULT.md` 综合问题驱动报告。遵循最小科学链条：Question → Study Design → Evidence → Inference → Qualified Claim → Next Decisive Test。报告不是治理文档拼接，也不创造新 evidence。

## 输入门槛

- `Design review: approved`；纳入的 RESULT 必须 `Status: reviewed` 且 Human Review receipt 完整、`Decision: approved`。
- 唯一合格 Artifact 可自动选择并在 dry-run 说明；多个合格候选可能改变范围时要求 Human 明确选择。
- 根或局部 Handoff 仅作 context 路由，不作科学事实；不递归发现未声明 Handoff，也不扫描其他 Question、全部 Pipeline 或 template。

## 科学综合

- 以 Claim-Evidence chain 综合所有指定 Artifact 的 `support | null | negative | contradictory | inconclusive` evidence；保留冲突，不按显著性筛选。
- 分开呈现 Observed Evidence、Inference、Qualified Claim、Uncertainty、Limitations/Applicability 和 Next Decisive Test，并给出可见 source anchor 与轻量 `source_map`。
- Technical validation 不等于 scientific support；Human approval 不等于 scientific validity；implementation reuse 也不改变 evidence relation。
- Question 未 `answered` 时明确标为阶段性或停止报告，不自动宣称研究问题已解决。

## 按需加载

- HTML 生成：读取 [`references/html.md`](references/html.md)。
- PDF 请求：读取 [`references/pdf.md`](references/pdf.md)；当前仅有明确的 unavailable boundary。
- 模板或样式调整：读取 [`references/templates.md`](references/templates.md)。
- 报告校验：读取 [`references/validation.md`](references/validation.md)。

## 边界

所有写入默认 dry-run，只有显式 `--apply` 后写入；除非显式 `--overwrite`，否则拒绝覆盖。不得改变 Question、BRIEF、Artifact、Pipeline 或 Human decision。事实仍以 BRIEF、RESULT 与其引用的 outputs/receipts 为准。

未满足审核门槛、输入冲突、资源越界、renderer 不可用或验证失败时停止，不生成看似成功的交付物。
