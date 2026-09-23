# Boss Hunting

本目录是 Boss Hunting 项目仓库，包含 Pixi 环境、Web 控制台和 Skills；真正被 Codex／Claude Code 识别的主 Skill 入口是 [skills/boss-hunting/SKILL.md](skills/boss-hunting/SKILL.md)。`skills/` 下的 Finder、Detective、Evaluator 等目录是协作模块，不是另一套同名系统。

Boss Hunting 根据公开证据发现和比较博士导师。医学探索的最低输入只有**医学领域、疾病／机制／科学问题、目标地区**，无需 CV。流程从种子研究发现 PI、核验身份、回查近五年研究、扩展合作网络，再调查五个模块：身份与科研定位、近五年主线、合作网络、最新研究与项目、博士培养轨迹。五维证据画像分别呈现方向契合、主线连续性、PI 角色置信度、证据充分性和当前活跃度；未知事项会标明，不生成导师质量总分。申请筛选需要相关真实背景；RP 和套磁信另需真实 CV、确切导师—项目目标与用户确认。

设计参考 Ben A. Barres 的 NeuroView [*How to pick a graduate advisor*](https://doi.org/10.1016/j.neuron.2013.10.005)（[PubMed](https://pubmed.ncbi.nlm.nih.gov/24139033/)）。文章讨论导师选择与指导质量，**并非对 Boss Hunting 的验证或认可**。本 Skill 只比较可公开核验的研究、项目及指导关系等事实，不推断导师人格或组内氛围。

## 首次使用：先检查依赖

在克隆后的 Boss Hunting 仓库运行 `node skills/advisor-pipeline/scripts/first-use.mjs`。它只检查当前 `linux-64` 平台、Pixi、锁定的 Node／Python 环境和七个 Skill 入口；Web 前端依赖单列为可选。检查使用 Pixi 的 `--as-is` 模式，**不安装依赖**。如果本机还没有 Node，先用终端执行 `pixi --version`、`node --version` 并处理缺失项；需要安装 Pixi 环境时由用户在仓库运行 `pixi install`，再重做检查。

首次检查还会在源仓库的 `skills/boss-hunting/credentials.env` 创建一次被 Git 忽略的空值模板，已有文件绝不覆盖。它只在用户配置目录登记源仓库路径，供其他项目中的 Skill 副本找到同一个文件；项目目录不保存 Key。检查结果先列环境状态，再列下方可选 API 凭据和申请网址，最后给出首次使用的 prompt 示例。

## API 凭据

凭据**全部可选**。默认先用宿主可用的内置网页检索；缺少 Key 时，可用匿名官方 API、官方公开网页或其他权威来源继续。当前代码负责凭据状态检测及来源路线选择；实际检索由运行中的 Agent 按可用工具执行，仓库没有为每个平台实现自动 API 客户端。

| 申请建议 | 变量 | 在 Skill 中的用途 | 申请入口 |
| --- | --- | --- | --- |
| 推荐 | `OPENALEX_API_KEY` | 论文、作者、机构及合作线索；当前任职仍须官方页面核实 | [OpenAlex 设置](https://openalex.org/settings/api) |
| 推荐 | `NCBI_API_KEY` | PubMed／E-utilities 生物医学文献；提高匿名检索额度 | [My NCBI 设置](https://www.ncbi.nlm.nih.gov/account/settings/) |
| 按需 | `ORCID_CLIENT_ID`＋`ORCID_CLIENT_SECRET` | 作者身份消歧、姓名变体及公开履历 | [ORCID Public API 注册](https://info.orcid.org/documentation/integration-guide/registering-a-public-api-client/) |
| 日本方向按需 | `CINII_APP_ID` | CiNii／KAKEN 论文、研究者和科研费记录 | [CiNii 开发者注册](https://support.nii.ac.jp/en/cinii/api/developer) |
| 按需 | `SEMANTIC_SCHOLAR_API_KEY` | 论文、引文及相关研究线索；引文关系不等于合作 | [Semantic Scholar 申请](https://www.semanticscholar.org/product/api#api-key-form) |
| 有机构权限时按需 | `WOS_API_KEY` | Web of Science 文献与引文交叉核对；Key 不代表拥有 Expanded API 或特定订阅层级 | [Clarivate Developer Portal](https://developer.clarivate.com/) |

申请时打开对应入口：OpenAlex 登录后在 API 设置复制 Key；NCBI 在 Account Settings 的 API Key Management 创建；ORCID 在 Developer Tools 注册 Public API client；CiNii/KAKEN 填写 Web API 开发者表单；Semantic Scholar 提交 Request an API Key 表单并查收邮件；WoS 在门户注册应用并申请订阅计划，需向机构确认 API 权限。

**提供形式：**在用户自己的 `credentials.env` 中按 `变量名=申请到的值` 每行填写一项；这是纯文本 `.env` 文件，不是 JSON。只填写已经申请到的凭据，其他项留空或删除；ORCID 的 Client ID 和 Client Secret 要一起填写。例如（尖括号内容仅是占位符，不是真实 Key）：

```dotenv
OPENALEX_API_KEY=<你的 OpenAlex Key>
NCBI_API_KEY=<你的 NCBI Key>
ORCID_CLIENT_ID=<你的 ORCID Client ID>
ORCID_CLIENT_SECRET=<你的 ORCID Client Secret>
CINII_APP_ID=<你的 CiNii Application ID>
SEMANTIC_SCHOLAR_API_KEY=<你的 Semantic Scholar Key>
WOS_API_KEY=<你的 Web of Science Key>
```

首次检查后，请**手动编辑源仓库**的 `skills/boss-hunting/credentials.env`，按上表填写已申请到的值；空值模板来自 [config/credentials.example.env](config/credentials.example.env)。进程环境变量或 `BOSS_HUNTING_CREDENTIALS_FILE` 可显式覆盖；旧版 OS 用户配置文件仍作为兼容回退。不要在申请项目里复制或新建 Key 文件。克隆仓库本身无法生成被 Git 忽略的文件，所以创建动作发生在首次检查时。

如果首次检查提示凭据文件权限过宽，填写真实 Key 前请核对宿主系统的文件访问权限；某些 WSL Windows 盘挂载不会按 Linux 的 `chmod` 显示权限。

检查状态（只显示状态词和文件路径，不显示 Key）：

```bash
pixi run --manifest-path /path/to/boss-hunting/pixi.toml node /path/to/boss-hunting/skills/advisor-pipeline/scripts/credentials.mjs --check
```

不要把真实 Key 提交到 Git、贴进聊天或写入报告。Key 全部可选；即使尚未申请，也可继续公开来源调查。详细权限与网站目录见[公开调研策略](skills/advisor-pipeline/references/browser-research-policy.md)和[医学来源目录](skills/advisor-pipeline/references/medical-sources.md)。

## 首次使用 prompt 示例

环境检查及 API 说明完成后，在申请项目文件夹输入；如果已经告诉 Agent 医学领域、科学问题和地区，无需重发：

```text
$boss-hunting 探索肿瘤免疫治疗反应的博士导师。医学领域是肿瘤学；
问题是肿瘤微环境如何影响免疫治疗反应；地区为香港和美国。目前没有 CV。
先做方向探索，按公开证据生成 HTML 报告。
```

## Codex／Claude Code 的 Subagents

主 Agent 规划子方向、调度、裁决冲突、合并证据并生成报告。独立方向或不同 PI 可并行；同一 PI 先做身份核验，再做近五年回查和网络扩展；证据审计最后执行。

| 角色 | 责任 |
| --- | --- |
| Seed Scout | 用综述绘制概念范围，从近五年原创研究产生 PI 候选 |
| Identity Resolver | 消歧作者，并用机构页面及作者贡献核定 PI 证据等级 |
| Trajectory Mapper | 回查每位 PI 近五年研究，区分持续主线与偶发参与 |
| Network Expander | 扩展合作，区分共同研究／项目与研究邻近关系 |
| Regional Project Investigator | 按地区核对公开项目、角色、期限和状态 |
| Doctoral Trajectory Investigator | 核对可证实的博士指导关系与培养轨迹 |
| Evidence Auditor | 最后检查来源、时点、冲突、缺口及结论边界 |

Subagent 只写 `runs/<run-id>/subagents/<task_id>.json`；主 Agent 通过共享合并脚本写入权威 `outputs/` 记录。细则见[医学流程](skills/advisor-pipeline/references/medical-profile.md)与[共享契约](skills/advisor-pipeline/references/investigation-contract.md)。

## 按使用方式准备依赖

依赖由 [Pixi](pixi.toml) 管理，默认平台为 `linux-64`；Windows 使用 WSL。在 Boss Hunting 仓库运行 `pixi install`。直接使用 Skills 不需 Web 前端依赖；Web 控制台另需运行 `pixi run web-install`。

## 方式一：Web 本地控制台

在仓库运行 `pixi run dev`，具体操作及故障排查见[前端指引](docs/FRONTEND_GUIDE.md)。

## 方式二：在自己的项目文件夹中直接使用 Skills

首次检查后，将 `skills/` 安装到申请项目的 `.agents/skills/`（Codex）或 `.claude/skills/`（Claude Code）；复制时必须排除源仓库的 `credentials.env`，真实 Key 始终留在源 Skill 目录：

```bash
mkdir -p /path/to/my-project/.agents/skills
tar -C /path/to/boss-hunting/skills --exclude='./boss-hunting/credentials.env' -cf - . | tar -C /path/to/my-project/.agents/skills -xf -
# Claude Code：将目标目录改为 /path/to/my-project/.claude/skills/
```

在申请项目文件夹打开 Codex 或 Claude Code，使用上面的 prompt；Agent 只补问缺失输入，深查与申请材料按[流程入口](skills/boss-hunting/SKILL.md)确认。

## 产物

所有产物位于**申请项目**。主报告为 `outputs/<学科或方向>-导师调研.html`，在具体研究、项目与比较理由旁附来源链接；缺失来源标为待核验。导师与证据记录为 `outputs/advisor_records.json`、`outputs/evidence.json`；运行记录位于 `runs/<run-id>/`。Excel 为按阶段生成的补充产物；确认精确目标后，RP／套磁信位于 `outputs/application-materials/<advisorProgramId>/`。

在仓库根目录从共享记录重建 HTML：

```bash
pixi run report --project-root /path/to/my-project
```

更多细节见 [Web 技术说明](web/README.md)和各模块 README。
