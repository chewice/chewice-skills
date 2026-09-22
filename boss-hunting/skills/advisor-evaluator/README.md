# Advisor Evaluator

## 用途

汇总 Finder 的研究匹配与客观申请信息、Detective 的已选维度证据，形成可比较的导师报告及申请总表。研究匹配、申请资格、招生机会、主观背调结论分别呈现。

医学探索采用分维度证据画像，保留未知与下一步核实事项，不套用通用总分或录取概率；通用申请模式按公开规则形成优先顺序。

## 运行必需依赖

- 可读写共享 JSON、检查报告/工作簿的 Agent。
- Finder/Detective 已产生的项目记录、证据、候选与匹配审计；仅医学探索时可使用真实导师级记录，无需虚构项目/批次。
- 完整技能集合，尤其是 [advisor-pipeline](../advisor-pipeline/README.md) 的共享契约、医学视图、HTML 生成器与工作簿运行时。
- [Pixi 环境](../../pixi.toml) 中的 Node.js `>=22.13,<23`；默认 `linux-64`，Windows 使用 WSL。

内置 OOXML 后备可直接导出 Excel，不必安装 `@oai/artifact-tool` 或 Python Excel 库。仅重建已有数据的报告不需要联网；补充核验过期或缺失事实时需要网页访问能力。工作簿预览是否可用取决于宿主提供的工具。

## 如何使用

在已有真实记录的申请项目内调用：

```text
$advisor-evaluator 请汇总现有候选和已确认背调结果，
分别显示研究匹配、申请资格、资助、风险与未知，生成 HTML 和申请总表。
```

医学探索示例：

```text
$advisor-evaluator 比较目前的神经免疫导师候选，重点看科学问题与训练支持，
保留未核验项目的导师，不计算综合分。
```

主要产物是 `outputs/{研究方向}-导师调研.html`；医学探索补充 `advisor_research_discovery_YYYYMMDD.xlsx`，申请模式补充 `advisor_application_ready_YYYYMMDD.xlsx`。不同导师对应的不同项目保持独立行。

安装见 [项目 README](../../README.md#方式二在自己的项目文件夹中直接使用-skills)，执行及验收规则见 [SKILL.md](SKILL.md) 和 [工作簿契约](references/workbook-contract.md)。
