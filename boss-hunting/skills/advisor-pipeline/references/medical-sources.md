# 医学来源能力注册表（Source Capability Registry）

这是唯一人工维护的来源目录。先加载 Global Core，再加载用户所选地区的 Regional Adapter；不是封闭白名单，不逐站爬取。具体主张引用记录页/文件，不以数据库首页替代。官方招生证据不能证明研究贡献，论文也不能证明当批次招生。来自官方页面、论文、基金记录的新来源可按任务使用，注明主体和用途。

每条来源同时声明 `capabilities`（能证明什么）、`retrieval`（preferred / fallback，按 [browser-research-policy.md](browser-research-policy.md) 四级降级）、`authority`（authoritative / supporting / discovery_only）和 `credentials.env` 变量（可选加速器，缺失不阻塞）。运行时实际路由写入 `runs/<run-id>/provider-capabilities.json`。

已删除：研究资源与平台条目（原 M03–M05）、学生资助条目（原 H03 等）。医学流程不再调查资源访问层级、博士个人资助、学费或培养环境。

## 通用规则

- `not_found` 必须由具体查询产生，不能由目录状态推导；公开库查无 ≠ 该 PI 无基金、无记录。
- 凭据只以 `configured | unavailable | invalid | capability-limited` 状态词出现；值不进 prompt、evidence、日志、报告。
- 有 key 不等于付费权限（WoS 分层 `starter | researcher | expanded | limited | unavailable`，未探测不假定 expanded）。
- Google Scholar 只做 discovery / backcheck；线索必须回到 PubMed、DOI/出版商、ORCID、当前机构或官方基金记录核实。遇 CAPTCHA/登录即停。
- 更新此目录时注明更换入口、用途与实际测试范围，不因一次失败删除整个国家支持。

## Global Core

| source_id | 名称与入口 | capabilities | retrieval preferred → fallback | authority | credentials.env |
| --- | --- | --- | --- | --- | --- |
| GC-OPENALEX | [OpenAlex](https://openalex.org/) · [API](https://docs.openalex.org/) | researcher discovery、works/authors/institutions、coauthor graph、author back-search | authenticated_api → anonymous_api → browser → PubMed/ORCID/官方页 | supporting（不能单独证明当前职位、博士指导、贡献、项目现状） | `OPENALEX_API_KEY` |
| GC-PUBMED | [PubMed / NCBI E-utilities](https://pubmed.ncbi.nlm.nih.gov/) · [帮助](https://pubmed.ncbi.nlm.nih.gov/help/) | 生物医学论文发现、PMID/MeSH、作者回查、出版类型/日期/摘要 | authenticated_api → anonymous_api（低速率）→ browser → Europe PMC/OpenAlex/出版商 | authoritative（论文元数据）；无通讯作者字段，`[lastau]` 不证明 PI | `NCBI_API_KEY`（缺失 ≠ 抓取 PubMed 网页） |
| GC-ORCID | [ORCID](https://orcid.org/) · [Public API](https://info.orcid.org/documentation/) | 身份消歧、姓名变体、任职历史、公开成果关联 | authenticated_api → anonymous_api → browser → 当前机构官方页 | supporting（自述；当前任职需官方页互证） | `ORCID_CLIENT_ID` + `ORCID_CLIENT_SECRET` |
| GC-S2 | [Semantic Scholar](https://www.semanticscholar.org/) · [API](https://api.semanticscholar.org/) | citations、references、related papers、research neighborhood | authenticated_api → anonymous_api → browser → OpenAlex/WoS | supporting；引用关系 ≠ 合作关系 | `SEMANTIC_SCHOLAR_API_KEY` |
| GC-WOS | [Web of Science](https://www.webofscience.com/) · [Developer](https://developer.clarivate.com/) | 文献回查、引用图、作者—机构核对、related works | authenticated_api（按实际 tier）→ 已授权用户自有网页访问 → OpenAlex/S2/PubMed | supporting；web 订阅 ≠ API 权限；不通过 Browser 伪造付费数据 | `WOS_API_KEY` |
| GC-CROSSREF | [Crossref REST](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | DOI 元数据、版本/更正关系、资助者字段 | anonymous_api → browser → 出版商原文/PubMed | authoritative（DOI 元数据）；缺项不证明无贡献 | 无（polite pool 用 mailto 即可） |
| GC-EPMC | [Europe PMC](https://europepmc.org/) · [API](https://europepmc.org/RestfulWebService) | 文献与版本、预印本—正式版关系、可用全文、资助者标注 | anonymous_api → browser → PubMed/出版商 | authoritative（记录）；全文按版本解释 | 无 |
| GC-PREPRINT | [bioRxiv](https://www.biorxiv.org/) · [medRxiv](https://www.medrxiv.org/) | 预印本 DOI、版本、日期、正式版关联 | anonymous_api（bioRxiv API）→ browser → Europe PMC | supporting；未同行评议，无预印本不扣分 | 无 |
| GC-CREDIT | [CRediT](https://credit.niso.org/) · [ICMJE](https://www.icmje.org/recommendations/browse/roles-and-responsibilities/defining-the-role-of-authors-and-contributors.html) | 贡献角色定义，用于读论文贡献声明 | browser（静态） | authoritative（定义）；作者次序不能代替贡献 | 无 |
| GC-INSTITUTION | 当前机构 / 实验室 / 研究生院 / 机构库（运行时定位） | 当前职位、导师名册、Graduate Program、学位论文、官方公告 | browser（静态优先）→ 图书馆导航 → 公开履历互证 | authoritative（身份、任职、博士指导关联的最终依据） | 无 |
| GC-SCHOLAR | [Google Scholar](https://scholar.google.com/) | 补充发现、作者页 backcheck | browser（CAPTCHA/登录即停）| discovery_only；不作证据来源 | 无 |
| GC-TRIALS | [ClinicalTrials.gov](https://clinicaltrials.gov/) · [API](https://clinicaltrials.gov/data-api/api) · [WHO ICTRP](https://trialsearch.who.int/) | 注册号、申办/负责角色、状态、更新 | anonymous_api → browser → 原注册平台/机构页 | supporting；试验角色 ≠ 博士指导资格或博士招生 | 无 |

## Regional Adapter

### US

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| US-NIH | [NIH RePORTER](https://reporter.nih.gov/) · [API](https://api.reporter.nih.gov/) · [FAQ](https://report.nih.gov/faqs) | 项目号、角色、财年预算/项目期、金额口径、状态 | anonymous_api → browser | authoritative | 年度 ≠ 全周期；母子项目不重复累计；active 可含无新增经费延期 |
| US-NSF | [NSF Award Search](https://www.nsf.gov/awardsearch/) | PI、机构、奖项号、项目期、金额 | anonymous_api → browser | authoritative | 非医学资金全集 |
| US-PROGRAM | 大学生物医学博士项目 / faculty / rotation 页（运行时定位） | 培养类型、导师资格、Graduate Program 映射、批次 | browser | authoritative | 不默认全部轮转；PI 无广告 ≠ 委员会项目关闭 |
| US-THESIS | 机构学位论文库（如 [DASH](https://dash.harvard.edu/)） | 博士关系、主题、年份、去向线索 | browser | authoritative | 博士后/共同作者不计为博士培养 |

### CN（中国大陆）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| CN-NSFC | [NSFC](https://www.nsfc.gov.cn/) · [知识平台](https://kd.nsfc.cn/) · [查询FAQ](https://www.nsfc.gov.cn/p1/2961/2962/3648/cx.html) | 项目号、题名、负责人、单位、期限、结题成果 | browser（公开功能）→ 官方获批/结题公告 → 机构公告 → 论文基金号（保留时点） | authoritative（有公开权限边界） | 人员承担查询可能需本人/管理员；**查无 ≠ 无 NSFC**，写明公开覆盖限制 |
| CN-MOST | [国家科技管理信息系统公共服务平台](https://service.most.gov.cn/) | 专项获批/公示、承担单位、公告日期 | browser | authoritative | 指南 ≠ 获资助；公开覆盖有限 |
| CN-ADMISSION | 学校研究生院 / 医学院招生（示例 [交大研招](https://yzb.sjtu.edu.cn/)） | 当批次简章、导师目录、Graduate Program 映射 | browser / 公开 PDF | authoritative | 医院需映射授予单位 |
| CN-THESIS | [CNKI](https://www.cnki.net/) · [万方](https://www.wanfangdata.com.cn/) · 学校知识库 | 博士论文题名、导师、授予单位、年份 | browser（登录另授权）→ 学校库 | supporting | 硕士不混成博士样本 |
| CN-TRIAL | [ChiCTR](https://www.chictr.org.cn/) | 注册号、角色、申办方、状态 | browser | supporting | 联系人/分中心 ≠ 总负责人 |
| CN-INSTITUTION | 医院/研究所科研与教育页（运行时定位） | 平台、队列、公开项目、培养资格线索 | browser | supporting | 学位/批次回招生单位 |

### HK（中国香港）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| HK-RGC | [RGC 计划](https://www.ugc.edu.hk/eng/rgc/funding_opport/) · [GRF Funded Research](https://www.ugc.edu.hk/eng/rgc/funding_opport/grf/funded_research.html) | 项目号、角色、年份、主题、金额口径（GRF/ECS/CRF/TRS） | browser | authoritative | GRF ≠ 全部 RGC；征集 ≠ 获奖 |
| HK-PROGRAM | 研究生院 / 项目（示例 [HKU](https://gradsch.hku.hk/)） | 师资、程序、Graduate Program 映射、批次 | browser | authoritative | 项目开放 ≠ 每位 PI 收人 |
| HK-THESIS | 大学论文库（示例 [HKU Libraries](https://lib.hku.hk/)） | 学位、指导关系、题名 | browser | authoritative | 不可见 ≠ 不存在 |

### TW（中国台湾）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| TW-NSTC | [NSTC](https://www.nstc.gov.tw/) · [研究人才](https://wrs.nstc.gov.tw/) · [补助查询](https://wsts.nstc.gov.tw/) | 身份、研究人才、补助/奖励类别与角色 | browser | authoritative | 奖励 ≠ 研究经费 |
| TW-GRB | [GRB](https://www.grb.gov.tw/) | 项目、报告、成果、日期 | browser | authoritative | 维护/失败 ≠ 查无 |
| TW-THESIS | [博硕士论文系统](https://ndltd.ncl.edu.tw/) | 指导教授、博士、学校、年份 | browser（登录另授权） | authoritative | 分清硕士/博士、共同指导 |
| TW-PROGRAM | 大学招生 / 系所页（示例 [台大](https://www.ntu.edu.tw/)） | 博士班简章、Graduate Program 映射 | browser | authoritative | 身份按官方条款问用户 |

### GB（英国）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| GB-GTR | [UKRI Gateway to Research](https://gtr.ukri.org/) · [API](https://gtr.ukri.org/resources/api.html) | 研究者、机构、项目、角色、周期、金额口径 | anonymous_api → browser | authoritative | 更新日期 ≠ 访问日期 |
| GB-PROGRAM | 大学 doctoral school / department（运行时定位） | 导师、DPhil/PhD 项目、Graduate Program 映射 | browser | authoritative | 不用欧盟目录覆盖英国 |

### DE（德国）与 EU

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| DE-GEPRIS | [DFG GEPRIS](https://gepris.dfg.de/) | 姓名、项目、机构、角色、期限 | browser | authoritative | 非德国全部资金 |
| EU-CORDIS | [CORDIS](https://cordis.europa.eu/projects) · [API](https://cordis.europa.eu/about/service-tools) | 协调/参与角色、周期、结果、资助口径 | anonymous_api → browser | authoritative | 联盟总额 ≠ PI 可支配额；不覆盖国家资金 |
| EU-EURAXESS | [EURAXESS](https://euraxess.ec.europa.eu/jobs/search) | 正式岗位、雇主、资格、截止 | browser | supporting | R1 ≠ 博士入学岗位 |
| EU-NATIONAL | ANR（FR）[获资助项目](https://anr.fr/en/funded-projects-and-impact/funded-projects/)、NWO（NL）[项目](https://www.nwo.nl/en/projects)、SNSF（CH）[Data Portal](https://data.snf.ch/) 等国家基金库 | 项目、角色、周期、金额口径 | browser → 官方导航 | authoritative | 英国、瑞士单独路由；不以 CORDIS 查不到排除 |

### JP（日本）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| JP-KAKEN | [KAKEN](https://kaken.nii.ac.jp/en/) · [CiNii Research](https://cir.nii.ac.jp/) · [API](https://support.nii.ac.jp/en/cir/r_opensearch) | 日本研究者、论文、机构、科研费角色/期间/经费口径 | authenticated_api（`CINII_APP_ID`）→ browser（官方网站，不声称 API 等价）→ researchmap/机构页 | authoritative | 非全部医学资金 |
| JP-RESEARCHMAP | [researchmap](https://researchmap.jp/) | 身份、专长、任职、公开成果 | browser | supporting | 自述与现机构互证 |
| JP-JREC | [JREC-IN](https://jrecin.jst.go.jp/seek/SeekTop?ln=1) | 正式职位、研究题目 | browser | supporting | 博士后 ≠ PhD opening |
| JP-PROGRAM | 大学研究科 / 专攻募集要项（示例 [东京大学](https://www.u-tokyo.ac.jp/)） | 学位、考试、事前联系、Graduate Program 映射 | browser / 当年 PDF | authoritative | "研究生" ≠ 博士学位在读 |

### CA（加拿大）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| CA-CIHR | [CIHR Funding Decisions Database](https://webapps.cihr-irsc.gc.ca/decisions/p/main.html) | 项目、PI 角色、年度、金额口径 | browser | authoritative | 年度决定 ≠ 全周期 |
| CA-NSERC | [NSERC Awards Database](https://www.nserc-crsng.gc.ca/ase-oro/index_eng.asp) | 奖项、角色、年度 | browser | authoritative | 非医学资金全集 |
| CA-PROGRAM | 大学 graduate studies / department（运行时定位） | 导师、Graduate Program 映射 | browser | authoritative | — |

### AU（澳大利亚）

| source_id | 名称与入口 | capabilities | retrieval | authority | 边界 |
| --- | --- | --- | --- | --- | --- |
| AU-NHMRC | [NHMRC outcomes](https://www.nhmrc.gov.au/funding/data-research/outcomes)（含 MRFF 链接） | 编号、角色、年度、金额口径 | browser / 公开下载 | authoritative | 汇总总额不分配给个人 |
| AU-ARC | [ARC Data Portal](https://dataportal.arc.gov.au/) | 角色、资助、期限 | browser / 官方导出 | authoritative | 非医学经费全集 |
| AU-PROGRAM | 大学 Graduate Research / Find a Supervisor（示例 [Melbourne](https://www.unimelb.edu.au/)） | 导师、PhD 项目、Graduate Program 映射、批次 | browser | authoritative | 校别/批次分查 |

## 查询模板与停止规则

替换花括号再执行；保留原词与英语全称、必要中/繁/日文变体；有歧义的缩写先展开，不把所有条件挤成极窄 AND。

```text
"{disease_or_mechanism}" "{question_or_method}"                     # Research Seeds
"{disease_or_mechanism}" review OR guideline                        # Map Seeds
"{PI_full_name}" "{institution}" faculty                            # 身份
site:{verified_institution_domain} "{PI_full_name}" graduate program # Graduate Program 映射
"{PI_full_name}" doctoral thesis supervisor                         # 博士培养
"{导师姓名}" "{单位}" 项目 基金
"{PI_name_Japanese}" 研究課題
```

PubMed（只加与本轮相关的条件）：

```text
("{verified_MeSH_term}"[MeSH Terms] OR "{disease_phrase}"[tiab])
AND ("{method_phrase}"[tiab] OR "{mechanism_phrase}"[tiab])
AND ("{start_YYYY/MM/DD}"[dp] : "{end_YYYY/MM/DD}"[dp])
"{PI_full_name}"[fau] AND ("{start}"[dp] : "{end}"[dp])            # 5 年回查
```

`[fau]` 是 full author，`[1au]` 第一作者，`[lastau]` 末位个人作者；`[ad]` 不证明机构与目标作者一一对应；不存在 `[corresponding author]` 字段。

每轮在 `runs/<run-id>/` 中记录范围、真实查询/筛选、访问来源/时间、事实及缺口。项目记录只查一次，PI 科研记录在多个项目间复用。优先补会改变判断的身份、主线与项目未知项；饱和规则见 medical-profile.md。来源受限按浏览器策略有限重试/降级，不把预算未查完写成没有候选。
