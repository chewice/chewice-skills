# ask-a-good-question

从研究方向、重要现象或具体困惑出发，结合真实领域证据，逐步找到值得回答、当前可以着手的科学问题。尤其适用于生物医学与生物信息学；允许探索、修订、暂不定题，并按需要拆成科研子问题和可交接任务。

使用入口是 [SKILL.md](SKILL.md)。[问题框架](references/question-framework.md)支持探索与取舍；[证据编排](references/evidence-orchestration.md)说明文献检索与 bear 路由；[前沿追踪](references/frontier-tracking.md)说明公开评审、作者路线与版本核查；[问题拆解](references/question-decomposition.md)说明分工与汇总；需要保存时按需使用 [Good Question Brief](assets/good-question-brief.md)。

## 思想来源与适用边界

以下是本次修订实际核查的原始材料。访谈核查了官网文字，未观看视频；方法论文和个人经验用于启发设计，不构成选题成功保证。

| 来源与阅读范围 | 原意及本技能采用的部分 | 边界 |
| --- | --- | --- |
| Uri Alon，2009，*How to Choose a Good Scientific Problem*，Molecular Cell 35:726–728；已读[作者机构原始 PDF](https://www.weizmann.ac.il/mcb/alon/sites/mcb.UriAlon/files/uploads/nurturing/howtochoosegoodproblem.pdf)三页全文，[DOI](https://doi.org/10.1016/j.molcel.2009.09.013) | PDF 第 1 页 “The Two Dimensions of Problem Choice” 用兴趣与可行性比较问题，并讨论不同职业阶段的取舍；第 2 页讨论兴趣的主观性与自我表达；第 2–3 页 “The Schema of Research” 描述遇到未知后问题可能改变。采用这些视角帮助研究者比较候选、识别可行动的切入点并保留转向。 | 兴趣包括预期知识增量及研究者的判断；可行性依赖技能、技术和时间。Pareto 比较不能代替个人选择，文中的时间经验不设为统一期限。 |
| Alfred G. Gilman，1994 年诺贝尔生理学或医学奖；[2007 年 4 月官方访谈全文](https://www.nobelprize.org/prizes/medicine/1994/gilman/interview/) | 首次资助项目回忆后的选题段：早期问题较宽，后来随数据与实验进展具体化；介绍 Dallas 之前的技术段：测量与实验能力改变问题的可回答性。采用“允许问题逐渐清晰”和“核查当前能做什么”。 | 不要求每轮都确定精确终题，也不据此允许无限扩散。膜上单组分与事件链是比较解释的实例，不能推成所有研究都必须有多个竞争模型。 |
| Eric F. Wieschaus，1995 年诺贝尔生理学或医学奖；[2009-03-17 官方访谈全文](https://www.nobelprize.org/prizes/medicine/1995/wieschaus/interview/)，选题段从官网标注的 21:10 开始 | 长期兴趣可以指向复杂问题；遗传筛选提供切入点，图谱仍需后续解释；他强调兴趣与当下可做之事结合。后文学生合作段说明新结果可以改变对项目的理解。 | 可做不等于容易，图谱不等于机制解释。个人能力与机会的经验不能替研究生或 PI 预设相同偏好。 |
| John R. Platt，1964，*Strong Inference*；核查[原文扫描](https://courses.washington.edu/esrm441/pdfs/Platt1964.pdf)第 1 页方法列表及相关讨论 | 比较替代解释，寻找能够区分它们的观察或实验，并循环修订。 | 适用于具有可区分预测的解释性问题；描述、测量与发现性探索不必先凑出竞争机制。 |
| Nosek 等，2018，*The preregistration revolution*；核查[原文](https://pmc.ncbi.nlm.nih.gov/articles/5856500/)摘要及区分预测与事后解释的相关章节 | 探索可以产生或修改假设；确认性检验须区别于产生该假设的探索。 | pilot 可反馈问题，但同一数据上的事后吻合不能冒充独立验证；是否预注册、保留验证数据或另做研究，依实际设计决定。 |

第一性原理与奥卡姆剃刀按使用者要求作为工作原则，操作定义见技能入口。CNS 种子、作者路线与公开评审的检索编排，以及本技能的人机分工，是结合这些材料与使用需求作出的设计选择：AI 承担 Search、Compress、Challenge、Formalize，并说明建议的依据和代价；研究者掌握 Salience、Framing、Taste、Bet、Pivot，即重要性、问题框定、兴趣取舍、投入与转向的最终判断。这套编排、角色名称、每轮终点与任务卡接口均不是上述作者提出或验证的规范。

研究生与 PI 的目标、时间承诺和风险承受可能不同，沿用他们已经表达的选择，缺失且会改变当前决定时再澄清。每轮可以结束于更清楚的现象、关键未知、可比较候选或最小试探方案；成熟度用于说明现状，不要求逐级完成。

## 环境与运行依赖

本技能本身是 Markdown 指令与模板。日常使用需要能够加载技能并读取相对引用文件的 AI 宿主；纯讨论不依赖专用运行时。需要外部证据时，宿主须具备可用的真实检索与来源阅读能力，或能读取研究者提供的原始材料，并记录实际覆盖范围。

| 使用方式 | 必要条件 |
| --- | --- |
| 讨论问题、整理已有材料 | AI 宿主可读本技能文件；保存 Brief 时有可写目标目录 |
| 联网检索、阅读论文或公开审稿 | 可用的学术检索或网页阅读能力，以及相应网络与来源访问权限 |
| 选择 bear 检索 | 对应 bear 技能及其完整 `references/`、Node.js ≥ 20、npm、`scimaster-cli`，以及有效 API Key、服务网络、可用额度和可写输出目录 |
| 维护与校验技能 | Python 3、PyYAML、`skill-creator` 的 `scripts/quick_validate.py`；Git 用于检查变更。这些不属于日常使用依赖 |

R、Python、MCP 服务和 Browser Use 均不是核心运行要求。Browser Use 可在现有工具适合交互式阅读时按需使用；公开网页或 PDF 可直接读取时，无需另装浏览器自动化。需要管理或排查运行环境时，使用当前环境中的 `pixi-environment-builder` 技能。

### 可选 bear 配置

先使所需 bear 技能在宿主中可发现，保留各自的 `SKILL.md` 和引用文件。复合技能的具体工作流以它自己的入口为准，无需为了一个任务预装全部 bear 系列。

使用者准备好 Node.js ≥ 20 和 npm 后，在 Agent 实际执行命令的环境中配置；复用已有兼容安装，确认 `node`、`npm` 和 `sci` 可由该环境的 PATH 找到。以下是安装与认证步骤，会修改运行环境和认证配置；只需在尚未配置时执行：

```bash
node --version
npm install -g scimaster-cli
sci init
sci --version
sci usage
```

`sci init` 交互式配置 API Key，按 [SciMaster](https://scimaster.bohrium.com/) 的账户入口取得 Key；不要把凭证放进对话、报告或仓库。命令及运行时要求可查 [bear 上游配置说明](https://github.com/fei0810/bear-research-skills#前置安装-scimaster-cli)和 [scimaster-cli 上游说明](https://github.com/scimaster/scimaster-cli)。配置后用 `sci --version`、`sci usage` 检查；版本命令成功仅表明 CLI 可启动，认证、额度和实际检索成功须分别确认。具体套餐与额度以当前服务返回为准。

`sci search` 会向所选输出目录写入带时间戳的 `.json` 与 `.bib`。实际调用完整 bear 工作流时，通常还会生成话题子目录中的 Markdown、HTML 和 BibTeX 报告；这些是该次检索的产物，按需链接进 Brief。HTML 自包含，可用普通浏览器离线阅读，无需前端构建或 Pandoc。

CLI 缺失、认证失败、额度不足或访问受限时，停止该 bear 路径，说明原因并使用可用的真实替代检索；保留检索工具、查询范围和缺口。没有可用来源时保留待核实状态，不能以模型记忆填补文献。

bear 技能来自独立上游项目 [bear-research-skills](https://github.com/fei0810/bear-research-skills)，其许可证为 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)；本技能引用其能力与产物，不复制或改写其源码。`scimaster-cli` 是另一个独立软件包，许可与安装要求以其上游为准。

## 验证范围

[评估案例](evals/evals.json)记录预期行为。维护时检查技能结构、JSON/YAML、相对链接与 Git 差异；静态校验通过不等于完成模型行为评测，也不证明外部检索覆盖完整。真实任务仍应记录来源、检索日期、阅读深度及未核实内容。
