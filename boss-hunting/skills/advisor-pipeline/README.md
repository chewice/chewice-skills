# Advisor Pipeline

## 用途

编排可恢复的导师调研项目：输入整理 → 导师发现与浅筛 → 用户确认背调范围 → 证据比较 → 按需准备 RP 或套磁信。它是 [Boss Hunting](../boss-hunting/README.md) 的兼容入口，也是项目初始化、共享数据契约、报告和确认脚本的所在地。

医学模式按科学问题与训练匹配分维度比较，通用模式保留有依据的数值匹配。结构化 JSON 是事实源；最终交付包含按学科/方向命名的 HTML，Excel 为补充。

## 运行必需依赖

- 可加载 Skills、读写本地文件并检索公开网页的 Agent；完整安装同级 Finder、Detective、Evaluator、Research Proposal 和 Outreach 技能。
- [pixi.toml](../../pixi.toml) 所定义的 Pixi 环境：`linux-64`，Node.js `>=22.13,<23`，Python `>=3.11,<3.13`。Windows 默认使用 WSL。
- 研究阶段默认先用 GPT 宿主实际提供的内置搜索/网页读取工具；官方静态页/API回退，动态JS表单才按需使用已有交互浏览器，不自动安装浏览器服务。默认 `builtin_web`，旧 `auto` 同样内置优先；显式用户后端选择保留。
- 纯项目初始化、HTML/Excel 导出不需要 Web npm 包或额外 Excel 库；Web 方式才需要 [Web 依赖](../../web/package.json)。

社区资料 PDF 抽取器、RP 的 LaTeX 和 Poppler 属于按需依赖，当前 Pixi manifest 未包含；见 [总依赖表](../../README.md#按使用方式准备依赖)。

## 如何使用

先按 [安装指引](../../README.md#方式二在自己的项目文件夹中直接使用-skills) 将整个 `skills/` 复制到申请项目。直接调用时，Agent 会按 [SKILL.md](SKILL.md) 初始化或安全迁移项目；需要手动准备时，可在终端执行：

```bash
pixi shell --manifest-path /path/to/boss-hunting/pixi.toml
cd /path/to/my-advisor-application
node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD"
node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD" --check
```

示例路径需替换为实际位置；Claude Code 安装将 `.agents/skills/` 换为 `.claude/skills/`。不要手工拼写 `project.json`。

```text
$advisor-pipeline 请依据当前项目里的真实 CV，寻找英国计算生物学博士导师，
目标为 2027 年入学、全额资助，先形成 10 位候选，再让我选择背调对象和维度。
```

已有项目可以直接要求“继续当前项目”，复用 CV、状态和证据。医学探索只需研究范围、训练目标及地区，无需先有 CV/学位/批次。通用发现需要真实 CV；客观申请筛选需要目标学位与入学批次。

背调及后置材料按现有确认流程执行；申请材料还需一个精确导师—项目目标、真实 CV 和已确认姓名。仅重建报告时可在仓库根目录运行：

```bash
pixi run report --project-root /path/to/my-advisor-application
```

输出与恢复规则见 [共享数据契约](references/data-contract.md) 和 [SKILL.md](SKILL.md)。
