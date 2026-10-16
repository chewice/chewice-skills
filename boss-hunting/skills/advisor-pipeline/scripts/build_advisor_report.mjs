#!/usr/bin/env node

import { overlayDoctoralProfile, labWebsiteVerified, doctoralWindow, firstAuthorPaperState, firstAuthorSummary, firstAuthorIdentity } from "./doctoral-evidence.mjs";
import { academicTalkRows, talkWindow } from "./academic-events.mjs";
import { publicationReview, publicationRoleLabel, readableText } from "./publication-evidence.mjs";
import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { isExecutedDirectly } from "./direct-execution.mjs";
import { isMedicalRankingCurrent, normalizeProjectMetadata } from "./project-contract.mjs";
import {
  buildMedicalDiscoveryView, compareMedicalCandidates, hasReadableProjectCv, isMedicalEvidenceProfile,
  evidenceProfile, normalizeMedicalCandidate, validateMedicalCandidateMappings, mergeResearchMainline, identityCoverage,
} from "./medical-evidence.mjs";

function html(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

const WORDS = {
  verified: "已核实", partial: "部分核实", not_found: "在所查范围内未找到", not_checked: "未检索或未核验",
  inaccessible: "访问受阻", conflict: "来源存在冲突", stale: "信息可能过期", not_applicable: "不适用", unknown: "尚不清楚",
  found: "找到记录", official_database: "官方数据库", supplementary: "补充来源",
  corresponding_author: "通讯作者", co_corresponding_author: "共同通讯作者", co_first_author: "共同第一作者", first_author: "第一作者", last_author: "末位作者",
  coauthor: "共同作者", principal_investigator: "项目负责人", co_investigator: "项目参与者",
  research_seed: "原创研究论文", map_seed: "综述提供的线索", collaboration: "合作研究线索", research_neighbor: "相关研究线索", official_roster: "机构导师名录",
  citation: "引用关系", co_citation: "共同被引用", bibliographic_coupling: "引用相同文献", semantic_similarity: "研究内容相近", related_papers: "相关论文",
  single_disease: "单一疾病", multiple_diseases: "多种疾病", pan_cancer: "泛癌", unrestricted: "不限",
  PI: "项目负责人", co_PI: "共同项目负责人", active: "在研", completed: "已结束", pending: "待确认",
  eligible: "符合已核实条件", ineligible: "不符合已核实条件", needs_confirmation: "需要进一步确认", advertised: "已有公开招募信息",
  fact: "公开事实", interpretation: "基于证据的解释", question: "待核实问题",
  committee_led: "由项目委员会招生", rotation_led: "轮转后选导师", pi_led: "由导师招生", position_led: "公开岗位申请",
  verified_open: "已核实开放申请", verified_closed: "已核实关闭申请", pass: "已通过核验", fail: "不符合条件",
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
function citationChip(row) {
  const url = sourceUrl(row);
  if (!urlKey(url)) return '<span class="citation-state">未提供可用公开链接</span>';
  const types = {institutional_profile:"机构主页", official_profile:"机构主页", publication:"论文来源", conference_programme:"会议议程", event_announcement:"活动预告", event_report:"活动报道", recording:"报告录像", official_database:"官方数据库", grant_database:"基金数据库"};
  const full = citationLabel(row);
  const short = types[row.source_type] || (Array.from(full).length <= 10 ? full : "原始来源");
  const detail = `${full} · ${new URL(url).hostname} · 查阅：${row.accessed_at || row.accessedAt || "未记录"}`;
  return `<a href="${html(new URL(url).href)}" class="citation-chip" target="_blank" rel="noopener noreferrer" title="${html(detail)}" aria-label="${html(detail)}">${html(short)}<span aria-hidden="true"> ↗</span></a>`;
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
    const content = Object.hasOwn(value, "text") ? sourcedValue(value.text, evidence) : Object.entries(value).filter(([key]) => !["sourceIds", "source_ids"].includes(key))
      .map(([key, item]) => `${html(FIELD_LABELS[key] || key)}：${sourcedValue(item, evidence)}`).join("；");
    return `${content}${references?.length ? ` <span class="sources">${evidenceReferences(references, evidence, linkedUrls(content))}</span>` : ""}`;
  }
  // Link only URLs actually present in the record; never synthesize a source.
  return typeof value === "string" && /^https?:\/\/\S+$/i.test(value) ? link(value, value) : html(text(value));
}

function facts(items, evidence) {
  return `<dl>${items.map(([label, value, sourceIds]) => {
    const content = evidence ? sourcedValue(value, evidence) : html(text(value));
    const references = sourceIds?.length ? evidenceReferences(sourceIds, evidence || [], linkedUrls(content))
      : evidence && !content.includes("<a ") ? "对应来源待补，信息待核验" : "";
    return `<div><dt>${html(label)}</dt><dd>${content}${references ? ` <span class="sources">${references}</span>` : ""}</dd></div>`;
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
  const warnings = [];
  const links = [...groups].flatMap(([key, rows]) => {
    const states = [...new Set(rows.map((row) => row.status || "not_checked"))].filter((state) => state !== "verified");
    if (states.length) warnings.push(...states.map(text));
    if (excluded.has(key)) return [];
    const row = rows.find((item) => item.citation_label) || rows[0];
    return [citationChip(row)];
  });
  if (new Set(matched.map(({row}) => row.evidence_id || row.evidenceId)).size < sourceIds.size) warnings.push("部分来源关联尚待补齐");
  const extra = links.length > 2 ? `<button class="citation-more" type="button" hidden aria-expanded="false" aria-label="展开其余 ${links.length - 2} 个来源">+${links.length - 2}</button><span class="citation-extra">${links.slice(2).join(" ")}</span>` : "";
  return `${links.slice(0,2).join(" ")}${extra}${warnings.length ? ` <span class="citation-state">${html([...new Set(warnings)].join("、"))}</span>` : ""}`;
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
// The four reading sections are independent of optional author/talk supplements.
const REPORT_MODULES = [
  ["a", "01", "导师概况"], ["b", "02", "研究主线与相关性"],
  ["p", "03", "近五年一作／通讯论文"], ["u", "04", "关键待核实事项"],
];
function moduleHeading(index, key) {
  const [, number, title] = REPORT_MODULES.find(([id]) => id === key);
  return `<div class="module module-${key}" id="advisor-${index + 1}-${key}"><h4><span class="module-number">${number}</span>${title}</h4>`;
}
function reportNavigation(advisors, medical) {
  return `<nav class="report-toc" aria-label="报告目录"><p class="toc-brand"><span class="toc-mark" aria-hidden="true">A</span><span><strong>Advisor Atlas</strong><small>导师调研</small></span></p><details class="toc-shell" open><summary>报告目录</summary><div class="toc-content">
<a href="#requirements">查找要求</a><a href="#overview">导师对照</a><a href="#advisors">导师详情</a>
${advisors.map((row, index) => {
    const id = `advisor-${index + 1}`;
    const name = html(row.name || row.advisorName || row.advisor_id || row.advisorId || "姓名待核实");
    return medical ? `<details class="toc-advisor" data-advisor="${id}"><summary><a href="#${id}">${name}</a></summary><div>${REPORT_MODULES.map(([key, number, title]) => `<a href="#${id}-${key}">${number} ${title}</a>`).join("")}</div></details>` : `<a href="#${id}">${name}</a>`;
  }).join("")}
<a href="#coverage">检索与来源</a></div></details></nav>`;
}
const REPORT_NAV_SCRIPT = `(() => {
  document.querySelectorAll('.citation-more').forEach((button, index) => {
    const extra = button.nextElementSibling;
    extra.id = 'citation-extra-' + index;
    button.setAttribute('aria-controls', extra.id);
    extra.hidden = true; button.hidden = false;
    const label = button.textContent;
    button.addEventListener('click', () => {
      extra.hidden = !extra.hidden;
      button.setAttribute('aria-expanded', String(!extra.hidden));
      button.setAttribute('aria-label', extra.hidden ? '展开其余 ' + label.slice(1) + ' 个来源' : '收起其余来源');
      button.textContent = extra.hidden ? label : '收起';
    });
  });
  const nav = document.querySelector('.report-toc');
  if (!nav) return;
  const shell = nav.querySelector('.toc-shell');
  const desktop = matchMedia('(min-width:1200px)');
  const links = [...nav.querySelectorAll('a[href^="#"]')];
  const targets = links.map(link => document.getElementById(link.hash.slice(1)));
  const groups = [...nav.querySelectorAll('.toc-advisor')];
  const scrollOffset = () => { document.documentElement.style.scrollPaddingTop = desktop.matches ? '28px' : (nav.getBoundingClientRect().height + 16) + 'px'; };
  const resize = () => { shell.open = desktop.matches; scrollOffset(); };
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
        const scroller = nav.querySelector('.toc-content');
        const box = scroller.getBoundingClientRect();
        const item = links[current].getBoundingClientRect();
        if (item.top < box.top + 12) scroller.scrollTop += item.top - box.top - 12;
        else if (item.bottom > box.bottom - 12) scroller.scrollTop += item.bottom - box.bottom + 12;
      }
    }
  };
  const schedule = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(update); } };
  addEventListener('scroll', schedule, {passive:true}); addEventListener('resize', schedule);
  nav.addEventListener('focusout', schedule);
  nav.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    if (!desktop.matches) { shell.open = false; scrollOffset(); }
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
};

function label(group, value) {
  return LABELS[group]?.[value] || value || "尚未核实";
}

function sources(ids, evidence, excludedUrls = []) {
  if (!ids?.length) return "";
  const content = evidenceReferences(ids, evidence, excludedUrls);
  return content ? `<span class="sources">${content}</span>` : "";
}

function human(value) {
  const result = readableText(value);
  return WORDS[result] || result;
}

function proseItems(values) {
  const items = [...new Set(values.flatMap(value => Array.isArray(value) ? value : [value]).map(human).filter(Boolean))];
  return items.filter(item => !items.some(other => other.length > item.length && other.includes(item)));
}

function coreIdentityCheck(row, evidence) {
  const check = identityCoverage(row, evidence);
  const fields = check.fields.filter(field => !["doctoralSupervisionLink", "researchPositioning"].includes(field.field));
  return { complete: fields.every(field => field.complete), fields, gaps: fields.filter(field => !field.complete) };
}

function workItem(work, evidence, pendingReason = "") {
  const role = publicationRoleLabel(work);
  const meta = [work.date || work.publicationDate || work.year, work.venue || work.journal,
    role && role !== "署名待核验" ? `导师署名${pendingReason ? "（待核验）" : ""}：${role}` : null,
    work.relationToMainline ? `相关性：${human(work.relationToMainline)}` : null,
    work.isPreprint ? "预印本（未经同行评审）" : null, human(work.publicationStatus),
    work.isPreprint && !work.publicationStatus ? "期刊发表状态待核实" : null]
    .filter(Boolean).map(html).join(" · ");
  const external = work.url || (work.doi ? `https://doi.org/${String(work.doi).replace(/^https?:\/\/doi\.org\//i, "")}` : null);
  const anchor = external ? link(external, work.title || external) : "";
  const heading = anchor.startsWith("<a ") ? anchor : `${html(work.title || "标题待核验")}${external ? "（未提供可用公开链接）" : ""}`;
  const refs = sources([...new Set([...(work.sourceIds || []), ...(work.roleSourceIds || [])])], evidence, [external]);
  return `<li>${heading}${refs ? ` ${refs}` : ""}${meta ? `<br><span class="muted">${meta}</span>` : ""}${pendingReason ? `<br><span class="citation-state">未纳入：${html(human(pendingReason))}</span>` : ""}</li>`;
}

function workList(works, evidence, empty) {
  return works.length ? `<ul class="works">${works.map(work => workItem(work, evidence)).join("")}</ul>` : `<p class="muted">${html(empty)}</p>`;
}

function publicationsSection(review, evidence) {
  const remaining = review.papers.slice(3);
  const years = [...new Set(remaining.map(work => String(work.date || work.publicationDate || work.year || "日期待核实").slice(0, 4)))];
  const covered = proseItems(review.searches.map(search => search.database || search.sourceName || search.source));
  const scope = review.window ? `${review.window.start} 至 ${review.window.end}` : "尚未记录有效的五年时间范围";
  return `<p class="publication-summary">${html(scope)} · 已核实 ${review.papers.length} 篇。${review.searchComplete ? "已完成所列来源及分页的核查。" : "检索或署名核验仍有缺口。"}</p>
${covered.length ? `<p class="muted">已查来源：${html(covered.join("、"))}。检索覆盖所列来源，不保证穷尽全部发表记录。</p>` : ""}
${workList(review.papers.slice(0, 3), evidence, "目前尚无同时满足日期、导师署名与来源核验要求的论文。")}
${remaining.length ? `<details class="publication-list"><summary>其余已核实论文（${remaining.length} 篇，按年份）</summary>${years.map(year => `<h5>${html(year)}</h5>${workList(remaining.filter(work => String(work.date || work.publicationDate || work.year || "日期待核实").slice(0, 4) === year), evidence, "")}`).join("")}</details>` : ""}
${review.pending.length ? `<details class="pending-publications"><summary>待核验或未纳入的论文线索（${review.pending.length} 条）</summary><p class="muted">以下线索不计入已核实论文数。</p><ul class="works">${review.pending.map(({paper, reason}) => workItem(paper, evidence, reason)).join("")}</ul></details>` : ""}`;
}

function academicTalkSection(mainline, evidence, advisorId) {
  const rows = academicTalkRows(mainline, evidence, advisorId);
  if (!rows.length) return "";
  const window = talkWindow(mainline.talkSearches);
  return `<details class="supplement"><summary>学术会议与演讲（补充信息，${rows.length} 条）</summary><p class="muted">${window ? `查阅范围：${html(window.start)} 至 ${html(window.end)}。` : ""}议程安排不等于已经报告。</p>
${["近两年活动","即将举行","日期或检索范围待核实","范围外记录"].map(group => {
    const selected = rows.filter(row => row.timing === group);
    return selected.length ? `<h5>${group}</h5><ul class="academic-talks">${selected.map(row => `<li><strong>${html(row.eventName || "活动名称未记录")}</strong> · ${html(row.date || "日期待核实")}<br>
${html(row.roleLabel)} · ${html(row.status)}<br>${row.title === row.talkTitle && urlKey(row.url) ? link(row.url,row.title) : html(row.title)} ${sources(row.sourceIds,evidence,row.title === row.talkTitle && urlKey(row.url) ? [row.url] : [])}
${row.titleZh ? `<br>中文译名：${html(row.titleZh)}` : ""}
${row.limitations ? `<br>${html(human(row.limitations))}` : ""}
${row.url && row.title !== row.talkTitle ? ` ${link(row.url,"活动页面")}` : ""}</li>`).join("")}</ul>` : "";
  }).join("")}</details>`;
}

function doctoralList(people, evidence) {
  return `<ul>${people.map(person => `<li><strong>${html(person.name || "姓名未公开")}</strong>${person.degreeOrYear ? ` · ${html(person.degreeOrYear)}` : ""}
${proseItems([person.topic, person.relationToMainline, person.supervisionEvidence, person.firstDestination, person.latestPublicRole, person.informationDate]).map(item => `<br>${html(item)}`).join("")}
${person.sourceIds.length ? `<br>${sources(person.sourceIds, evidence)}` : ""}</li>`).join("")}</ul>`;
}

function authorAppendix(doctoral, evidence) {
  const window = doctoralWindow(doctoral);
  const profiles = doctoral.firstAuthorProfiles.filter(person => person.papers.length || firstAuthorIdentity(person, evidence) || person.researchSummary);
  if (!profiles.length && !doctoral.currentDoctoral.length && !doctoral.formerDoctoral.length) return "";
  const people = profiles.map(person => {
    const eligible = person.papers.filter(paper => firstAuthorPaperState(paper, window, evidence) === "eligible");
    const pending = person.papers.filter(paper => firstAuthorPaperState(paper, window, evidence) !== "eligible");
    const summary = firstAuthorSummary(person, window, evidence);
    return `<div class="person-entry first-author"><header class="person-heading"><h5>${html(person.name || "姓名待核实")}</h5>${firstAuthorIdentity(person, evidence) ? `<span class="person-role">${html(firstAuthorIdentity(person, evidence))}</span>` : ""}</header>
${person.identitySourceIds.length ? `<p class="person-meta">${sources(person.identitySourceIds, evidence)}</p>` : ""}
${person.researchSummary ? `<p>${html(summary)}${person.summarySourceIds.length ? ` ${sources(person.summarySourceIds, evidence)}` : ""}</p>` : ""}
${eligible.length ? workList(eligible.map(paper => ({...paper, advisorRoles:[paper.advisorRole]})), evidence, "") : ""}
${pending.length ? `<details><summary>关联论文仍需核验（${pending.length} 条）</summary><ul class="works">${pending.map(paper => workItem({...paper, advisorRoles:[paper.advisorRole]}, evidence, firstAuthorPaperState(paper, window, evidence))).join("")}</ul></details>` : ""}</div>`;
  }).join("");
  return `<details class="author-appendix"><summary>作者附录（可选补充）</summary><p class="muted">第一作者学历或身份信息不影响导师论文纳入；共同署名本身不证明指导关系。</p>${people}
${doctoral.currentDoctoral.length ? `<h5>已有的当前博士生信息</h5>${doctoralList(doctoral.currentDoctoral, evidence)}` : ""}
${doctoral.formerDoctoral.length ? `<h5>已有的毕业博士信息</h5>${doctoralList(doctoral.formerDoctoral, evidence)}` : ""}
${doctoral.emergingPiNote ? `<p>${html(human(doctoral.emergingPiNote))}</p>` : ""}</details>`;
}

function unresolvedItems(row, evidence, review, discovery) {
  const profile = row.evidenceProfile;
  const selected = proseItems([profile.keyUnknowns]).flatMap(item => item
    .replace(/Finder阶段未深查三模块|用户选定后补充三模块背景调研|用户选择后再查完整近五年通讯论文与作者信息/g, "")
    .split(/[；;]/).map(part => part.replace(/^[\s，,。]+|[\s，,。]+$/g, "")).filter(Boolean))
    .filter(item => !discovery || !/招生|招生名额|申请批次|博士项目映射|doctoral.*(?:supervision|program)|programme.*(?:intake|terms)|program.*(?:intake|terms)/i.test(item));
  return proseItems([...selected, ...coreIdentityCheck(row, evidence).gaps.map(gap => `${gap.label}：${gap.reason}`),
    ...(!review.searchComplete && !review.limitations.length ? [review.searches.length ? "近五年论文的检索或署名核验尚未完成，详见论文清单。" : "近五年论文检索记录尚未补齐。"] : []), review.limitations]);
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
  // Preserve advisor-level publications when an application snapshot is older.
  const stored = evidenceProfile(advisor);
  const storedMainline = normalizeMedicalCandidate(advisor, project, index).evidenceProfile.researchMainline;
  const projectedMainline = normalizeMedicalCandidate(factsRow, project, index).evidenceProfile.researchMainline;
  factsRow.evidenceProfile.researchMainline = mergeResearchMainline(storedMainline, projectedMainline);
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
  const name = row.name || row.advisorName || "姓名待核实";
  const identity = profile.identity;
  const mainline = profile.researchMainline;
  const doctoral = profile.doctoralTrajectory;
  const discovery = project.searchMode === "discovery";
  const review = publicationReview(mainline, evidence, advisorId);
  const officialUrl = identity.officialProfileUrl || row.homepage || row.advisorHomepage;
  const identityCheck = coreIdentityCheck(row, evidence);
  const positionGap = identityCheck.gaps.find(field => field.field === "currentPosition");
  const institution = human(identity.currentInstitution || row.school || row.schoolName);
  const department = human(identity.department);
  const position = human(identity.currentPosition);
  const region = human(row.region || row.country || row.countryName);
  const identityDetails = [
    department && department !== institution ? `<span class="advisor-department">${html(department)}</span>` : "",
    position ? `<span class="advisor-position">${html(position)}</span>` : "",
    position && positionGap ? `<span class="identity-note" title="${html(positionGap.reason)}">${positionGap.reason.startsWith("来源存在冲突") ? "职称来源冲突" : "职称待核实"}</span>` : "",
    region ? `<span class="advisor-region">地区：${html(region)}</span>` : "",
  ].filter(Boolean);
  const labs = doctoral.labWebsites.filter(site => site.url).map(site => `<span>${link(site.url, site.title)}${labWebsiteVerified(site, evidence) ? "" : "（导师归属待核实）"}</span>`);
  const identityRefs = [...new Set([...identity.sourceIds, ...identityCheck.fields.flatMap(field => field.sourceIds), ...doctoral.labWebsites.flatMap(site => site.sourceIds)])];
  const mainlineText = proseItems([mainline.longTermQuestion || identity.researchPositioning, mainline.continuingThemes,
    mainline.newDirections.length ? `近期拓展：${human(mainline.newDirections)}` : "", mainline.recentShift ? `研究转向：${human(mainline.recentShift)}` : ""]);
  const continuity = proseItems([profile.researchRouteContinuity.reasons]);
  const researchIds = [...new Set([...mainline.sourceIds, ...profile.researchRouteContinuity.sourceIds])];
  const unresolved = unresolvedItems(row, evidence, review, discovery);
  const applicationEntry = !discovery && opportunities.length ? `<details class="application-entry"><summary>真实申请入口（申请筛选模式）</summary>${facts([["项目 / 学位 / 批次 / 路径", opportunities.map(candidate => ({
    program: candidate.program || candidate.programNameEn || candidate.programNameZh, degree: candidate.degree, intake: candidate.intake,
    pathway: candidate.applicationPathway, eligibility: candidate.feasibility, opportunity: candidate.opportunityStatus, url: candidate.programUrl,
    sourceIds: profileReferences([candidate.eligibilityEvidence, candidate.hardConstraintEvidence, candidate.opportunityEvidence]),
  }))]], evidence)}</details>` : "";
  return `<article id="advisor-${index + 1}" class="advisor"><h3>${html(name)}</h3>
${moduleHeading(index, "a")}<div class="advisor-affiliation">${institution ? `<p class="advisor-institution">${html(institution)}</p>` : ""}
${identityDetails.length ? `<p class="advisor-meta">${identityDetails.join(" ")}</p>` : ""}${!institution && !identityDetails.length ? '<p class="muted">任职信息待核实</p>' : ""}</div>
${evidenceStatusRow(profile)}
<p class="profile-links">${[officialUrl ? link(officialUrl, "机构导师介绍") : "", ...labs].filter(Boolean).join(" · ")}${identityRefs.length ? ` ${sources(identityRefs, evidence, [officialUrl, ...doctoral.labWebsites.map(site => site.url)])}` : ""}</p>
${identity.affiliationAsOf ? `<p class="muted">任职信息核对日期：${html(identity.affiliationAsOf)}</p>` : ""}</div>
${moduleHeading(index, "b")}<p class="research-mainline">${mainlineText.length ? mainlineText.map((item, itemIndex) => itemIndex === 0 ? `<strong class="research-question">${html(item)}</strong>` : html(item)).join("；") : "研究主线仍需核实"}${researchIds.length ? ` ${sources(researchIds, evidence)}` : ""}</p>
<p class="research-fit">与您的研究需求：<strong class="fit-label">${html(label("fit", profile.researchQuestionFit.status))}</strong>。${html(human(profile.researchQuestionFit.reasons))} ${sources(profile.researchQuestionFit.sourceIds, evidence, researchIds.map(id => sourceUrl(evidence.find(item => (item.evidence_id || item.evidenceId) === id) || {})))}</p>
${continuity.length ? `<p class="muted">${html(label("continuity", profile.researchRouteContinuity.status))}：${html(continuity.join("；"))}</p>` : ""}
${human(profile.fitBoundary) ? `<p class="research-boundary"><strong>相关性边界：</strong>${html(human(profile.fitBoundary))}</p>` : ""}</div>
${moduleHeading(index, "p")}${publicationsSection(review, evidence)}</div>
${moduleHeading(index, "u")}${unresolved.length ? `<ul>${unresolved.map(item => `<li>${html(item)}</li>`).join("")}</ul>` : `<p>本轮所列范围内未登记未解决事项。</p>`}
${profile.formalRecords.length ? `<p><strong>更正、撤稿或机构公告：</strong>${html(human(profile.formalRecords))}</p>` : ""}</div>
${authorAppendix(doctoral, evidence)}${academicTalkSection(mainline, evidence, advisorId)}${applicationEntry}</article>`;
}

function medicalOverviewTable(rows, evidence, discovery, advisors) {
  if (!rows.length) return `<p>尚无导师记录。</p>`;
  return `<div class="table-wrap"><table class="overview"><thead><tr><th>导师与机构</th><th>与需求的关系</th><th>近五年论文</th><th>需要进一步确认</th></tr></thead><tbody>${rows.map(row => {
    const detailIndex = advisors.findIndex(advisor => (advisor.advisor_id || advisor.advisorId) === (row.advisor_id || row.advisorId));
    const advisor = advisors[detailIndex] || row;
    const profile = advisor.evidenceProfile;
    const review = publicationReview(profile.researchMainline, evidence, advisor.advisor_id || advisor.advisorId);
    const anchor = detailIndex >= 0 ? `advisor-${detailIndex + 1}` : "advisors";
    const gaps = unresolvedItems(advisor, evidence, review, discovery);
    return `<tr><td><a href="#${anchor}"><strong>${html(row.name || row.advisorName || "姓名待核实")}</strong></a><br>${html(human(profile.identity.currentInstitution || row.school || row.schoolName))}${discovery ? "" : `<br>${html(text([row.program, row.degree, row.intake]))}`}</td>
<td>${html(label("fit", profile.researchQuestionFit.status))}<br>${proseItems([profile.researchQuestionFit.reasons, profile.fitBoundary]).map(html).join("<br>")}${sources(profile.researchQuestionFit.sourceIds, evidence)}</td>
<td><a href="#${anchor === "advisors" ? anchor : `${anchor}-p`}">已核实 ${review.papers.length} 篇</a>${review.pending.length ? `<br>${review.pending.length} 条线索未纳入` : ""}<br>${review.searchComplete ? "所列来源检索完成" : "仍有检索或核验缺口"}</td>
<td>${html(gaps.slice(0, 2).join("；") || "本轮未登记未解决事项")}${gaps.length > 2 ? `<br><a href="#${anchor}-u">另有 ${gaps.length - 2} 项</a>` : ""}</td></tr>`;
  }).join("")}</tbody></table></div>`;
}

function sourceAppendix(evidence, advisors, medical = false) {
  const groups = new Map();
  const names = new Map(advisors.map(row => [row.advisor_id || row.advisorId, row.name || row.advisorName]));
  evidence.forEach((row, index) => { const key = urlKey(sourceUrl(row)) || `missing-${index}`;
    const group = groups.get(key) || []; group.push({ row, index }); groups.set(key, group); });
  if (!evidence.length) return `<p>尚未保存可核验来源。</p>`;
  const content = `<p class="muted">同一网页集中展示；各项事实的核验情况分别保留。核实一项事实不代表该网页能支持所有结论。</p>${[...groups.values()].map(group => {
    const source = group.find(({ row }) => row.citation_label)?.row || group[0].row;
    return `<details class="source-detail"><summary>${html(citationLabel(source))}</summary><p>${link(sourceUrl(source), citationLabel(source))}</p>
${group.map(({ row, index }) => `<div id="evidence-${index + 1}" class="source-claim"><p><strong>${html(names.get(row.entity_id || row.entity) || "相关记录")} · ${html(text(row.status || "not_checked"))}</strong></p>
<p>${html(medical ? human(row.claim || row.finding || row.value || row.excerpt) : text(row.claim || row.finding || row.value || row.excerpt))}</p>
${facts([...(row.accessed_at || row.accessedAt ? [["网页查阅日期", row.accessed_at || row.accessedAt]] : []), ...(row.source_updated_at ? [["页面更新时间", row.source_updated_at]] : []),
...(row.intake || row.applicable_intake ? [["适用招生批次", row.intake || row.applicable_intake]] : []),
...(row.excerpt && row.excerpt !== row.claim ? [["原文支持片段", row.excerpt]] : []),
...(row.limitations || row.failure_reason ? [["仍有的限制", human(row.limitations || row.failure_reason)]] : [])])}
${medical ? "" : `<details class="technical"><summary>技术记录（复核用）</summary><pre>${html(JSON.stringify(row, null, 2))}</pre></details>`}</div>`).join("")}</details>`;
  }).join("")}`;
  return medical ? `<details class="source-appendix"><summary>来源原文与查阅记录（${groups.size} 个网页）</summary>${content}</details>` : `<h3>来源原文与查阅记录</h3>${content}`;
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
:root{--ink:#263445;--muted:#5b6778;--line:#dce5ed;--canvas:#fff;--card:#fff;--accent:#245780;--accent-dark:#1e3a5f;--accent-soft:#edf4fb;--green:#166354;--green-soft:#edf7f3;--amber:#865515;--amber-soft:#fff5e4;--sidebar:#f1f5f9;--shadow:0 10px 30px rgba(30,58,95,.045)}
*{box-sizing:border-box}html{scroll-padding-top:24px;background:var(--canvas)}
body{margin:0;padding:20px 18px 48px;color:var(--ink);background:var(--canvas);font:17px/1.7 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased;overflow-wrap:anywhere}
main{max-width:1000px;margin:0 auto}
.eyebrow{margin:0 0 8px;color:var(--accent);font-size:11px;font-weight:800;letter-spacing:.16em}
header,main>section{padding:28px 32px;margin:0 0 14px;border:1px solid var(--line);border-radius:18px;background:var(--card);box-shadow:var(--shadow)}
h1{margin:6px 0 14px;color:var(--accent-dark);font-size:36px;font-weight:700;line-height:1.25;letter-spacing:-.02em}
h2{margin:0 0 18px;padding:0;border:0;color:var(--accent-dark);font-size:24px;font-weight:650;line-height:1.35}
h3{margin:8px 0 12px;color:var(--accent-dark);font-size:26px;font-weight:650;line-height:1.3}
h4{margin:22px 0 12px;font-size:19px;font-weight:650;line-height:1.4}
h5{margin:20px 0 8px;font-size:16px}h6{margin:16px 0 6px;font-size:15px}p{margin:10px 0}
a{color:var(--accent);text-underline-offset:3px}a:hover{color:var(--accent-dark)}
a:focus-visible,button:focus-visible,summary:focus-visible,[id]:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
.muted,.sources,.status-line,.person-meta,.person-role,.field-label{color:var(--muted);font-size:14px}
.sources{display:inline;margin-inline-start:5px;line-height:1.9}
.citation-chip,.citation-more{display:inline-block;vertical-align:baseline;max-width:100%;padding:1px 8px;margin:2px 2px;border:1px solid #d5e1ec;border-radius:999px;background:#f3f6fa;color:#48617b;font:500 13px/1.7 ui-sans-serif,system-ui,sans-serif;text-decoration:none;cursor:pointer}
.citation-chip:hover,.citation-more:hover{background:#e5eef7;color:var(--accent-dark);border-color:#9cb7d0}
.citation-more[hidden],.citation-extra[hidden]{display:none}
.citation-state{color:var(--amber);font-size:13px;margin-inline-start:4px}
@media(pointer:coarse){.citation-chip,.citation-more{padding:5px 9px;min-height:32px}}.status-line{margin:0 0 8px}
header>p:last-of-type,.status-line{padding:8px 12px;border-radius:10px;background:var(--sidebar)}
article{padding:8px 0 4px;margin:28px 0 0;border:0}
.advisor>h3{margin:8px 0 18px;padding:0;border:0;color:var(--accent-dark);font-size:32px;font-weight:700;letter-spacing:-.015em}
.module{margin:18px 0;padding:20px 22px 18px;border:1px solid var(--line);border-radius:14px;background:var(--card);box-shadow:0 6px 18px rgba(30,58,95,.025)}
.module>h4{display:flex;gap:12px;align-items:center;margin:0 0 16px;padding:0 0 14px;border-bottom:1px solid var(--line);background:none;color:var(--ink)}
.module-number{display:inline-grid;place-items:center;min-width:32px;height:32px;border-radius:10px;background:var(--module-chip,var(--accent-soft));color:var(--module-ink,var(--accent-dark));font:700 12px/1 ui-sans-serif,system-ui,sans-serif;font-variant-numeric:tabular-nums}
.module-a{--module-chip:var(--accent-soft);--module-ink:var(--accent-dark)}.module-b{--module-chip:var(--green-soft);--module-ink:var(--green)}.module-p{--module-chip:var(--sidebar);--module-ink:var(--muted)}.module-u{--module-chip:var(--amber-soft);--module-ink:var(--amber);border-color:#e5d8bf}
.module-a>h4{color:var(--accent-dark)}.module-b>h4{color:var(--green)}.module-u>h4,.module-u li::marker{color:var(--amber)}
.advisor-affiliation{margin:0 0 16px}.advisor-institution{margin:0 0 8px;color:var(--accent-dark);font-size:18px;font-weight:600}
.advisor-meta{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px 12px;margin:0;font-size:16px;line-height:1.65}.advisor-department{flex-basis:100%}.advisor-region{color:var(--muted)}
.advisor-position{min-width:0;max-width:100%;padding:3px 10px;border:1px solid #d5e4f3;border-radius:7px;background:var(--accent-soft);color:var(--accent-dark);font-weight:600}
.identity-note{padding:3px 8px;border:1px solid #e5d8bf;border-radius:7px;background:var(--amber-soft);color:var(--amber);font-size:14px;font-weight:600}
.profile-links{margin:12px 0;font-size:15px}.profile-links>a{font-weight:600}
.research-mainline{margin:0 0 18px;padding:16px 18px;border-left:3px solid var(--green);border-radius:0 10px 10px 0;background:var(--green-soft);color:var(--green);font-size:20px;line-height:1.75}.research-question{font-weight:650}
.research-fit{font-size:17px}.fit-label{color:var(--accent-dark);font-weight:700}
.research-boundary{padding:12px 16px;border-left:3px solid var(--amber);border-radius:0 8px 8px 0;background:#fffaf1;font-size:16px}.research-boundary>strong{color:var(--amber)}
dl{margin:12px 0}dl>div{display:grid;grid-template-columns:190px minmax(0,1fr);gap:20px;margin:14px 0}dt{font-weight:650}dd{margin:0;min-width:0}
.table-wrap{max-width:100%;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:14px;table-layout:fixed}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:12px 14px}th{color:var(--accent-dark);background:var(--sidebar);font-weight:650}tr:last-child td{border-bottom:0}
.overview td:first-child>a{font-size:17px;color:var(--accent-dark)}.overview td:first-child>a strong{font-weight:700}.overview tbody tr:nth-child(even){background:#f8fafc}
li{margin:12px 0}ul,ol{padding-left:22px}details{margin:14px 0}summary{cursor:pointer;font-weight:650}details>p,details>div{margin-left:16px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;padding:12px;border-radius:10px;background:var(--sidebar)}
.source-detail{border-bottom:1px solid var(--line);padding:10px 0}.source-claim{border-top:1px solid var(--line);padding-top:8px}.search-record{margin:18px 0}
.person-entry{margin:22px 0;padding:0 0 18px;border-bottom:1px solid var(--line)}.person-entry:last-child{border-bottom:0;padding-bottom:0}
.person-heading{display:flex;align-items:baseline;gap:8px 16px;flex-wrap:wrap;margin:0 0 6px}
.person-heading h5,.person-heading h6{margin:0;font-size:18px;font-weight:600;line-height:1.35}.person-meta{margin:4px 0 12px}.field-label{display:block;margin-bottom:3px}.person-work h6{font-weight:500}.works{padding-left:20px}.works li{margin:16px 0}.works li>a{font-size:17px;font-weight:600}.works li::marker{color:var(--muted)}.person-entry details{margin:12px 0}
.toc-brand{display:flex;align-items:center;gap:11px;margin:0 4px 18px;color:var(--ink)}
.toc-mark{width:35px;height:35px;border-radius:11px;display:grid;place-items:center;background:var(--accent-dark);color:#fff;font:italic 20px/1 Georgia,serif;box-shadow:0 6px 16px rgba(30,58,95,.15)}
.toc-brand strong{display:block;color:var(--accent-dark);font-size:16px;font-weight:650;line-height:1.2}.toc-brand small{display:block;margin-top:3px;color:var(--muted);font-size:11px;letter-spacing:.12em}
.report-toc{display:block;position:sticky;top:0;z-index:5;margin:0 0 16px;padding:16px 16px 10px;border:1px solid var(--line);border-radius:0 0 16px 16px;background:var(--sidebar);color:var(--ink);font-size:14px;line-height:1.5;box-shadow:0 10px 24px rgba(30,58,95,.06)}
.report-toc details{margin:0}.report-toc summary{padding:10px 8px;color:var(--muted)}
.report-toc a{display:block;padding:8px 12px;border:0;border-radius:10px;color:#46586e;text-decoration:none;transition:background .16s ease,color .16s ease}
.report-toc a:hover{background:#e3edf7;color:var(--accent-dark)}
.report-toc a[aria-current]{color:var(--accent-dark);background:#dfeaf6;box-shadow:inset 3px 0 0 var(--accent);font-weight:700}
.report-toc .toc-content{margin:0;max-height:65vh;overflow-y:auto;overscroll-behavior:contain;padding:4px 0 8px;scrollbar-width:thin;scrollbar-color:#a9bbcf transparent}
.report-toc .toc-advisor>div{margin:0 0 4px 8px}.report-toc .toc-advisor>summary{font-weight:600;overflow-wrap:anywhere;padding-left:8px}
.report-toc .toc-advisor a{font-size:13px}.report-toc .toc-advisor>summary>a{display:inline;padding:2px 0;font-size:14px;box-shadow:none}
html{scroll-padding-top:76px}
@media(max-width:700px){body{padding:12px 12px 36px;font-size:16px}h1{font-size:28px}h2{font-size:21px}header,main>section{padding:20px 12px}.advisor>h3{font-size:26px}.module{padding:18px 14px}.module>h4{font-size:18px;gap:10px}.research-mainline{padding:12px 14px;font-size:20px}.research-boundary{padding:10px 12px}dl>div{grid-template-columns:1fr;gap:3px}table,tbody,tr,td{display:block;width:100%}thead{display:none}tr{border-bottom:1px solid var(--line);padding:12px 0}td{border:0;padding:6px 14px}td:before{content:attr(data-label);display:block;color:var(--muted);font-weight:650;margin-bottom:2px}details>p,details>div{margin-left:0}.table-wrap{border:0;background:transparent}}
@media(min-width:1200px){body{padding:34px 36px 54px 280px}main{margin:0}.report-toc{position:fixed;left:16px;top:50%;transform:translateY(-50%);width:216px;max-height:70vh;overflow:hidden;padding:16px 12px;border:1px solid var(--line);border-radius:14px;margin:0;box-shadow:0 10px 24px rgba(30,58,95,.08)}.report-toc .toc-shell>summary{display:none}.report-toc .toc-content{max-height:calc(70vh - 100px)}html{scroll-padding-top:28px}}
@media print{.citation-more{display:none!important}.citation-extra[hidden]{display:inline!important}.citation-chip{background:transparent;border-color:#ccc}html,body{background:#fff;color:var(--ink)}body{max-width:none;padding:0;font-size:11pt}nav,.technical,.report-toc{display:none!important}header,main>section,.module,.table-wrap{box-shadow:none;border-color:#ccc}h2,h3,h4,h5,h6{break-after:avoid}tr,.source-claim,.person-entry{break-inside:avoid}a{color:var(--accent-dark)}details{display:block}details>*{display:block}details::details-content{content-visibility:visible;display:block}summary{list-style:none}.source-detail{break-inside:auto}table{font-size:10pt}.advisor>h3{margin-top:20px}}
@page{margin:12mm}
@media print{.works>li{break-inside:avoid}.source-appendix:not([open])>:not(summary),.pending-publications:not([open])>:not(summary){display:none!important}}
@media print{h1{font-size:23pt}h2{font-size:17pt}.advisor>h3{font-size:20pt}.module>h4{font-size:13pt}.advisor-institution{font-size:12pt}.advisor-meta{font-size:10.5pt}.advisor-position{background:transparent;border-color:#aaa}.research-mainline{font-size:12pt;border-left-color:#777;background:transparent;color:var(--ink)}.research-boundary{font-size:10.5pt;background:transparent;border-left-color:#777}.research-fit,.works li>a{font-size:11pt}.muted,.status-line,.profile-links{font-size:9.5pt}.citation-chip,.citation-state{font-size:9pt}.overview tbody tr:nth-child(even){background:transparent}}
@media(prefers-reduced-motion:reduce){.report-toc a{transition:none}}
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
    ...(medical ? [["Seeds / 饱和", [audit.seedSummary, audit.saturation ? `饱和：${text(audit.saturation)}` : null].filter(Boolean).length
      ? [audit.seedSummary, audit.saturation ? `饱和：${text(audit.saturation)}` : null].filter(Boolean)
      : "未保存 seed / 饱和记录"]] : []),
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
  // Discovery lists advisors; application lists advisor–programme opportunities.
  const overviewRows = discovery ? advisorRows : programRows;
  const identityChecks = medical ? advisorRows.map(row => ({ row, ...coreIdentityCheck(row, evidence) })) : [];
  const missingIdentityChecks = identityChecks.filter(check => !check.complete);
  const publicationChecks = medical ? advisorRows.map(row => ({ row, ...publicationReview(row.evidenceProfile.researchMainline, evidence, row.advisor_id || row.advisorId) })) : [];
  const missingPublicationChecks = publicationChecks.filter(check => !check.searchComplete);
  const completion = missingIdentityChecks.length || missingPublicationChecks.length
    ? `部分完成：${[missingIdentityChecks.length ? "身份信息" : "", missingPublicationChecks.length ? "近五年论文检索或署名核验" : ""].filter(Boolean).join("、")}尚有缺口`
    : medical && advisorRows.length ? "已完成所列来源范围的身份与论文核查" : audit.completionTier === "blocked" ? "检索受阻" : "部分完成或完成情况未记录";
  const prose = (value, fallback) => typeof value === "string" && !/^[a-z0-9_]+$/i.test(value) ? value : fallback;
  const pageCount = new Set(evidence.map(row => urlKey(sourceUrl(row))).filter(Boolean)).size;
  const pendingCount = evidence.filter(row => ["partial", "inaccessible", "not_checked", "conflict", "stale"].includes(row.status)).length;
  const evidenceSection = `<section id="coverage"><h2>本次查了什么，还缺什么</h2>
${medical ? `<p>${html(prose(audit.searchCoverage || audit.coverage, `本轮包含 ${advisorRows.length} 位导师，保存了 ${pageCount} 个来源网页；${pendingCount} 条来源主张仍有核验或访问限制。`))}</p>
<p>论文检索范围、已核实数量和未纳入原因见各导师论文清单。检索记录仅支持所列来源的覆盖情况。</p>
${missingPublicationChecks.length ? `<p>论文检索或核验仍有缺口：${html(missingPublicationChecks.map(({row}) => row.name || row.advisorName || "姓名待核实").join("、"))}。</p>` : ""}
${audit.limitations?.length ? `<p>${html(human(audit.limitations))}</p>` : ""}` : `${facts([["实际检索范围", prose(audit.searchCoverage || audit.coverage, `已保存 ${pageCount} 个来源网页的 ${evidence.length} 条主张；其中 ${pendingCount} 条仍有核验或访问限制。`)],["仍需补查", audit.limitations?.length ? audit.limitations : "请结合各导师的待核实事项阅读"]])}<details class="technical"><summary>查询与工具记录（复核用）</summary>${coverage}</details>`}
${sourceAppendix(evidence, advisorRows, medical)}
${historicalRanking && !medical ? `<details class="technical"><summary>历史比较记录（不用于当前顺序或申请判断）</summary><pre>${html(JSON.stringify(ranking, null, 2))}</pre></details>` : ""}</section>`;
  const head = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-${REPORT_NAV_HASH}'; base-uri 'none'; form-action 'none'">
<title>${html(subject(project))} — 导师调研</title>
<style>${REPORT_STYLE}</style></head>
<body>${reportNavigation(advisorRows.map(row => ({...row, ...(advisorFacts.get(row.advisor_id || row.advisorId) || {})})), medical)}<main><header><p class="eyebrow">Boss Hunting · 导师调研</p><h1>${html(subject(project))}</h1>
${fixtureNotice ? `<p><strong>虚构示例 / FICTIONAL FIXTURE：</strong>${html(fixtureNotice)}</p>` : ""}
<p>${discovery ? "生物医学导师方向探索" : medical ? "生物医学导师申请筛选" : "导师与申请项目调研"} · ${html(project.target || "地区尚未确认")} · ${advisorRows.length} 位导师记录${medical && discovery ? "" : ` / ${programRows.length} 个真实项目机会`}</p>
${historicalRanking ? `<p><strong>历史比较待复核：</strong>已有 ${rankings.length} 条比较记录的调查确认已失效或不适用于当前范围。保留研究和来源痕迹；当前按稳定名称展示，申请资格待重新核对。</p>` : ""}
<p class="muted">${medical ? "按研究相关性和持续研究情况展示，顺序不代表导师质量排名。" : "结论依据共享记录；申请条件、名额与资金在行动前需要按项目批次重核。"}</p>${medical ? `<p><strong>本轮完成情况：</strong>${html(completion)}</p>` : ""}${discovery ? '<p class="muted">本轮聚焦研究方向与论文；招生资格、名额与申请批次未纳入调查。</p>' : ""}</header>`;
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
    ["可接受相邻方向 / 排除项", [profile.adjacentInterests, profile.exclusions]],
  ].filter(([, value]) => value.some((items) => Array.isArray(items) && items.length));
  return responsiveTables(`${head}
<section id="requirements"><h2>本次找导师的要求</h2>${facts([
  ["生物医学领域", profile.fields],
  ["疾病 / 机制与科学问题", [profile.diseaseScope, profile.diseasesOrMechanisms, profile.researchQuestions]],
  ["目标国家 / 地区", profile.regions],
  ...optionalProfile,
])}</section>
<section id="overview"><h2>导师简短对照</h2>${medicalOverviewTable(overviewRows, evidence, discovery, advisorRows)}${programDetails}</section>
<section id="advisors"><h2>逐位导师详情</h2>${advisorRows.length ? advisorRows.map((row, index) => medicalAdvisorSection(advisorFacts.get(row.advisor_id || row.advisorId) || row, index, project, programRows.filter((candidate) => (candidate.advisor_id || candidate.advisorId) === (row.advisor_id || row.advisorId)), evidence)).join("") : "<p>尚无导师事实记录。</p>"}</section>
${evidenceSection}
<p class="muted">论文按已核实的第一／共同第一／通讯／共同通讯署名与日期纳入；作者画像为可选补充。</p></main><script id="report-navigation">${REPORT_NAV_SCRIPT}</script></body></html>`);
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

export async function exportAdvisorReport(projectRoot, { checkIdentity = false } = {}) {
  const root = resolve(projectRoot);
  const project = await readJson(resolve(root, "project.json"));
  const keys = ["advisor_records", "program_records", "evidence", "candidates"];
  const arrays = await Promise.all(keys.map((key) => readJson(resolve(root, "outputs", `${key}.json`), [])));
  arrays.forEach((value, index) => { if (!Array.isArray(value)) throw new Error(`${keys[index]}.json 顶层必须是数组`); });
  const [advisors, programs, evidence, candidates] = arrays;
  const identityChecks = isMedicalEvidenceProfile(project) ? advisors.map((row) => ({ advisorId: row.advisor_id || row.advisorId, name: row.name, ...identityCoverage(row, evidence) })) : [];
  if (checkIdentity) return { complete: identityChecks.every((check) => check.complete), identityChecks };
  const ranking = await readJson(resolve(root, "outputs", "ranking.json"), []);
  const audit = await readJson(resolve(root, "outputs", "matching-audit.json"), {});
  const report = buildAdvisorReport({ project, advisors, programs, evidence, candidates, ranking, audit,
    cvValid: await hasReadableProjectCv(root, project.cv), providerCapabilities: await latestProviderCapabilities(root) });
  await mkdir(resolve(root, "outputs"), { recursive: true });
  const output = resolve(root, "outputs", reportFilename(project));
  await writeFile(output, report, "utf8");
  return { output, advisorCount: advisors.length, candidateCount: candidates.length, identityGaps: identityChecks.filter((check) => !check.complete).map(({advisorId, name, gaps}) => ({advisorId, name, gaps})) };
}

if (isExecutedDirectly(import.meta.url)) {
  const index = process.argv.indexOf("--project-root");
  const root = index < 0 ? "" : process.argv[index + 1];
  if (!root) throw new Error("Usage: build_advisor_report.mjs --project-root <project-directory>");
  console.log(JSON.stringify(await exportAdvisorReport(root, { checkIdentity: process.argv.includes("--check-identity") })));
}
