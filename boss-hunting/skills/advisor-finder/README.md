# Advisor Finder

## 用途

从目标范围和申请者背景发现真实导师，比较研究匹配，形成 shortlist，再为申请模式核对官方项目、学位、入学批次与申请条件。医学探索可仅凭研究兴趣和训练目标开始；通用模式需要真实 CV。

本阶段只做导师身份、近期研究、代表作和公开招生信号的浅筛；选定导师的深入背调交给 [Advisor Detective](../advisor-detective/README.md)。

## 运行必需依赖

- 可检索和阅读公开网页、读取 CV、写入本地记录的 Agent，以及可用网络。
- 完整 Advisor Atlas `skills/`；脚本直接引用同级 [advisor-pipeline](../advisor-pipeline/README.md) 的数据契约、医学视图和工作簿运行时。
- 项目 [Pixi 环境](../../pixi.toml) 中的 Node.js `>=22.13,<23`，用于匹配策略、HTML/Excel 生成；默认 `linux-64`，Windows 使用 WSL。
- 输入：目标学校/地区/学科范围；通用模式的真实可读 CV，或医学模式所需的研究兴趣/可追溯背景。做客观申请筛选前需明确学位和批次。

无需额外 Excel 库、Web npm 包或固定学术检索 API Key；具体来源访问受当前网络和宿主工具能力限制。医学动态页面按需使用宿主浏览器工具。

## 如何使用

按 [完整安装说明](../../README.md#方式二在自己的项目文件夹中直接使用-skills) 复制技能集合，在申请项目内调用：

```text
$advisor-finder 使用项目现有 CV，寻找香港和新加坡的计算生物学博士导师。
目标为 2027 年入学、全额资助，shortlist 保留 10 位，并核对官方申请条件。
```

```text
$advisor-finder 先探索英国的神经免疫方向导师。我希望学习单细胞与空间组学，
目前只比较研究问题和训练支持，暂不判断申请资格。
```

首次项目建议通过 [Boss Hunting](../boss-hunting/README.md) 初始化。已有 CV 和当前有效来源会被复用；未核实的资格或项目保持待确认，不作为通过条件。

产物包括 `outputs/advisor_records.json`、`program_records.json`、`evidence.json`、`candidates.json`，以及按研究方向命名的 HTML 和补充 Excel。详细流程见 [SKILL.md](SKILL.md)，匹配规则见 [matching-strategy.md](references/matching-strategy.md)。
