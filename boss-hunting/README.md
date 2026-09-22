# Boss Hunting

在现有 Advisor Atlas 工作流内，从医学研究兴趣或真实 CV 和申请目标出发，完成
候选导师发现、选择式背景调查与证据比较，并可继续为一个
明确的导师—项目组合生成可核验的 **Research Proposal（RP）** 和个性化
**套磁信（Advisor Outreach）**。

主入口为 **`$boss-hunting`（Boss Hunting）**，继续调用现有 Finder → Detective →
Evaluator；`advisor-pipeline` 保留兼容。安装时复制完整 `skills/`，包含 Boss Hunting
入口及各模块，不另建事实源。

医学配置采用四步交互：**医学领域 → 疾病/机制、研究方式与训练目标 → 地区及
申请入口 → 发现、浅筛、确认深查和比较**。已提供的信息不重复询问，泛癌、机制
优先、跨领域与明确未定均可接受；已有能力和希望学习的方法分开记录。

| 医学模式 | 输入与输出 |
| --- | --- |
| `discovery` 方向探索 | 无需 CV/学位/批次；形成真实导师及方向、训练匹配证据。未核实项目时输出导师探索表，不编造项目/资格 |
| `application` 申请筛选 | 补学位、批次、硬约束及相关真实背景；CV 或标注来源的结构化背景均可，缺失条件保持待确认 |

医学默认 `evidence_profile`，科学问题、训练支持、资格、机会、资源、研究经费、
博士资助和公开培养样本分列；不使用综合分、reach/match/safer 配额或录取概率。
通用非医学模式保留原数值匹配与组合策略。RP/套磁信仍需真实 CV、身份与确切目标确认。

执行细则：[医学画像](skills/advisor-pipeline/references/medical-profile.md)、
[国内外来源目录](skills/advisor-pipeline/references/medical-sources.md)、
[Browser Use 策略](skills/advisor-pipeline/references/browser-research-policy.md)。
目录按地区/任务给出入口、查询、字段、边界和回退，并注明本次实测/未复测范围。
默认先用 GPT 宿主实际提供的内置搜索/网页浏览工具（如 `web.run` 或 `web_search`），
按当前工具支持的动作查找并打开具体来源。内置能力不足时回退官方静态页/API；动态
JS 表单才按需使用已有交互式浏览器。`backend` 默认 `builtin_web`，旧 `auto` 同样
内置优先，用户显式选择的后端保留。enabled 不自动安装工具、连接付费云或上传CV。
内置网页检索记录实际工具/提供方和 `static_web`，不冒称安装或实测了 Browser Use。
深查候选与维度确认保留，医学公开资源调查不自动下载社区资料。

最终导师调研结果以 **HTML** 为主，按学科领域/研究方向命名，例如
`肿瘤免疫-导师调研.html`。版面简洁，重点呈现候选比较、证据、未知和下一步；
文件写入项目 `outputs/`。原 Excel 继续作为补充导出。共享生成器
`skills/advisor-pipeline/scripts/build_advisor_report.mjs --project-root PATH`
直接读取已有记录，不重新联网或维护第二份事实源。
每项研究、经费、培养、资格、截止日期和比较依据旁直接附对应的具体来源超链接，
可就地点击复核；页尾汇总仅作补充。链接来自共享证据记录，缺少具体来源的内容
明确标为待核验，不编造网址；报告保持简洁，并仅允许安全的 HTTP(S) 外部链接。

## Pixi 依赖环境

仓库的 `pixi.toml` 统一管理运行入口，默认且仅声明 `platforms = ["linux-64"]`。
工作区名 `boss-hunting` 已按小写名称规则校验。Conda-forge 提供 Node.js 22
和 Python；前端 JS 包保留原 `web/package-lock.json`，通过 Pixi 任务调用 `npm ci`，
不再另建一份 JS 依赖清单。纯 Skills、HTML 和内置 OOXML 导出无需安装 Excel 库。

```bash
pixi install
pixi run check-runtime
pixi run web-install
pixi run test
pixi run typecheck
pixi run lint
```

只验证无前端构建依赖的逻辑时用 `pixi run test-core`；完整 `test` 先构建 Web。
`typecheck` 在已有 Web 构建后，用锁定的 Wrangler 从实际构建配置生成本地类型，
分别检查浏览器和 Worker 源码，避免两种环境的全局类型互相覆盖；不执行部署。
重新导出 HTML：`pixi run report --project-root /path/to/application`。
首次使用须有可用 Pixi 及包源网络；这些任务不安装或启用浏览器服务。
`pixi run init` 是可选编辑器设置任务，会覆盖 `.vscode/settings.json`，不会自动执行；
保留的模板含 R 路径，但本 Skill 不需要也不会安装 R。Windows 默认通过 WSL 使用此
Linux 环境，其他平台须明确扩展 manifest 后另行验证。

### 按使用方式准备依赖

| 使用范围 | 必需依赖 | 按需依赖与边界 |
| --- | --- | --- |
| 直接调用 Skills | 能读取本地 Skills、文件和公开网页的 Agent；完整 `skills/`；Pixi 运行环境中的 Node.js `>=22.13,<23` | 不必安装 Web 的 npm 包；纯 HTML 和 Excel 导出使用内置实现，不要求 `@oai/artifact-tool` |
| Web 本地控制台 | 上述 Pixi 环境、`web/package-lock.json` 对应的 npm 包、浏览器；已登录的 Codex/Claude Code，或可用的自定义 Responses API | 运行 `pixi run web-install` 安装前端/桥接依赖；API 模式另需接口地址和 Key |
| 公开导师检索 | 优先 GPT 宿主实际暴露的内置搜索/网页读取工具 | 官方静态页/API回退；动态JS/表单才用已有交互浏览器。不绑定必须安装的 Browser Use 服务或付费账号 |
| 社区 PDF 本地检索 | Python `>=3.11,<3.13`；`pdftotext`（Poppler）或 Python `pypdf` 二选一 | 仅在用户同意社区资料下载时需要；Python 已在 Pixi 中，PDF 抽取器未写入当前 manifest |
| RP 的完整 PDF 交付 | `latexmk` 及可用的 LaTeX/PDF 编译和参考文献工具链（当前构建器使用 `latexmk -pdf`），模板用到的宏包/字体；Poppler 页面渲染和文本抽取工具 | LaTeX、Poppler 均未写入当前 manifest；缺少时需先说明并另行配置，不能把仅有源文件的结果当成完整交付 |

依赖范围以 [pixi.toml](pixi.toml)、[Web 包清单](web/package.json) 和各 Skill
的 README 为准。准备申请材料还需可读取的真实 CV、确认的申请者姓名、精确的
导师—项目目标和合法公开文献访问；这些是运行输入，不是软件安装包。
按需启用的 PDF/LaTeX 工具也应补入同一 Pixi 工作区管理，并单独验证，
不要用全局安装替代；当前基础环境不声称这些可选工具链已经就绪。
套磁邮件仅生成文本和审计记录，不需要邮箱插件或邮件发送凭据。

## 从找导师到准备申请材料

| 能力 | Advisor Atlas 会做什么 | 主要产物 |
|---|---|---|
| 导师发现 | 解析医学画像或真实 CV，在目标范围内发现导师并完成研究匹配 | 候选名单、研究匹配证据 |
| 客观筛选 | 核对项目、学位、申请季、截止日期、材料与招生条件 | advisor—program 可行性记录 |
| 导师背调 | 按用户选择的导师和维度调查论文主线、项目、招生与风险 | 背调证据与风险提示 |
| 最终决策 | 医学采用分维度证据画像；通用模式保留数值匹配 | 按学科/方向命名的 HTML 主报告，Excel 补充与结构化比较 |
| Research Proposal | 先核对官方格式，再完成文献综述、研究问题、方法、可行性与引用审计 | LaTeX、BibTeX、PDF、review 与 evidence 文件 |
| 套磁信 | 用导师事实和申请者真实经历建立具体连接，按联系规则生成可复制邮件 | 邮件正文、证据桥与引用审计 |

RP 和套磁信不是通用模板，也不会自动套用排名第一的导师。用户必须选择一个精确
`advisorProgramId`，确认材料种类和生成顺序后才会开始。两类材料都会复用项目最初
上传的 CV；CV 仍然有效时不会重复索要。

引用过的导师/团队文献和独立领域文献会保存为合法公开 PDF，并记录来源、关系证据、
读取层级、用途、SHA-256 和本地路径。系统只生成材料，不会发送邮件或提交申请。

本项目只有两种使用方式：

| 使用方式 | 适合谁 | 在哪里操作 |
|---|---|---|
| **方式一：Web 本地控制台** | 希望用图形界面填写资料、选择模型并查看进度 | 浏览器中的 `http://localhost:3000/` |
| **方式二：在自己的项目文件夹中直接使用 Skills** | 习惯 Codex Desktop、Codex CLI 或 Claude Code，希望由 Agent 直接管理文件 | 自己创建的本地申请项目文件夹 |

两种方式使用的是同一组导师匹配 Skills。区别只是由 Web 前端驱动，还是直接让 Codex / Claude 在项目文件夹中调用 Skills。

> 第一次使用或准备修改前端时，请先阅读 [Advisor Atlas 前端使用与维护指引](docs/FRONTEND_GUIDE.md)。
>
> **如何选择：** Web 和直接使用 Skills 共享同一套状态、确认和产物校验契约。希望有表单、进度和授权卡片时使用 Web；希望完全控制项目目录或在终端中工作时使用 Codex Desktop、Codex CLI 或 Claude Code。

```text
医学画像 或 真实 CV + 申请目标
        ↓
候选导师发现与匹配
        ↓
重点导师背景调查
        ↓
分维度证据比较（通用模式可数值评分）
        ↓
用户选择并确认一个精确导师—项目组合
        ↓
Research Proposal（LaTeX + BibTeX + PDF）
和/或个性化套磁信（可复制邮件 + 引用审计）
```

## 方式一：使用 Web 本地控制台

Web 模式适合不想一直在终端里操作的用户。你可以在页面中创建申请项目、上传 CV、填写研究兴趣、选择模型并查看运行进度。

### 1. 本地登录 Codex 或 Claude

Web 前端本身不提供 Codex 或 Claude 账号登录。请先在自己的电脑上安装并登录至少一个本地执行工具：

```bash
# 检查 Codex
codex --version
codex login

# 检查 Claude Code
claude --version
claude
```

只需要 Codex 或 Claude Code 其中一个可用。登录完成后，Web 控制台会自动检测本机状态。

> Web 控制台也保留自定义 API 高级选项，但这仍属于 Web 使用方式，不是第三种运行模式。

### 2. 启动 Web 控制台

```bash
pixi install
pixi run web-install
pixi run dev
```

然后打开：

- Web 控制台：<http://localhost:3000/>
- 本地桥接服务：<http://127.0.0.1:4318/>

`pixi run dev` 会同时启动前端和本地桥接服务。停止时按 `Ctrl+C`。
请从仓库根目录运行；Node.js 来自项目 Pixi 环境，不要求另外安装全局 Node。

### 3. 在网页中开始

1. 点击“新建申请项目”，填写项目名称。
2. 填写目标院校或地区范围。
3. 选择领域配置和探索/申请模式；医学先完成四步画像，探索无需 CV，申请可填真实结构化背景。通用模式上传可读真实 CV。
4. 填写申请者真实姓名，供后续 RP 与套磁信核验。
5. 如有地区、排除国家、排名、费用或 funding 底线，填写“必须满足的硬条件”。
6. 设置 Phase 1 希望保留的导师数量（默认 10）；通用模式另可选择均衡、稳妥或冲刺组合，医学不采用配额。
7. 保存申请资料。
8. 随时选择本机已登录的 Codex 或 Claude Code。
9. 点击“开始寻找导师”。
10. 正式申请条件筛选前补齐学位和申请季；医学探索可在导师层面结束。
11. 选择重点导师，并勾选需要的背景调查维度。
12. P2 显示“已完成”后直接查看背调结果；需要补充维度时再重新运行。
13. 生成医学证据比较或通用排名；主要查看 `outputs/` 按领域命名的 HTML 报告，Excel 为补充，医学序号不是质量排名。
14. 从最终排名中选择一个精确导师—项目组合，选择 RP、套磁信或两者及其顺序。
15. 检查最终确认摘要；确认后再启动 RP 或套磁信生成。

Phase 1 的最低输入未完成前，网页和后端只阻止启动任务，不阻止用户先选择模型。候选导师、背调证据和最终排名在任务真正开始前均为 `0`，不会显示演示结果。

Agent 需要执行命令、修改文件或申请网络权限时，网页会暂停并显示结构化授权卡片。用户可选择“允许一次”“本次运行允许”或“拒绝”，无需切回终端回答 CLI 提示。

在要求 CV 的通用流程或材料模块中，CV 缺失、不可读或不是真实申请者材料会进入“等待补充资料”。在运行面板上传替换 CV 并点击“保存并继续本轮”，可继续原 run 和会话；医学探索不因无 CV 被阻止。

### Web 模式支持的模型

| 模型来源 | 使用方式 |
|---|---|
| Codex | 先在本机完成 Codex CLI 登录，控制台自动检测 |
| Claude Code | 先在本机完成 Claude Code 登录，控制台自动检测 |
| 自定义 API（高级） | 填写 Base URL 和 Key，读取模型列表后选择精确模型 ID；项目自带本地 Codex 运行引擎，不要求登录 Codex |

自定义接口需要兼容 OpenAI Responses API，并提供 `GET /models`。API Key 只保存在当前本地桥接进程的内存中，服务重启后需要重新连接。

### Web 项目放在哪里

Web 创建的申请项目默认位于仓库根目录的 `projects/`：

```text
projects/
└── application-20260726-135030-abcd/
    ├── project.json
    ├── status.json
    ├── inputs/
    │   └── <上传的 CV>
    ├── outputs/
    │   ├── candidates.json
    │   ├── candidates-excluded.json
    │   ├── matching-audit.json
    │   ├── advisor_records.json
    │   ├── program_records.json
    │   ├── evidence.json
    │   └── application-materials/
    │       └── <advisorProgramId>/
    │           ├── research-proposal.tex
    │           ├── references.bib
    │           ├── research-proposal.pdf
    │           ├── outreach-email.txt
    │           ├── proposal-review.md / outreach-audit.md
    │           └── literature/
    │               ├── manifest.json
    │               ├── advisor-work/*.pdf
    │               └── field-work/*.pdf
    ├── community-cache/       # 仅在明确同意后生成
    ├── runs/
    │   └── <run-id>/
    ├── .agents/
    │   └── skills/
    └── .claude/
        └── skills/
```

网页创建项目时只需填写项目名称，后端会自动生成文件夹 ID。不同申请项目不会共用 CV、状态或运行记录。

- `project.json`：申请季、目标范围、研究兴趣、精确导师选择和调查维度
- `status.json`：当前工作流阶段和结果数量
- `inputs/`：上传的 CV
- `outputs/`：候选名单、工作簿和报告
- `community-cache/`：用户明确同意后下载的本地第三方社区资料，可在页面中清除
- `runs/`：每次执行的元数据与事件
- `.agents/skills/`：Codex 项目级 Skills
- `.claude/skills/`：Claude Code 项目级 Skills

`projects/` 和 `.advisor-atlas/` 已加入 Git 忽略列表，避免把个人申请材料和本地运行配置误提交到仓库。

申请资料和任务结果保存在本地项目目录；执行任务时，本次任务需要的内容会由你选择的模型服务处理。

## 方式二：在自己的项目文件夹中直接使用 Skills

这种方式不需要启动 Web 前端。创建项目文件夹，放入完整 Skills 与当前模式所需资料，然后让 Codex 或 Claude 工作。医学探索可以暂不放 CV。

这里的 Desktop 主要指 Codex Desktop；Claude 侧使用 Claude Code 在项目文件夹中运行。

### 1. 创建自己的申请项目文件夹

```bash
mkdir -p ~/Documents/my-advisor-application
cd ~/Documents/my-advisor-application
```

把 CV、目标学校说明或其他申请资料放进这个文件夹。例如：

```text
my-advisor-application/
├── My_CV.pdf
└── application_notes.md
```

每个申请项目都应该使用不同文件夹，例如：

```text
Documents/
├── 2027-us-hci-phd/
├── 2027-europe-ai-phd/
└── postdoc-health-ai/
```

这样不同项目的 CV、候选导师、状态文件和输出结果不会混在一起。

### 2. 选择让 Codex 或 Claude 使用 Skills

#### 选择 Codex

把完整 Skills 复制到项目的 `.agents/skills/`：

```bash
mkdir -p ~/Documents/my-advisor-application/.agents/skills
cp -R /path/to/boss-hunting/skills/* \
  ~/Documents/my-advisor-application/.agents/skills/
```

复制后的结构：

```text
my-advisor-application/
├── My_CV.pdf
└── .agents/
    └── skills/
        ├── boss-hunting/
        ├── advisor-finder/
        ├── advisor-detective/
        ├── advisor-evaluator/
        ├── advisor-research-proposal/
        ├── advisor-outreach/
        └── advisor-pipeline/
```

然后选择一种打开方式：

- 在 Codex Desktop 中打开 `my-advisor-application` 文件夹。
- 或者在终端中进入该文件夹后运行 `codex`。

```bash
cd ~/Documents/my-advisor-application
codex
```

#### 选择 Claude Code

把完整 Skills 复制到项目的 `.claude/skills/`：

```bash
mkdir -p ~/Documents/my-advisor-application/.claude/skills
cp -R /path/to/boss-hunting/skills/* \
  ~/Documents/my-advisor-application/.claude/skills/
```

复制后的结构：

```text
my-advisor-application/
├── My_CV.pdf
└── .claude/
    └── skills/
        ├── boss-hunting/
        ├── advisor-finder/
        ├── advisor-detective/
        ├── advisor-evaluator/
        ├── advisor-research-proposal/
        ├── advisor-outreach/
        └── advisor-pipeline/
```

然后在终端中进入项目并启动 Claude Code：

```bash
cd ~/Documents/my-advisor-application
claude
```

#### 同一个项目同时支持 Codex 和 Claude

如果你希望之后可以自由切换，可以同时保留两套项目级目录：

```text
my-advisor-application/
├── My_CV.pdf
├── .agents/skills/    # Codex 使用
└── .claude/skills/    # Claude Code 使用
```

两边都复制完整 Skills，不要只复制 `SKILL.md`。`advisor-finder` 目录还包含生成工作簿所需的脚本。

### 3. 在 Codex 或 Claude 中调用 Skill

打开项目文件夹后，例如医学探索（示例输入，不是真实检索成果）：

```text
使用 $boss-hunting 做医学方向探索。领域是肿瘤，机制优先并保留泛癌范围，
希望做计算与数据研究，未来学习统计建模；已有能力暂未提供。
地区选中国香港和美国，暂未确定学位项目与入学批次，没有 CV。
先做公开浅查和证据比较；深查仍等我选择确切候选和维度。
```

医学申请筛选示例（同样只是输入示例）：

```text
使用 $boss-hunting 继续医学申请筛选，复用已有方向探索。
目标为指定地区的研究型 PhD 和我提供的真实入学批次；背景以我提供的
结构化学历、研究经历、资格为自述。只核对相关条件，缺失项待确认。
研究经费与博士资助分开比较，暂不开始 RP 或套磁信。
```

通用模式输入示例：

```text
使用 $boss-hunting 开始通用导师匹配。

先读取当前项目中的真实 CV，并检查：
1. CV 是否真实、可读取
2. 目标学校或目标范围
3. 研究兴趣与权重
4. 目标学位
5. 申请季

如果缺少信息，请先询问我，不要编造。

Phase 1 完成后不要自动选择 Top N 进入背调。请像 Web 前端一样：
1. 展示可选择的真实导师—项目组合；
2. 展示全部调查维度，并默认选择前三项；
3. 让我选择导师和调查维度；
4. 如涉及导师风评，单独询问是否允许本地社区资料；
5. 展示预计消耗和最终配置，得到我确认后再开始 Phase 2。
```

首次直接运行时，`advisor-pipeline` 会在当前文件夹初始化与 Web
兼容的 `project.json`、`status.json` 和 `outputs/`。CLI 与 Web 使用同一套
结构化状态、三阶段分析和后置申请材料流程，区别只在于 CLI 用编号菜单代替网页复选框。

Phase 1 完成后，CLI 会显示类似下面的选择门：

```text
导师—项目组合：
[1] Prof. A｜University A｜PhD in CS｜匹配 8.9｜eligible
[2] Prof. B｜University B｜PhD in HCI｜匹配 8.3｜needs_confirmation

调查维度：
[1] 基础身份与当前职位（默认）
[2] 最近三年研究兴趣与方向（默认）
[3] 近期项目与招生状态（默认）
[4-11] 其余可选维度

回复示例：
导师：1,2
维度：保留默认，并增加 5,6,10
社区资料：不允许
```

Agent 必须在显示精确导师、维度、预计消耗和社区资料授权的最终摘要后
等待确认。菜单操作只保存草稿；只有最终确认才生成可供 Phase 2 使用的
确认快照。只给人数、导师姓名或“Top N”不能代替精确选择。

也可以只调用某个阶段：

```text
使用 advisor-finder 帮我寻找候选导师。
```

```text
使用 advisor-detective 对候选导师进行背景调查。如果当前项目还没有保存
精确导师—项目和调查维度，请先展示与 Web 前端一致的完整选项并等待我确认，
不要自动按 Top N 开始。
```

```text
使用 advisor-evaluator 根据已有证据生成最终排名。
```

```text
使用 advisor-research-proposal，先核对我的真实 CV 和真实姓名，再针对我明确
选择的 advisorProgramId 核对官方 RP 要求，完成文献综述、研究设计和可行性审计。
```

```text
使用 advisor-outreach，先核对我的真实 CV 和真实姓名，再针对我明确选择的
advisorProgramId，基于导师证据和官方联系要求起草套磁信，不要发送邮件。
```

这种模式下，输出文件直接保存在你自己的申请项目文件夹中，不会出现在 Web 控制台的 `projects/` 列表里。

## 两种方式如何选择

| 需求 | 推荐方式 |
|---|---|
| 第一次使用，希望有填写引导 | Web 本地控制台 |
| 想在页面里看到 0/5、候选数量和任务进度 | Web 本地控制台 |
| 已经在 Codex Desktop 中管理科研项目 | 直接使用 Skills |
| 习惯在终端中使用 Codex 或 Claude Code | 直接使用 Skills |
| 希望完全控制自己的项目目录结构 | 直接使用 Skills |
| 希望在一个界面里管理多个申请项目 | Web 本地控制台 |

通常选择一种方式作为项目的主入口：选择 Web 时由 Web 管理 `projects/`；选择直接使用 Skills 时，在你自己创建的项目文件夹中完成全部工作。

## 递进式三阶段分析 + 申请材料

### 阶段 1：导师发现、研究匹配与客观申请筛选

`advisor-finder` 根据医学画像或 CV、目标范围与研究兴趣：

- 按用户选择的 Top N 构建更大的目标院校或院系导师发现池
- 低成本核对身份、研究方向、代表作与官方招生信号
- 先识别导师主导、委员会主导、公开岗位或结构化项目，再决定套磁、项目申请或岗位申请
- 先执行用户的硬条件；不满足即排除，证据不足保持待核实
- 将导师映射到真实学校、项目、学位和申请季
- 对研究匹配后的 shortlist 补齐截止日期、学费、奖学金、材料、RP 和联系要求
- 分开显示研究匹配、CV 履历匹配、申请定位、机会证据和客观申请可行性，不把 QS 或学校名气混入研究匹配分
- 用确定性脚本控制 shortlist（仅通用模式控制冲刺比例），保留排除项和 matching audit
- 记录来源并生成匹配结果

Finder 浏览导师或项目页面时已经发现的信息会立即保存；后续只查询缺失、过期或冲突字段。同一项目的信息只查一次，再关联到多位导师。

通用模式候选表的“综合匹配”由确定性脚本按 `60% 研究匹配 + 40% CV 履历匹配`
计算，并保留一位小数；它不是录取概率。硬条件、客观资格、申请路径和当前机会
证据始终单独展示，不能被高分覆盖。系统会依次处理：排除已确认的硬失败 → 核实
未知申请路径 → 核实未知硬条件 → 核实未知申请资格 → 按官方路径联系导师、申请
项目或申请公开岗位。缺失信息保持“待核实”，不会被换算成 0 分。

Web 每轮只把当前阶段的 Skill 加入 Agent 上下文：Finder、Detective、Evaluator、RP 和 Outreach 不会先加载完整 Pipeline 或其他阶段规则。直接使用 Skills 时，`advisor-pipeline` 仍负责跨阶段编排；各阶段内部再按需读取共享契约和 reference。

### 阶段 2：按勾选维度背景调查

`advisor-detective` 对选中的导师继续调查：

- 基础身份与当前职位、最近三年研究方向、近期项目与招生状态（新项目默认勾选）
- 研究产出与趋势
- 课题组成员及去向
- 指导环境、组内生态与工作方式
- 资源、funding、署名和职业支持
- 学术诚信、公开争议、国际学生支持及合作网络

不再使用 `shallow / medium / high`。通用默认前三项；医学默认另含研究轨迹、博士培养、资源及合作，菜单统一由共享目录生成。用户选什么就查什么，未选标“用户未选择复核”；已有事实复用。医学 `public_only` 不因资源维度自动触发社区资料授权。用户显式扩展社区调查并独立同意后，才按原机制下载/检索；匿名内容只作线索。

### 阶段 3：证据比较或通用排名

`advisor-evaluator` 分开汇总研究与训练匹配、背景、硬条件、申请路径、机会、资格和所选背调维度。医学探索生成探索表，申请阶段生成申请比较表；通用流程保留申请就绪总表与数值排序。明确不适用的机会不会被综合分覆盖，未知也不当作不合格。

评分用于辅助筛选，不替代申请者对导师风格、招生状态和合作方式的独立判断。

### 后置申请材料：RP 与套磁信

完成排名后，用户先选择精确的 `advisorProgramId` 和材料目的，再按官方要求调用：

- `advisor-research-proposal`：核对目标项目格式，完成问题收窄、可追溯文献综述、
  gap、问题—方法映射、伦理/可行性和引用审计。
- `advisor-outreach`：核对联系规则，以“导师事实 → 申请者真实证据 → 可辩护连接”
  起草首封、招聘回复、follow-up 或回信。

两者没有固定先后。需要随首封附 RP 时先做 RP；首封只询问招生/申请路径时先写
邮件。Web 和 CLI 都会要求再次选择精确目标、材料和顺序，并展示最终摘要等待确认。
确认后才允许搜索、下载和写作；排名第一不会被自动选中。后置材料保存在
`outputs/application-materials/<advisorProgramId>/`，不会自动发送或提交。

每种材料都必须同时列出导师本人/团队文献与独立领域文献。实际引用只接受合法
公开版本，PDF 下载到本地并在 `literature/manifest.json` 记录 canonical URL、
公开获取依据、读取层级、用途、SHA-256 和文件大小；导师文献还必须记录“导师本人
署名”或“已核验团队作者”的关系证据，领域文献不得含目标导师署名。Web 会直接列出
每条引用及本地路径；不得绕过付费墙。缺少任一类
文献、文件或校验信息时，本轮显示为 `partial`，不会把流畅文本冒充完成结果。
已经下载且 URL、公开获取依据、文件大小和 SHA-256 都匹配的 PDF 会直接复用；只有
显式刷新或完整性检查不一致时才重新下载。

完整调研和证据边界见 [`docs/OUTREACH_RP_RESEARCH.md`](docs/OUTREACH_RP_RESEARCH.md)。
Skill 与 Pipeline 的运行开销、风险和测试证据见
[`docs/SKILL_TOKEN_OPTIMIZATION.md`](docs/SKILL_TOKEN_OPTIMIZATION.md)。

## Skills 与兼容入口

| Skill | 作用 |
|---|---|
| [boss-hunting](skills/boss-hunting/README.md) | Boss Hunting 主入口，调用同一现有流程 |
| [advisor-finder](skills/advisor-finder/README.md) | 发现真实候选、完成研究匹配和客观申请筛选 |
| [advisor-detective](skills/advisor-detective/README.md) | 按用户勾选维度对重点导师进行证据化背景调查 |
| [advisor-evaluator](skills/advisor-evaluator/README.md) | 分开汇总主客观结论并生成申请就绪总表 |
| [advisor-research-proposal](skills/advisor-research-proposal/README.md) | 为精确导师—项目生成或审计证据化 RP |
| [advisor-outreach](skills/advisor-outreach/README.md) | 为精确导师—项目起草或审计个性化套磁邮件 |
| [advisor-pipeline](skills/advisor-pipeline/README.md) | 编排三阶段分析与后置申请材料 |

Skills 源文件位于：

```text
skills/
├── boss-hunting/
├── advisor-finder/
├── advisor-detective/
├── advisor-evaluator/
├── advisor-research-proposal/
├── advisor-outreach/
└── advisor-pipeline/
```

## 输出与状态

根据执行阶段，项目可能产生：

- `ADVISOR_STATE.md`
- `DETECTIVE_STATE.md`
- `EVALUATOR_STATE.md`
- `outputs/<学科领域或方向>-导师调研.html`（主报告）
- `outputs/discovery-view.json`（医学探索派生视图）
- `advisor_research_discovery_<日期>.xlsx`（探索补充）
- `advisor_shortlist_<日期>.xlsx`
- `advisor_detective_<日期>.xlsx`
- `advisor_application_ready_<日期>.xlsx`
- `outputs/application-materials/<advisorProgramId>/research-proposal.tex`
- `outputs/application-materials/<advisorProgramId>/references.bib`
- `outputs/application-materials/<advisorProgramId>/research-proposal.pdf`
- `outputs/application-materials/<advisorProgramId>/proposal-build.json`
- `outputs/application-materials/<advisorProgramId>/proposal-evidence.md`
- `outputs/application-materials/<advisorProgramId>/proposal-review.md`
- `outputs/application-materials/<advisorProgramId>/outreach-email.txt`
- `outputs/application-materials/<advisorProgramId>/outreach-audit.md`
- `outputs/application-materials/<advisorProgramId>/literature/manifest.json`
- `outputs/application-materials/<advisorProgramId>/literature/advisor-work/*.pdf`
- `outputs/application-materials/<advisorProgramId>/literature/field-work/*.pdf`
- `outputs/candidates.json`
- `outputs/advisor_records.json`
- `outputs/program_records.json`
- `outputs/evidence.json`
- `outputs/detective-results.json`
- `outputs/ranking.json`
- `runs/<run-id>/events.ndjson`（Web 模式）

具体结果取决于使用的 Skill、搜索范围和模型是否完成了对应任务。
三类 Excel 均由仓库随附的确定性 Builder 生成：有 Codex Spreadsheet Runtime
时优先使用它，普通 Windows/macOS/Linux 环境则自动使用无额外安装的 OOXML
后备。用户不需要也不应手动安装 `@oai/artifact-tool`。

### 社区资料隐私与版权边界

- 公开仓库只保存来源链接、同步机制、证据规则和隐私规则，不保存下载快照。
- 公开可访问不等于获得再分发授权。
- 快照仅在用户明确同意后保存到当前申请项目本地，并可从页面清除。
- PDF 没有成功生成可搜索文本时，必须标记“未完成检索”，不能写“未发现记录”。
- 镜像、转载和同源引用不算多个独立证据。

## 常见问题

### Web 页面为什么显示候选导师、背调证据都是 0？

这是新项目的真实初始状态。只有导师搜索实际产生候选结果后，数字才会更新。

### Web 中“开始寻找导师”为什么不能点击？

每个阶段的前置条件不同，按钮读取的是同一份 readiness matrix：

| 阶段 | 必需条件 |
| --- | --- |
| Finder 1A（通用导师发现） | 目标院校或地区范围 + 一份可读取的真实 CV |
| Finder（医学方向探索） | 已确认医学画像及地区，可明确未定/不限；无需 CV/学位/批次 |
| Finder（医学申请筛选） | 医学画像、学位、批次、相关真实 CV 或结构化背景；缺失资格保持待确认 |
| Finder 1B（客观筛选） | 1A 已产出候选 + 目标学位 + 申请季 |
| Detective（背调） | 带稳定 `advisorProgramId` 的候选 + 与当前草稿一致的已确认配置 |
| Ranking（综合排名） | 至少一条 Detective 结果 |
| RP / 陶瓷信 | 有效真实 CV + 已确认申请者姓名 + 当前排名中的精确 `advisorProgramId` + 材料/顺序确认快照；后一个材料还需前一个通过产物校验 |

“开始寻找导师”按当前模式检查对应输入。通用流程不能以兴趣代替 CV；医学探索接受无 CV，医学申请接受注明来源的真实背景。探索未做的资格核验不标为通过。

另外请确认 Codex 或 Claude 至少有一个显示为“可用”。通用 Finder 或 RP/套磁信所需 CV 被移动、删除或是占位材料时，会暂停并要求修复后继续原会话。医学模式按对应真实背景要求处理；RP/套磁信仍须补齐真实姓名和 CV，不生成示例署名成品。

### 关掉运行面板会不会把任务杀掉？

不会。关闭面板只是隐藏它，任务仍在后台运行，顶栏会显示“任务运行中”。点击它可以重新接回原任务，包括之前的日志和还没处理的授权请求；刷新页面同样会自动接回。要真正停止，请在面板底部点“取消任务”。

同一个申请项目同时只允许一个任务：重复启动会返回 409，并直接接回已经在跑的那个。不同项目之间仍可并行。

### 为什么模型说“做完了”，页面却显示“本轮已结束，但尚未产生 Phase 2 结果”？

因为完成状态以磁盘真实产物为准。医学探索从真实导师记录派生结果，申请流程按阶段校验 `candidates.json` / `detective-results.json` / `ranking.json`；HTML 主报告及兼容工作簿需与记录一致。RP/套磁信另外校验确认版本、两类文献、目标导师关系、本地 PDF、manifest 和引用审计。缺失、错配、非法 JSON 或旧确认版本均不能被模型一句“完成”代替。

### 日志提示缺少 `@oai/artifact-tool` 或反复出现 `apply_patch verification failed`，怎么办？

更新到最新版本后，Excel Builder 会在该组件不可用时自动走仓库内置的便携
OOXML 路径，不再要求 Agent 临时创建和修改 `build_phase*_artifacts.mjs`。请先
`git pull`，再重新启动 Web；已有 JSON 和证据可以直接复用，只重新生成缺少的
Excel，不需要重新搜索导师或重跑整个阶段。

如果最新版本仍出现该提示，请检查运行日志中的 `workbookEngine`。正常值为
`artifact-tool` 或 `portable-ooxml`；工作簿需能通过完整 XLSX 校验，最终导师调研
还要求与共享数据一致的 HTML 主报告。设计与风险说明见
[`docs/EXCEL_RUNTIME_COMPATIBILITY.md`](docs/EXCEL_RUNTIME_COMPATIBILITY.md)。

### Web 为什么检测不到 Codex 或 Claude？

Web 使用的是本机 CLI 登录状态。请先在普通终端中确认对应命令已经安装并登录，然后在页面的运行面板中点击“刷新状态”。

普通终端、VS Code 集成终端与 Web 本地控制台在同一系统用户下运行时，通常
共享 Codex/Claude 的登录缓存，因此在哪里完成 CLI 登录都可以被检测到。Web
检测的是“CLI 已安装且登录有效”，不是某个 App 或终端窗口是否正在打开；仅仅
启动一个 `codex`/`claude` 进程不会改变检测结果。通过自定义中转站环境变量或
Codex custom provider 启动的终端也不会自动变成 Web 的 Custom API 连接，仍需
在 Web 高级设置中单独填写 Base URL、Key 和模型。

### Custom API 运行时报错 “spawn codex ENOENT”，怎么办？

这表示中转站的接口、Key 和模型列表可能已经验证成功，但旧版本仍依赖系统中
另行安装的 `codex` 命令，真正启动任务时找不到本地 Agent 运行引擎。更新后
Codex app-server 已随 Web 依赖安装；无需登录 Codex：

```bash
git pull
cd web
npm install
npm run dev
```

### 运行任务时报错 “spawn EINVAL”，怎么办？

**这个问题已经修复，请更新到最新版本的项目代码。**

```bash
git pull
cd web
npm install
npm run dev
```

原因：旧版本在启动本地任务时，让子进程独立成新会话（`detached`）。该选项依赖的系统底层标志在部分系统上不被支持，会被直接拒绝并返回 `EINVAL`，任务因此在模型服务真正启动前就中断。

这个报错与以下因素**都无关**，不需要在这些方向排查：

- **Node.js 版本**：升级 Node 不能解决，新旧版本都会出现
- **所选模型**：Codex、Claude Code、自定义 API 三条路径都会遇到，因为它们经过同一段启动代码
- **网络或 API 配置**：报错时子进程尚未创建，还没有发出任何一次请求

如果更新代码后仍然报错，请提供 `node -v` 的输出，以及你的操作系统版本（macOS 运行 `sw_vers`，Windows 在“设置 → 系统 → 关于”中查看）。

如果升级 Node 后问题依旧，请换一个全新的普通终端窗口重新启动本地控制台（不要通过其他脚本或工具间接拉起），再试一次。

### 直接使用 Skills 时，为什么 Codex 或 Claude 没识别到？

检查：

- 当前打开的是否为正确申请项目文件夹
- Codex 是否使用 `.agents/skills/`
- Claude Code 是否使用 `.claude/skills/`
- 是否复制了完整 Skill 目录
- 是否在复制 Skills 后重新打开了会话

### 可以从 Web 切换到直接使用 Skills 吗？

可以。Web 创建的每个项目已经包含 `.agents/skills/` 和 `.claude/skills/`，两边共用同一套 schemaVersion 8 契约。

```bash
cd "projects/<project-id>"  # 将 <project-id> 替换为实际项目 ID
node .agents/skills/advisor-pipeline/scripts/init_project.mjs --root "$PWD" --check
codex   # 或 claude
```

`--check` 是只读校验，会指出缺失或不合法的文件；不带 `--check` 会确定性地补齐结构，且不会覆盖已有的 Finder / Detective 产物。Web 与这些 CLI 写入脚本共用项目级文件锁；若另一个操作正在写入，会等待或明确提示稍后重试，不再各自基于旧快照覆盖 `project.json`。

这些 CLI 脚本会规范化真实路径，因此从 macOS 的 `/tmp`、软链接后的项目目录或软链接后的 Skill 目录调用时也会正常执行，不会出现“退出码为 0 但没有输出或文件”的静默失败。

选择阶段请用确定性脚本渲染菜单，不要让模型自由排版：

```bash
node .agents/skills/advisor-pipeline/scripts/render_investigation_menu.mjs --root "$PWD"
```

完成排名后，申请材料同样先使用确定性菜单与确认脚本：

```bash
node .agents/skills/advisor-pipeline/scripts/render_application_materials_menu.mjs --root "$PWD"
node .agents/skills/advisor-pipeline/scripts/confirm_application_materials.mjs \
  --root "$PWD" --confirmed-by-user \
  --advisor-id exact-advisor-program-id \
  --materials research_proposal,outreach_email \
  --order research_proposal,outreach_email
```

Web 管理的项目还可在仓库 `web/` 目录运行
`npm run backend -- materials-status --project <project-id>`，直接列出每项材料的
引用分类、题名、作者、canonical URL 和本地 PDF 绝对路径。

### 项目里的 skills 会随仓库更新吗？

不会自动更新。Web 每次启动任务前会把仓库当前的 skills 同步到该项目；但你手动复制到别处的项目文件夹是一份快照，仓库更新后不会跟着变。需要更新时重新复制一次：

```bash
cp -R /path/to/repo/skills/. .agents/skills/
cp -R /path/to/repo/skills/. .claude/skills/
```

复制不会覆盖 `inputs/`、`outputs/`、`project.json` 和社区缓存。

### 导师信息一定准确吗？

不一定。职位、招生状态和研究方向会变化，公开评价也可能存在偏差。发送邮件或提交申请前，应重新访问导师主页和院系官方页面确认关键信息。

## 开发与验证

面向普通用户的使用方式只有前面两种。下面的命令用于开发和测试，不是第三种产品使用方式。

```bash
cd web

# 构建并运行服务端渲染测试
npm test

# 单独构建
npm run build

# 只启动本地桥接服务，供开发调试
npm run runtime

# 查看桥接服务和模型状态
npm run backend -- health
```

更多本地后端命令和技术细节见 [`web/README.md`](web/README.md)。
本轮 Token/计算优化的逐项审计见
[`docs/SKILL_TOKEN_OPTIMIZATION.md`](docs/SKILL_TOKEN_OPTIMIZATION.md)。

主要目录：

```text
.
├── README.md
├── skills/
├── projects/              # Web 创建的本地申请项目，Git 忽略
└── web/
    ├── app/               # 前端界面
    ├── local-runtime/     # 本地执行桥接与 CLI
    ├── tests/
    └── README.md          # Web 层技术说明
```

控制台不会自动 commit、push、部署或发送邮件。

## 当前边界

- Web 自定义 API 当前要求兼容 OpenAI Responses API
- 背调质量取决于公开证据、网页可访问性和所选模型能力
- 复杂范围的导师搜索可能需要较长时间
- 最终排名是决策辅助，不是招生结果预测

---

Advisor Atlas 负责整理信息与证据，最终申请决策仍由你做出。
