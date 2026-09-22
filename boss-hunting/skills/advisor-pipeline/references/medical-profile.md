# 医学配置：三步输入、Seeds → PI 验证 → 合作网络 → 五模块深查

适用于 `domainProfile: medical`。沿用同一项目契约与 Finder → Detective → Evaluator，不另建数据库。来源能力注册表见 [medical-sources.md](medical-sources.md)，凭据/降级与浏览器执行见 [browser-research-policy.md](browser-research-policy.md)。开发/修改 Skill 本身时不运行以下问卷或搜索。

## 两种模式

| 模式 | 最低输入 | 结论边界 |
| --- | --- | --- |
| `discovery` 方向探索 | 医学领域、疾病/机制/科学问题、目标地区（可明确不限） | 无 CV、成绩、论文或申请者能力即可开始；产出导师级 Evidence Profile 与五模块调研；不判断个人竞争力、资格全部通过或录取概率 |
| `application` 申请筛选 | 前述画像、目标学位与批次、资金/其他硬约束、与条件有关的真实背景 | 可用真实 CV 或足够的结构化背景；只核对有依据的条件，缺失项为 `needs_confirmation` |

结构化背景写入 `applicantBackground`，标明 `source` 为 `self_reported`、`documented` 或 `not_provided`。自述不能伪装成外部验证。只索取会影响当前条件判断的背景。RP/套磁信继续执行原真实 CV、姓名、确切导师—项目与材料确认条件。

## 三步输入

只补问未提供的信息；复用对话和 `project.json` 已确认内容；一次完整输入不拆成重复问答。`medicalIntakeStatus` 只检查这三步，`researchModes` 等可选项从不阻塞。

1. **医学领域** `medicalProfile.fields`（可多选）：精神、神经、肿瘤、血液、免疫、骨科、基础医学、公共卫生或其他交叉方向。不用所在科室代替研究方向，允许非医院团队。
2. **疾病/机制/科学问题** `diseaseScope` / `diseasesOrMechanisms` / `researchQuestions`：单病种、多病种、泛癌/泛疾病、机制优先或未定；病因、机制、分型、治疗反应、预后、预防、方法开发或未定。保留"泛癌"，不强迫改成单病种。
3. **目标地区** `target`（权威字段）→ `medicalProfile.regions` 派生：大陆、香港、台湾、美国、澳大利亚、日本、欧盟/具体欧洲国家、其他或不限，可多选。宽泛欧洲探索需报告实际覆盖国家；英国、瑞士各走其国家来源。

可选、不阻塞：`researchObjects`（物种/组织/人群/数据类型）、`researchScales`（分子/细胞/个体/群体）、`researchModes`（研究范式：临床队列/试验、实验机制、计算与数据、群体/方法学）、`methodPreferences`（希望研究中出现的方法，不是已有能力）、`adjacentInterests`、`exclusions`。

`inputStatus` 区分 `unasked`、`answered`、`undecided`、`unrestricted`；空值不是用户已明确未定/不限。**不再收集** `currentSkills`、`desiredTraining`；schema 10 迁移时删除旧值。

申请模式补 `degree`、`season`、资金底线及必要背景。核实研究型 PhD/DPhil、临床专业/职业训练、联合培养的区别；医院主任、教授或研究所职位不证明博士指导资格。

## 发现流程：先宽后窄

```text
科学问题 → Seeds（并行按子方向）→ PI 提取 → 身份消歧（Level A–D）→ 5 年回查
→ Validated PI 池 → 合作网络扩展（≤2 轮）→ 饱和判断 → Shortlist（展示顺序）→ 五模块深查
```

### Seeds

按子方向并行产生两类种子；由 Seed Scouts 完成，Main Agent 规划子方向：

- **Map Seeds**：综述、指南、共识。只用于概念版图、术语与子方向划分，**不直接产生 PI**；一篇热门综述不能使其作者成为核心 PI（T19）。
- **Research Seeds**：近五年原创研究（默认窗口按运行日期生成，参数不是质量标准）。从 Research Seeds 提取 PI 候选。

覆盖 + 饱和停止：每个子方向至少一组 Research Seeds；当新查询不再产生新 PI 或新子方向时停止，不凑数、不声称穷尽。

### PI 识别与 Level A–D

禁止"末位作者 = PI"自动规则。PI 候选来自通讯作者、贡献声明（CRediT 的 supervision / conceptualization / funding acquisition）、官方 PI/实验室页面、基金 PI 记录。

| Level | 含义 | 最低证据 |
| --- | --- | --- |
| A | verified | 官方机构页面 + 至少一项已核实 PI 角色（通讯/贡献声明/基金 PI） |
| B | probable | 多篇末位/通讯但无贡献声明，或官方页面存在而角色未读全文（T23 上限） |
| C | emerging | 近期独立建组、首批论文以通讯出现、无毕业博士；过去主要一作者可进入此层（T24） |
| D | identity_unresolved | 同名未消歧、机构不一致、无官方页面 |

Identity Resolver 用 OpenAlex / ORCID / 官方页面消歧，记录 `nameVariants`、`identifiers`、`affiliationAsOf`。旧机构与当前机构不同的同名作者必须写明时点，不错误映射 affiliation（T07）。API 与官方页面不一致时保留冲突，由 Main Agent 用当前官方机构页裁决并说明（T40）。

### 5 年回查（back_search）

每位 PI 独立回查近五年产出，判断 `researchRouteContinuity`：`sustained_core`（持续主线）、`active_emerging`（活跃新兴）、`new_expansion`（新扩展）、`occasional_participation`（偶发参与）、`unclear`。最初只命中一篇同病种论文的 PI 必须回查后才能声称主线（T06）。回查窗口写入 `back_search.window` 与 `sourceIds`。

### 合作网络

深度固定为 1（ego network）。两类边严格分开（T21）：

- **collaboration edge**：共同发表、共同项目/基金、共同试验、共同 consortium 领导。
- **research-neighbor edge**：引用、共被引、文献耦合、语义相似、related papers。只表示科学邻近，不是合作。

核心合作者 heuristic（`collaboration-network.mjs` 可配置工程默认值，不是科学标准）：A. ≥2 篇方向相关共同研究；B. ≥1 篇共同研究 + 共同项目/基金/试验；C. ≥2 个不同年份且主题连续。单篇 300+ 作者 consortium 论文不产生数百核心合作者（T20）；只有重复合作、consortium 领导或贡献声明才保留。边权 = 方向相关共同记录数。

Network Expander 最多两轮；新线索回到身份消歧与回查，**不递归调查合作者本身的网络**（T25）。饱和：本轮新增 validated PI 为 0，或增长 < 10%（可配置）且无新子方向/聚类，或达轮次上限即停止（T26）。

### Shortlist 与展示顺序

按 `researchQuestionFit` → `researchRouteContinuity` → 稳定名称排序，是展示顺序，不是导师质量排名。引用量、H 指数、机构声望、基金总额、网络中心度不参与排序（T22 Emerging PI 保护）。

## Evidence Profile（五维）

每位 PI 记录 `evidence_profile`（导师记录）/ `evidenceProfile`（候选）：

| 维度 | 词表 |
| --- | --- |
| `researchQuestionFit` | `direct` / `partial` / `adjacent` / `weak` / `insufficient_information` |
| `researchRouteContinuity` | `sustained_core` / `active_emerging` / `new_expansion` / `occasional_participation` / `unclear` |
| `piRoleConfidence` | `verified` / `probable` / `emerging` / `identity_unresolved` + `level: A–D` |
| `evidenceSufficiency` | `strong` / `adequate` / `sparse` / `conflicted` |
| `currentActivity` | `active` / `recent_signal` / `unclear` / `apparently_inactive_in_checked_scope` |

每个子项带 `sourceIds` 指向 `evidence.json`；reasons 必须有来源。另有 `formalRecords[]`（更正/撤稿/机构公告，精确绑定，不推断个人不端）、`fitBoundary`、`keyUnknowns[]`、`nextVerification[]`。不再有 `trainingFit`、`resources`、`researchFunding`、`doctoralFunding`、`doctoralOutcomes`、`trainingEnvironment`、总分。

## 五模块内容

| 模块 | Section ID | 内容 | 不做 |
| --- | --- | --- | --- |
| A 导师身份与当前科研定位 | `identity_research_positioning` | 当前机构/院系/职位、官方页面、研究定位、姓名变体与标识、最低限度博士指导关联、Graduate Program 映射（研究生院/博士项目/导师名册） | 不评估人格、指导风格 |
| B 近五年科研主线与研究路线 | `research_mainline_5y` | 长期科学问题、持续主题、新方向、研究对象、方法、近期转向、代表性工作（已核实角色、与主线关系）、仅参与工作单列、预印本与正式版去重（T09） | 不做方法质量审计（T05），不按热点数量排序 |
| C 科研合作网络 | `collaboration_network` | 核心合作者（当前机构/职位、合作证据、年份、共享主题、其自身核心方向）、边类型与计数、研究邻居单列 | 不递归、不作中心度排名 |
| D 最新公开研究动向与项目支撑 | `latest_signals_projects` | 最新论文、预印本、公开项目（项目名称 / 编号 / 资助机构 / PI 角色 / 期限 / 状态 / 公开金额与口径）、注册与试验 | 金额不重复累计、不转成博士个人资助（T10）；试验招募不等于博士招生（T11）；公开库查无 ≠ 无基金（T29） |
| E 博士培养轨迹 | `doctoral_trajectory` | 当前博士生 / 已毕业博士（指导证据、学位/年份、课题、与主线关系、产出、首个去向、最新公开角色、信息日期）、Graduate Program、Emerging PI 说明 | 不计算毕业率、去向率、培养成功率（T31）；仅姓名无指导证据不计入（T30）；博士后不混入 alumni（T12） |

Barres 式"导师应做什么"的吸收边界：只取可公开核验的科研主线、指导关系与产出证据；不评价关怀、氛围、工时或人格（T32）。

## 来源优先级

身份与任职：当前官方机构页 > ORCID > OpenAlex；论文与角色：PubMed/DOI 出版商页 > Europe PMC > OpenAlex > Semantic Scholar；项目：所选地区官方基金库（NIH RePORTER、NSFC、RGC、UKRI GtR、DFG GEPRIS、KAKEN、CORDIS 等）> 机构公告 > 论文致谢基金号；博士培养：研究生院/学位论文库 > 官方实验室页 > 正式履历。Google Scholar 只作 discovery / backcheck，遇 CAPTCHA/登录即停。凭据缺失按四级降级，只用状态词，不进 prompt/evidence。

## 证据与续跑

最终结果以简洁、内容为主的 HTML 报告交付：`outputs/{topic}-导师调研.html`（`build_advisor_report.mjs --project-root PATH`）。首页紧凑表（导师 | 核心研究问题 | 近五年科研主线 | 核心合作生态 | 最新研究信号 | 方向契合与边界）→ 每位导师 A–E → 方向契合与主要边界 → 来源及检索覆盖说明（含 seed / 网络轮次 / 饱和 / provider-capabilities）。Excel 保留补充兼容。

每项研究、项目、培养记录及比较理由旁直接附其具体记录的 HTTP(S) 链接（item-level）；数据库首页或搜索页不算（T13）；页尾证据编号仅作补充。无具体来源写"来源待补/待核验"，不造网址（T14）。

每项主张以 `fact` / `interpretation` / `question` 区分，关联实体、字段、URL、标题、源日期、访问日期、片段/页码、读取深度、检索方式、限制。状态 `verified` / `partial` / `not_found` / `not_checked` / `inaccessible` / `conflict` / `stale` / `not_applicable`；`not_found` 需说明查过哪些来源与查询；摘要、空框架、403 不足以标 verified 或查无（T08、T15）。

Subagent 输出只写 `runs/<run-id>/subagents/`，由 Main Agent 用 `merge_subagent_findings.mjs` 合并；完成度分 `complete` / `partial` / `blocked`，不把 fixture 当真实检索。从探索转申请只补批次/资格缺口；Excel 丢失从共享 JSON 重导出。
