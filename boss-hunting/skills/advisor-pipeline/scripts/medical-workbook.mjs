import { doctoralWorkbookSummary, overlayDoctoralProfile } from "./doctoral-evidence.mjs";
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

function works(items) {
  return text(items.map((work) => [work.title, work.year, work.venue, work.verifiedRole !== "unknown" ? work.verifiedRole : null, work.doi || work.url]
    .filter(Boolean).join(" | ")));
}

function people(items) {
  return text(items.map((person) => [person.name, person.degreeOrYear, person.topic, person.firstDestination, person.latestPublicRole].filter(Boolean).join(" | ")));
}

// Columns follow the five public-evidence modules (A identity, B mainline,
// C network, D latest signals/projects, E doctoral trajectory). Training,
// resources, doctoral personal funding and environment columns were removed.
function profileTable(name, candidates, project, advisorOnly = false) {
  const discovery = project.searchMode === "discovery" || advisorOnly;
  const headers = [
    "展示序号（非质量排名）", "advisor_id", "advisorProgramId", "导师姓名", "当前机构 / 院系 / 职位", "官方主页",
    "真实项目", "学位", "入学批次", "发现路径", "PI 角色置信 / Level", "证据充分度", "当前活跃度",
    "研究问题契合", "契合理由与证据", "主线连续性", "连续性理由",
    "A 当前科研定位", "A 博士指导关联", "B 长期科学问题", "B 持续主题 / 新方向 / 近期转向", "B 代表性工作（已核实角色）",
    "C 核心合作者", "C 研究邻居", "D 最新论文 / 预印本", "D 公开项目记录", "E 当前博士生", "E 已毕业博士", "E Graduate Program",
    "正式记录", "方向契合边界", "关键未知", "下一步核验",
    "项目/岗位路径", "申请资格", "招生机会", "硬条件状态与依据", "比较分组", "最后核验日期", "来源",
  ];
  const data = candidates.map((original, index) => {
    const row = normalizeMedicalCandidate(original, project, index);
    const profile = evidenceProfile(row);
    const stored = project.advisorRecords?.find((advisor) => (advisor.advisor_id || advisor.advisorId) === (row.advisor_id || row.advisorId));
    const base = evidenceProfile(stored || {});
    const doctoral = base.doctoralTrajectory || base.doctoral_trajectory;
    if (doctoral) profile.doctoralTrajectory = overlayDoctoralProfile(doctoral, profile.doctoralTrajectory);
    const mainline = profile.researchMainline;
    const network = profile.collaborationNetwork;
    const signals = profile.latestSignals;
    const doctoralView = normalizeMedicalCandidate({ ...row, evidenceProfile: profile }, project, index).evidenceProfile.doctoralTrajectory;
    return [
      index + 1, row.advisor_id || row.advisorId || "", advisorOnly ? "" : row.advisorProgramId || "",
      row.name || row.advisorName || "",
      text([profile.identity.currentInstitution || row.current_institution || row.school || row.schoolName, profile.identity.department, profile.identity.currentPosition].filter(Boolean)),
      sourceLink(profile.identity.officialProfileUrl || row.homepage || row.advisorHomepage),
      advisorOnly ? "" : row.program || row.programNameZh || row.programNameEn || "",
      advisorOnly ? "" : row.degree || "", advisorOnly ? "" : row.intake || "",
      row.discoveredVia, text([profile.piRoleConfidence.status, profile.piRoleConfidence.level].filter(Boolean)),
      profile.evidenceSufficiency, profile.currentActivity,
      profile.researchQuestionFit.status, text(profile.researchQuestionFit.reasons),
      profile.researchRouteContinuity.status, text(profile.researchRouteContinuity.reasons),
      text(profile.identity.researchPositioning), text(profile.identity.doctoralSupervisionLink),
      text(mainline.longTermQuestion),
      text([mainline.continuingThemes.length ? `持续：${mainline.continuingThemes.join("；")}` : "", mainline.newDirections.length ? `新方向：${mainline.newDirections.join("；")}` : "", mainline.recentShift ? `近期转向：${mainline.recentShift}` : ""].filter(Boolean)),
      works(mainline.representativeWorks),
      text(network.coreCollaborators.map((person) => [person.name, person.currentInstitution, person.jointRecordCount ? `${person.jointRecordCount} 条共同记录` : null].filter(Boolean).join(" | "))),
      text(network.researchNeighbors.map((neighbor) => [neighbor.name, neighbor.type].filter(Boolean).join(" | "))),
      works([...signals.latestPapers, ...signals.preprints]),
      text(signals.projects.map((item) => [item.title, item.projectId, item.fundingBody, item.piRole, item.period, item.status, item.amount !== null && item.amount !== undefined ? `${item.amount} ${item.amountUnit || ""}` : "金额未公开"].filter(Boolean).join(" | "))),
      people(doctoralView.currentDoctoral), people(doctoralView.formerDoctoral),
      text([doctoralView.graduateProgram.graduateSchool, doctoralView.graduateProgram.doctoralProgram, doctoralView.graduateProgram.supervisorListing,
        doctoralView.emergingPiNote ? `新兴 PI：${doctoralView.emergingPiNote}` : null, doctoralWorkbookSummary(doctoralView, project.evidenceRecords)].filter(Boolean)),
      text(profile.formalRecords), text(profile.fitBoundary), text(profile.keyUnknowns), text(profile.nextVerification),
      discovery && row.applicationPathway === "unknown" ? "本次未核验" : row.applicationPathway,
      discovery ? "本次未核验" : row.feasibility,
      discovery && row.opportunityStatus === "unknown" ? "本次未核验" : row.opportunityStatus,
      text([row.hardConstraintStatus, ...(row.hardConstraintReasons || [])]),
      row.comparisonGroup,
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
  project.advisorRecords = advisors;
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
    ["比较模式", "evidence_profile；展示序号按研究问题契合与主线连续性排列，不是导师质量排名；不生成综合分、引用量排名、录取概率或申请竞争分组"],
    ["检索模式", project.searchMode || "discovery"], ["目标范围", text(project.target)],
    ["研究画像", text(project.medicalProfile)],
    ["五模块", "A 导师身份与当前科研定位；B 近五年科研主线与研究路线；C 科研合作网络；D 最新公开研究动向与项目支撑；E 博士培养轨迹"],
    ["已删除范围", "不评估训练匹配、实验室资源、博士生个人资助、培养环境/氛围、申请者能力或综合质量分"],
    ["项目记录", "说明科研支撑；公开库无记录不等于没有基金；金额按来源单位原样记录"],
    ["合作网络", "collaboration edge（共同发表/项目/基金/试验）与 research-neighbor edge（引用/共被引/相似）分开；单篇 consortium 论文不构成合作"],
    ["未知与培养样本", "未查、未找到、访问受阻、部分、冲突和过期分别保留；没有分母不计算毕业率或培养成功率；新兴 PI 无毕业博士不作负面推断"],
    ["材料边界", "导师级探索记录无项目ID，不进入RP/套磁材料选择；材料模块仍需真实背景及确切导师—项目确认"],
  ]));
  return sheets;
}
