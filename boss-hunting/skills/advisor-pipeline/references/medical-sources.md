# 医学来源目录：按地区与核验任务路由

这是唯一人工维护的网站目录。加载通用基础入口，再加载用户所选地区与研究路线；不是封闭白名单，不逐站爬取。具体主张引用记录页/文件，不以数据库首页替代。官方招生证据不能证明研究贡献，论文也不能证明当批次招生。来自官方页面、论文、基金记录的新来源可按任务使用，注明主体和用途。

## 入口核验级别

每行最后一列同时表示日期、范围和层级，避免把需求说明中的历史观测当成本次测试：

- **S** = 2026-09-22 本次开发用静态网页工具读到实质官方说明，仅限括号内页面；无动态查询/Browser Use E2E。
- **D** = 2026-09-22 按用户升级说明登记的入口，本次开发未访问；说明中的读取失败、维护或动态提示不是本次测试结果，运行时重新检查。
- **R** = 2026-09-22 按说明登记的官方导航任务，目标机构/页面运行时定位；所附示例只说明导航，不代表推荐或已测。

D/R 不表示入口现已可用，也不表示不可用。`not_found` 必须由具体查询产生，不能由目录状态推导。更新此目录时注明更换入口、用途与实际测试范围，不因一次失败删除整个国家支持。

## 2026-09-22 增量联网抽样

默认先用宿主 GPT 内置网页工具，本轮实际调用 `web__run`；完整结果、失败和具体来源见
[联网验收 HTML](../../../docs/live-tests/2026-09-22-builtin-web/医学导师检索-内置浏览器联网验收.html)。
读到了 Oxford 肿瘤学博士课程/国际学历页、北大2026博士招生PDF及导师简介、PubMed 34329587、NIH官方FAQ和API说明。
NIH动态搜索只有JS提示，PMC全文入口遇验证码，部分链接内部错误；PDF `find` 漏匹配后由正文窗口复核，截图未得到可检视图像。
以上仅适用于具体记录，不能泛化为整个站点或所有数据库已验证。目录所列其他学校示例仍保留原D/R状态；API文档可读不代表已执行API查询。

## 通用：论文、身份、贡献与学位成果

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | [PubMed](https://pubmed.ncbi.nlm.nih.gov/) · [帮助](https://pubmed.ncbi.nlm.nih.gov/help/) | 全球 / 研究发现 | 疾病/机制、方法、姓名 `[au]`、日期 `[dp]`；见下模板 | PMID、DOI、作者、机构、日期、摘要 | 不存在通讯作者专用字段；机构需与个人消歧，全文贡献另查 | 静态 / 官方 API / Browser Use | G04、出版商、机构库 | S（帮助）；本轮检索与PMID 34329587详情读取见增量记录 |
| G02 | [MeSH](https://www.ncbi.nlm.nih.gov/mesh/) | 全球 / 标准词 | 疾病全称、同义词 | 主题词、入口词、上下位关系 | 未索引论文可能遗漏，须结合自由词 | 静态 / Browser Use | G01自由词/专业词表 | D |
| G03 | [PMC](https://pmc.ncbi.nlm.nih.gov/) | 全球 / 合法全文 | PMID/PMCID、DOI、标题 | 贡献、Methods、Funding、Data/Code availability | 全文公开不代表数据可直接使用 | 静态 / 官方 API / Browser Use | 出版商合法开放版、机构库 | D |
| G04 | [Europe PMC](https://europepmc.org/) | 全球 / 文献与版本 | 姓名、疾病、DOI、标题 | 原始记录、可用全文、预印本关系 | 按具体版本解释，不假定全文可用 | 静态 / API / Browser Use | G01、出版商、机构库 | D |
| G05 | [bioRxiv](https://www.biorxiv.org/) | 全球 / 前沿基础研究 | 姓名、疾病/机制、方法、时间窗 | DOI、版本、日期、作者、正式版关联 | 预印本未完成同行评议；无记录不扣分 | 静态 / Browser Use | 实验室课题、正式发表页 | D |
| G06 | [medRxiv](https://www.medrxiv.org/) | 全球 / 健康预印本 | 姓名、临床问题、研究方式 | DOI、版本、公开日期、正式版 | 不当成已确证结论；去重 | 静态 / Browser Use | G04、实验室/出版商 | D |
| G07 | [Google Scholar](https://scholar.google.com/) | 全球 / 补充发现 | 姓名+机构、准确标题 | 文献线索、公开作者主页 | 算法聚合不证明当前任职/招生或完整产出 | Browser Use / 静态 | 验证码时 G01/G04/出版商，不绕过 | D |
| G08 | [ORCID](https://orcid.org/) | 全球 / 身份消歧 | 姓名、机构、已知 ORCID | 姓名变体、标识、任职/成果来源 | 自述/旧资料不能独立证明当前资格 | 静态 / API / Browser Use | 当前机构官网、出版商作者信息 | D |
| G09 | [OpenAlex](https://openalex.org/) | 全球 / 跨学科发现 | 作者、机构、作品题名/DOI | 标识、作品和合作线索 | 消歧可能错；API认证/用量查实时官方文档 | 静态 / API / Browser Use | G01、G10、机构/出版商 | D |
| G10 | [Crossref REST 文档](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | 全球 / 元数据 | DOI、准确标题 | DOI、标题、作者、日期、更新/版本关系 | 提交元数据缺项不证明没有贡献/成果 | 官方 API / 静态 | 出版商原文、G01 | D |
| G11 | [ICMJE](https://www.icmje.org/recommendations/browse/roles-and-responsibilities/defining-the-role-of-authors-and-contributors.html) · [CRediT](https://credit.niso.org/) | 全球 / 贡献解释 | 查定义，再读论文贡献声明 | 实际公开的概念、监督、方法、分析、资源、资金等角色 | 作者次序/通讯身份不能代替具体贡献 | 静态 | 具体论文声明；无法读取则未知 | S（CRediT）；ICMJE未复测 |
| G12 | 当前机构/实验室/机构库；[大学官网导航示例](https://www.sjtu.edu.cn/) | 全球 / 任职、培养 | Faculty / People / Research / Graduate / Repository；姓名+机构 | 当前职位、导师名册、项目、学位论文、手册、平台 | 官网宣传/制度不证明实际指导体验；不强制`.edu` | 静态 / Browser Use | 项目/学院官网、图书馆导航、公开履历互证 | R |

## 中国大陆

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | 学校研招/医学院；[交大研招示例](https://yzb.sjtu.edu.cn/) · [医学院示例](https://www.shsmu.edu.cn/yjsy/zsgz1.htm) | 大陆 / 博士入口 | 姓名、专业、年份、博士、申请考核 | 当批次简章、学院细则、导师目录、资格、学位、奖助 | 示例非推荐；医院需映射授予单位，校本部不替代医学院细则 | 静态 / Browser Use / 公开PDF | 学校官网→研究生院/学院招生栏目 | D |
| C02 | [NSFC](https://www.nsfc.gov.cn/) · [知识平台](https://kd.nsfc.cn/) · [查询FAQ](https://www.nsfc.gov.cn/p1/2961/2962/3648/cx.html) | 大陆 / 项目与结题 | 项目号、题名、负责人、单位，按公开功能查询 | 角色、题名、期限、可见金额口径、结题成果 | 人员承担/参与查询可能需本人或单位管理员；不承诺个人全部在研基金 | 静态 / Browser Use；登录另授权 | 官方获批/结题公告→机构项目→论文基金号，保留时点 | S（FAQ）；主页/平台未复测 |
| C03 | [国家科技管理信息系统公共服务平台](https://service.most.gov.cn/) | 大陆 / 专项公开资料 | 专项、题名、项目号、单位 | 获批/公示、承担单位、公告日期 | 指南/征求意见不等于获资助；公开覆盖有限 | 静态 / Browser Use | 科技部官方导航、项目单位公告 | D |
| C04 | [CNKI](https://www.cnki.net/) · [万方](https://www.wanfangdata.com.cn/) | 大陆 / 中文论文与博士论文 | 姓名、导师、授予单位、博士、年份 | 公开题名、学位、导师、年份、摘要 | 商业/登录/付费不绕过；硕士不能混成博士样本 | 静态 / Browser Use；登录另授权 | 学校知识库、学位公告、公开摘要 | D |
| C05 | [ChiCTR](https://www.chictr.org.cn/) | 大陆及相关研究 / 试验 | 疾病、题名、单位、研究者、注册号 | 注册号、角色、申办方、状态、更新时间 | 联系人/分中心不等于总负责人或博士导师；不证明数据访问 | 静态 / Browser Use | 原机构项目、M01、U04 | D |
| C06 | 医院/研究所科研与教育；[医学院官方入口示例](https://www.shsmu.edu.cn/) | 大陆 / 资源与培养 | 目标机构官网→科研/教学/研究生；姓名、队列 | 平台、队列、公开项目、培养资格线索 | 医院陈述仅支持其时点；学位/批次回招生单位 | 静态 / Browser Use | 授予大学、课题论文、官方平台页 | R |

NSFC 降级证据不能把旧论文基金号变成当前资助。[官方查询 FAQ](https://www.nsfc.gov.cn/p1/2961/2962/3648/cx.html) 说明人员项目数查询需本人/管理员入口，已结题成果有公开平台。账户内博士报名系统不是候选发现前提；不要求用户提供研招账号。

## 中国香港

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H01 | 研究生院/项目；[HKU示例](https://gradsch.hku.hk/) | 香港 / 项目入口 | PhD、program、supervisor、intake | 师资、程序、联系要求、费用、资助、批次 | 具体学院/项目要求优先；项目开放不等于每位PI收人 | 静态 / Browser Use | 大学官网→学院/研究生院、公开招生文件 | D |
| H02 | [RGC计划](https://www.ugc.edu.hk/eng/rgc/funding_opport/) · [GRF获资助研究](https://www.ugc.edu.hk/eng/rgc/funding_opport/grf/funded_research.html) | 香港 / 项目资金 | 按GRF/ECS/CRF/TRS等官方 Funded Projects Enquiry；姓名、机构、主题 | 项目号、角色、年份、主题、金额口径 | GRF不是全部RGC；计划征集非获奖事实；不猜旧路径 | 静态 / Browser Use | RGC官方导航、机构获批公告 | D |
| H03 | [HKPFS](https://www.ugc.edu.hk/eng/rgc/funding_opport/hkpfs/) | 香港 / 学生资助 | 年度、资格、大学配套要求 | 条件、期限、步骤、校方截止 | 竞争奖学金不是个人已获资助；与PI研究经费分列 | 静态 / Browser Use | RGC/大学当年奖学金文件 | D |
| H04 | 大学论文库；[HKU图书馆示例](https://lib.hku.hk/) | 香港 / 博士培养 | 姓名、thesis、supervisor、年份 | 学位、指导关系、题名、毕业记录 | 不可见不等于不存在；不推算全体结果 | 静态 / Browser Use | 大学库导航、项目/校友正式履历 | R |

## 中国台湾

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | 大学招生/系所；[台大示例](https://www.ntu.edu.tw/) | 台湾 / 博士入口 | 博士班、招生簡章、系所、年份、申請身分 | 学位、当年资格、身份适用入口、实验室、奖助 | 身份按官方条款问用户，不自行假定 | 静态 / Browser Use | 官方招生/国际事务/系所导航 | R |
| T02 | [NSTC](https://www.nstc.gov.tw/) · [研究人才](https://wrs.nstc.gov.tw/) | 台湾 / 身份与研究 | 姓名、机构、专长 | 公开任职/研究人才线索、更新时间 | 公开资料有覆盖和更新限制 | 静态 / Browser Use | 当前大学官网、论文身份消歧 | D |
| T03 | [学术补助奖励查询](https://wsts.nstc.gov.tw/) | 台湾 / 补助 | 姓名、机构、年度、具体类别 | 补助/奖励类别、研究项目、角色 | 奖励不等于研究经费，字段按类别解释 | 静态 / Browser Use | NSTC官方导航、机构公告 | D |
| T04 | [GRB](https://www.grb.gov.tw/) | 台湾 / 研究项目 | 题名、主持人、执行单位 | 项目、报告、成果、日期 | 维护/失败不是查无；报告不证明现仍在资助 | 静态 / Browser Use | NSTC官方链接、项目单位资料 | D |
| T05 | [博硕士论文系统](https://ndltd.ncl.edu.tw/) | 台湾 / 培养 | 指導教授、博士、学校、年份 | 论文、学位、指导关系、年份 | 分清硕士/博士、共同指导；全文依权限 | 静态 / Browser Use；登录另授权 | 大学论文库、正式履历 | D |

## 美国

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U01 | 大学/生物医学博士项目；[大学导航示例](https://www.harvard.edu/) | 美国 / 正式入口 | Graduate、Biomedical Sciences、PhD、faculty、rotation | 培养类型、导师资格、轮转、资助承诺、资格/批次 | 不默认全部轮转，PI无广告不说明委员会项目关闭 | 静态 / Browser Use | 项目手册、官方招生文件、学院页 | R |
| U02 | [NIH RePORTER](https://reporter.nih.gov/) · [API](https://api.reporter.nih.gov/) · [FAQ](https://report.nih.gov/faqs) | 美国 / 研究经费 | 姓名变体+机构、项目号、主题；active后必要财年 | 角色、财年、预算/项目期、金额口径、状态 | 年度非全周期；母子可能重复；active可含无新增经费延期；不保证学生资助 | Browser Use / 官方API / 静态说明 | 改查必要财年、机构公告、论文基金号 | S（FAQ/API文档）；搜索页JS空壳，API查询未执行 |
| U03 | [NSF Award Search](https://www.nsf.gov/awardsearch/) | 美国 / 基础/交叉资金 | PI、机构、主题、奖项号 | 角色、项目期、金额口径、状态 | 补充NIH，非医学资金全集 | Browser Use / 官方API | NSF官方导航、机构项目公告 | D |
| U04 | [ClinicalTrials.gov](https://clinicaltrials.gov/) · [API说明](https://clinicaltrials.gov/data-api/api) | 全球 / 临床研究 | 疾病、单位、研究者、NCT号 | 注册号、申办/负责角色、状态、更新 | 并非仅美国；试验角色不证明数据权限或博士指导资格 | Browser Use / 官方API | 原注册/机构页面、M01；API按现行schema | D |
| U05 | 学位论文/实验室/毕业生页；[Harvard DASH示例](https://dash.harvard.edu/) | 美国 / 培养 | 姓名、doctoral thesis、supervisor | 博士关系、主题、年份、成果、去向 | 博士后或共同作者不能计为博士培养 | 静态 / Browser Use | 机构图书馆导航、项目毕业记录 | R |

[NIH FAQ](https://report.nih.gov/faqs) 区分项目期与预算期，并说明 active 可能包括无新增经费延期。保存财年和金额口径；不要累计母项目与已计入的子项目，不把研究经费解释为学生资助。未找到 NIH/NSF 不证明没有慈善、医院、机构等其他资金。

## 欧洲：共同入口及国家补充

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | [CORDIS项目](https://cordis.europa.eu/projects) | 欧盟项目 / 研究 | 题名、项目号、机构、主题 | 协调/参与角色、周期、结果、资助口径 | 不覆盖全部国家资金；联盟总额非PI可支配额 | 静态 / Browser Use | 欧盟官方项目页、参与单位记录 | D |
| E02 | [EURAXESS岗位](https://euraxess.ec.europa.eu/jobs/search) | 欧洲及所列地区 / 机会 | 国家、学科、岗位类型、PhD | 正式标题、雇主、资格、学位关联、截止 | R1不单独证明博士入学岗位；回雇主原文 | Browser Use / 静态 | 雇主招聘/doctoral school官网 | D |
| E03 | [UKRI GtR](https://gtr.ukri.org/) | 英国 / 基金 | 研究者、机构、题名、编号 | 角色、周期、金额口径、成果、数据更新日期 | 更新日期不是访问日期；研究项目非学生资助 | 静态 / Browser Use | UKRI/项目单位公告、学校studentship | D |
| E04 | [DFG GEPRIS](https://gepris.dfg.de/) | 德国 / 基金 | 姓名、项目、机构 | 角色、主题、期限、项目关系 | 不是德国全部资金 | 静态 / Browser Use | DFG/机构公开公告 | D |
| E05 | [ANR获资助项目](https://anr.fr/en/funded-projects-and-impact/funded-projects/) | 法国 / 基金 | 题名、机构、协调人、年度 | 协调/参与角色、主题、期限 | 挑战/受阻不是无项目 | 静态 / Browser Use | ANR导航、项目单位/课题网站 | D |
| E06 | [NWO项目](https://www.nwo.nl/en/projects) | 荷兰 / 基金 | 姓名、机构、题名 | 项目、角色、周期 | 旧深链或失败不能证明无资助 | 静态 / Browser Use | NWO官方导航→项目、机构公告 | D |
| E07 | [SNSF Data Portal](https://data.snf.ch/) | 瑞士 / 基金 | 姓名、机构、项目号 | 项目、资助口径、机构、角色、周期 | 非欧盟数据库完整覆盖；岗位与研究经费分查 | Browser Use / 静态 | SNSF官方导航、学校岗位页 | D |
| E08 | 国家大学/研究所/博士项目；[EURAXESS导航](https://euraxess.ec.europa.eu/) | 欧洲各国 / 学位与岗位 | doctoral school、PhD、学位授予单位、当地语言 | 学位归属、联合指导、项目、岗位、资助、批次 | 研究所任职不自动等于授予学位；不套国别流程 | 静态 / Browser Use | 候选当前机构→合作大学官方文件 | R |

英国与瑞士单独路由。其他国家按任务补其官方资助/学校来源，不以 CORDIS 查不到排除，不只搜英语页面。宽泛欧洲探索报告实际覆盖国家。

## 澳大利亚

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A01 | 大学研究学位/导师/奖学金；[Melbourne示例](https://www.unimelb.edu.au/) | 澳大利亚 / 入口 | Research Degrees、Graduate Research、Find a Supervisor | 导师、PhD项目、费用、奖学金周期/资格、批次 | 校别/批次分查，研究经费非学生奖学金 | 静态 / Browser Use | 当前大学研究生院/学院官方导航 | R |
| A02 | [NHMRC outcomes](https://www.nhmrc.gov.au/funding/data-research/outcomes) | 澳大利亚 / 项目资金 | 年度数据、姓名、机构、项目 | 编号、角色、年度、金额口径、数据字典 | 汇总总额不分配给个人；保留年度/字段定义 | 静态 / Browser Use / 公开下载 | NHMRC导航、项目/机构公告 | D |
| A03 | [ARC Data Portal](https://dataportal.arc.gov.au/) | 澳大利亚 / 基础与交叉 | 姓名、机构、主题、编号 | 角色、资助、期限、项目 | 非医学经费全集 | Browser Use / 官方导出 | ARC/机构公告 | D |
| A04 | MRFF：从 [NHMRC outcomes](https://www.nhmrc.gov.au/funding/data-research/outcomes) 的卫生部门链接进入 | 澳大利亚 / 医学项目 | MRFF、题名、机构、年度 | 官方资助公告、项目、角色、周期 | 下游未核验，不编造深链或完整覆盖 | 静态 / Browser Use | 卫生部门官方导航、获资助机构 | R |

## 日本

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J01 | [KAKEN](https://kaken.nii.ac.jp/en/) | 日本 / 研究经费 | 日/英姓名、机构、项目号、题名 | 角色、主题、研究期间、经费口径 | 不是全部医学资金；博士资格另查 | 静态 / Browser Use | 机构/官方资助公告 | D |
| J02 | [researchmap](https://researchmap.jp/) | 日本 / 身份与研究 | 正确日文/英文姓名、单位 | 专长、公开成果、任职、更新 | 自述/旧资料与现机构互证 | 静态 / Browser Use | 当前机构官网、J01、出版商 | D |
| J03 | [JREC-IN](https://jrecin.jst.go.jp/seek/SeekTop?ln=1) | 日本 / 岗位与团队 | 姓名、学科、机构、职位类型 | 正式职位、研究题目、资格、期限 | 各类研究/教职不是博士招生；博士后不得冒充PhD opening | 静态 / Browser Use | 雇主原广告、J04 | D |
| J04 | 大学研究科/专攻；[东京大学示例](https://www.u-tokyo.ac.jp/) | 日本 / 博士入口 | 博士、医学研究科、募集要項、年份 | 学位、考试、语言、事前联系、奖助、身份 | “研究生”不自动等于博士学位在读；读具体制度 | 静态 / Browser Use | 大学→研究科→招生、当年PDF | R |

## 医学资源：只按研究路线补充

| source_id | 名称与可点击入口 | 地区 / 任务 | 查询字段/关键词 | 优先提取 | 证据边界 | 访问方式 | 失败回退 | 日期/层级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | [WHO ICTRP](https://trialsearch.who.int/) | 全球 / 临床注册 | 疾病、单位、姓名、注册号 | 原注册平台/号、角色、状态、更新 | 多平台注册去重；聚合后回原记录 | 静态 / Browser Use | 原注册平台、U04/C05、机构页 | D |
| M02 | [ClinicalTrials.gov](https://clinicaltrials.gov/) / [ChiCTR](https://www.chictr.org.cn/) | 跨地区 / 临床关系 | 按U04/C05 | 按U04/C05 | 主办/牵头/分中心/联系人分开，不能证明数据访问 | 按U04/C05 | 原记录、M01 | D；复用U04/C05 |
| M03 | [GEO](https://www.ncbi.nlm.nih.gov/geo/) | 全球 / 组学 | accession、PI、论文、疾病 | 提交、原论文、项目关系、开放条件 | 公共数据使用不等于独家资源；不下载大型矩阵 | 静态 / 官方API / Browser Use | 原论文Data availability、机构数据页 | D |
| M04 | 队列/脑库/样本库/联盟；从 [PMC全文](https://pmc.ncbi.nlm.nih.gov/) 或具体项目原始链接进入 | 全球 / 资源治理 | 论文Methods/Data availability、资源名、access | 治理、参加角色、范围、申请条件 | 机构成员不证明PI/新博士有全数据权限 | 静态 / Browser Use | 资源机构官方导航、原论文 | R |
| M05 | Core Facilities / Research Platforms；[机构导航示例](https://www.sjtu.edu.cn/) | 全球 / 技术训练 | 成像、病理、计算、统计、模型等所需平台 | 服务、准入、费用、方法指导 | 机构有设施不保证PI或新博士能使用 | 静态 / Browser Use | 具体平台/项目文件、公开服务条例 | R |

## 查询模板与停止规则

替换花括号再执行；保留原词与英语全称、必要中/繁/日文变体；有歧义的缩写先展开，不把所有条件挤成极窄AND。

```text
"{disease_or_mechanism}" "{question_or_method}"
"{disease_or_mechanism}" laboratory "{region_or_institution}"
"{PI_full_name}" "{institution}" faculty
site:{verified_institution_domain} "{PI_full_name}" graduate program
site:{verified_institution_domain} "{program}" "{intake}" admissions
"{导师姓名}" "{单位}" 博士 招生
"{姓名}" "{系所}" 博士班 指導教授
"{姓名}" "{单位}" 项目 基金
"{PI_name_Japanese}" "{university}" 博士 募集要項
"{PI_name_Japanese}" 研究課題
"{PI_full_name}" doctoral thesis supervisor
"{program}" PhD funding scholarship
"{PI_full_name}" cohort biobank data access
```

PubMed（只加与本轮相关的条件）：

```text
("{verified_MeSH_term}"[MeSH Terms] OR "{disease_phrase}"[tiab])
AND ("{method_phrase}"[tiab] OR "{mechanism_phrase}"[tiab])
AND ("{start_YYYY/MM/DD}"[dp] : "{end_YYYY/MM/DD}"[dp])
```

[PubMed帮助](https://pubmed.ncbi.nlm.nih.gov/help/) 已核对：`[fau]` 是 full author，`[1au]` 是第一作者，`[lastau]` 是末位个人作者；`[ad]` 不证明机构与目标作者一一对应。不存在可自造的 `[corresponding author]` 字段。MeSH 和自由词结合以覆盖尚未索引论文。

每轮在 run/evidence 中记录范围、真实查询/筛选、访问来源/时间、事实及缺口。项目申请事实只查一次，PI科研记录在多个项目间复用。优先补会改变决策的博士入口、资助等未知项；足够支持约定比较或边际信息很少时停止。来源受限按浏览器策略有限重试/降级，不把预算未查完写成没有候选。
