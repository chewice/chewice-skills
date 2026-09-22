#!/usr/bin/env node

import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
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
  // Topic = field + disease/mechanism; long research questions stay in the body.
  const terms = isMedicalEvidenceProfile(project)
    ? [...(profile.fields || []), ...(profile.diseasesOrMechanisms || [])]
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

// ---------------------------------------------------------------------------
// Medical five-module rendering
// ---------------------------------------------------------------------------

const LABELS = {
  fit: { direct: "直接相关", partial: "部分相关", adjacent: "相邻方向", weak: "弱相关", insufficient_information: "信息不足" },
  continuity: { sustained_core: "持续核心方向", active_emerging: "活跃新兴方向", new_expansion: "新近扩展", occasional_participation: "偶发参与", unclear: "不明确" },
  role: { verified: "已核实 PI 角色", probable: "很可能为 PI", emerging: "新兴 PI", identity_unresolved: "身份未解析" },
  sufficiency: { strong: "证据充分", adequate: "证据足够", sparse: "证据稀少", conflicted: "证据冲突" },
  activity: { active: "近期活跃", recent_signal: "有近期信号", unclear: "活跃度不明", apparently_inactive_in_checked_scope: "在已检查范围内未见近期活动" },
  edge: { coauthorship: "共同发表", shared_project: "共同项目", shared_grant: "共同基金", shared_trial: "共同试验" },
};

function label(group, value) {
  return LABELS[group]?.[value] || value || "未核验 / unknown";
}

function sources(ids, evidence) {
  return `<span class="sources">${evidenceReferences(ids, evidence)}</span>`;
}

function workItem(work, evidence) {
  const meta = [work.year, work.venue, work.verifiedRole && work.verifiedRole !== "unknown" ? `角色：${work.verifiedRole}` : null,
    work.relationToMainline ? `与主线关系：${work.relationToMainline}` : null, work.isPreprint ? "预印本（未经同行评审）" : null]
    .filter(Boolean).map(html).join(" · ");
  const external = work.url || (work.doi ? `https://doi.org/${String(work.doi).replace(/^https?:\/\/doi\.org\//i, "")}` : null);
  const anchor = external ? link(external, work.title || external) : "";
  // Unsafe or missing URLs never drop the (escaped) title itself.
  const heading = anchor.startsWith("<a ") ? anchor : `${html(work.title || "标题待核验")}${external ? "（未提供可用公开链接）" : ""}`;
  return `<li>${heading}${meta ? `<br><span class="muted">${meta}</span>` : ""}<br>${sources(work.sourceIds, evidence)}</li>`;
}

function workList(works, evidence, empty) {
  return works.length ? `<ul class="works">${works.map((work) => workItem(work, evidence)).join("")}</ul>` : `<p class="muted">${html(empty)}</p>`;
}

function egoNetworkSvg(name, network) {
  const collaborators = network.coreCollaborators.slice(0, 12);
  if (!collaborators.length) return "";
  const width = 640; const height = 360; const cx = width / 2; const cy = height / 2; const radius = 130;
  const counts = new Map();
  for (const edge of network.edges) {
    const key = String(edge.target ?? "");
    counts.set(key, (counts.get(key) || 0) + (edge.count || 0));
  }
  const nodes = collaborators.map((collaborator, index) => {
    const angle = (Math.PI * 2 * index) / collaborators.length - Math.PI / 2;
    return { collaborator, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle),
      weight: counts.get(String(collaborator.collaboratorId ?? "")) || counts.get(String(collaborator.name)) || collaborator.jointRecordCount || 1 };
  });
  const truncate = (value) => { const chars = Array.from(String(value || "")); return chars.length > 18 ? `${chars.slice(0, 17).join("")}…` : chars.join(""); };
  return `<figure class="ego-network"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${html(name)} 的一层科研合作网络" xmlns="http://www.w3.org/2000/svg">
<title>${html(name)} 的一层科研合作网络（边粗细 = 方向相关共同记录数）</title>
${nodes.map((node) => `<line x1="${cx}" y1="${cy}" x2="${node.x.toFixed(1)}" y2="${node.y.toFixed(1)}" stroke="#7a8794" stroke-width="${Math.min(8, 1 + node.weight).toFixed(1)}" stroke-linecap="round"/>`).join("\n")}
${nodes.map((node) => `<g><circle cx="${node.x.toFixed(1)}" cy="${node.y.toFixed(1)}" r="7" fill="#fff" stroke="#185a8d" stroke-width="2"/><text x="${node.x.toFixed(1)}" y="${(node.y + (node.y >= cy ? 22 : -14)).toFixed(1)}" text-anchor="middle" font-size="12" fill="#20252b">${html(truncate(node.collaborator.name))} (${node.weight})</text></g>`).join("\n")}
<circle cx="${cx}" cy="${cy}" r="11" fill="#185a8d"/><text x="${cx}" y="${cy - 18}" text-anchor="middle" font-size="13" font-weight="600" fill="#20252b">${html(truncate(name))}</text>
</svg><figcaption class="muted">一层（depth=1）合作网络示意，仅显示核心合作者；边粗细表示方向相关共同记录数，不表示合作质量。研究邻居不在图中。</figcaption></figure>`;
}

function collaboratorTable(network, evidence) {
  if (!network.coreCollaborators.length) return `<p class="muted">未识别到满足重复合作 heuristic 的核心合作者；单篇 consortium 论文不构成合作关系。</p>`;
  return `<div class="table-wrap"><table><thead><tr><th>核心合作者</th><th>当前机构 / 职位</th><th>合作证据</th><th>合作年份 / 共同主题</th><th>对方核心方向与近期路线</th><th>与目标导师主线的关系</th></tr></thead><tbody>${network.coreCollaborators.map((person) => `<tr>
    <td><strong>${html(person.name || person.collaboratorId || "姓名待核验")}</strong></td>
    <td>${html(text([person.currentInstitution, person.currentPosition]))}</td>
    <td>${html(text(person.collaborationEvidence.length ? person.collaborationEvidence.map((item) => typeof item === "string" ? item : `${label("edge", item.type)}${item.year ? ` ${item.year}` : ""}`) : `${person.jointRecordCount || 0} 条共同记录`))}</td>
    <td>${html(text([[person.firstYear, person.lastYear].filter(Boolean).join("–"), person.sharedTopics]))}</td>
    <td>${html(text([person.ownCoreDirection, person.recentRoute]))}</td>
    <td>${html(text(person.relationToMainline))}<br>${sources(person.sourceIds, evidence)}</td>
  </tr>`).join("")}</tbody></table></div>`;
}

function projectTable(projects, evidence) {
  if (!projects.length) return `<p class="muted">已检查的公开项目库中未找到记录；公开数据库无记录不等于该导师没有基金或项目。</p>`;
  return `<div class="table-wrap"><table><thead><tr><th>项目名称</th><th>项目编号</th><th>资助机构 / 来源</th><th>PI 角色</th><th>期限</th><th>状态</th><th>公开金额（单位）</th></tr></thead><tbody>${projects.map((project) => `<tr>
    <td>${html(text(project.title))}<br>${sources(project.sourceIds, evidence)}</td>
    <td>${html(text(project.projectId))}</td>
    <td>${html(text([project.fundingBody, project.source]))}</td>
    <td>${html(text(project.piRole))}</td>
    <td>${html(text(project.period))}</td>
    <td>${html(text(project.status))}</td>
    <td>${project.amount === null || project.amount === undefined ? "未公开" : `${html(project.amount)} ${html(project.amountUnit || "")}${project.amountBasis ? `（${html(project.amountBasis)}）` : ""}`}</td>
  </tr>`).join("")}</tbody></table></div>`;
}

function doctoralList(people, evidence, empty) {
  if (!people.length) return `<p class="muted">${html(empty)}</p>`;
  return `<ul>${people.map((person) => `<li><strong>${html(person.name || "姓名未公开")}</strong>${person.degreeOrYear ? ` · ${html(person.degreeOrYear)}` : ""}
    <br>${html(text([person.topic ? `课题：${person.topic}` : null, person.relationToMainline ? `与主线关系：${person.relationToMainline}` : null].filter(Boolean)))}
    <br>${html(text([person.supervisionEvidence.length ? `指导证据：${person.supervisionEvidence.join("；")}` : "指导证据待核验",
      person.firstDestination ? `首个公开去向：${person.firstDestination}` : null, person.latestPublicRole ? `最新公开角色：${person.latestPublicRole}` : null,
      person.informationDate ? `信息日期：${person.informationDate}` : null].filter(Boolean)))}
    <br>${sources(person.sourceIds, evidence)}</li>`).join("")}</ul>`;
}

function evidenceStatusRow(profile) {
  return `<p class="status-line"><span>PI 角色：${html(label("role", profile.piRoleConfidence.status))}${profile.piRoleConfidence.level ? `（Level ${html(profile.piRoleConfidence.level)}）` : ""}</span> · <span>证据充分度：${html(label("sufficiency", profile.evidenceSufficiency))}</span> · <span>当前活跃度：${html(label("activity", profile.currentActivity))}</span></p>`;
}

function medicalAdvisorSection(advisor, index, project, opportunities, evidence) {
  const advisorId = advisor.advisor_id || advisor.advisorId;
  const currentEvaluations = opportunities.filter((candidate) => candidate.evaluationCurrent);
  // Advisor-level facts, then Finder's opportunity-level profile, then the
  // current evaluation override field by field; identities never change.
  const factsRow = { ...opportunities[0], ...advisor,
    evidenceProfile: { ...evidenceProfile(advisor), ...evidenceProfile(opportunities[0] || {}), ...(currentEvaluations[0]?.evidenceProfile || {}) } };
  const row = normalizeMedicalCandidate(factsRow, { ...project, searchMode: "discovery" }, index);
  const profile = row.evidenceProfile;
  const name = row.name || row.advisorName || advisorId;
  const identity = profile.identity;
  const mainline = profile.researchMainline;
  const network = profile.collaborationNetwork;
  const signals = profile.latestSignals;
  const doctoral = profile.doctoralTrajectory;
  const discovery = project.searchMode === "discovery";
  const officialUrl = identity.officialProfileUrl || row.homepage || row.advisorHomepage;
  const applicationEntry = !discovery && opportunities.length ? `<div class="module"><h4>真实申请入口（申请筛选模式）</h4>${facts([["项目 / 学位 / 批次 / 路径", opportunities.map((candidate) => ({
    program: candidate.program || candidate.programNameEn || candidate.programNameZh, degree: candidate.degree, intake: candidate.intake,
    pathway: candidate.applicationPathway, eligibility: candidate.feasibility, opportunity: candidate.opportunityStatus, url: candidate.programUrl,
    sourceIds: profileReferences([candidate.eligibilityEvidence, candidate.hardConstraintEvidence, candidate.opportunityEvidence]),
  }))]], evidence)}</div>` : "";
  return `<article id="advisor-${index + 1}" class="advisor"><h3>${html(name)}</h3>
${evidenceStatusRow(profile)}
<p class="muted">发现路径：${html(row.discoveredVia)}${row.networkRound ? ` · 网络第 ${row.networkRound} 轮` : ""} · 方向契合：${html(label("fit", profile.researchQuestionFit.status))} · 主线连续性：${html(label("continuity", profile.researchRouteContinuity.status))}</p>
<div class="module" id="advisor-${index + 1}-a"><h4>A. 导师身份与当前科研定位</h4>${facts([
  ["当前机构 / 院系 / 职位", [identity.currentInstitution || row.current_institution || row.school || row.schoolName, identity.department, identity.currentPosition], identity.sourceIds],
  ["官方主页 / 身份标识", [officialUrl, Object.keys(identity.identifiers).length ? identity.identifiers : null, identity.nameVariants.length ? `姓名变体：${identity.nameVariants.join("、")}` : null].filter((item) => item !== null), identity.sourceIds],
  ["当前科研定位", identity.researchPositioning, identity.sourceIds],
  ["博士指导关联（最低限度）", [identity.doctoralSupervisionLink, doctoral.graduateProgram.graduateSchool, doctoral.graduateProgram.doctoralProgram, doctoral.graduateProgram.supervisorListing, doctoral.graduateProgram.institutionalRelationship].filter(Boolean), [...(identity.sourceIds || []), ...(doctoral.graduateProgram.sourceIds || [])]],
  ["信息时间点", identity.affiliationAsOf || row.last_verified_at || row.lastVerifiedAt],
], evidence)}</div>
<div class="module" id="advisor-${index + 1}-b"><h4>B. 近五年科研主线与研究路线</h4>${facts([
  ["长期科学问题", mainline.longTermQuestion, mainline.sourceIds],
  ["持续主题 / 新方向 / 近期转向", [mainline.continuingThemes.length ? `持续：${mainline.continuingThemes.join("；")}` : null, mainline.newDirections.length ? `新方向：${mainline.newDirections.join("；")}` : null, mainline.recentShift ? `近期转向：${mainline.recentShift}` : null].filter(Boolean), mainline.sourceIds],
  ["研究对象 / 方法", [mainline.researchObjects, mainline.methods], mainline.sourceIds],
  ["回查窗口", mainline.backSearchWindow || row.back_search?.window || "近五年（默认）", row.back_search?.sourceIds],
], evidence)}
<h5>代表性工作（已核实角色）</h5>${workList(mainline.representativeWorks, evidence, "尚未登记已核实角色的代表性工作。")}
${mainline.participationOnlyWorks.length ? `<h5>仅参与型工作（不计入主线）</h5>${workList(mainline.participationOnlyWorks, evidence, "")}` : ""}</div>
<div class="module" id="advisor-${index + 1}-c"><h4>C. 科研合作网络</h4>${egoNetworkSvg(name, network)}${collaboratorTable(network, evidence)}
<h5>研究邻居（科学邻近，不是合作）</h5>${network.researchNeighbors.length ? `<ul>${network.researchNeighbors.map((neighbor) => `<li>${html(neighbor.name || neighbor.collaboratorId || "")} · ${html(neighbor.type)}${neighbor.note ? ` · ${html(neighbor.note)}` : ""} ${sources(neighbor.sourceIds, evidence)}</li>`).join("")}</ul>` : `<p class="muted">未登记研究邻居。</p>`}</div>
<div class="module" id="advisor-${index + 1}-d"><h4>D. 最新公开研究动向与项目支撑</h4>
<h5>最新论文</h5>${workList(signals.latestPapers, evidence, "未登记最新论文；不代表没有产出。")}
${signals.preprints.length ? `<h5>预印本</h5>${workList(signals.preprints, evidence, "")}` : ""}
<h5>公开项目 / 基金记录</h5>${projectTable(signals.projects, evidence)}
${signals.registries.length || signals.trials.length ? facts([["注册 / 试验记录", [signals.registries, signals.trials], signals.sourceIds]], evidence) : ""}</div>
<div class="module" id="advisor-${index + 1}-e"><h4>E. 博士培养轨迹</h4>
<h5>当前博士生（公开可见）</h5>${doctoralList(doctoral.currentDoctoral, evidence, "未找到公开可见的当前博士生；不代表没有。")}
<h5>已毕业博士（公开可见）</h5>${doctoralList(doctoral.formerDoctoral, evidence, "未找到公开可见的已毕业博士；新兴 PI 可能尚无毕业博士，不作负面推断。")}
${doctoral.emergingPiNote ? `<p class="muted">${html(doctoral.emergingPiNote)}</p>` : ""}
<p class="muted">${html(doctoral.sampleLimitation)}</p></div>
${applicationEntry}
<div class="module"><h4>方向契合与主要边界</h4>${facts([
  ["与用户研究问题的契合", [label("fit", profile.researchQuestionFit.status), ...profile.researchQuestionFit.reasons], profile.researchQuestionFit.sourceIds],
  ["主线连续性", [label("continuity", profile.researchRouteContinuity.status), ...profile.researchRouteContinuity.reasons], profile.researchRouteContinuity.sourceIds],
  ["主要边界", profile.fitBoundary],
  ["正式记录（更正 / 撤稿 / 机构公告）", profile.formalRecords.length ? profile.formalRecords : "已检查范围内未登记"],
  ["关键未知", profile.keyUnknowns],
  ["下一条最值得核验的信息", profile.nextVerification],
], evidence)}</div></article>`;
}

function overviewCell(items) {
  const filtered = items.filter((item) => item !== null && item !== undefined && item !== "");
  return filtered.length ? filtered.map((item) => `<div>${item}</div>`).join("") : `<span class="muted">未核验 / unknown</span>`;
}

function medicalOverviewTable(rows, evidence, discovery) {
  if (!rows.length) return `<p>尚无导师记录；本次未生成任何虚构导师、项目或来源。</p>`;
  return `<div class="table-wrap"><table class="overview"><thead><tr><th>导师</th><th>核心研究问题</th><th>近五年科研主线</th><th>核心合作生态</th><th>最新研究信号</th><th>方向契合与边界</th></tr></thead><tbody>${rows.map((row, index) => {
    const profile = row.evidenceProfile;
    const latest = profile.latestSignals.latestPapers[0] || profile.latestSignals.preprints[0];
    return `<tr>
    <td><a href="#advisor-${index + 1}"><strong>${html(row.name || row.advisorName || row.advisor_id || row.advisorProgramId)}</strong></a><br><span class="muted">${html(text([profile.identity.currentInstitution || row.current_institution || row.school || row.schoolName, profile.identity.currentPosition]))}</span>${discovery ? "" : `<br>${html(text([row.program, row.degree, row.intake]))}<br>${link(row.programUrl, "项目入口")}`}<br><span class="muted">${html(label("role", profile.piRoleConfidence.status))}</span></td>
    <td>${overviewCell([html(text(profile.researchMainline.longTermQuestion || profile.researchQuestionFit.reasons[0]))])}</td>
    <td>${overviewCell([html(label("continuity", profile.researchRouteContinuity.status)), profile.researchMainline.continuingThemes.length ? html(profile.researchMainline.continuingThemes.slice(0, 3).join("；")) : null, profile.researchMainline.recentShift ? `<span class="muted">近期转向：${html(profile.researchMainline.recentShift)}</span>` : null])}</td>
    <td>${overviewCell([profile.collaborationNetwork.coreCollaborators.length ? html(profile.collaborationNetwork.coreCollaborators.slice(0, 3).map((person) => person.name).join("、")) : null, `<span class="muted">${profile.collaborationNetwork.coreCollaborators.length} 位核心合作者 / ${profile.collaborationNetwork.researchNeighbors.length} 位研究邻居</span>`])}</td>
    <td>${overviewCell([html(label("activity", profile.currentActivity)), latest ? html(`${latest.title}${latest.year ? `（${latest.year}）` : ""}`) : null, `<span class="muted">${profile.latestSignals.projects.length} 条公开项目记录</span>`])}</td>
    <td>${overviewCell([`<strong>${html(label("fit", profile.researchQuestionFit.status))}</strong>`, profile.fitBoundary ? html(profile.fitBoundary) : null, profile.keyUnknowns[0] ? `<span class="muted">${html(profile.keyUnknowns[0])}</span>` : null, `<span class="sources">${evidenceReferences(profile.researchQuestionFit.sourceIds, evidence)}</span>`])}</td>
  </tr>`;
  }).join("")}</tbody></table></div>`;
}

function medicalBoundarySection(rows) {
  if (!rows.length) return "";
  return `<ul>${rows.map((row, index) => {
    const profile = row.evidenceProfile;
    return `<li><a href="#advisor-${index + 1}"><strong>${html(row.name || row.advisorName || row.advisor_id || "")}</strong></a> · ${html(label("fit", profile.researchQuestionFit.status))} · ${html(label("continuity", profile.researchRouteContinuity.status))}<br>${html(text([profile.fitBoundary, profile.keyUnknowns.slice(0, 2)]))}</li>`;
  }).join("")}</ul>`;
}

const REPORT_STYLE = "body{max-width:1100px;margin:auto;padding:32px 24px;color:#20252b;background:#fff;font:16px/1.7 system-ui,sans-serif}h1{font-size:30px;line-height:1.3}h2{font-size:23px;margin-top:36px;border-bottom:1px solid #ddd;padding-bottom:8px}h3{font-size:20px}h4{font-size:17px;margin:18px 0 6px}h5{font-size:15px;margin:14px 0 4px;color:#3b4652}a{color:#185a8d;text-underline-offset:3px}p{max-width:95ch}.muted,.sources{color:#59636d;font-size:14px}article{padding:8px 0 24px;border-bottom:1px solid #e5e7eb}.module{margin:8px 0 12px;padding:8px 12px;border-left:3px solid #e5e7eb}.status-line{font-size:14px}dl>div{display:grid;grid-template-columns:210px 1fr;gap:16px;margin:12px 0}dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:12px;min-width:150px;overflow-wrap:anywhere}th{background:#f4f6f8}li{margin:14px 0;overflow-wrap:anywhere}.works li{margin:8px 0}.ego-network{margin:8px 0 16px}.ego-network svg{max-width:640px;width:100%;height:auto;background:#fbfcfd;border:1px solid #e5e7eb;border-radius:8px}@media(max-width:640px){body{padding:20px 16px}dl>div{grid-template-columns:1fr;gap:2px}}@media print{body{max-width:none;padding:0}article{break-inside:avoid}a{color:inherit}}";

// ---------------------------------------------------------------------------
// Generic (non-medical) advisor brief — unchanged weighted-score contract
// ---------------------------------------------------------------------------

function advisorSection(advisor, index, project, candidates, evidence) {
  const advisorId = advisor.advisor_id || advisor.advisorId;
  const opportunities = candidates.filter((candidate) => (candidate.advisor_id || candidate.advisorId) === advisorId);
  const row = { ...opportunities[0], ...advisor };
  const sourcesFor = (...fields) => fieldEvidenceIds(evidence, [advisorId], fields);
  return `<article id="advisor-${index + 1}"><h3>${html(row.name || row.advisorName || advisorId)}</h3>
    <p>${html(row.current_institution || row.currentInstitution || row.school || row.schoolName || "当前机构待核验")} · ${link(row.homepage || row.advisorHomepage, "官方主页")}</p>
    ${facts([
      ["研究方向", row.research_directions || row.directions],
      ["近期研究、角色与贡献证据", row.recent_papers || row.recentPapers || row.researchAndPapers, sourcesFor("recent_papers", "recentPapers", "researchAndPapers", "research", "contributions")],
      ["真实申请入口", opportunities.length ? opportunities.map((candidate) => ({
        program: candidate.program || candidate.programNameEn || candidate.programNameZh,
        degree: candidate.degree, intake: candidate.intake, pathway: candidate.applicationPathway,
        eligibility: candidate.feasibility, opportunity: candidate.opportunityStatus, url: candidate.programUrl,
        sourceIds: profileReferences([candidate.eligibilityEvidence, candidate.hardConstraintEvidence, candidate.opportunityEvidence]),
      })) : "尚未映射真实项目"],
      ["风险提示", row.risk_flags],
      ["待补信息", row.missing_fields],
      ["最后核验日期", row.last_verified_at || row.lastVerifiedAt],
    ], evidence)}
    <p class="sources">${evidenceReferences(row.source_ids || row.sourceIds, evidence)}</p></article>`;
}

export function buildAdvisorReport({ project = {}, advisors = [], programs = [], evidence = [], candidates = [], ranking = [], audit = {}, cvValid = false, providerCapabilities = null } = {}) {
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
  const limitations = evidence.filter((row) => ["inaccessible", "not_checked", "conflict", "stale", "partial"].includes(row.status))
    .map((row) => `${row.page_title || row.title || row.evidence_id || "来源"}: ${row.status}${row.failure_reason ? `；${row.failure_reason}` : ""}`);
  const capabilityFacts = providerCapabilities?.providers ? [["数据来源可用性（run metadata）", Object.entries(providerCapabilities.providers).map(([id, route]) =>
    `${id}: ${route.selected_route}${route.credential_status && route.credential_status !== "not_applicable" ? `（credential ${route.credential_status}）` : ""}`)],
  ["运行模式", providerCapabilities.mode]] : [["数据来源可用性（run metadata）", "未保存 provider-capabilities.json；不能声称使用了认证 API"]];
  const coverage = facts([
    ["实际查询与筛选", queries.length ? queries : "未保存查询记录，不能声称已穷尽检索"],
    ["实际覆盖范围", audit.searchCoverage || audit.coverage || "未保存独立覆盖摘要；目标地区不等于已查遍该地区"],
    ["访问限制与待核验来源", limitations.length ? limitations : "已保存证据未列出此类限制；不代表所有来源可访问"],
    ...(medical ? capabilityFacts : []),
    ...(medical ? [["Seeds / 网络 / 饱和", [audit.seedSummary, audit.networkRounds !== undefined ? `网络轮次：${audit.networkRounds}` : null, audit.saturation ? `饱和：${text(audit.saturation)}` : null].filter(Boolean).length
      ? [audit.seedSummary, audit.networkRounds !== undefined ? `网络轮次：${audit.networkRounds}` : null, audit.saturation ? `饱和：${text(audit.saturation)}` : null].filter(Boolean)
      : "未保存 seed / 网络扩展 / 饱和记录"]] : []),
    [medical ? "本轮导师与候选选择" : "本轮项目候选选择", { 保留: audit.selectedCount ?? candidates.length,
      [medical ? "明确不适用" : "未保留"]: audit.excludedCount ?? "未记录", 因调研预算暂缓: audit.deferredCount ?? "未记录",
      ...(medical ? { 导师记录: advisorRows.length } : {}) }],
  ]);
  const programDetails = medical && discovery ? "" : programRows.map((row) => {
    const program = programById.get(row.program_id || row.programId) || {};
    const sourcesFor = (...fields) => fieldEvidenceIds(evidence,
      [row.program_id || row.programId, row.advisorProgramId], fields, row.intake);
    return `<details><summary>${html(row.name || row.advisorName || row.advisorProgramId)} · ${html(row.program || "项目名称待核验")}：申请条件与时效</summary>${facts([
      ["学位 / 批次 / 招生路径", [row.degree, row.intake, row.applicationPathway], sourcesFor("degree", "intake", "applicationPathway", "application_pathway")],
      ["轮转与联系规则", [row.rotation || program.rotation, row.advisorContactRequirements || row.advisor_contact_requirements || program.contact_rules], sourcesFor("rotation", "contact_rules", "advisorContactRequirements")],
      ["项目截止日（批次 / 时区）", program.deadlines?.program || program.program_deadline || program.deadline, sourcesFor("deadline", "program_deadline", "deadlines.program")],
      ["奖学金截止日（批次 / 时区）", program.deadlines?.scholarship || program.scholarship_deadline, sourcesFor("scholarship_deadline", "deadlines.scholarship")],
      ["岗位截止日（批次 / 时区）", program.deadlines?.position || program.position_deadline, sourcesFor("position_deadline", "deadlines.position")],
      ["学费 / 项目资助条款", [program.tuition, program.scholarships], sourcesFor("tuition", "scholarships")],
      ["申请材料 / RP要求", [program.application_materials, program.rp_requirement], sourcesFor("application_materials", "rp_requirement")],
      ["资格 / 硬约束依据", [row.feasibility, row.feasibilityReasons, row.hardConstraintStatus, row.hardConstraintReasons], profileReferences([row.eligibilityEvidence, row.hardConstraintEvidence])],
      ["最后核验 / 待补条件", [program.last_verified_at, program.missing_fields]],
    ], evidence)}<p class="sources">项目相关来源：${evidenceReferences(program.source_ids || program.sourceIds, evidence)}</p></details>`;
  }).join("");
  const genericTable = programRows.length ? `<div class="table-wrap"><table><thead><tr><th>导师 / 真实项目</th><th>匹配依据</th><th>资格 / 招生机会</th><th>下一步</th></tr></thead><tbody>${programRows.map((row) => `<tr>
    <td><strong>${html(row.name || row.advisorName || row.advisorProgramId)}</strong><br>${html(text([row.program, row.degree, row.intake]))}<br>${link(row.programUrl, "项目入口")}</td>
    <td>${sourcedValue(row.matchReasons || row.fitEvidence, evidence)}</td>
    <td>资格：${html(row.feasibility || "needs_confirmation")}<br><span class="sources">${evidenceReferences(profileReferences([row.eligibilityEvidence, row.hardConstraintEvidence]), evidence)}</span><br>机会：${html(row.opportunityStatus || "unknown")}<br><span class="sources">${evidenceReferences(profileReferences(row.opportunityEvidence), evidence)}</span><br>${html(row.comparisonGroup || "")}</td>
    <td>${sourcedValue(row.recommendedAction, evidence)}</td>
  </tr>`).join("")}</tbody></table></div>` : "<p>尚未映射真实博士项目。</p>";
  // Discovery lists advisors; application lists advisor–programme opportunities. Both use the same five-module overview.
  const overviewRows = discovery ? advisorRows : programRows;
  const evidenceSection = `<section><h2>${medical ? "来源及检索覆盖说明" : "证据、来源与信息缺口"}</h2><p class="muted">verified 仅说明保存的来源支持该项主张；转载与同源页面不算独立佐证。未检索、未找到、受阻、部分、冲突和过期分别保留。${medical ? "所有导师级链接均为 item-level 外链；下方证据编号仅作补充索引。" : ""}</p>
${evidence.length ? `<ol>${evidence.map((row, index) => `<li id="evidence-${index + 1}"><strong>${html(row.title || row.page_title || row.evidence_id || row.evidenceId || `证据 ${index + 1}`)}</strong> · ${link(row.final_url || row.source_url || row.url)}
${facts([["主张 / 类型", [row.claim || row.finding || row.value || row.excerpt, row.claim_type || row.claimType]],
  ["实体 / 支持字段", [row.entity_id || row.entity, row.fields_supported || row.field]],
  ["状态 / 提取状态", [row.status || "not_checked", row.extraction_status || row.extractionStatus]],
  ["适用批次 / 来源更新时间 / 访问时间", [row.intake || row.applicable_intake, row.source_updated_at, row.accessed_at || row.accessedAt]],
  ["读取深度 / 检索方式 / 定位", [row.reading_depth || row.read_depth || row.readDepth, [row.retrieval_method || row.retrievalMethod, row.retrieval_provider, row.retrieval_tool].filter(Boolean), row.page_locator || row.locator]],
  ["支持片段 / 同源组 / 限制", [row.excerpt, row.same_source_group || row.source_group_id || row.sourceGroupId, row.limitations || row.failure_reason]],
])}</li>`).join("")}</ol>` : "<p>未保存可核验的事实级证据；当前内容不能视作已核验结论。</p>"}
${coverage}
${historicalRanking ? `<details><summary>历史比较记录（不用于当前顺序或申请判断）</summary>${facts([
  ["历史比较模式 / 确认版本", [ranking.rankingMode, ranking.confirmedRevision]],
  ["历史确认指纹", ranking.confirmedFingerprint],
  ["历史候选ID", rankings.map((row) => row.advisorProgramId || row.advisor_program_id)],
])}</details>` : ""}</section>`;
  const head = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>${html(subject(project))} — 导师调研</title>
<style>${REPORT_STYLE}</style></head>
<body><header><p class="muted">Boss Hunting · 共享记录派生报告</p><h1>${html(subject(project))}</h1>
${fixtureNotice ? `<p><strong>虚构示例 / FICTIONAL FIXTURE：</strong>${html(fixtureNotice)}</p>` : ""}
<p>${discovery ? "生物医学导师方向探索" : medical ? "生物医学导师申请筛选" : "导师与申请项目调研"} · ${html(project.target || "地区尚未确认")} · ${advisorRows.length} 位导师记录${medical && discovery ? "" : ` / ${programRows.length} 个真实项目机会`}</p>
${historicalRanking ? `<p><strong>历史比较待复核：</strong>已有 ${rankings.length} 条比较记录的调查确认已失效或不适用于当前范围。保留研究和来源痕迹；当前按稳定名称展示，申请资格待重新核对。</p>` : ""}
<p class="muted">${medical ? "按研究问题契合与主线连续性展示，列表顺序不是导师质量排名。未知不代表不符合；没有综合导师分、引用量排名、录取概率或培养成功率。" : "结论依据共享记录；申请条件、名额与资金在行动前需要按项目批次重核。"}</p></header>`;
  if (!medical) {
    return `${head}
<section><h2>本次研究画像</h2>${facts([["研究兴趣", project.interests], ["目标学位 / 批次", [project.degree, project.season]], ["硬约束", project.hardConstraints]])}</section>
<section><h2>候选比较与真实项目入口</h2>${genericTable}${programDetails}</section>
<section><h2>导师证据简报</h2>${advisorRows.length ? advisorRows.map((row, index) => advisorSection(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project, programRows, evidence)).join("") : "<p>尚无导师事实记录。</p>"}</section>
${evidenceSection}
<p class="muted">本报告由本地共享记录生成，不会访问网页、发送邮件或启动申请材料。</p></body></html>`;
  }
  const optionalProfile = [
    ["研究对象 / 尺度", [profile.researchObjects, profile.researchScales]],
    ["研究范式 / 方法偏好", [profile.researchModes, profile.methodPreferences]],
  ].filter(([, value]) => value.some((items) => Array.isArray(items) && items.length));
  return `${head}
<section><h2>本次研究画像</h2>${facts([
  ["生物医学领域", profile.fields],
  ["疾病 / 机制与科学问题", [profile.diseaseScope, profile.diseasesOrMechanisms, profile.researchQuestions]],
  ["目标国家 / 地区", profile.regions],
  ...optionalProfile,
  ["可接受相邻方向 / 排除项", [profile.adjacentInterests, profile.exclusions]],
])}</section>
<section><h2>候选导师概览</h2>${medicalOverviewTable(overviewRows, evidence, discovery)}${programDetails}</section>
<section><h2>导师五模块深查</h2>${advisorRows.length ? advisorRows.map((row, index) => medicalAdvisorSection(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project, programRows.filter((candidate) => (candidate.advisor_id || candidate.advisorId) === (row.advisor_id || row.advisorId)), evidence)).join("") : "<p>尚无导师事实记录。</p>"}</section>
<section><h2>方向契合与主要边界</h2>${medicalBoundarySection(advisorRows)}</section>
${evidenceSection}
<p class="muted">本报告由本地共享记录生成，不会访问网页、发送邮件或启动申请材料。项目记录说明科研支撑，不说明博士生个人资助；公开培养样本没有分母时不计算成功率；未在公开库中找到不等于没有。</p></body></html>`;
}

async function readJson(path, fallback) {
  try { return JSON.parse(await readFile(path, "utf8")); }
  catch (error) { if (error.code === "ENOENT" && fallback !== undefined) return fallback; throw error; }
}

async function latestProviderCapabilities(root) {
  const runs = await readdir(resolve(root, "runs")).catch(() => []);
  for (const run of runs.sort().reverse()) {
    const capabilities = await readJson(resolve(root, "runs", run, "provider-capabilities.json"), null);
    if (capabilities) return capabilities;
  }
  return null;
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
    cvValid: await hasReadableProjectCv(root, project.cv), providerCapabilities: await latestProviderCapabilities(root) });
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
