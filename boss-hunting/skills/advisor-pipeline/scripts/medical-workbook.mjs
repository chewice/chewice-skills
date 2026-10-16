import { firstAuthorIdentity, firstAuthorSummary, doctoralWindow, overlayDoctoralProfile } from "./doctoral-evidence.mjs";
import { academicTalkRows } from "./academic-events.mjs";
import { dateCell, formulaCell } from "./workbook-runtime.mjs";
import { buildMedicalDiscoveryView, evidenceProfile, identityCoverage, medicalProject, normalizeMedicalCandidate, mergeResearchMainline } from "./medical-evidence.mjs";
import { publicationReview, publicationRoleLabel, readableText } from "./publication-evidence.mjs";

const rows = value => Array.isArray(value) ? value : [];
const words = {
  verified: "已核实", partial: "部分核实", inaccessible: "访问受阻", not_checked: "待核实", not_found: "所查范围未找到",
  conflict: "来源存在冲突", stale: "信息可能过期", unknown: "尚不清楚", not_applicable: "不适用",
  direct: "直接相关", adjacent: "相邻方向", weak: "弱相关", insufficient_information: "信息不足",
  eligible: "符合已核实条件", ineligible: "不符合已核实条件", needs_confirmation: "需要进一步确认",
  committee_led: "由项目委员会招生", rotation_led: "轮转后选导师", pi_led: "由导师招生", position_led: "公开岗位申请",
  verified_open: "已核实开放申请", verified_closed: "已核实关闭申请", advertised: "已有公开招募", pass: "已通过核验", fail: "不符合条件",
};
function text(value) { const prose = readableText(value); return words[prose] || prose; }
function compact(values, separator = "；") {
  const items = [...new Set(values.flatMap(value => Array.isArray(value) ? value : [value]).map(text).filter(Boolean))];
  return items.filter(item => !items.some(other => other.length > item.length && other.includes(item))).join(separator);
}
function sourceUrl(row) { return row.final_url || row.source_url || row.url || ""; }
function sourceLink(value, label = "查看来源") {
  const url = String(value || "");
  if (!/^https?:\/\/[^\s]+$/i.test(url)) return "";
  const escaped = url.replaceAll('"', '""');
  return formulaCell(`HYPERLINK("${escaped}","${label}")`, label);
}
function table(name, headers, data, widths) {
  return { name, headers, rows: data, widths: widths || headers.map((_, index) => index === 0 ? 24 : 38), freezeRows: 1, freezeColumns: 1 };
}
function publicationUrl(paper) {
  return paper.url || (paper.doi ? `https://doi.org/${String(paper.doi).replace(/^https?:\/\/doi\.org\//i, "")}` : "");
}
function combinedRow(original, project, index) {
  const row = normalizeMedicalCandidate(original, project, index);
  const stored = project.advisorRecords.find(advisor => (advisor.advisor_id || advisor.advisorId) === (row.advisor_id || row.advisorId));
  if (!stored) return row;
  const storedProfile = evidenceProfile(stored);
  const profile = { ...storedProfile, ...row.evidenceProfile };
  profile.researchMainline = mergeResearchMainline(normalizeMedicalCandidate(stored, project).evidenceProfile.researchMainline, row.evidenceProfile.researchMainline);
  const doctoral = storedProfile.doctoralTrajectory || storedProfile.doctoral_trajectory;
  if (doctoral) profile.doctoralTrajectory = overlayDoctoralProfile(doctoral, profile.doctoralTrajectory);
  return normalizeMedicalCandidate({ ...stored, ...row, evidenceProfile: profile }, project, index);
}
function unresolved(row, review, project) {
  const profile = row.evidenceProfile;
  const personal = rows(profile.keyUnknowns).map(text).flatMap(item => item
    .replace(/Finder阶段未深查三模块|用户选定后补充三模块背景调研|用户选择后再查完整近五年通讯论文与作者信息/g, "")
    .split(/[；;]/).map(part => part.replace(/^[\s，,。]+|[\s，,。]+$/g, "")).filter(Boolean))
    .filter(item => project.searchMode !== "discovery" || !/招生|招生名额|申请批次|博士项目映射|doctoral.*(?:supervision|program)|programme.*(?:intake|terms)|program.*(?:intake|terms)/i.test(item));
  const identity = identityCoverage(row, project.evidenceRecords).gaps
    .filter(gap => !["doctoralSupervisionLink", "researchPositioning"].includes(gap.field))
    .map(gap => `${gap.label}：${gap.reason}`);
  return compact([...personal, ...identity, ...(!review.searchComplete && !review.limitations.length ? [review.searches.length ? "近五年论文的检索或署名核验尚未完成，详见论文清单。" : "近五年论文检索记录尚未补齐。"] : []), ...review.limitations], "\n");
}
function mainlineSummary(profile) {
  const mainline = profile.researchMainline;
  return compact([mainline.longTermQuestion || profile.identity.researchPositioning, mainline.continuingThemes,
    mainline.newDirections.length ? `近期拓展：${text(mainline.newDirections)}` : "", mainline.recentShift ? `研究转向：${text(mainline.recentShift)}` : ""]);
}

// Workbook views consume the same review as HTML; pending leads never inflate counts.
export function buildMedicalWorkbookSheets(input, overrides = {}) {
  const evidence = rows(input.evidenceRows || input.evidence || input.sources || input.sourceRows);
  const advisors = rows(input.advisorRecords || input.advisor_records);
  const project = { ...medicalProject(input), cvValid: input.cvValid === true, evidenceRecords: evidence, advisorRecords: advisors };
  const candidates = rows(overrides.candidates || input.applicationRows || input.candidates || input.advisors);
  if (project.searchMode !== "discovery" && candidates.some(row => !row.advisorProgramId)) {
    throw new Error("医学申请比较必须使用真实 advisorProgramId；导师级记录请使用方向探索输出");
  }
  const records = advisors.length ? advisors : [...new Map(candidates.map(row => [row.advisor_id || row.advisorId, row])).values()];
  const discovery = buildMedicalDiscoveryView(records, project);
  const views = discovery.map((advisor, index) => {
    const candidate = candidates.find(row => (row.advisor_id || row.advisorId) === (advisor.advisor_id || advisor.advisorId));
    return combinedRow(candidate ? { ...advisor, ...candidate, evidenceProfile: { ...evidenceProfile(advisor), ...evidenceProfile(candidate) } } : advisor, project, index);
  });
  const reviews = views.map(row => publicationReview(row.evidenceProfile.researchMainline, evidence, row.advisor_id || row.advisorId));
  const names = new Map(views.map(row => [row.advisor_id || row.advisorId, row.name || row.advisorName || "姓名待核实"]));
  const overview = views.map((row, index) => {
    const profile = row.evidenceProfile;
    const identity = profile.identity;
    return [row.name || row.advisorName || "姓名待核实",
      compact([identity.currentInstitution || row.school || row.schoolName, identity.department, identity.currentPosition], " · "),
      text(row.region || row.country || row.countryName), mainlineSummary(profile),
      compact([words[profile.researchQuestionFit.status] || "相关性待核实", profile.researchQuestionFit.reasons, profile.fitBoundary]),
      reviews[index].papers.length, unresolved(row, reviews[index], project), sourceLink(identity.officialProfileUrl || row.homepage || row.advisorHomepage, "导师主页")];
  });
  const papers = [], pending = [], authors = [], talks = [];
  views.forEach((row, index) => {
    const name = names.get(row.advisor_id || row.advisorId);
    const review = reviews[index];
    const paperRow = (paper, status) => [name, paper.date ? dateCell(paper.date) : text(paper.year), text(paper.title), text(paper.venue || paper.journal),
      publicationRoleLabel(paper), compact([paper.relationToMainline, paper.isPreprint ? "预印本（未经同行评审）" : "", paper.publicationStatus]), status, sourceLink(publicationUrl(paper), "论文原文")];
    papers.push(...review.papers.map(paper => paperRow(paper, "署名与日期已核实")));
    pending.push(...review.pending.map(({paper, reason}) => paperRow(paper, `未纳入：${text(reason)}`)));
    const doctoral = row.evidenceProfile.doctoralTrajectory;
    for (const person of doctoral.firstAuthorProfiles) {
      if (!person.papers.length && !firstAuthorIdentity(person, evidence) && !person.researchSummary) continue;
      const summary = person.researchSummary ? firstAuthorSummary(person, doctoralWindow(doctoral), evidence) : "";
      authors.push([name, text(person.name), "论文第一作者", firstAuthorIdentity(person, evidence), summary,
        compact(person.papers.map(paper => paper.title), "\n"), compact(person.papers.map(publicationUrl), "\n")]);
    }
    for (const [kind, people] of [["已有当前博士生信息", doctoral.currentDoctoral], ["已有毕业博士信息", doctoral.formerDoctoral]]) {
      for (const person of people) authors.push([name, text(person.name), kind, text(person.degreeOrYear), compact([person.topic, person.relationToMainline, person.supervisionEvidence, person.firstDestination, person.latestPublicRole]), "", compact(evidence.filter(item => person.sourceIds.includes(item.evidence_id || item.evidenceId)).map(sourceUrl), "\n")]);
    }
    talks.push(...academicTalkRows(row.evidenceProfile.researchMainline, evidence, row.advisor_id || row.advisorId).map(talk => [name, talk.date || "日期待核实", text(talk.eventName), text(talk.title), text(talk.roleLabel), text(talk.status), text(talk.limitations), sourceLink(talk.url)]));
  });
  const sourceGroups = new Map();
  evidence.forEach((row, index) => {
    const key = sourceUrl(row) || `missing-${index}`;
    const group = sourceGroups.get(key) || [];
    group.push(row);
    sourceGroups.set(key, group);
  });
  const sourceRows = [...sourceGroups.values()].map(group => {
    const nameFor = row => names.get(row.entity_id || row.entity) || row.advisorName || "相关记录";
    const people = [...new Set(group.map(nameFor))];
    const date = group.map(row => row.accessed_at || row.accessedAt).filter(Boolean).sort().at(-1);
    const claim = row => `${people.length > 1 ? `${nameFor(row)}：` : ""}${text(row.claim || row.finding || row.value || row.excerpt)}${new Set(group.map(item => item.status)).size > 1 ? `（${words[row.status] || "待核实"}）` : ""}`;
    return [people.join("、"), compact(group.map(claim), "\n"), sourceLink(sourceUrl(group[0])), date ? dateCell(date) : "",
      compact(group.map(row => words[row.status] || "待核实")), compact(group.flatMap(row => [row.limitations, row.failure_reason, row.gap]), "\n"),
      compact(group.map(row => row.citation_label || row.page_title || row.title))];
  });
  views.forEach((row, index) => {
    const review = reviews[index];
    const scope = review.window ? `${review.window.start} 至 ${review.window.end}` : "未记录有效的五年时间范围";
    const checked = compact(review.searches.map(search => search.database || search.sourceName || search.source), "、");
    sourceRows.push([names.get(row.advisor_id || row.advisorId), `论文核查范围：${scope}${checked ? `；已查来源：${checked}` : ""}`, "", review.window?.end ? dateCell(review.window.end) : "",
      review.searchComplete ? "所列来源检索完成" : "检索或署名核验仍有缺口", compact(review.limitations, "\n"), "论文核查说明"]);
  });
  sourceRows.push(["本轮说明", project.searchMode === "discovery" ? "本轮聚焦研究方向与论文；招生资格、名额与申请批次未纳入调查。" : "申请信息按真实项目与批次列示，行动前需核对当期规则。", "", "", "", "论文按已核实的第一、共同第一、通讯或共同通讯署名与日期纳入；作者画像为可选补充。", ""]);
  const sheets = [
    table("导师概览", ["姓名", "机构与职务", "地区", "研究主线", "相关性", "已核实论文数", "关键待核实", "主页"], overview, [24, 46, 14, 65, 65, 16, 65, 45]),
    table("近五年论文", ["导师", "发表日期", "论文标题", "期刊／平台", "导师署名", "相关性与文献说明", "核验状态", "原文链接"], papers, [24, 18, 76, 32, 24, 55, 25, 45]),
    table("来源说明", ["相关导师", "支持内容", "来源链接", "查阅日期", "核验情况", "限制与待核实", "来源名称"], sourceRows, [24, 76, 45, 18, 28, 65, 42]),
  ];
  if (pending.length) sheets.push(table("待核验论文", ["导师", "发表日期", "论文标题", "期刊／平台", "记录中的署名（待核验）", "相关性与文献说明", "未纳入原因", "原文链接"], pending, [24, 18, 76, 32, 26, 55, 65, 45]));
  if (authors.length) sheets.push(table("作者附录", ["相关导师", "作者／学生姓名", "记录类别", "公开身份", "已有研究或去向信息", "关联论文", "来源链接"], authors, [24, 24, 24, 32, 65, 65, 45]));
  if (talks.length) sheets.push(table("学术活动", ["导师", "日期", "会议／活动", "演讲标题", "参与角色", "核验情况", "限制", "活动链接"], talks));
  const applications = candidates.filter(row => row.advisorProgramId);
  if (applications.length) sheets.push(table("申请项目", ["导师", "项目", "学位", "批次", "申请路径", "资格与条件", "招生机会", "待核实", "项目入口"], applications.map(original => {
    const row = normalizeMedicalCandidate(original, project);
    return [row.name || row.advisorName || names.get(row.advisor_id || row.advisorId), text(row.program || row.programNameZh || row.programNameEn), text(row.degree), text(row.intake), text(row.applicationPathway),
      compact([row.feasibility, row.feasibilityReasons, row.hardConstraintReasons]), text(row.opportunityStatus), compact([row.evidenceProfile.keyUnknowns, row.evidenceProfile.nextVerification]), sourceLink(row.programUrl)];
  })));
  return sheets;
}
