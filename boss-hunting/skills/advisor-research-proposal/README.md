# Advisor Research Proposal

## 用途

为一个明确导师—项目组合开发、改写或审计 Research Proposal，也可生成早期讨论用的 concept note。先核对官方要求，再以实际阅读的文献界定问题、缺口、方法、可行性和导师契合点。普通申请综述不等同系统综述。

## 运行必需依赖

- 可读取真实 CV、检索官方要求和论文、阅读 PDF、写入文档并运行本地命令的 Agent；合法公开文献的网络访问。
- 输入：真实可读 CV、确认的申请者姓名、精确导师—项目目标、材料用途及官方要求。项目中已有有效 CV 时直接复用。
- 在 Advisor Atlas 项目内使用时，需完整技能集合、共享记录和已确认的材料目标/顺序；[advisor-pipeline](../advisor-pipeline/README.md) 提供文献下载、确认和构建脚本。
- 项目 [Pixi 环境](../../pixi.toml) 中的 Node.js `>=22.13,<23`，默认 `linux-64`（Windows 使用 WSL）。
- **完整 PDF 交付额外需要**：`latexmk` 和可用的 LaTeX PDF 编译、参考文献工具链（当前脚本运行 `latexmk -pdf`，默认配合 pdfLaTeX/BibTeX）、模板用到的宏包/字体，以及 Poppler 的页面渲染/文本抽取工具用于检查全部 PDF 页面。

当前 Pixi manifest **未包含 LaTeX 和 Poppler**。仅讨论问题或审阅文本不需先编译 PDF；承诺完整交付前需确认这些工具可用。缺失时应先说明所需安装和配置，不将仅有 `.tex` 源码当作完整 PDF 交付。

## 如何使用

按 [项目安装说明](../../README.md#方式二在自己的项目文件夹中直接使用-skills) 准备技能，在已有目标的申请项目中调用：

```text
$advisor-research-proposal 请为我已选择的导师—项目组合准备一份 concept note。
复用项目里的 CV，先核对官方要求和研究问题，再开展文献综述与方法设计。
```

已有 RP 的示例：

```text
$advisor-research-proposal 用 review 模式审阅我提供的 RP，
检查问题与方法是否对应、引用是否支持论述，先给出有边界的修订建议。
```

目标和姓名不从排名或示例中推断。用户确认研究方向，项目内后置材料还需按 [材料契约](../advisor-pipeline/references/application-materials-contract.md) 确认范围。

项目产物写入 `outputs/application-materials/<advisorProgramId>/`，包含 `.tex`、`.bib`、PDF、构建记录、证据与审阅说明，以及可核验的导师/团队和独立领域文献包。内部审计问题放入 review 文件，不作为正文内容。

流程见 [SKILL.md](SKILL.md)，编译与视觉检查见 [LaTeX 交付说明](references/latex-delivery.md)。技能不提交申请。
