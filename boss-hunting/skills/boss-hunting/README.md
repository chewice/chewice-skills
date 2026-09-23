# Boss Hunting Skill

医学探索从**医学领域 → 疾病／机制／科学问题 → 目标地区**开始，无需 CV。Skill 发现并核验 PI，调查身份与定位、近五年主线、合作网络、最新研究／项目、博士培养轨迹，再用五维证据画像比较。申请筛选需要真实相关背景；RP／套磁信另需真实 CV、确切目标和确认。

设计参考 Ben A. Barres 的 [*How to pick a graduate advisor*](https://doi.org/10.1016/j.neuron.2013.10.005)（[PubMed](https://pubmed.ncbi.nlm.nih.gov/24139033/)）。文章讨论导师选择与指导质量，并未验证或认可本 Skill；调查只记录可公开核验的事实。

## 凭据与 Subagents

API Key **全部可选**：`OPENALEX_API_KEY`（论文／作者／机构）、`NCBI_API_KEY`（PubMed）、`ORCID_CLIENT_ID`＋`ORCID_CLIENT_SECRET`（身份消歧）、`CINII_APP_ID`（日本 CiNii／KAKEN）、`SEMANTIC_SCHOLAR_API_KEY`（引文线索）、`WOS_API_KEY`（已有机构权限下的交叉核对）。申请入口和限制见[项目 README 凭据表](../../README.md#api-凭据)。Key 放在用户配置目录，参照[空值模板](../../config/credentials.example.env)，不要提交到 Git 或贴进聊天。缺失 Key 仍可用公开来源；当前代码做凭据状态与来源路线选择，检索由运行中的 Agent 使用可用工具执行。

Codex／Claude Code 的主 Agent 负责调度、冲突裁决、合并和报告。Seed Scout 找种子研究；Identity Resolver 核验 PI；Trajectory Mapper 回查五年主线；Network Expander 梳理合作；Regional Project Investigator 核对地区项目；Doctoral Trajectory Investigator 核对博士指导关系；Evidence Auditor 最后审计来源。独立方向或 PI 可并行，同一 PI 先核验身份再回查。子代理只写 `runs/<run-id>/subagents/`，主 Agent 合并进 `outputs/`。[调度规则](../advisor-pipeline/SKILL.md#medical-discovery-orchestration)。

## 使用与结果

在仓库运行 `pixi install`（默认 `linux-64`；Windows 使用 WSL），将完整 `skills/` 复制到申请项目的 `.agents/skills/`（Codex）或 `.claude/skills/`（Claude Code）。在项目文件夹调用：

```text
$boss-hunting 探索肿瘤免疫治疗反应的博士导师：领域是肿瘤学，
问题是肿瘤微环境如何影响免疫治疗反应，地区为香港和美国；目前没有 CV。
```

主报告位于申请项目的 `outputs/<学科或方向>-导师调研.html`；导师与来源记录为 `outputs/advisor_records.json`、`outputs/evidence.json`，运行记录在 `runs/<run-id>/`。Excel 为补充；确认精确目标后，RP／套磁信在 `outputs/application-materials/<advisorProgramId>/`。安装命令、Key 申请网址及 Web 使用方法见[项目 README](../../README.md)，执行规则见[SKILL.md](SKILL.md)。
