# Advisor Outreach

## 用途

为一个精确导师—项目组合起草或审计个性化套磁邮件，包括询问招生/研究契合、回应公开职位、跟进或回复。依据官方联系规则，将导师真实研究与申请者 CV 中可证明的经历连接起来，交付可复制邮件及独立审计说明。

## 运行必需依赖

- 可读取本地 CV、检索和阅读公开网页/论文并写入文本的 Agent，以及官方信息和合法公开文献的网络访问。
- 输入：真实可读 CV、确认的申请者姓名、明确导师/项目/学位/批次、联系目的，以及已有往来（回复或跟进时）。复用有效的项目 CV，不重复要求上传。
- 在 Advisor Atlas 内使用时，需完整技能集合与共享项目记录、已确认的目标及材料顺序；[advisor-pipeline](../advisor-pipeline/README.md) 提供确认、文献下载与审计脚本。
- 调用这些项目脚本时使用 [Pixi 环境](../../pixi.toml) 中 Node.js `>=22.13,<23`，默认 `linux-64`（Windows 使用 WSL）。独立在对话中起草/审阅文本不需要本技能专属安装包。

本技能不需要邮箱插件、SMTP 凭据或 LaTeX。若另行准备 RP 附件，其依赖见 [Advisor Research Proposal](../advisor-research-proposal/README.md)。

## 如何使用

在已安装技能并选定目标的申请项目内调用：

```text
$advisor-outreach 请针对我已选定的导师—项目组合，起草一封询问 2027 年博士机会的邮件。
复用项目 CV，先核对是否允许提前联系导师，再用具体论文和我的真实经历建立联系。
```

独立使用时提供目标官方页面、CV、确认姓名和联系目的；有既往邮件时同时提供必要上下文。Agent 先判断合适联系渠道，再决定正文、附件和一个主要问题，不默认选择排名第一的导师。

在项目中输出到 `outputs/application-materials/<advisorProgramId>/`：

- `outreach-email.txt`：主题、正文和附件清单。
- `outreach-audit.md`：官方联系规则、导师事实与 CV 证据的对应、引用、未解决事项和跟进建议。
- `literature/manifest.json` 及合法公开 PDF：项目材料契约要求的导师/团队和独立领域文献记录。

独立对话使用可直接返回邮件与审计两部分。技能只准备邮件，用户自行发送。详见 [SKILL.md](SKILL.md)、[写作指南](references/drafting-guide.md) 和 [材料契约](../advisor-pipeline/references/application-materials-contract.md)。
