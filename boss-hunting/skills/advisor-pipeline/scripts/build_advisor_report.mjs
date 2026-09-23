#!/usr/bin/env node

import { overlayDoctoralProfile, labWebsiteVerified, doctoralCoverage, doctoralWindow, firstAuthorPaperState, firstAuthorSummary, firstAuthorIdentity } from "./doctoral-evidence.mjs";
import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { isExecutedDirectly } from "./direct-execution.mjs";
import { isMedicalRankingCurrent, normalizeProjectMetadata } from "./project-contract.mjs";
import {
  buildMedicalDiscoveryView, compareMedicalCandidates, hasReadableProjectCv, isMedicalEvidenceProfile,
  evidenceProfile, normalizeMedicalCandidate, validateMedicalCandidateMappings, projectSearchCoverage,
} from "./medical-evidence.mjs";

function html(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

const WORDS = {
  verified: "已核实", partial: "部分核实", not_found: "在所查范围内未找到", not_checked: "未检索或未核验",
  inaccessible: "访问受阻", conflict: "来源存在冲突", stale: "信息可能过期", not_applicable: "不适用", unknown: "尚不清楚",
  found: "找到记录", official_database: "官方基金库", supplementary: "补充来源",
  corresponding_author: "通讯作者", co_corresponding_author: "共同通讯作者", co_first_author: "共同第一作者", first_author: "第一作者", last_author: "末位作者",
  coauthor: "共同作者", principal_investigator: "项目负责人", co_investigator: "项目参与者",
  research_seed: "原创研究论文", map_seed: "综述提供的线索", collaboration: "合作研究线索", research_neighbor: "相关研究线索", official_roster: "机构导师名录",
  citation: "引用关系", co_citation: "共同被引用", bibliographic_coupling: "引用相同文献", semantic_similarity: "研究内容相近", related_papers: "相关论文",
  single_disease: "单一疾病", multiple_diseases: "多种疾病", pan_cancer: "泛癌", unrestricted: "不限",
  PI: "项目负责人", co_PI: "共同项目负责人", active: "在研", completed: "已结束", pending: "待确认",
  eligible: "符合已核实条件", ineligible: "不符合已核实条件", needs_confirmation: "需要进一步确认", advertised: "已有公开招募信息",
  fact: "公开事实", interpretation: "基于证据的解释", question: "待核实问题",
};
const FIELD_LABELS = { program: "项目", degree: "学位", intake: "招生批次", pathway: "申请路径", eligibility: "申请资格", opportunity: "招生机会", url: "原文", title: "名称", name: "名称", note: "说明", status: "核验情况", reason: "理由", claim: "记录内容", year: "年份", type: "类型", orcid: "ORCID", openalex: "OpenAlex" };
function text(value) {
  if (value === null || value === undefined || value === "") return "未记录";
  if (Array.isArray(value)) { const present = value.filter((item) => item !== null && item !== undefined && item !== "" && (!Array.isArray(item) || item.length)); return present.length ? present.map(text).join("；") : "未记录"; }
  if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${FIELD_LABELS[key] || key}：${text(item)}`).join("；");
  return WORDS[value] || String(value);
}

function sourceUrl(row) { return row.final_url || row.source_url || row.url; }
function urlKey(value) {
  try { const url = new URL(value); if (!["http:", "https:"].includes(url.protocol)) return null;
    url.hash = ""; for (const key of [...url.searchParams.keys()]) if (/^utm_/i.test(key)) url.searchParams.delete(key);
    return url.href;
  } catch { return null; }
}
function citationLabel(row) {
  return row.citation_label || row.page_title || row.title || ({ institutional_profile: "机构导师介绍", official_profile: "机构导师介绍", publication: "研究论文", grant_database: "基金库检索记录", official_database: "官方数据库记录" }[row.source_type]) || (urlKey(sourceUrl(row)) ? `原始来源｜${new URL(sourceUrl(row)).hostname}` : "未提供来源标题");
}
function linkedUrls(content) { return [...content.matchAll(/href="([^"]+)"/g)].map((match) => match[1].replaceAll("&amp;", "&")); }

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
      .map(([key, item]) => `${html(FIELD_LABELS[key] || key)}：${sourcedValue(item, evidence)}`).join("；");
    return `${content}${references?.length ? `<br><span class="sources">${evidenceReferences(references, evidence, linkedUrls(content))}</span>` : ""}`;
  }
  // Link only URLs actually present in the record; never synthesize a source.
  return typeof value === "string" && /^https?:\/\/\S+$/i.test(value) ? link(value, value) : html(text(value));
}

function facts(items, evidence) {
  return `<dl>${items.map(([label, value, sourceIds]) => {
    const content = evidence ? sourcedValue(value, evidence) : html(text(value));
    const references = sourceIds?.length ? evidenceReferences(sourceIds, evidence || [], linkedUrls(content))
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

function evidenceReferences(ids, evidence, excludedUrls = []) {
  const sourceIds = new Set(Array.isArray(ids) ? ids : []);
  const matched = evidence.map((row, index) => ({ row, index })).filter(({ row }) =>
    sourceIds.has(row.evidence_id || row.evidenceId));
  if (!matched.length) return "来源关联尚待补齐，信息待核验";
  const groups = new Map();
  for (const { row, index } of matched) { const key = urlKey(sourceUrl(row)) || `missing-${index}`; const group = groups.get(key) || []; group.push(row); groups.set(key, group); }
  const excluded = new Set(excludedUrls.map(urlKey).filter(Boolean));
  const links = [...groups].flatMap(([key, rows]) => {
    const states = [...new Set(rows.map((row) => row.status || "not_checked"))].filter((state) => state !== "verified");
    const note = states.length ? `（${html(states.map(text).join("、"))}）` : "";
    if (excluded.has(key)) return note ? [note] : [];
    const row = rows.find((item) => item.citation_label) || rows[0];
    return [`${link(sourceUrl(row), citationLabel(row))}${note}`];
  });
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
const REPORT_MODULES = [
  ["a", "01", "身份与任职"], ["b", "02", "研究方向与近年论文"],
  ["c", "03", "主要合作研究者"], ["d", "04", "科研基金与近期进展"],
  ["e", "05", "博士指导情况"],
];
function moduleHeading(index, key) {
  const [, number, title] = REPORT_MODULES.find(([id]) => id === key);
  return `<div class="module module-${key}" id="advisor-${index + 1}-${key}"><h4><span class="module-number">${number}</span>${title}</h4>`;
}
function reportNavigation(advisors, medical) {
  return `<nav class="report-toc" aria-label="报告目录"><details class="toc-shell" open><summary>报告目录</summary><div class="toc-content">
<a href="#requirements">查找要求</a><a href="#overview">导师对照</a><a href="#advisors">导师详情</a>
${advisors.map((row, index) => {
    const id = `advisor-${index + 1}`;
    const name = html(row.name || row.advisorName || row.advisor_id || row.advisorId || "姓名待核实");
    return medical ? `<details class="toc-advisor" data-advisor="${id}"><summary><a href="#${id}">${name}</a></summary><div>${REPORT_MODULES.map(([key, number, title]) => `<a href="#${id}-${key}">${number} ${title}</a>`).join("")}</div></details>` : `<a href="#${id}">${name}</a>`;
  }).join("")}
<a href="#coverage">检索与来源</a></div></details></nav>`;
}
const REPORT_NAV_SCRIPT = `(() => {
  const nav = document.querySelector('.report-toc');
  if (!nav) return;
  const shell = nav.querySelector('.toc-shell');
  const desktop = matchMedia('(min-width:1200px)');
  const links = [...nav.querySelectorAll('a[href^="#"]')];
  const targets = links.map(link => document.getElementById(link.hash.slice(1)));
  const groups = [...nav.querySelectorAll('.toc-advisor')];
  const resize = () => { shell.open = desktop.matches; };
  resize(); desktop.addEventListener('change', resize);
  let scheduled = false;
  const update = () => {
    scheduled = false;
    let current = 0;
    targets.forEach((target, index) => { if (target && target.getBoundingClientRect().top <= 120) current = index; });
    links.forEach((link, index) => { if (index === current) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current'); });
    if (!nav.contains(document.activeElement)) {
      const active = targets[current]?.closest('article')?.id;
      groups.forEach(group => { group.open = group.dataset.advisor === active; });
      if (desktop.matches) {
        const box = nav.getBoundingClientRect();
        const item = links[current].getBoundingClientRect();
        if (item.top < box.top + 12) nav.scrollTop += item.top - box.top - 12;
        else if (item.bottom > box.bottom - 12) nav.scrollTop += item.bottom - box.bottom + 12;
      }
    }
  };
  const schedule = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(update); } };
  addEventListener('scroll', schedule, {passive:true}); addEventListener('resize', schedule);
  nav.addEventListener('focusout', schedule);
  nav.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    if (!desktop.matches) shell.open = false;
    const target = document.getElementById(link.hash.slice(1));
    if (target) { target.setAttribute('tabindex', '-1'); target.focus({preventScroll:true}); }
    schedule();
  });
  update();
})();`;
const REPORT_NAV_HASH = createHash("sha256").update(REPORT_NAV_SCRIPT).digest("base64");


// ---------------------------------------------------------------------------

const LABELS = {
  fit: { direct: "直接相关", partial: "部分相关", adjacent: "相邻方向", weak: "弱相关", insufficient_information: "信息不足" },
  continuity: { sustained_core: "持续核心方向", active_emerging: "活跃新兴方向", new_expansion: "新近扩展", occasional_participation: "偶发参与", unclear: "不明确" },
  role: { verified: "已核实研究负责人身份", probable: "研究负责人身份尚待确认", emerging: "新近独立的研究负责人", identity_unresolved: "身份尚未确认" },
  sufficiency: { strong: "证据充分", adequate: "证据足够", sparse: "证据稀少", conflicted: "证据冲突" },
  activity: { active: "近期活跃", recent_signal: "有近期信号", unclear: "活跃度不明", apparently_inactive_in_checked_scope: "在已检查范围内未见近期活动" },
  edge: { coauthorship: "共同发表", shared_project: "共同项目", shared_grant: "共同基金", shared_trial: "共同试验" },
};

function label(group, value) {
  return LABELS[group]?.[value] || value || "尚未核实";
}

function sources(ids, evidence, excludedUrls = []) {
  const content = evidenceReferences(ids, evidence, excludedUrls);
  return content ? `<span class="sources">${content}</span>` : "";
}

function workItem(work, evidence) {
  const meta = [work.year, work.venue, work.verifiedRole && work.verifiedRole !== "unknown" ? `作者角色：${text(work.verifiedRole)}` : null,
    work.relationToMainline ? `与研究方向的关系：${work.relationToMainline}` : null, work.isPreprint ? "预印本（未经同行评审）" : null]
    .filter(Boolean).map(html).join(" · ");
  const external = work.url || (work.doi ? `https://doi.org/${String(work.doi).replace(/^https?:\/\/doi\.org\//i, "")}` : null);
  const anchor = external ? link(external, work.title || external) : "";
  // Unsafe or missing URLs never drop the (escaped) title itself.
  const heading = anchor.startsWith("<a ") ? anchor : `${html(work.title || "标题待核验")}${external ? "（未提供可用公开链接）" : ""}`;
  const refs = sources(work.sourceIds, evidence, [external]);
  return `<li>${heading}${meta ? `<br><span class="muted">${meta}</span>` : ""}${refs ? `<br>${refs}` : ""}</li>`;
}

function workList(works, evidence, empty) {
  return works.length ? `<ul class="works">${works.map((work) => workItem(work, evidence)).join("")}</ul>` : `<p class="muted">${html(empty)}</p>`;
}

function collaboratorProfiles(network, evidence) {
  if (!network.coreCollaborators.length) return `<p class="muted">尚未筛选出有公开合作依据的研究者。</p>`;
  const records = (person, project) => {
    const items = person.collaborationEvidence.filter((item) => typeof item === "object" && item !== null
      && (project ? ["shared_project", "shared_grant", "shared_trial"].includes(item.type) : item.type === "coauthorship"));
    const legacy = project ? [] : person.collaborationEvidence.filter((item) => typeof item === "string");
    if (!items.length && !legacy.length) return `<p class="muted">未记录可核验的${project ? "合作项目" : "合作产出"}。</p>`;
    const content = `<ul class="works">${items.map((item) => {
      const name = item.title || item.project_title || `${label("edge", item.type)}（具体名称未记录）`;
      const content = `${item.url ? link(item.url, name) : html(name)}${item.year ? ` · ${html(item.year)}` : ""}`;
      return `<li>${content}${sources(item.sourceIds || item.source_ids || person.sourceIds, evidence, linkedUrls(content))}</li>`;
    }).join("")}${legacy.map((item) => `<li>${html(item)} ${sources(person.sourceIds, evidence)}</li>`).join("")}</ul>`;
    return items.length + legacy.length > 3 ? `<details><summary>${project ? "合作项目" : "合作产出"}（${items.length + legacy.length} 项）</summary>${content}</details>` : content;
  };
  return `<div class="people-list">${network.coreCollaborators.map((person) => `<div class="person-entry collaborator">
    <header class="person-heading"><h5>${html(person.name || "姓名待核验")}</h5></header>
    <p class="person-meta">${html(text([person.currentInstitution, person.currentPosition]))}${person.sourceIds.length ? ` ${sources(person.sourceIds, evidence)}` : ""}</p>
    <p><span class="field-label">科研方向</span>${html(text(person.ownCoreDirection))}</p>
    <div class="person-work"><h6>与导师合作的项目</h6>${records(person, true)}
    <h6>与导师合作的产出</h6>${records(person, false)}</div>
  </div>`).join("")}</div>`;
}

function projectTable(projects, evidence) {
  if (!projects.length) return `<p class="muted">尚未登记可核验的项目详情。是否查过基金库，请看上方检索记录；未找到公开记录不等于没有基金。</p>`;
  return `<div class="table-wrap"><table><thead><tr><th>项目名称</th><th>项目编号</th><th>资助机构 / 来源</th><th>项目中的角色</th><th>期限</th><th>状态</th><th>公开金额（单位）</th></tr></thead><tbody>${projects.map((project) => `<tr>
    <td>${html(text(project.title))}<br>${sources(project.sourceIds, evidence)}</td>
    <td>${html(text(project.projectId))}</td>
    <td>${html(text([project.fundingBody, project.source]))}</td>
    <td>${html(text(project.piRole))}</td>
    <td>${html(text(project.period))}</td>
    <td>${html(text(project.status))}</td>
    <td>${project.amount === null || project.amount === undefined ? "未公开" : `${html(project.amount)} ${html(project.amountUnit || "")}${project.amountBasis ? `（${html(project.amountBasis)}）` : ""}`}</td>
  </tr>`).join("")}</tbody></table></div>`;
}

function projectSearchList(searches, evidence, advisorId) {
  const coverage = projectSearchCoverage(searches, evidence, advisorId);
  return `<p><strong>${html(coverage.summary)}</strong></p>${searches.length ? searches.map((search) => `<div class="search-record">
<h6>${html(search.database || "数据库未记录")} · ${html(search.status === "partial" ? "部分完成" : text(search.status))}</h6>
${facts([["查询姓名与机构", search.query], ["检索日期", search.checkedAt || "未记录"], ["检索范围", search.scope],
  ["来源类别", text(search.sourceKind)], ["访问限制与补查说明", search.limitations || "未记录限制说明"]])}
${search.requiresInteraction ? `<p>${html(projectSearchCoverage([search], evidence, advisorId).complete ? "已完成交互查询与结果核验" : "交互查询尚未完成核验")}</p>` : ""}
${search.interactionAttempts?.length ? `<details><summary>实际交互尝试与限制</summary>${search.interactionAttempts.map(attempt => facts([["执行日期", attempt.checkedAt], ["执行结果", attempt.reason || attempt.outcome], ["工具", [attempt.provider, attempt.tool].filter(Boolean).join(" / ")]]) + sources(attempt.sourceIds || [], evidence)).join("")}</details>` : ""}
${sources(search.sourceIds, evidence)}</div>`).join("") : `<p class="muted">旧记录没有逐位基金检索过程，本项需要补查。</p>`}`;
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

function doctoralSearchDetails(doctoral, kind, evidence) {
  const records = doctoral.searches.filter((row) => row.kind === kind);
  if (!records.length) return `<p class="muted">未记录此项检索。</p>`;
  return records.map((row) => `<p>${html(text(row.status))} · ${html(row.database || "来源未记录")} · 查阅日期：${html(row.checkedAt || "未记录")}</p>
<details><summary>检索范围与限制</summary>${facts([["实际查询", row.query], ["时间范围", [row.windowStart, row.windowEnd]], ["限制", row.limitations || "未记录"]])}${sources(row.sourceIds, evidence)}</details>`).join("");
}

function doctoralSupplement(doctoral, evidence) {
  const window = doctoralWindow(doctoral);
  const labs = doctoral.labWebsites.map((site) => `<div><p>${link(site.url, site.title)} · ${labWebsiteVerified(site, evidence) ? "与导师的归属关系已核实" : "与导师的归属关系待核实"}${site.status === "found" ? "" : ` · ${html(text(site.status))}`} ${sources(site.sourceIds, evidence, [site.url])}</p>
${site.pages.map((page) => `<p>${link(page.url, page.title)}${page.status === "found" ? "" : ` · ${html(text(page.status))}`}<br>网页查阅日期：${html(page.accessedAt || "未记录")} · 页面更新时间：${html(page.updatedAt || "页面未注明")}${page.limitations ? `<br>${html(page.limitations)}` : ""} ${sources(page.sourceIds, evidence, [page.url])}</p>`).join("")}</div>`).join("");
  const people = doctoral.firstAuthorProfiles.map((person) => {
    const eligible = person.papers.filter((paper) => firstAuthorPaperState(paper, window, evidence) === "eligible");
    const pending = person.papers.filter((paper) => firstAuthorPaperState(paper, window, evidence) !== "eligible");
    const papers = eligible.map((paper) => ({...paper, year: paper.date || paper.year,
      verifiedRole: paper.firstAuthorRole, relationToMainline: `导师署名：${text(paper.advisorRole)}`}));
    const works = workList(papers, evidence, "尚无符合范围且作者角色已核实的共同论文。");
    return `<div class="person-entry first-author"><header class="person-heading"><h6>${html(person.name || "姓名待核实")}</h6><span class="person-role">${html(firstAuthorIdentity(person, evidence))}</span></header>
${person.identitySourceIds.length ? `<p class="person-meta">${sources(person.identitySourceIds, evidence)}</p>` : ""}
<p><span class="field-label">基于这些共同论文的总结</span>${html(firstAuthorSummary(person, window, evidence))}${person.summarySourceIds.length ? ` ${sources(person.summarySourceIds, evidence)}` : ""}</p>
${papers.length > 3 ? `<details><summary>共同论文（${papers.length} 篇）</summary>${works}</details>` : works}
${pending.length ? `<details><summary>未纳入画像的论文线索（${pending.length} 条）</summary><ul>${pending.map((paper) => `<li>${html(paper.title || "标题待核实")}：${html(firstAuthorPaperState(paper, window, evidence))}${sources(paper.sourceIds, evidence)}</li>`).join("")}</ul></details>` : ""}</div>`;
  }).join("");
  return `<h5>实验室官网与查阅情况</h5>${doctoralSearchDetails(doctoral, "lab_website", evidence)}${labs || "<p>尚未登记已核验的实验室网站；不代表没有。</p>"}
<h5>近五年通讯作者论文中的第一作者</h5><p class="muted">第一作者不自动代表博士生；身份依据单独核验。${window ? `论文日期范围：${html(window.start)} 至 ${html(window.end)}。` : "未记录有效的近五年检索范围。"}</p>
${doctoralSearchDetails(doctoral, "corresponding_papers", evidence)}${people || "<p>尚未登记第一作者画像；不代表没有共同论文。</p>"}`;
}

function evidenceStatusRow(profile) {
  return `<p class="status-line"><span>${html(label("role", profile.piRoleConfidence.status))}</span> · <span>公开信息：${html(label("sufficiency", profile.evidenceSufficiency))}</span> · <span>近期研究活动：${html(label("activity", profile.currentActivity))}</span></p>`;
}

function reportAdvisorRow(advisor, index, project, opportunities) {
  const currentEvaluations = opportunities.filter((candidate) => candidate.evaluationCurrent);
  // Advisor-level facts, then Finder's opportunity-level profile, then the
  // current evaluation override field by field; identities never change.
  const factsRow = { ...opportunities[0], ...advisor,
    evidenceProfile: { ...evidenceProfile(advisor), ...evidenceProfile(opportunities[0] || {}), ...(currentEvaluations[0]?.evidenceProfile || {}) } };
  // Grant follow-ups live on the advisor record. An older opportunity snapshot
  // must not hide them in application-mode reports.
  const stored = evidenceProfile(advisor);
  const storedSignals = stored.latestSignals || stored.latest_signals;
  if (storedSignals) {
    for (const names of [["projects", "grants"], ["projectSearches", "project_searches"]]) {
      const signals = factsRow.evidenceProfile.latestSignals || factsRow.evidenceProfile.latest_signals || {};
      const additions = storedSignals[names[0]] || storedSignals[names[1]];
      if (!additions?.length) continue;
      const others = signals[names[0]] || signals[names[1]] || [];
      const key = (item) => names[0] === "projects"
        ? JSON.stringify([item.source || item.fundingBody || item.funding_body, item.projectId || item.project_id || item.grant_id || item.title])
        : JSON.stringify([item.database, item.query, item.scope, item.checkedAt || item.checked_at]);
      const seen = new Set(additions.map(key));
      factsRow.evidenceProfile.latestSignals = { ...signals, [names[0]]: [...additions, ...others.filter((item) => !seen.has(key(item)))] };
    }
  }
  const storedDoctoral = stored.doctoralTrajectory || stored.doctoral_trajectory;
  if (storedDoctoral) {
    const projected = factsRow.evidenceProfile.doctoralTrajectory || factsRow.evidenceProfile.doctoral_trajectory || {};
    factsRow.evidenceProfile.doctoralTrajectory = overlayDoctoralProfile(storedDoctoral, projected);
  }
  return normalizeMedicalCandidate(factsRow, { ...project, searchMode: "discovery" }, index);
}

function medicalAdvisorSection(advisor, index, project, opportunities, evidence) {
  const advisorId = advisor.advisor_id || advisor.advisorId;
  const row = reportAdvisorRow(advisor, index, project, opportunities);
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
<p>与您的研究需求：${html(label("fit", profile.researchQuestionFit.status))}。${html(profile.researchQuestionFit.reasons.join("；"))} ${sources(profile.researchQuestionFit.sourceIds, evidence)}</p>
<p><strong>目前能确认和不能确认的事项：</strong>${html(text(profile.fitBoundary))}</p>
${moduleHeading(index, "a")}${facts([
  ["当前机构 / 院系 / 职位", [identity.currentInstitution || row.current_institution || row.school || row.schoolName, identity.department, identity.currentPosition], identity.sourceIds],
  ["主要研究方向", identity.researchPositioning, identity.sourceIds],
  ["博士指导资格与所属项目", [identity.doctoralSupervisionLink, doctoral.graduateProgram.graduateSchool, doctoral.graduateProgram.doctoralProgram, doctoral.graduateProgram.supervisorListing, doctoral.graduateProgram.institutionalRelationship].filter(Boolean), [...(identity.sourceIds || []), ...(doctoral.graduateProgram.sourceIds || [])]],
], evidence)}<p>${link(officialUrl, "机构导师介绍")} · 任职信息核对日期：${html(identity.affiliationAsOf || "未记录")}</p></div>
${moduleHeading(index, "b")}${facts([
  ["长期科学问题", mainline.longTermQuestion, mainline.sourceIds],
  ["持续主题 / 新方向 / 近期转向", [mainline.continuingThemes.length ? `持续：${mainline.continuingThemes.join("；")}` : null, mainline.newDirections.length ? `新方向：${mainline.newDirections.join("；")}` : null, mainline.recentShift ? `近期转向：${mainline.recentShift}` : null].filter(Boolean), mainline.sourceIds],
  ["研究对象 / 方法", [mainline.researchObjects, mainline.methods], mainline.sourceIds],
  ["是否持续研究这一方向", [label("continuity", profile.researchRouteContinuity.status), ...profile.researchRouteContinuity.reasons], profile.researchRouteContinuity.sourceIds],
], evidence)}${facts([["论文检索时间范围", mainline.backSearchWindow || row.back_search?.window || "未记录实际检索范围"]])}
<h5>代表性论文及作者角色</h5>${workList(mainline.representativeWorks, evidence, "尚未登记已核实作者角色的代表性论文。")}
${mainline.participationOnlyWorks.length ? `<h5>仅参与型工作（不计入主线）</h5>${workList(mainline.participationOnlyWorks, evidence, "")}` : ""}</div>
${moduleHeading(index, "c")}${collaboratorProfiles(network, evidence)}
</div>
${moduleHeading(index, "d")}
<h5>逐位基金库检索</h5>${projectSearchList(signals.projectSearches, evidence, advisorId)}
<h5>公开项目 / 基金记录</h5>${projectTable(signals.projects, evidence)}
<h5>近期论文</h5>${workList(signals.latestPapers.filter((work) => !mainline.representativeWorks.some((prior) => prior.title === work.title)), evidence, signals.latestPapers.length ? "近期论文已列入上方代表性论文。" : "未登记近期论文；不代表没有产出。")}
${signals.preprints.length ? `<h5>预印本</h5>${workList(signals.preprints, evidence, "")}` : ""}
${signals.registries.length || signals.trials.length ? facts([["注册 / 试验记录", [signals.registries, signals.trials], signals.sourceIds]], evidence) : ""}</div>
${moduleHeading(index, "e")}
${doctoralSupplement(doctoral, evidence)}
<h5>当前博士生（公开可见）</h5>${doctoralList(doctoral.currentDoctoral, evidence, "尚未登记可核验的当前博士生；不代表没有。")}
<h5>已毕业博士（公开可见）</h5>${doctoralList(doctoral.formerDoctoral, evidence, "尚未登记可核验的已毕业博士；新兴 PI 可能尚无毕业博士，不作负面推断。")}
${doctoral.emergingPiNote ? `<p class="muted">${html(doctoral.emergingPiNote)}</p>` : ""}
<p class="muted">${html(doctoral.sampleLimitation)}</p></div>
${applicationEntry}
${profile.formalRecords.length ? facts([["更正、撤稿或机构公告", profile.formalRecords]], evidence) : ""}
${facts([["仍需确认的信息", profile.keyUnknowns], ["建议下一步核实", profile.nextVerification]])}</article>`;
}

function medicalOverviewTable(rows, evidence, discovery, advisors) {
  if (!rows.length) return `<p>尚无导师记录。</p>`;
  return `<div class="table-wrap"><table class="overview"><thead><tr><th>导师与机构</th><th>与需求的关系</th><th>基金检索结果</th><th>需要进一步确认</th></tr></thead><tbody>${rows.map((row) => {
    const detailIndex = advisors.findIndex((advisor) => (advisor.advisor_id || advisor.advisorId) === (row.advisor_id || row.advisorId));
    const profile = { ...row.evidenceProfile, latestSignals: advisors[detailIndex]?.evidenceProfile.latestSignals || row.evidenceProfile.latestSignals };
    const anchor = detailIndex >= 0 ? `advisor-${detailIndex + 1}` : "advisors";
    const coverage = projectSearchCoverage(profile.latestSignals.projectSearches, evidence, row.advisor_id || row.advisorId);
    return `<tr><td><a href="#${anchor}"><strong>${html(row.name || row.advisorName || row.advisor_id)}</strong></a><br>${html(text(profile.identity.currentInstitution || row.school || row.schoolName))}${discovery ? "" : `<br>${html(text([row.program, row.degree, row.intake]))}`}</td>
<td>${html(label("fit", profile.researchQuestionFit.status))}<br>${html(text(profile.researchMainline.longTermQuestion || profile.researchQuestionFit.reasons[0]))}${sources(profile.researchQuestionFit.sourceIds, evidence)}</td>
<td><a href="#${anchor === "advisors" ? anchor : `${anchor}-d`}">${html(coverage.summary)}</a><br>${profile.latestSignals.projects.length} 条已登记项目</td>
<td>${html(text([profile.fitBoundary, profile.keyUnknowns[0]].filter(Boolean)))}</td></tr>`;
  }).join("")}</tbody></table></div>`;
}

function sourceAppendix(evidence, advisors) {
  const groups = new Map();
  const names = new Map(advisors.map((row) => [row.advisor_id || row.advisorId, row.name || row.advisorName]));
  evidence.forEach((row, index) => { const key = urlKey(sourceUrl(row)) || `missing-${index}`;
    const group = groups.get(key) || []; group.push({ row, index }); groups.set(key, group); });
  if (!evidence.length) return `<p>尚未保存可核验来源。</p>`;
  return `<h3>来源原文与查阅记录</h3><p class="muted">同一网页集中展示；各项事实的核验情况分别保留。核实一项事实不代表该网页能支持所有结论。</p>${[...groups.values()].map((group) => {
    const source = group.find(({ row }) => row.citation_label)?.row || group[0].row;
    return `<details class="source-detail"><summary>${html(citationLabel(source))}</summary><p>${link(sourceUrl(source), citationLabel(source))}</p>
${group.map(({ row, index }) => `<div id="evidence-${index + 1}" class="source-claim"><p><strong>${html(names.get(row.entity_id || row.entity) || "相关记录")} · ${html(text(row.status || "not_checked"))}</strong>（${html(text(row.claim_type || row.claimType || "fact"))}）</p>
<p>${html(text(row.claim || row.finding || row.value || row.excerpt))}</p>
${facts([["网页查阅日期", row.accessed_at || row.accessedAt || "未记录"], ["页面更新时间", row.source_updated_at || "页面未注明"],
...(row.intake || row.applicable_intake ? [["适用招生批次", row.intake || row.applicable_intake]] : []),
...(row.excerpt ? [["原文支持片段", row.excerpt]] : []),
...(row.limitations || row.failure_reason ? [["仍有的限制", row.limitations || row.failure_reason]] : [])])}
<details class="technical"><summary>技术记录（复核用）</summary><pre>${html(JSON.stringify(row, null, 2))}</pre></details></div>`).join("")}</details>`;
  }).join("")}`;
}

// Add mobile labels to our own generated tables; external text is already escaped.
function responsiveTables(report) {
  return report.replace(/(<table[^>]*><thead>[\s\S]*?<\/thead>)(<tbody>[\s\S]*?<\/tbody>)/g, (all, head, body) => {
    const headings = [...head.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((match) => match[1].replace(/<[^>]*>/g, ""));
    return head + body.replace(/<tr>([\s\S]*?)<\/tr>/g, (row, cells) => { let index = 0;
      return `<tr>${cells.replace(/<td>/g, () => `<td data-label="${headings[index++] || "内容"}">`)}</tr>`;
    });
  });
}

const REPORT_STYLE = `
*{box-sizing:border-box}html{scroll-padding-top:24px}body{max-width:1000px;margin:auto;padding:48px 28px;color:#202124;background:#fff;font:17px/1.7 system-ui,-apple-system,"Segoe UI",sans-serif;overflow-wrap:anywhere}
h1{font-size:30px;line-height:1.35;margin:12px 0 20px}h2{font-size:24px;margin:48px 0 20px;border-bottom:1px solid #ddd;padding-bottom:10px}h3{font-size:22px;margin:32px 0 14px}h4{font-size:19px;margin:28px 0 14px}h5{font-size:17px;margin:24px 0 10px}h6{font-size:15px;margin:18px 0 8px}p{margin:10px 0}a{color:#185a8d;text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:2px solid #185a8d;outline-offset:4px}
.muted,.sources,.status-line{color:#555;font-size:14px}.sources{display:inline-block;margin-top:4px}.module{margin:24px 0;padding-top:4px;border-top:1px solid #e5e5e5}article{padding:0 0 30px;margin:32px 0 0;border-bottom:1px solid #aaa}dl{margin:12px 0}dl>div{display:grid;grid-template-columns:190px minmax(0,1fr);gap:20px;margin:14px 0}dt{font-weight:600}dd{margin:0;min-width:0}table{border-collapse:collapse;width:100%;font-size:14px;table-layout:fixed}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:12px 10px}th{font-weight:600}th:first-child,td:first-child{padding-left:0}.table-wrap{max-width:100%}li{margin:12px 0}ul,ol{padding-left:24px}details{margin:14px 0}summary{cursor:pointer;font-weight:600}details>p,details>div{margin-left:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.source-detail{border-bottom:1px solid #e5e5e5;padding:10px 0}.source-claim{border-top:1px solid #eee;padding-top:8px}.search-record{margin:18px 0}.person-entry{margin:24px 0;padding:0 0 24px;border-bottom:1px solid #e5e5e5}.person-entry:last-child{border-bottom:0;padding-bottom:0}.person-heading{display:flex;align-items:baseline;gap:8px 16px;flex-wrap:wrap;margin:0 0 6px}.person-heading h5,.person-heading h6{font-size:18px;margin:0;font-weight:600}.person-meta,.person-role{font-size:14px;color:#555}.person-meta{margin:4px 0 12px}.field-label{display:block;font-size:14px;color:#555;margin-bottom:3px}.person-work h6{font-weight:500;color:#555}.works{padding-left:20px}.works li{margin:14px 0}.person-entry details{margin:12px 0}.sources{margin-left:4px}nav{display:flex;gap:20px;flex-wrap:wrap;font-size:14px;margin:24px 0}
@media(max-width:700px){body{padding:24px 16px;font-size:16px}h1{font-size:25px}h2{font-size:21px}dl>div{grid-template-columns:1fr;gap:3px}table,tbody,tr,td{display:block;width:100%}thead{display:none}tr{border-bottom:1px solid #bbb;padding:12px 0}td{border:0;padding:6px 0}td:before{content:attr(data-label);display:block;font-weight:600;margin-bottom:2px}details>p,details>div{margin-left:0}}
@media print{body{max-width:none;padding:0;font-size:11pt}nav,.technical{display:none}h2,h3,h4,h5,h6{break-after:avoid}tr,.source-claim{break-inside:avoid}a{color:#185a8d}details{display:block}details>*{display:block}details::details-content{content-visibility:visible;display:block}summary{list-style:none}.source-detail{break-inside:auto}table{font-size:10pt}}
/* Module identity is consistent across advisors, with text and numbering as well as color. */
.advisor>h3{font-size:28px;border-top:2px solid #354352;padding-top:22px;margin-top:52px}
.module{margin:40px 0;border:0;padding:0}.module>h4{display:flex;gap:14px;align-items:baseline;background:var(--module-bg,#f1f3f5);border-left:3px solid var(--module-edge,#687785);padding:12px 16px;margin:0 0 22px;color:#202c38}
.module-a{--module-bg:#edf3fa;--module-edge:#6685a8}.module-b{--module-bg:#edf6f3;--module-edge:#5f8b80}.module-c{--module-bg:#f3eff8;--module-edge:#89729d}.module-d{--module-bg:#fbf2e9;--module-edge:#ac8257}.module-e{--module-bg:#eff2f5;--module-edge:#758594}.module-number{font-size:14px;font-weight:600;font-variant-numeric:tabular-nums}
.report-toc{display:block;position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #dce1e6;margin:0 0 24px;font-size:14px;line-height:1.5}
.report-toc details{margin:0}.report-toc summary{padding:10px 8px}.report-toc a{display:block;padding:7px 10px;text-decoration:none;color:#414b56;border-left:2px solid transparent}.report-toc a:hover{background:#f3f5f7}.report-toc a[aria-current]{color:#185a8d;border-left-color:#185a8d;background:#edf3fa;font-weight:600}.report-toc .toc-content{margin:0;max-height:65vh;overflow-y:auto;overscroll-behavior:contain;padding:6px 0 12px}.report-toc .toc-advisor>div{margin:0 0 4px 12px}.report-toc .toc-advisor>summary{font-weight:600;overflow-wrap:anywhere}.report-toc .toc-advisor a{font-size:13px}.report-toc .toc-advisor>summary>a{display:inline;padding:2px 0;font-size:14px;border:0}.report-toc .toc-advisor>summary{padding-left:8px}
html{scroll-padding-top:76px}[id]:focus{outline:none}[id]:focus-visible{outline:2px solid #185a8d;outline-offset:5px}
@media(min-width:1200px){body{max-width:1340px;padding-right:300px}.report-toc{position:fixed;right:max(24px,calc((100vw - 1340px)/2 + 28px));top:50%;transform:translateY(-50%);width:240px;max-height:80vh;overflow-y:auto;border:0;border-left:1px solid #dce1e6;padding-left:12px;margin:0}.report-toc .toc-shell>summary{display:none}.report-toc .toc-content{max-height:none}html{scroll-padding-top:28px}}
@media print{body{max-width:none;padding:0}.report-toc{display:none!important}.module>h4{border:1px solid #aaa;border-left:3px solid #555;background:#f4f4f4;print-color-adjust:exact}.advisor>h3{margin-top:26px}}

`;

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
  let advisorRows = medical ? buildMedicalDiscoveryView(advisors, project) : advisors;
  const advisorFacts = new Map(advisors.map((row) => [row.advisor_id || row.advisorId, row]));
  const programById = new Map(programs.map((row) => [row.program_id || row.programId, row]));
  const programRows = compared.map((row) => {
    const program = programById.get(row.program_id || row.programId) || {};
    return { ...row, degree: row.degree || program.degree, intake: row.intake || program.intake,
      program: row.program || row.programNameEn || row.programNameZh || program.program_name_en || program.program_name_zh,
      programUrl: row.programUrl || program.program_url };
  });
  if (medical) advisorRows = advisorRows.map((row, index) => reportAdvisorRow(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project,
    programRows.filter((candidate) => (candidate.advisor_id || candidate.advisorId) === (row.advisor_id || row.advisorId))));
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
    <td>资格：${html(text(row.feasibility || "needs_confirmation"))}<br><span class="sources">${evidenceReferences(profileReferences([row.eligibilityEvidence, row.hardConstraintEvidence]), evidence)}</span><br>机会：${html(text(row.opportunityStatus || "unknown"))}<br><span class="sources">${evidenceReferences(profileReferences(row.opportunityEvidence), evidence)}</span><br>${html(row.comparisonGroup || "")}</td>
    <td>${sourcedValue(row.recommendedAction, evidence)}</td>
  </tr>`).join("")}</tbody></table></div>` : "<p>尚未映射真实博士项目。</p>";
  // Discovery lists advisors; application lists advisor–programme opportunities. Both use the same five-module overview.
  const overviewRows = discovery ? advisorRows : programRows;
  const missingGrantChecks = medical ? advisorRows.filter((row) => !projectSearchCoverage(row.evidenceProfile.latestSignals.projectSearches, evidence, row.advisor_id || row.advisorId).complete) : [];
  const missingDoctoralChecks = medical ? advisorRows.filter((row) => !doctoralCoverage(row.evidenceProfile.doctoralTrajectory, evidence)) : [];
  const completion = medical && missingGrantChecks.length ? "部分完成：基金检索尚有缺口" : medical && missingDoctoralChecks.length ? "部分完成：第一作者或实验室补查尚有缺口" : audit.completionTier === "complete" ? "已完成本轮设定范围的检索" : audit.completionTier === "blocked" ? "检索受阻" : "部分完成或完成情况未记录";
  const prose = (value, fallback) => typeof value === "string" && !/^[a-z0-9_]+$/i.test(value) ? value : fallback;
  const pageCount = new Set(evidence.map((row) => urlKey(sourceUrl(row))).filter(Boolean)).size;
  const pendingCount = evidence.filter((row) => ["partial", "inaccessible", "not_checked", "conflict", "stale"].includes(row.status)).length;
  const evidenceSection = `<section id="coverage"><h2>本次查了什么，还缺什么</h2>
${facts([["实际检索范围", prose(audit.searchCoverage || audit.coverage, `已保存 ${pageCount} 个来源网页的 ${evidence.length} 条主张；其中 ${pendingCount} 条仍有核验或访问限制。未记录完整地域覆盖范围。`)],
["候选发现方式", prose(audit.seedSummary, "候选发现方式尚未提供文字说明，已保存的查询过程见下方详情")],
["合作线索扩展", audit.networkRounds !== undefined ? `已记录 ${audit.networkRounds} 轮；轮次数不代表查全了所有导师` : "未记录扩展过程"],
["检索是否充分", prose(audit.saturation, "尚无充分的文字说明支持已查全；停止检索的记录见下方详情")],
["仍需补查", audit.limitations?.length ? audit.limitations : "请结合各导师的待核实事项阅读"]])}
${medical ? `<p>基金检索尚未完成或受限：${missingGrantChecks.length ? html(missingGrantChecks.map((row) => row.name || row.advisorName).join("、")) : "无；仅指已记录的数据库和查询范围"}。</p>` : ""}
${medical && missingDoctoralChecks.length ? `<p>第一作者或实验室补查尚未完成：${html(missingDoctoralChecks.map((row) => row.name || row.advisorName).join("、"))}。详见逐位博士指导情况。</p>` : ""}
<details class="technical"><summary>查询与工具记录（复核用）</summary>${coverage}</details>
${sourceAppendix(evidence, advisorRows)}
${historicalRanking ? `<details class="technical"><summary>历史比较记录（不用于当前顺序或申请判断）</summary><pre>${html(JSON.stringify(ranking, null, 2))}</pre></details>` : ""}</section>`;
  const head = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-${REPORT_NAV_HASH}'; base-uri 'none'; form-action 'none'">
<title>${html(subject(project))} — 导师调研</title>
<style>${REPORT_STYLE}</style></head>
<body>${reportNavigation(advisorRows.map(row => ({...row, ...(advisorFacts.get(row.advisor_id || row.advisorId) || {})})), medical)}<main><header><p class="muted">Boss Hunting · 导师调研</p><h1>${html(subject(project))}</h1>
${fixtureNotice ? `<p><strong>虚构示例 / FICTIONAL FIXTURE：</strong>${html(fixtureNotice)}</p>` : ""}
<p>${discovery ? "生物医学导师方向探索" : medical ? "生物医学导师申请筛选" : "导师与申请项目调研"} · ${html(project.target || "地区尚未确认")} · ${advisorRows.length} 位导师记录${medical && discovery ? "" : ` / ${programRows.length} 个真实项目机会`}</p>
${historicalRanking ? `<p><strong>历史比较待复核：</strong>已有 ${rankings.length} 条比较记录的调查确认已失效或不适用于当前范围。保留研究和来源痕迹；当前按稳定名称展示，申请资格待重新核对。</p>` : ""}
<p class="muted">${medical ? "按研究问题的相关性和持续研究情况展示，列表顺序不是导师质量排名。未知不代表不符合；没有综合导师分、引用量排名、录取概率或培养成功率。" : "结论依据共享记录；申请条件、名额与资金在行动前需要按项目批次重核。"}</p>${medical ? `<p><strong>本轮完成情况：</strong>${html(completion)}</p>` : ""}</header>`;
  if (!medical) {
    return responsiveTables(`${head}
<section id="requirements"><h2>本次找导师的要求</h2>${facts([["研究兴趣", project.interests], ["目标学位 / 批次", [project.degree, project.season]], ["硬约束", project.hardConstraints]])}</section>
<section id="overview"><h2>候选比较与真实项目入口</h2>${genericTable}${programDetails}</section>
<section id="advisors"><h2>导师详情</h2>${advisorRows.length ? advisorRows.map((row, index) => advisorSection(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project, programRows, evidence)).join("") : "<p>尚无导师事实记录。</p>"}</section>
${evidenceSection}
<p class="muted">本报告由本地共享记录生成，不会访问网页、发送邮件或启动申请材料。</p></main><script id="report-navigation">${REPORT_NAV_SCRIPT}</script></body></html>`);
  }
  const optionalProfile = [
    ["研究对象 / 尺度", [profile.researchObjects, profile.researchScales]],
    ["研究范式 / 方法偏好", [profile.researchModes, profile.methodPreferences]],
  ].filter(([, value]) => value.some((items) => Array.isArray(items) && items.length));
  return responsiveTables(`${head}
<section id="requirements"><h2>本次找导师的要求</h2>${facts([
  ["生物医学领域", profile.fields],
  ["疾病 / 机制与科学问题", [profile.diseaseScope, profile.diseasesOrMechanisms, profile.researchQuestions]],
  ["目标国家 / 地区", profile.regions],
  ...optionalProfile,
  ["可接受相邻方向 / 排除项", [profile.adjacentInterests, profile.exclusions]],
])}</section>
<section id="overview"><h2>导师简短对照</h2>${medicalOverviewTable(overviewRows, evidence, discovery, advisorRows)}${programDetails}</section>
<section id="advisors"><h2>逐位导师详情</h2>${advisorRows.length ? advisorRows.map((row, index) => medicalAdvisorSection(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project, programRows.filter((candidate) => (candidate.advisor_id || candidate.advisorId) === (row.advisor_id || row.advisorId)), evidence)).join("") : "<p>尚无导师事实记录。</p>"}</section>
${evidenceSection}
<p class="muted">本报告由本地共享记录生成，不会访问网页、发送邮件或启动申请材料。项目记录说明科研支撑，不说明博士生个人资助；公开培养样本没有分母时不计算成功率；未在公开库中找到不等于没有。</p></main><script id="report-navigation">${REPORT_NAV_SCRIPT}</script></body></html>`);
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
