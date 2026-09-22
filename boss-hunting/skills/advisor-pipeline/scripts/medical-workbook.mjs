import { dateCell, formulaCell } from "./workbook-runtime.mjs";
import { buildMedicalDiscoveryView, evidenceProfile, medicalProject, normalizeMedicalCandidate } from "./medical-evidence.mjs";

function rows(value) { return Array.isArray(value) ? value : []; }

function text(value) {
  if (value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) return value.map(text).filter(Boolean).join("\n");
  if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${key}: ${text(item)}`).join("; ");
  return String(value);
}

function sourceLink(value) {
  const url = String(value || "");
  if (!/^https?:\/\/[^\s]+$/i.test(url)) return url;
  const escaped = url.replaceAll('"', '""');
  // Only the exporter constructs formulas; source text is never a formula cell.
  return formulaCell(`HYPERLINK("${escaped}","${escaped}")`, url);
}

function table(name, headers, data) {
  return { name, headers, rows: data, widths: headers.map((header, index) => index < 3 ? 24 : 38), freezeRows: 1, freezeColumns: 3 };
}

function profileTable(name, candidates, project, advisorOnly = false) {
  const discovery = project.searchMode === "discovery" || advisorOnly;
  const headers = [
    "展示序号（非质量排名）", "advisor_id", "advisorProgramId", "导师姓名", "当前机构", "官方主页",
    "真实项目", "学位", "入学批次", "疾病/机制", "研究方式", "核心科学问题",
    "科学问题匹配", "科学匹配理由与证据", "希望获得的训练", "训练支持与证据",
    "近期代表研究及 DOI/来源", "项目/岗位路径", "是否轮转", "联系规则",
    "申请资格", "招生机会", "硬条件状态与依据", "研究资源及访问证据层级",
    "研究项目经费", "博士生资助", "博士培养公开样本与局限", "培养制度与环境",
    "关键未知", "支持的风险", "下一步核验", "比较分组", "最后核验日期", "来源",
  ];
  const data = candidates.map((original, index) => {
    const row = normalizeMedicalCandidate(original, project, index);
    const profile = evidenceProfile(row);
    return [
      index + 1, row.advisor_id || row.advisorId || "", advisorOnly ? "" : row.advisorProgramId || "",
      row.name || row.advisorName || "", row.currentInstitution || row.current_institution || row.school || row.schoolName || "",
      sourceLink(row.homepage || row.advisorHomepage),
      advisorOnly ? "" : row.program || row.programNameZh || row.programNameEn || "",
      advisorOnly ? "" : row.degree || "", advisorOnly ? "" : row.intake || "",
      text(profile.diseasesOrMechanisms || row.diseasesOrMechanisms || project.medicalProfile?.diseasesOrMechanisms || project.medicalProfile?.diseaseScope),
      text(profile.researchModes || row.researchModes || project.medicalProfile?.researchModes),
      text(profile.researchQuestions || row.researchQuestions || project.medicalProfile?.researchQuestions),
      profile.scientificFit.status, text(profile.scientificFit),
      text(project.medicalProfile?.desiredTraining), text(profile.trainingFit),
      text(row.recent_papers || row.recentPapers || row.researchAndPapers),
      discovery && row.applicationPathway === "unknown" ? "本次未核验" : row.applicationPathway,
      text(row.rotation || row.rotationRequirements || "本次未核验"),
      text(row.advisorContactRequirements || row.advisor_contact_requirements),
      discovery ? "本次未核验" : row.feasibility,
      discovery && row.opportunityStatus === "unknown" ? "本次未核验" : row.opportunityStatus,
      text([row.hardConstraintStatus, ...(row.hardConstraintReasons || [])]),
      text(profile.resources || row.resources), text(profile.researchFunding || row.research_funding),
      text(profile.doctoralFunding || row.doctoral_funding), text(profile.doctoralOutcomes || row.doctoral_outcomes),
      text(profile.trainingEnvironment || row.training_environment),
      text(profile.keyUnknowns), text(profile.supportedRisks || row.risksAndGaps),
      text(profile.nextVerification || row.recommendedAction), row.comparisonGroup,
      row.lastVerifiedAt || row.last_verified_at ? dateCell(row.lastVerifiedAt || row.last_verified_at) : "",
      text(row.officialSources || row.source_ids || row.sourceIds),
    ];
  });
  return table(name, headers, data);
}

export function buildMedicalWorkbookSheets(input, overrides = {}) {
  const project = { ...medicalProject(input),
    cvValid: input.cvValid === true,
    evidenceRecords: rows(input.evidenceRows || input.evidence || input.sources || input.sourceRows) };
  const advisors = rows(input.advisorRecords || input.advisor_records);
  const candidates = rows(overrides.candidates || input.applicationRows || input.candidates || input.advisors);
  const sheets = [];
  if (project.searchMode === "discovery") {
    const unmapped = advisors.length ? advisors : candidates.filter((row) => !row.advisorProgramId);
    const view = buildMedicalDiscoveryView(unmapped, project);
    sheets.push(profileTable("1_医学方向探索", view, project, true));
    const mapped = candidates.filter((row) => row.advisorProgramId);
    if (mapped.length) sheets.push(profileTable("2_真实项目比较", mapped, project));
  } else {
    if (candidates.some((row) => !row.advisorProgramId)) {
      throw new Error("医学申请比较必须使用真实 advisorProgramId；导师级记录请使用方向探索输出");
    }
    sheets.push(profileTable("1_医学申请比较", candidates, project));
    if (advisors.length) sheets.push(profileTable("2_导师探索视图", buildMedicalDiscoveryView(advisors, project), project, true));
  }
  const evidence = rows(input.evidenceRows || input.evidence || input.sources || input.sourceRows);
  sheets.push(table("3_证据来源与缺口", [
    "证据ID", "实体", "支持字段", "主张类型", "主张内容", "事实状态", "来源 URL", "页面标题",
    "来源更新时间", "访问时间", "适用批次", "支持片段/定位", "读取深度", "检索方式", "提取状态", "同源组", "限制",
  ], evidence.map((row) => [
    row.evidence_id || row.evidenceId || "", row.entity_id || row.entity || row.advisorName || "",
    text(row.fields_supported || row.field || row.sectionId), row.claim_type || row.claimType || "",
    text(row.claim || row.finding || row.value), row.status || "not_checked", sourceLink(row.final_url || row.source_url || row.url), row.page_title || row.title || "",
    row.source_updated_at || row.sourceUpdatedAt || "", row.accessed_at || row.accessedAt ? dateCell(row.accessed_at || row.accessedAt) : "",
    row.intake || row.applicable_intake || "", text([row.excerpt || row.note, row.page_locator || row.locator].filter(Boolean)), row.reading_depth || row.read_depth || row.readDepth || "",
    row.retrieval_method || row.retrievalMethod || "", row.extraction_status || row.extractionStatus || "",
    row.same_source_group || row.source_group_id || row.sourceGroupId || "", text(row.limitations || row.failure_reason || row.gap),
  ])));
  sheets.push(table("4_配置与解释", ["项目", "内容"], [
    ["比较模式", "evidence_profile；展示序号不是导师质量排名；不生成综合分、录取概率或申请竞争分组"],
    ["检索模式", project.searchMode || "discovery"], ["目标范围", text(project.target)],
    ["用户画像", text(project.medicalProfile)],
    ["研究经费与博士资助", "分别记录；机构有资源、导师使用、当前项目使用、新博士可用是不同证据层级"],
    ["未知与培养样本", "未查、未找到、访问受阻、冲突和过期分别保留；没有分母不计算毕业率或成功率"],
    ["材料边界", "导师级探索记录无项目ID，不进入RP/套磁材料选择；材料模块仍需真实背景及确切导师—项目确认"],
  ]));
  return sheets;
}
