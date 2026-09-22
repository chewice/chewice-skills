# Boss Hunting

## 用途

导师发现与比较的主入口。根据医学研究兴趣或真实 CV，调用 Finder、Detective、Evaluator，逐步形成有来源的候选名单、背景调查和比较报告，也支持继续已有项目。医学探索可不提供 CV；申请筛选与申请材料各有对应输入要求。

本技能复用 [advisor-pipeline](../advisor-pipeline/README.md) 的状态和脚本，不维护第二套流程。主产物为申请项目 `outputs/` 下按学科或研究方向命名的 HTML，Excel 为补充导出。

## 运行必需依赖

- 可加载本地 Skills、读写项目文件并检索公开网页的 Agent，例如 Codex 或 Claude Code。
- 完整的同级技能集合，尤其是 `advisor-pipeline` 及 Finder、Detective、Evaluator；安装时复制整个 `skills/`。
- [项目 Pixi 环境](../../pixi.toml)：默认平台为 `linux-64`，Windows 使用 WSL；Node.js `>=22.13,<23` 用于初始化和导出。该环境同时声明 Python `>=3.11,<3.13`，用于按需社区同步。
- 事实核验默认先用宿主实际暴露的联网工具，按真实 schema 执行：GPT/Codex 宿主的内置搜索与网页阅读（`web.run`、`web_search`），或 Wisp Science 的浏览器工具组（`browser_setup`、`web_open_tab`、`web_scan`、`web_execute_js`、`web_screenshot`、`web_save_assets`）。官方静态页/API 作为回退，动态 JS 表单才使用已有交互浏览器。Wisp Science 浏览器复用真实 Chrome 会话，证据记 `retrieval_method: browser` 与 `retrieval_provider: wisp_science_browser`；没有固定必装的 Browser Use 服务。

直接使用 Skills 不要求安装 Web 的 npm 包、R 或 Excel 库。社区 PDF 检索、RP 编译等依赖仅在进入相应阶段时需要，见 [完整依赖与安装说明](../../README.md#按使用方式准备依赖)。

## 如何使用

1. 按 [项目安装说明](../../README.md#方式二在自己的项目文件夹中直接使用-skills)，将完整 `skills/` 放到申请项目的 `.agents/skills/`（Codex）或 `.claude/skills/`（Claude Code），保留仓库作为共享 Pixi 依赖环境。
2. 在该申请项目中调用技能，提供已有资料。例如：

   ```text
   $boss-hunting 我想探索肿瘤免疫方向的博士导师，地区为英国和香港。
   我希望学习单细胞分析，目前先做方向与训练匹配探索，没有 CV。
   ```

   ```text
   $boss-hunting 继续当前申请项目，复用已保存的 CV 和候选记录。
   ```

3. Agent 只补问缺失输入，完成发现后由用户选择具体导师—项目与背调维度；申请材料另行确认目标与种类。

流程细则见 [SKILL.md](SKILL.md)。技能生成研究资料与申请材料，不发送邮件或提交申请。
