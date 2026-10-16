# 医学配置：三步输入、PI 验证与近五年署名文献

适用于 `domainProfile: medical`。沿用同一项目契约与 Finder → Detective → Evaluator，不另建数据库。来源能力注册表见 [medical-sources.md](medical-sources.md)，凭据/降级与浏览器执行见 [browser-research-policy.md](browser-research-policy.md)。开发/修改 Skill 本身时不运行以下问卷或搜索。

## 两种模式

| 模式 | 最低输入 | 结论边界 |
| --- | --- | --- |
| `discovery` 方向探索 | 医学领域、疾病/机制/科学问题、目标地区（可明确不限） | 无 CV、成绩、论文或申请者能力即可开始；产出导师概况、研究主线与近五年署名文献；不判断个人竞争力、资格全部通过或录取概率 |
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
→ Validated PI 池 → 覆盖与饱和判断 → Shortlist（展示顺序）→ 署名文献回查与报告
```

### Seeds

按子方向并行产生两类种子；由 Seed Scouts 完成，Main Agent 规划子方向：

- **Map Seeds**：综述、指南、共识。只用于概念版图、术语与子方向划分，**不直接产生 PI**；一篇热门综述不能使其作者成为核心 PI（T19）。
- **Research Seeds**：近五年原创研究（默认窗口按运行日期生成，参数不是质量标准）。从 Research Seeds 提取 PI 候选。

覆盖 + 饱和停止：每个子方向至少一组 Research Seeds；当新查询不再产生新 PI 或新子方向时停止，不凑数、不声称穷尽。

### PI 识别与 Level A–D

禁止"末位作者 = PI"自动规则。PI 候选来自通讯作者、贡献声明（CRediT 的 supervision / conceptualization / funding acquisition）、官方 PI/实验室页面。

| Level | 含义 | 最低证据 |
| --- | --- | --- |
| A | verified | 官方机构页面 + 至少一项已核实 PI 角色（通讯/贡献声明） |
| B | probable | 多篇末位/通讯但无贡献声明，或官方页面存在而角色未读全文（T23 上限） |
| C | emerging | 近期独立建组、首批论文以通讯出现、无毕业博士；过去主要一作者可进入此层（T24） |
| D | identity_unresolved | 同名未消歧、机构不一致、无官方页面 |

Identity Resolver 用 OpenAlex / ORCID / 官方页面消歧，记录 `nameVariants`、`identifiers`、`affiliationAsOf`。旧机构与当前机构不同的同名作者必须写明时点，不错误映射 affiliation（T07）。API 与官方页面不一致时保留冲突，由 Main Agent 用当前官方机构页裁决并说明（T40）。

### 5 年回查（back_search）

每位 PI 独立回查近五年产出，判断 `researchRouteContinuity`：`sustained_core`（持续主线）、`active_emerging`（活跃新兴）、`new_expansion`（新扩展）、`occasional_participation`（偶发参与）、`unclear`。最初只命中一篇同病种论文的 PI 必须回查后才能声称主线（T06）。回查窗口写入 `back_search.window` 与 `sourceIds`。

### 发现范围

以原创论文、作者回查和官方名册补充候选；已见共同署名可作发现线索，但不单独调查合作研究者、合作项目或基金，不执行合作网络画像。每个子方向有实际研究种子后，新查询不再增加相关 PI 或子方向时可停止；记录实际覆盖和停止原因，不声称穷尽。

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

## 核心内容与可选附录

| 模块 | Section ID | 内容 | 不做 |
| --- | --- | --- | --- |
| 导师概况 | `identity_research_positioning` | 当前机构、院系、职位、官方与实验室主页、研究定位、姓名变体与标识；博士项目映射仅在申请范围内核查 | 不从职位推断招生资格 |
| 研究主线与五年署名文献 | `research_mainline_5y` | 全部研究方向的第一／共同第一／通讯／共同通讯论文、预印本与期刊正式版关系、精确日期与署名依据；完整检索后再选正文代表作 | 不用两三篇代表作代替五年回查，不按热点数量排序 |
| 作者与指导关系补充（可选） | `doctoral_trajectory` | 已有第一作者姓名、共同论文方向与可靠公开身份；明确指导关系可补充；有内容时放折叠附录 | 不作为论文纳入或核心报告完成门槛，不把共同署名推断为指导关系 |

Barres 式"导师应做什么"的吸收边界：只取可公开核验的科研主线、指导关系与产出证据；不评价关怀、氛围、工时或人格（T32）。

## 近期学术会议与演讲

近期会议与演讲作为补充信息：复用已有有效记录；用户要求专项补查时，检索本次检索日向前两年的公开活动。无内容不铺空栏目，不影响本轮论文检索完成度。未来活动单列，不计作已出席。保存实际 checkedAt 与 windowStart/windowEnd，不把论文的五年窗口用于会议。

- 来源顺序：会议官网议程/摘要集、主办方论坛或讲座页面 → 院校/实验室活动回顾 → 官方公开视频及介绍。用姓名变体＋机构＋研究方向消歧，结合 conference/keynote/invited talk/symposium/seminar/论坛/报告等检索；核对举办年份，避免同名活动跨届混淆。会议摘要署名本身不证明导师为报告人。
- 每条记录活动名称、活动日期、参与角色、**演讲标题原文**、可选中文译名、来源及核验状态。标题未公开或查不到就明确写缺失；不能以会议名、分会场主题或论文题名推断个人演讲标题。
- 大会报告、邀请报告、分会场报告可作为演讲；主持、讨论嘉宾、普通参会单独标注，不自动作为演讲。只有公开来源明确表述个人演讲时才按 speaker 记录。
- 议程/预告只能支持“预告安排（实际报告待核实）”，即使日期已过去也不能自动升级。主办方/机构活动回顾或录像明确支持实际报告，才标“已确认报告”；核对同一导师、活动和日期。未来日期不能写已经报告。
- `researchMainline.academicTalks[]` 与 `talkSearches[]` 使用共享 evidence；结构见 investigation-contract.md。活动来源 evidence 的 source_type 为 conference_programme/event_announcement/event_report/recording，实体必须绑定该导师。不得将普通网页访问成功等同于报告事实核验。
- 找到活动、所查范围未找到、访问受阻、部分完成、未检索分开记录。旧数据缺检索过程时保留待补查，不能声称“没有学术活动”。会议记录仅补充近期研究动向，不替代论文证据或形成导师质量排名。

## 身份字段落表与报告前检查

查看官方介绍正文后，同步填写 `identity.currentInstitution`、`department`、`currentPosition`、`researchPositioning`、`affiliationAsOf`（实际任职核验日，YYYY-MM-DD）。博士项目／指导关系在申请范围内核查，有证据时填写 `doctoralSupervisionLink`；发现阶段不因此扩展招生调查。每项主张在现有 evidence 中关联 `entity_id`、`fields_supported`（例如 `identity.currentPosition`）、`claim`、来源 URL、正文片段及核验状态；identity.sourceIds 保留来源关联。snake_case 字段同样支持。citation_label 仅用于显示链接，不能代替字段值或作为自动提取依据。

未能填写时，在对应字段的 evidence 中记录真实状态与 limitations：未核验、所查来源未提供、访问受阻、来源冲突等。查无须写明查询范围；不从头衔推断博士招生，不把访问日或页面更新日当任职核验日，不从旧报告复制未经复核的职称。

交付前运行只读检查：`node scripts/build_advisor_report.mjs --project-root <项目目录> --check-identity`（使用实际技能脚本路径）。逐位处理范围内的 identityChecks.gaps：已读正文有证据但字段为空，核对后写回共享记录；已填值缺字段级来源，补齐实际支持它的证据；真正无法核实的保留原因。此检查仍列出全部历史身份字段，但发现阶段的核心完成度不以博士指导链接或重复的研究定位字段为门槛。真实任职冲突仍必须显现。生成器不联网、不从证据标题猜值，也不自动修改事实；允许交付有明确缺口的部分报告。

## 来源优先级

身份与任职：当前官方机构页 > ORCID > OpenAlex；论文与角色：PubMed/DOI 出版商页 > Europe PMC > OpenAlex > Semantic Scholar；博士培养：研究生院/学位论文库 > 官方实验室页 > 正式履历。Google Scholar 只作 discovery / backcheck，遇 CAPTCHA/登录即停。凭据缺失按四级降级，只用状态词，不进 prompt/evidence。

## 证据与续跑

最终结果为离线单文件 HTML：`outputs/{topic}-导师调研.html`（`build_advisor_report.mjs --project-root PATH`），沿用现有字体、颜色和导航。阅读顺序为 **要求简述 → 导师对照 → 逐位导师详情 → 来源与检索范围**。详情按导师概况、研究主线与相关性、近五年一作／通讯论文、关键待核实事项组织。技术查询、内部 ID、原始 JSON 留在数据和运行记录，不嵌入 HTML。窄屏纵向阅读，打印展开论文并隐藏目录。Excel 是补充产物。

合作研究者和科研基金已从当前调查、菜单、HTML、Excel 和完成度门槛中移除；已移除对应运行逻辑；已有原始记录不改写。研究模块统一保存 `researchMainline.representativeWorks/latestPapers/preprints`。旧 `latestSignals.latestPapers/preprints` 仍可读入研究模块。

预印本需核对是否已有期刊正式版，记录期刊/平台、发表日期、DOI、`publicationStatus`、`publishedVersionDoi`、`versionStatus` 和 `versionSourceIds`。版本证据必须来自明确关联两版的官方页面或接口，支持 `researchMainline.publications.publishedVersionDoi`；仅填写 DOI 不算核实。版本关联已核实且正式版署名已符合纳入条件时合并展示，保留两版来源；否则保留预印本与待核实事项。不得仅凭相似题名合并不同论文。

每项研究、项目、培养记录及比较理由旁直接附具体记录 HTTP(S) 链接；数据库首页不支持项目事实。查询结果页可支持检索过程（需保存姓名/机构/范围及结果），不能仅凭首页声称查无。证据可加 `citation_label`（如“机构导师介绍”“MDD 海马研究｜2026”），缺失回退页面标题或来源类型；禁用“证据 5”等编号链接。同一信息块去重网址；不同结论保留必要链接。来源附录按网页合并，但保留不同主张和各自状态。缺来源写待核验，不造网址。

任职信息核对日期只取 identity.affiliationAsOf；网页查阅日期取证据 accessed_at；页面更新时间取 source_updated_at，不能互相代替。正文用简短中文说明实际检索与遗漏；重复的空字段、内部字段名和英文状态码不向读者展示。职称冲突、署名不确定、患者研究与遗传映射等重要区别仍须明确。

每项主张以 `fact` / `interpretation` / `question` 区分，关联实体、字段、URL、标题、源日期、访问日期、片段/页码、读取深度、检索方式、限制。状态 `verified` / `partial` / `not_found` / `not_checked` / `inaccessible` / `conflict` / `stale` / `not_applicable`；`not_found` 需说明查过哪些来源与查询；摘要、空框架、403 不足以标 verified 或查无（T08、T15）。

Subagent 输出只写 `runs/<run-id>/subagents/`，由 Main Agent 用 `merge_subagent_findings.mjs` 合并；完成度分 `complete` / `partial` / `blocked`，不把 fixture 当真实检索。从探索转申请只补批次/资格缺口；Excel 丢失从共享 JSON 重导出。

## 近五年一作／通讯论文回查（核心内容）

逐位检索全部研究方向，不设置论文数量上限。先通过机构／实验室主页、姓名变体与可靠标识消歧，再对官方论文目录和 PubMed、Europe PMC、OpenAlex 等实际可用入口交叉回查。查完实际结果分页，记录命中数、筛选数、窗口、检索条件、来源和访问限制；不能把同姓缩写命中数当成导师论文数。至少说明官方目录与文献库各自是否查过、是否受阻，不用数据库首页或空壳声称查无。

论文属于导师且第一／共同第一／通讯／共同通讯之一已核实，才计入清单。第一作者可由完整作者顺序与身份依据核验；共同第一和通讯角色须有作者注释、出版商通讯栏或全文说明。末位、共同资深、团队负责人均不能替代通讯作者。优先保存发表日期，边界年份仅有年份时列待核验；预印本和正式版仅在明确关联时去重。论文纳入与第一作者学历、画像或指导关系是否调查完全分离。

完整论文存入现有 `researchMainline.latestPapers`，代表作只是显示选取；具体字段见 investigation-contract.md。旧自由文本署名只保留为线索，不能通过包含 corresponding 等词自动变成已核实。没有有效窗口、没有完整查询回执或仍有未解决的署名/日期问题时，保留部分完成。完成仅指本次有记录的范围，不能承诺全球穷尽。

默认显示最近三篇已核实论文，其余按年份折叠，完整清单不截断；待核验线索单列且不计数。实验室主页并入概况。作者画像仅有内容时作为可选附录；姓名消歧仍用 personId，共同署名不证明指导关系，方向总结只能依据已核实共同论文。未选择画像补查时，不为完成报告扩展调查学历、成员或校友。

### 报告阅读排版

首页导师对照保留紧凑表格，正文每位导师只说一次研究定位、相关性和重要限制。已有第一作者资料使用折叠的纵向条目。论文标题直接链接原文，日期、期刊、中文署名和研究关系并列。正文不显示 raw JSON、内部 ID、英文字段名或空字段矩阵；结构化主题的文字和来源分别提取，不能输出 `[object Object]`。Excel 使用“导师概览”“近五年论文”“来源说明”，有内容时加“作者附录”；论文逐篇占行，待核验线索单列，不用一个超宽表装全部事实。

报告导航与分区沿用共享生成器，目录链接仅指向实际存在的章节；窄屏使用顶部折叠目录。保持离线单文件，只允许内置导航脚本的 CSP 哈希，不加载外部框架。打印隐藏目录并展开完整论文清单。
