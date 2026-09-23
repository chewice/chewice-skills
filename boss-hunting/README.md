# Boss Hunting

Boss Hunting 根据公开证据发现和比较博士导师。医学探索的最低输入只有**医学领域、疾病／机制／科学问题、目标地区**，无需 CV。流程从种子研究发现 PI、核验身份、回查近五年研究、扩展合作网络，再调查五个模块：身份与科研定位、近五年主线、合作网络、最新研究与项目、博士培养轨迹。五维证据画像分别呈现方向契合、主线连续性、PI 角色置信度、证据充分性和当前活跃度；未知事项会标明，不生成导师质量总分。申请筛选需要相关真实背景；RP 和套磁信另需真实 CV、确切导师—项目目标与用户确认。

设计参考 Ben A. Barres 的 NeuroView [*How to pick a graduate advisor*](https://doi.org/10.1016/j.neuron.2013.10.005)（[PubMed](https://pubmed.ncbi.nlm.nih.gov/24139033/)）。文章讨论导师选择与指导质量，**并非对 Boss Hunting 的验证或认可**。本 Skill 只比较可公开核验的研究、项目及指导关系等事实，不推断导师人格或组内氛围。

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

复制[空值模板](config/credentials.example.env)，填入**用户配置目录**中的 `boss-hunting/credentials.env`：Linux／WSL 位于 `~/.config/`（若设置 `XDG_CONFIG_HOME`，则在其下），macOS 位于 `~/.config/`，Windows 位于 `%APPDATA%`；也可用 `BOSS_HUNTING_CREDENTIALS_FILE` 指定路径。进程环境变量优先于文件。检查状态（只显示状态词和文件路径）：

```bash
pixi run --manifest-path /path/to/boss-hunting/pixi.toml node /path/to/boss-hunting/skills/advisor-pipeline/scripts/credentials.mjs --check
```

不要把真实 Key 提交到 Git、贴进聊天或写入报告。详细权限与网站目录见[公开调研策略](skills/advisor-pipeline/references/browser-research-policy.md)和[医学来源目录](skills/advisor-pipeline/references/medical-sources.md)。

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

将完整 `skills/` 复制到申请项目的 `.agents/skills/`（Codex）或 `.claude/skills/`（Claude Code）：

```bash
mkdir -p /path/to/my-project/.agents/skills
cp -R /path/to/boss-hunting/skills/. /path/to/my-project/.agents/skills/
# Claude Code：将目标目录改为 /path/to/my-project/.claude/skills/
```

在申请项目文件夹打开 Codex 或 Claude Code，调用：

```text
$boss-hunting 探索肿瘤免疫治疗反应的博士导师。医学领域是肿瘤学；
问题是肿瘤微环境如何影响免疫治疗反应；地区为香港和美国。目前没有 CV。
```

Agent 只补问缺失输入；深查与申请材料按[流程入口](skills/boss-hunting/SKILL.md)确认。

## 产物

所有产物位于**申请项目**。主报告为 `outputs/<学科或方向>-导师调研.html`，在具体研究、项目与比较理由旁附来源链接；缺失来源标为待核验。导师与证据记录为 `outputs/advisor_records.json`、`outputs/evidence.json`；运行记录位于 `runs/<run-id>/`。Excel 为按阶段生成的补充产物；确认精确目标后，RP／套磁信位于 `outputs/application-materials/<advisorProgramId>/`。

在仓库根目录从共享记录重建 HTML：

```bash
pixi run report --project-root /path/to/my-project
```

更多细节见 [Web 技术说明](web/README.md)和各模块 README。
