# ask-a-good-question

从研究方向、重要现象或具体困惑出发，结合真实领域证据，逐步找到值得回答、当前可以着手的科学问题。尤其适用于生物医学与生物信息学；允许探索、修订、暂不定题，并按需要拆成科研子问题和可交接任务。

## 用途与交付

本技能辅助研究者提出和修订问题：Agent 负责检索、整理证据、挑战推断和明确问题表达；研究者决定什么值得关注、是否投入以及何时转向。

| 你当前的需要 | 可以获得的结果 |
| --- | --- |
| 只有一个宽泛领域 | 有来源的领域认识、具体未知和可进一步核实的 entry point |
| 有现象、异常或初步解释 | 替代解释、区分性预测和最小核实步骤；描述问题不强求机制 |
| 在候选之间做取舍 | 同一时间与投入尺度下的兴趣—可行性比较，保留人的选择 |
| 已选定问题，需要分工 | 科研子问题、依赖关系、任务卡和汇总接口 |
| 带着新证据再次讨论 | 修订问题与切入口，保留仍适用的证据和工作 |

研究生入门可偏重可行性，PI 的长期方向可偏重兴趣；这是讨论建议，实际目标与个人偏好优先。一次探索可以停在合适的切入口，不必立即形成最终课题。任务包交付后，分析、实验与实际委派按需另行开展。

使用入口是 [SKILL.md](SKILL.md)。[问题框架](references/question-framework.md)支持探索与取舍；[证据编排](references/evidence-orchestration.md)说明文献检索与 bear 路由；[前沿追踪](references/frontier-tracking.md)说明公开评审、作者路线与版本核查；[问题拆解](references/question-decomposition.md)说明分工与汇总；需要保存时按需使用 [Good Question Brief](assets/good-question-brief.md)。

## 思想来源与适用边界

以下是技能设计已核查的思想来源。“背书”指可追溯的方法依据，不表示作者或机构认可、认证本技能。访谈核查了官网文字，未观看视频；方法论文和个人经验用于启发设计，不构成选题成功保证。

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

本技能本身是 Markdown 指令与模板，但完整使用环境包含下列前置依赖。**使用前必须先安装 bear 系列 Skills，并配置其 SciMaster 检索环境**；不能只复制本技能的 `SKILL.md` 就视为准备完成。bear 上游为 [fei0810/bear-research-skills](https://github.com/fei0810/bear-research-skills)，Git 地址为 `https://github.com/fei0810/bear-research-skills.git`。

| 类别 | 必要条件 |
| --- | --- |
| AI 宿主 | 支持 Agent Skills，能读取技能及相对引用、执行 CLI、访问来源；保存产物时有可写目录 |
| 必装技能 | 本技能完整目录，以及 `bear-onboard`、`bear-map`、`bear-trace`、`bear-scoop`、`bear-propose`、`bear-support`、`bear-counter`、`bear-review` 及各自引用文件 |
| 安装与检索运行时 | Node.js ≥ 20、npm/npx；使用下述仓库安装方式时还需 Git。Agent 的执行环境须能从 PATH 找到相应命令 |
| SciMaster 服务 | `scimaster-cli`、有效 API Key、可用额度，以及访问服务的网络；账户条件以服务当前规定为准 |
| 来源阅读 | 可用的网页/PDF 阅读能力及相应访问权限，用于核查论文、公开审稿和作者信息；不要求特定浏览器工具 |
| 维护与校验技能 | Python 3、PyYAML、`skill-creator` 的 `scripts/quick_validate.py`；Git 用于检查变更。这些不属于日常使用依赖 |

R、Python、MCP 服务和 Browser Use 均不是日常使用的必装依赖。Browser Use 可按需用于交互式阅读；公开网页或 PDF 可直接读取时，无需另装浏览器自动化。Windows、WSL、远程主机或容器中，应把依赖安装在 Agent 实际运行命令的环境，不能用另一环境的安装结果代替。需要管理或排查运行环境时，使用当前环境中的 `pixi-environment-builder` 技能。

## 安装：先完成 bear 前置任务

### 1. 安装并认证 SciMaster CLI

先准备满足要求的 Node.js、npm 和 Git，复用已有兼容安装。以下命令由使用者在该环境的终端执行；安装与认证只需在尚未配置时进行：

```bash
node --version
npm --version
git --version
npm install -g scimaster-cli
sci init
sci --version
sci usage
```

`sci init` 交互式配置 API Key，在 [SciMaster](https://scimaster.bohrium.com/) 账户设置中创建 Key；不要把凭证放进对话、报告或仓库。命令及运行时要求见 [bear 上游配置说明](https://github.com/fei0810/bear-research-skills#前置安装-scimaster-cli)。`sci --version` 仅证明 CLI 可启动，`sci usage` 用于核查账户访问与额度；二者都不能代替一次真实检索。

### 2. 安装 bear 系列，再安装本技能

以下使用第三方 [skills CLI](https://github.com/vercel-labs/skills)，以 Codex 的用户级安装为例；命令会下载并安装技能。先安装 bear 全系列，再安装本技能：

```bash
npx skills add https://github.com/fei0810/bear-research-skills.git --skill '*' --agent codex --global
npx skills add https://github.com/chewice/chewice-skills.git --skill ask-a-good-question --agent codex --global
npx skills list
```

`--skill '*'` 选择 bear 仓库中的全部技能，`--agent codex` 限定目标宿主，`--global` 表示用户级安装。项目级安装省略 `--global`；其他受支持宿主改用其 agent 名称。不使用 `--all`，因为 skills CLI 将其解释为安装到所有宿主。安装器的具体行为以其上游说明为准。

如果要使用本地尚未发布的修改，在本仓库根目录用下面的命令替代第二条远程安装命令：

```bash
npx skills add ./ask-a-good-question --agent codex --global
```

也可以完整复制技能目录到宿主支持的位置。Codex 的用户级位置为 `~/.agents/skills/`，项目级位置为 `.agents/skills/`：将本技能目录和 bear 仓库 `skills/` 下的各个 `bear-*` 目录分别放入，不要只复制入口文件，也不要仅克隆仓库后就假定宿主已经发现技能。发现与调用方式见 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。

### 3. 确认前置任务完成

确认宿主能发现本技能和上述八个 bear 技能、能读取引用文件，并在同一执行环境检查 `sci --version` 与 `sci usage`。首次需要文献时，围绕真实问题做一次小范围 bear 检索，检查是否返回可定位来源；这一步会使用检索额度并生成文件，执行前明确输出目录。安装后技能未出现时，重新启动宿主并检查安装位置。

未安装 bear 或未完成初始配置时，先完成前置任务，不能把通用网页搜索当作已满足安装要求。已配置后若认证失效、额度不足或服务故障，停止失败的 bear 调用，说明原因，再用可用的真实来源降级继续；记录缺口，不虚称 bear 检索成功。安装全系列不意味着每轮执行全系列，只调用当前问题所需的技能。

## 如何使用

在宿主中选择 `ask-a-good-question` 并描述当前困惑。Codex CLI 或 IDE 扩展可用 `$ask-a-good-question` 显式调用；也可直接说明技能名称和任务。以下示例输入到 Agent 对话中，不是终端命令：

```text
$ask-a-good-question
我刚进入神经免疫领域，目前只有公开横断面转录组数据。
这轮更重视两周内能核实的切入口，先不要确定最终课题。
请结合真实文献建立领域认识，比较值得追问的未知；
把需要我决定的取舍列出来，检索产物保存到 ./evidence/question-selection/。
```

后续可以说：“结合这份 pilot 结果修订原来的解释和问题”，或“沿用我选定的问题，拆成可交给研究者或 Agent 的任务包，先不执行”。提供已有记录、数据清单和资源限制即可，不必先填完整问卷；明确本轮是选择一次核实、一个项目还是长期方向，有助于比较可行性与兴趣。

需要保存时，指定 Brief 的路径，例如 `./question-brief.md`。Brief 记录证据、候选、人的选择和下一步；未决定最终问题也可以交付。仅对一个既定 idea 做立项前文献审计时，直接使用 `bear-propose`；已有主张只需支持文献时，使用 `bear-support`。

### 产物与故障处理

`sci search` 会向所选输出目录写入带时间戳的 `.json` 与 `.bib`。实际调用完整 bear 工作流时，通常还会生成话题子目录中的 Markdown、HTML 和 BibTeX 报告；这些是该次检索的产物，按需链接进 Brief。HTML 自包含，可用普通浏览器离线阅读，无需前端构建或 Pandoc。

没有可用来源时保留待核实状态，不能以模型记忆填补文献。故障降级期间沿用仍适用的已有证据，注明实际工具、查询范围和阅读深度。

bear 技能来自独立上游项目 [bear-research-skills](https://github.com/fei0810/bear-research-skills)，其许可证为 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)；本技能引用其能力与产物，不复制或改写其源码。`scimaster-cli` 是另一个独立软件包，许可与安装要求以其上游为准。

## 验证范围

[评估案例](evals/evals.json)记录预期行为。维护时检查技能结构、JSON/YAML、相对链接与 Git 差异；静态校验通过不等于完成模型行为评测，也不证明外部检索覆盖完整。真实任务仍应记录来源、检索日期、阅读深度及未核实内容。
