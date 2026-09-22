#!/usr/bin/env node

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { isExecutedDirectly } from "./direct-execution.mjs";
import { isMedicalRankingCurrent, normalizeProjectMetadata } from "./project-contract.mjs";
import {
  buildMedicalDiscoveryView, compareMedicalCandidates, hasReadableProjectCv, isMedicalEvidenceProfile,
  evidenceProfile, normalizeMedicalCandidate, validateMedicalCandidateMappings,
} from "./medical-evidence.mjs";

function html(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function text(value) {
  if (value === null || value === undefined || value === "") return "未核验 / unknown";
  if (Array.isArray(value)) return value.length ? value.map(text).join("；") : "未核验 / unknown";
  if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${key}: ${text(item)}`).join("；");
  return String(value);
}

function link(url, label = "打开来源") {
  try {
    const parsed = new URL(String(url));
    if (!["http:", "https:"].includes(parsed.protocol)) return "未提供可用公开链接";
    return `<a href="${html(parsed.href)}" target="_blank" rel="noopener noreferrer">${html(label)}</a>`;
  } catch { return "未提供可用公开链接"; }
}

function subject(project) {
  const profile = project.medicalProfile || {};
  const terms = isMedicalEvidenceProfile(project)
    ? [...(profile.fields || []), ...(profile.diseasesOrMechanisms || []), ...(profile.researchQuestions || [])]
    : (project.interests || []).map((item) => typeof item === "string" ? item : item.name);
  return [...new Set(terms.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim()))]
    .join(" · ") || project.name || "导师研究";
}

export function reportFilename(project = {}) {
  let name = subject(project).replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-")
    .replace(/[\s·]+/g, "-").replace(/-+/g, "-").replace(/^[.\s-]+|[.\s-]+$/g, "");
  name = Array.from(name).slice(0, 50).join("");
  if (!name || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(name)) name = `研究-${name || "导师"}`;
  return `${name}-导师调研.html`;
}

function sourcedValue(value, evidence) {
  if (Array.isArray(value)) return value.length
    ? value.map((item) => `<div class="fact-item">${sourcedValue(item, evidence)}</div>`).join("") : html(text(value));
  if (value && typeof value === "object") {
    const references = value.sourceIds || value.source_ids;
    const content = Object.entries(value).filter(([key]) => !["sourceIds", "source_ids"].includes(key))
      .map(([key, item]) => `${html(key)}: ${sourcedValue(item, evidence)}`).join("；");
    return `${content}${references?.length ? `<br><span class="sources">${evidenceReferences(references, evidence)}</span>` : ""}`;
  }
  // Link only URLs actually present in the record; never synthesize a source.
  return typeof value === "string" && /^https?:\/\/\S+$/i.test(value) ? link(value, value) : html(text(value));
}

function facts(items, evidence) {
  return `<dl>${items.map(([label, value, sourceIds]) => {
    const content = evidence ? sourcedValue(value, evidence) : html(text(value));
    const references = sourceIds?.length ? evidenceReferences(sourceIds, evidence || [])
      : evidence && !content.includes("<a ") ? "对应来源待补，信息待核验" : "";
    return `<div><dt>${html(label)}</dt><dd>${content}${references ? `<br><span class="sources">${references}</span>` : ""}</dd></div>`;
  }).join("")}</dl>`;
}

function rankingRows(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.rankings)) return value.rankings;
  if (Array.isArray(value?.ranking)) return value.ranking;
  throw new Error("ranking.json 必须是数组或包含 rankings/ranking 数组的对象");
}

function evidenceReferences(ids, evidence) {
  const sourceIds = new Set(Array.isArray(ids) ? ids : []);
  const matched = evidence.map((row, index) => ({ row, index })).filter(({ row }) =>
    sourceIds.has(row.evidence_id || row.evidenceId));
  if (!matched.length) return "来源关联尚待补齐，信息待核验";
  const links = matched.map(({ row, index }) =>
    `${link(row.final_url || row.source_url || row.url, `来源 ${index + 1}：${row.page_title || row.title || "原始页面"}`)}（${html(row.status || "not_checked")}）；<a href="#evidence-${index + 1}">证据 ${index + 1}</a>`);
  if (matched.length < sourceIds.size) links.push("部分来源关联尚待补齐");
  return links.join(" · ");
}

function fieldEvidenceIds(evidence, entities, fields, intake) {
  return evidence.filter((row) => {
    const supported = row.fields_supported || (row.field ? [row.field] : []);
    const batch = row.intake || row.applicable_intake;
    return entities.filter(Boolean).includes(row.entity_id || row.entity)
      && Array.isArray(supported) && supported.some((field) => fields.includes(field))
      && (!intake || !batch || batch === intake);
  }).map((row) => row.evidence_id || row.evidenceId).filter(Boolean);
}

function profileReferences(profile) {
  if (!profile || typeof profile !== "object") return [];
  return Object.entries(profile).flatMap(([key, value]) =>
    ["sourceIds", "source_ids"].includes(key) && Array.isArray(value)
      ? value : typeof value === "object" ? profileReferences(value) : []);
}

function fitComparison(profile, evidence) {
  const labels = { strong: "强匹配", partial: "部分匹配/支持", adjacent: "相邻方向", mismatch: "不匹配",
    insufficient_information: "信息不足", supported: "有可见训练支持", unknown: "未知" };
  return [["科学问题", profile.scientificFit], ["训练目标", profile.trainingFit]].map(([label, fit]) =>
    `<strong>${label}：${html(labels[fit?.status] || "未知")}</strong><br>${html(text(fit?.reasons || "匹配依据待补"))}<br><span class="sources">${evidenceReferences(fit?.sourceIds || fit?.source_ids, evidence)}</span>`,
  ).join("<br><br>");
}

function advisorSection(advisor, index, project, candidates, evidence) {
  const medical = isMedicalEvidenceProfile(project);
  const advisorId = advisor.advisor_id || advisor.advisorId;
  const opportunities = candidates.filter((candidate) => (candidate.advisor_id || candidate.advisorId) === advisorId);
  const currentEvaluations = opportunities.filter((candidate) => candidate.evaluationCurrent);
  const factsRow = { ...opportunities[0], ...advisor,
    evidenceProfile: currentEvaluations[0]?.evidenceProfile || advisor.evidenceProfile || advisor.evidence_profile || opportunities[0]?.evidenceProfile };
  const row = medical ? normalizeMedicalCandidate(factsRow, { ...project, searchMode: "discovery" }, index) : factsRow;
  const profile = row.evidenceProfile || {};
  const advisorProfile = medical ? normalizeMedicalCandidate(advisor, { ...project, searchMode: "discovery" }, index).evidenceProfile : {};
  const sourcesFor = (...fields) => fieldEvidenceIds(evidence, [advisorId], fields);
  const sourceIds = [
    ...(row.source_ids || row.sourceIds || []),
    ...(profile.scientificFit?.sourceIds || profile.scientificFit?.source_ids || []),
    ...(profile.trainingFit?.sourceIds || profile.trainingFit?.source_ids || []),
    ...currentEvaluations.flatMap((candidate) => profileReferences(candidate.evidenceProfile)),
  ];
  const evaluatedField = (keys, fallback) => currentEvaluations.length
    ? currentEvaluations.map((candidate) => ({
      项目: candidate.program, 批次: candidate.intake,
      评价: keys.map((key) => {
        const value = candidate.evidenceProfile[key];
        return value === null || value === undefined || (Array.isArray(value) && !value.length)
          ? advisorProfile[key] : value;
      }),
    })) : fallback;
  return `<article id="advisor-${index + 1}"><h3>${html(row.name || row.advisorName || advisorId)}</h3>
    <p>${html(row.current_institution || row.currentInstitution || row.school || row.schoolName || "当前机构待核验")} · ${link(row.homepage || row.advisorHomepage, "官方主页")}</p>
    ${facts([
      ["科学问题与训练匹配", medical ? evaluatedField(["scientificFit", "trainingFit"], [profile.scientificFit, profile.trainingFit]) : row.research_directions || row.directions],
      ["近期研究、角色与贡献证据", row.recent_papers || row.recentPapers || row.researchAndPapers, sourcesFor("recent_papers", "recentPapers", "researchAndPapers", "research", "contributions")],
      ["研究资源及可访问层级", evaluatedField(["resources"], profile.resources || row.resources), sourcesFor("resources")],
      ["研究项目经费", evaluatedField(["researchFunding"], profile.researchFunding || row.research_funding), sourcesFor("researchFunding", "research_funding")],
      ["博士生资助", evaluatedField(["doctoralFunding"], profile.doctoralFunding || row.doctoral_funding), sourcesFor("doctoralFunding", "doctoral_funding")],
      ["博士培养公开样本与局限", evaluatedField(["doctoralOutcomes"], profile.doctoralOutcomes || row.doctoral_outcomes), sourcesFor("doctoralOutcomes", "doctoral_outcomes")],
      ["培养制度与环境", evaluatedField(["trainingEnvironment"], profile.trainingEnvironment || row.training_environment), sourcesFor("trainingEnvironment", "training_environment")],
      ["真实申请入口", opportunities.length ? opportunities.map((candidate) => ({
        program: candidate.program || candidate.programNameEn || candidate.programNameZh,
        degree: candidate.degree, intake: candidate.intake, pathway: candidate.applicationPathway,
        eligibility: project.searchMode === "discovery" ? "本次未核验" : candidate.feasibility,
        opportunity: candidate.opportunityStatus,
        url: candidate.programUrl,
        sourceIds: profileReferences([candidate.eligibilityEvidence, candidate.hardConstraintEvidence, candidate.opportunityEvidence]),
      })) : "尚未映射真实项目；本次未核验申请资格，不生成项目ID"],
      ["关键未知与支持的风险", evaluatedField(["keyUnknowns", "supportedRisks"], [profile.keyUnknowns, profile.supportedRisks || row.risk_flags])],
      ["下一条最值得核验的信息", evaluatedField(["nextVerification"], profile.nextVerification || row.missing_fields)],
      ["最后核验日期", row.last_verified_at || row.lastVerifiedAt],
    ], evidence)}
    <p class="sources">${evidenceReferences(sourceIds, evidence)}</p></article>`;
}

export function buildAdvisorReport({ project = {}, advisors = [], programs = [], evidence = [], candidates = [], ranking = [], audit = {}, cvValid = false } = {}) {
  const medical = isMedicalEvidenceProfile(project);
  if (medical) {
    project = normalizeProjectMetadata(project);
    const errors = validateMedicalCandidateMappings(candidates, { advisorRecords: advisors, programRecords: programs });
    if (errors.length) throw new Error(errors.join("; "));
  }
  const rankings = rankingRows(ranking);
  const currentMedicalRanking = medical && isMedicalRankingCurrent(project, ranking);
  const historicalRanking = medical && rankings.length > 0 && !currentMedicalRanking;
  const rankedIds = new Map(rankings.map((row, index) => [row.advisorProgramId || row.advisor_program_id, index]));
  let candidateFacts = candidates.map((row) => ({ ...row, evaluationCurrent: false }));
  if (currentMedicalRanking) {
    const byId = new Map(candidates.map((row) => [row.advisorProgramId, row]));
    const evaluatedById = new Map();
    for (const evaluated of rankings) {
      const id = evaluated.advisorProgramId || evaluated.advisor_program_id;
      const candidate = byId.get(id);
      if (!candidate || evaluatedById.has(id)) throw new Error("当前医学评价必须引用唯一的既有真实候选ID");
      for (const keys of [["advisor_id", "advisorId"], ["program_id", "programId"], ["degree"], ["intake"]]) {
        const original = keys.map((key) => candidate[key]).find(Boolean);
        const updated = keys.map((key) => evaluated[key]).find(Boolean);
        if (original && updated && original !== updated) throw new Error("当前医学评价不得改变候选的导师、项目、学位或批次身份");
      }
      evaluatedById.set(id, evaluated);
    }
    candidateFacts = candidates.map((candidate) => {
      const evaluated = evaluatedById.get(candidate.advisorProgramId);
      return evaluated ? { ...candidate, ...evaluated, evaluationCurrent: true,
        advisorProgramId: candidate.advisorProgramId,
        evidenceProfile: { ...evidenceProfile(candidate), ...evidenceProfile(evaluated) },
      } : { ...candidate, evaluationCurrent: false };
    });
  }
  let compared = medical
    ? candidateFacts.map((row, index) => normalizeMedicalCandidate(row, { ...project, cvValid, evidenceRecords: evidence }, index)).sort(compareMedicalCandidates)
    : [...candidates].sort((left, right) => (rankedIds.get(left.advisorProgramId) ?? Infinity) - (rankedIds.get(right.advisorProgramId) ?? Infinity));
  if (historicalRanking) {
    compared = compared.map((row) => ({ ...row, feasibility: "needs_confirmation", hardConstraintStatus: "unknown",
      recommendedAction: "reconfirm_investigation", comparisonGroup: "needs_verification" }))
      .sort((left, right) => String(left.name || left.advisorName || left.advisorProgramId)
        .localeCompare(String(right.name || right.advisorName || right.advisorProgramId)));
  }
  const advisorRows = medical ? buildMedicalDiscoveryView(advisors, project) : advisors;
  const advisorFacts = new Map(advisors.map((row) => [row.advisor_id || row.advisorId, row]));
  const programById = new Map(programs.map((row) => [row.program_id || row.programId, row]));
  const programRows = compared.map((row) => {
    const program = programById.get(row.program_id || row.programId) || {};
    return { ...row, degree: row.degree || program.degree, intake: row.intake || program.intake,
      program: row.program || row.programNameEn || row.programNameZh || program.program_name_en || program.program_name_zh,
      programUrl: row.programUrl || program.program_url };
  });
  const discovery = medical && project.searchMode === "discovery";
  const profile = project.medicalProfile || {};
  const fixtureNotice = project.fixtureNotice || (audit.fixture === true
    ? "All identities and claims are simulated local fixtures; no live advisor research was performed." : "");
  const queries = [...new Set(evidence.map((row) => row.query_or_filter_summary).filter(Boolean))];
  const limitations = evidence.filter((row) => ["inaccessible", "not_checked", "conflict", "stale"].includes(row.status))
    .map((row) => `${row.page_title || row.title || row.evidence_id || "来源"}: ${row.status}${row.failure_reason ? `；${row.failure_reason}` : ""}`);
  const coverage = facts([
    ["实际查询与筛选", queries.length ? queries : "未保存查询记录，不能声称已穷尽检索"],
    ["实际覆盖范围", audit.searchCoverage || audit.coverage || "未保存独立覆盖摘要；目标地区不等于已查遍该地区"],
    ["访问限制与待核验来源", limitations.length ? limitations : "已保存证据未列出此类限制；不代表所有来源可访问"],
    ["本轮项目候选选择", { 保留: audit.selectedCount ?? candidates.length,
      [medical ? "明确不适用" : "未保留"]: audit.excludedCount ?? "未记录", 因调研预算暂缓: audit.deferredCount ?? "未记录" }],
  ]);
  const programDetails = programRows.map((row) => {
    const program = programById.get(row.program_id || row.programId) || {};
    const sourcesFor = (...fields) => fieldEvidenceIds(evidence,
      [row.program_id || row.programId, row.advisorProgramId], fields, row.intake);
    return `<details><summary>${html(row.name || row.advisorName || row.advisorProgramId)} · ${html(row.program || "项目名称待核验")}：申请条件与时效</summary>${facts([
      ["学位 / 批次 / 招生路径", [row.degree, row.intake, row.applicationPathway], sourcesFor("degree", "intake", "applicationPathway", "application_pathway")],
      ["轮转与联系规则", [row.rotation || program.rotation, row.advisorContactRequirements || row.advisor_contact_requirements || program.contact_rules], sourcesFor("rotation", "contact_rules", "advisorContactRequirements")],
      ["项目截止日（批次 / 时区）", program.deadlines?.program || program.program_deadline || program.deadline, sourcesFor("deadline", "program_deadline", "deadlines.program")],
      ["奖学金截止日（批次 / 时区）", program.deadlines?.scholarship || program.scholarship_deadline, sourcesFor("scholarship_deadline", "deadlines.scholarship")],
      ["岗位截止日（批次 / 时区）", program.deadlines?.position || program.position_deadline, sourcesFor("position_deadline", "deadlines.position")],
      ["学费 / 博士生资助", [program.tuition, program.scholarships || program.doctoral_funding], sourcesFor("tuition", "scholarships", "doctoral_funding", "doctoralFunding")],
      ["申请材料 / RP要求", [program.application_materials, program.rp_requirement], sourcesFor("application_materials", "rp_requirement")],
      ["资格 / 硬约束依据", discovery ? "本次未核验" : [row.feasibility, row.feasibilityReasons, row.hardConstraintStatus, row.hardConstraintReasons], discovery ? [] : profileReferences([row.eligibilityEvidence, row.hardConstraintEvidence])],
      ["最后核验 / 待补条件", [program.last_verified_at, program.missing_fields]],
    ], evidence)}<p class="sources">项目相关来源：${evidenceReferences(program.source_ids || program.sourceIds, evidence)}</p></details>`;
  }).join("");
  const table = programRows.length ? `<div class="table-wrap"><table><thead><tr><th>导师 / 真实项目</th><th>问题与训练匹配</th><th>资格 / 招生机会</th><th>下一步</th></tr></thead><tbody>${programRows.map((row) => `<tr>
    <td><strong>${html(row.name || row.advisorName || row.advisorProgramId)}</strong><br>${html(text([row.program, row.degree, row.intake]))}<br>${link(row.programUrl, "项目入口")}</td>
    <td>${medical ? fitComparison(row.evidenceProfile, evidence) : sourcedValue(row.matchReasons || row.fitEvidence, evidence)}</td>
    <td>资格：${html(discovery ? "本次未核验申请资格" : row.feasibility || "needs_confirmation")}<br><span class="sources">${evidenceReferences(profileReferences([row.eligibilityEvidence, row.hardConstraintEvidence]), evidence)}</span><br>机会：${html(row.opportunityStatus || "unknown")}<br><span class="sources">${evidenceReferences(profileReferences(row.opportunityEvidence), evidence)}</span><br>${html(row.comparisonGroup || "")}</td>
    <td>${sourcedValue(row.evidenceProfile?.nextVerification?.length ? row.evidenceProfile.nextVerification : row.recommendedAction, evidence)}</td>
  </tr>`).join("")}</tbody></table></div>` : "<p>尚未映射真实博士项目。以下导师级探索结果保留待核验入口，不生成项目、入学批次或材料目标ID。</p>";
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>${html(subject(project))} — 导师调研</title>
<style>body{max-width:1100px;margin:auto;padding:32px 24px;color:#20252b;background:#fff;font:16px/1.7 system-ui,sans-serif}h1{font-size:30px;line-height:1.3}h2{font-size:23px;margin-top:36px;border-bottom:1px solid #ddd;padding-bottom:8px}h3{font-size:20px}a{color:#185a8d;text-underline-offset:3px}p{max-width:95ch}.muted,.sources{color:#59636d;font-size:14px}article{padding:8px 0 24px;border-bottom:1px solid #e5e7eb}dl>div{display:grid;grid-template-columns:210px 1fr;gap:16px;margin:12px 0}dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:12px;min-width:170px;overflow-wrap:anywhere}th{background:#f4f6f8}li{margin:14px 0;overflow-wrap:anywhere}@media(max-width:640px){body{padding:20px 16px}dl>div{grid-template-columns:1fr;gap:2px}}@media print{body{max-width:none;padding:0}article{break-inside:avoid}a{color:inherit}}</style></head>
<body><header><p class="muted">Boss Hunting · 共享记录派生报告</p><h1>${html(subject(project))}</h1>
${fixtureNotice ? `<p><strong>虚构示例 / FICTIONAL FIXTURE：</strong>${html(fixtureNotice)}</p>` : ""}
<p>${discovery ? "医学方向探索" : medical ? "医学申请筛选" : "导师与申请项目调研"} · ${html(project.target || "地区尚未确认")} · ${advisorRows.length} 位导师记录 / ${programRows.length} 个真实项目机会</p>
${historicalRanking ? `<p><strong>历史比较待复核：</strong>已有 ${rankings.length} 条比较记录的调查确认已失效或不适用于当前范围。保留研究和来源痕迹；当前按稳定名称展示，申请资格待重新核对。</p>` : ""}
<p class="muted">${medical ? "按科学问题与期望训练展示，列表顺序不是导师质量排名。未知不代表不符合；没有综合导师分、录取概率或保底判断。" : "结论依据共享记录；申请条件、名额与资金在行动前需要按项目批次重核。"}</p></header>
<section><h2>本次研究画像</h2>${facts(medical ? [
  ["疾病 / 机制与科学问题", [profile.diseaseScope, profile.diseasesOrMechanisms, profile.researchQuestions]],
  ["研究方式", profile.researchModes], ["已有能力", profile.currentSkills], ["未来训练目标", profile.desiredTraining],
  ["可接受相邻方向 / 排除项", [profile.adjacentInterests, profile.exclusions]],
] : [["研究兴趣", project.interests], ["目标学位 / 批次", [project.degree, project.season]], ["硬约束", project.hardConstraints]])}</section>
<section><h2>候选比较与真实项目入口</h2>${table}${programDetails}</section>
<section><h2>导师证据简报</h2>${advisorRows.length ? advisorRows.map((row, index) => advisorSection(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project, programRows, evidence)).join("") : "<p>尚无导师事实记录。</p>"}</section>
<section><h2>证据、来源与信息缺口</h2><p class="muted">verified 仅说明保存的来源支持该项主张；转载与同源页面不算独立佐证。未检索、未找到、受阻、冲突和过期分别保留。</p>
${evidence.length ? `<ol>${evidence.map((row, index) => `<li id="evidence-${index + 1}"><strong>${html(row.title || row.page_title || row.evidence_id || row.evidenceId || `证据 ${index + 1}`)}</strong> · ${link(row.final_url || row.source_url || row.url)}
${facts([["主张 / 类型", [row.claim || row.finding || row.value || row.excerpt, row.claim_type || row.claimType]],
  ["实体 / 支持字段", [row.entity_id || row.entity, row.fields_supported || row.field]],
  ["状态 / 提取状态", [row.status || "not_checked", row.extraction_status || row.extractionStatus]],
  ["适用批次 / 来源更新时间 / 访问时间", [row.intake || row.applicable_intake, row.source_updated_at, row.accessed_at || row.accessedAt]],
  ["读取深度 / 检索方式 / 定位", [row.reading_depth || row.read_depth || row.readDepth, row.retrieval_method || row.retrievalMethod, row.page_locator || row.locator]],
  ["支持片段 / 同源组 / 限制", [row.excerpt, row.same_source_group || row.source_group_id || row.sourceGroupId, row.limitations || row.failure_reason]],
])}</li>`).join("")}</ol>` : "<p>未保存可核验的事实级证据；当前内容不能视作已核验结论。</p>"}</section>
<section><h2>检索覆盖、审计与未完成事项</h2>${coverage}
${historicalRanking ? `<details><summary>历史比较记录（不用于当前顺序或申请判断）</summary>${facts([
  ["历史比较模式 / 确认版本", [ranking.rankingMode, ranking.confirmedRevision]],
  ["历史确认指纹", ranking.confirmedFingerprint],
  ["历史候选ID", rankings.map((row) => row.advisorProgramId || row.advisor_program_id)],
])}</details>` : ""}
<p class="muted">本报告由本地共享记录生成，不会访问网页、发送邮件或启动申请材料。研究经费与博士资助分开解释；机构拥有资源不保证新博士可用，公开培养样本没有分母时不计算成功率。</p></section></body></html>`;
}

async function readJson(path, fallback) {
  try { return JSON.parse(await readFile(path, "utf8")); }
  catch (error) { if (error.code === "ENOENT" && fallback !== undefined) return fallback; throw error; }
}

export async function exportAdvisorReport(projectRoot) {
  const root = resolve(projectRoot);
  const project = await readJson(resolve(root, "project.json"));
  const keys = ["advisor_records", "program_records", "evidence", "candidates"];
  const arrays = await Promise.all(keys.map((key) => readJson(resolve(root, "outputs", `${key}.json`), [])));
  arrays.forEach((value, index) => { if (!Array.isArray(value)) throw new Error(`${keys[index]}.json 顶层必须是数组`); });
  const [advisors, programs, evidence, candidates] = arrays;
  const ranking = await readJson(resolve(root, "outputs", "ranking.json"), []);
  const audit = await readJson(resolve(root, "outputs", "matching-audit.json"), {});
  const report = buildAdvisorReport({ project, advisors, programs, evidence, candidates, ranking, audit,
    cvValid: await hasReadableProjectCv(root, project.cv) });
  await mkdir(resolve(root, "outputs"), { recursive: true });
  const output = resolve(root, "outputs", reportFilename(project));
  await writeFile(output, report, "utf8");
  return { output, advisorCount: advisors.length, candidateCount: candidates.length };
}

if (isExecutedDirectly(import.meta.url)) {
  const index = process.argv.indexOf("--project-root");
  const root = index < 0 ? "" : process.argv[index + 1];
  if (!root) throw new Error("Usage: build_advisor_report.mjs --project-root <project-directory>");
  console.log(JSON.stringify(await exportAdvisorReport(root)));
}
