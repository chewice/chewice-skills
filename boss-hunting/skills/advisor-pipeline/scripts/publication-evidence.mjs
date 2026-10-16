// One publication projection for HTML, Excel and the incremental research merge.
const list = value => Array.isArray(value) ? value : [];
const get = (row, name) => row?.[name] ?? row?.[name.replace(/[A-Z]/g, c => `_${c.toLowerCase()}`)];
const refs = (row, name = "sourceIds") => [...new Set(list(get(row, name)).map(String).filter(Boolean))];
const roleNames = {first_author:"第一作者", co_first_author:"共同第一作者", corresponding_author:"通讯作者", co_corresponding_author:"共同通讯作者"};
const roleAliases = {first:"first_author", "first author":"first_author", "co-first":"co_first_author", "co-first author":"co_first_author", corresponding:"corresponding_author", "corresponding author":"corresponding_author", "co-corresponding":"co_corresponding_author", "co-corresponding author":"co_corresponding_author"};
const words = {verified:"已核实", partial:"部分核实", not_checked:"待核验", not_found:"所查范围未找到", inaccessible:"访问受阻", conflict:"来源存在冲突", stale:"信息可能过期", unknown:"待核验", found:"已找到", published:"已正式发表", epublish:"在线发表", ppublish:"正式出版", aheadofprint:"在线优先发表", preprint:"预印本", direct:"直接相关", adjacent:"相邻方向", weak:"关联较弱", insufficient_information:"信息不足", adequate:"已有部分证据", strong:"证据较充分", sparse:"证据有限", active:"近期活跃", recent_signal:"有近期研究", ...roleNames};
const roleFields = /advisorRoles|advisor_roles|authorRole|author_role|verifiedRole|verified_role|authorship|署名/;

// Only content-bearing properties are prose. Evidence IDs and schema keys stay in JSON.
export function readableText(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return [...new Set(value.map(readableText).filter(Boolean))].join("；");
  if (typeof value === "object") {
    for (const key of ["text", "summary", "claim", "reason", "description", "name", "title", "value"]) {
      if (value[key] !== undefined) return readableText(value[key]);
    }
    return value.reasons ? readableText(value.reasons) : (words[value.status] || "");
  }
  return words[value] || String(value);
}

function publicationTitle(value) {
  // Publisher metadata may contain inline JATS/HTML emphasis. Keep the words.
  return readableText(value).replace(/<\/?(?:i|b|em|strong|sup|sub|italic|bold|jats:italic|jats:bold)\b[^>]*>/gi, "")
    .replace(/&(amp|lt|gt|quot|apos);/g, (_, name) => ({amp:"&",lt:"<",gt:">",quot:'"',apos:"'"}[name]));
}

export function normalizePublication(item = {}) {
  if (typeof item !== "object" || !item) item = {title: readableText(item)};
  const role = get(item, "verifiedRole") ?? item.role ?? "unknown";
  const explicit = get(item, "advisorRoles");
  const roles = Array.isArray(explicit) ? explicit : [get(item, "advisorRole") ?? role];
  return {
    ...item,
    title: publicationTitle(item.title), date: item.date || null, year: item.year ?? null,
    venue: readableText(item.venue || item.journal || item.journal_or_preprint) || null,
    doi: item.doi || item.DOI || null, url: item.url || item.final_url || null,
    verifiedRole: role,
    advisorRoles: [...new Set(roles.map(role => roleAliases[role] || role).filter(role => roleNames[role]))],
    roleStatus: get(item, "roleStatus") || "not_checked",
    roleSourceIds: refs(item, "roleSourceIds"),
    relationToMainline: readableText(get(item, "relationToMainline") ?? item.relation),
    isPreprint: get(item, "isPreprint") === true,
    publishedVersionDoi: get(item, "publishedVersionDoi") || null,
    versionStatus: get(item, "versionStatus") || "not_checked",
    versionSourceIds: refs(item, "versionSourceIds"),
    publicationStatus: get(item, "publicationStatus") || null,
    sourceIds: [...new Set([...refs(item), ...refs(item.title), ...refs(item.venue || item.journal), ...refs(get(item, "relationToMainline") ?? item.relation)])],
  };
}

const doiKey = value => String(value || "").replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "").toLowerCase().trim();
const titleKey = work => String(work.title || "").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
const workYear = work => String(work.date || work.year || "").slice(0, 4);

function samePublication(a, b) {
  const da = doiKey(a.doi), db = doiKey(b.doi);
  if (da && db) return da === db;
  if (a.url && a.url === b.url) return true;
  return Boolean(titleKey(a)) && titleKey(a) === titleKey(b) && workYear(a) === workYear(b) && a.isPreprint === b.isPreprint;
}

export function mergePublicationRecords(records, additions) {
  const result = list(records).map(normalizePublication);
  for (const raw of list(additions)) {
    const incoming = normalizePublication(raw);
    const prior = result.find(work => samePublication(work, incoming));
    if (!prior) { result.push(incoming); continue; }
    const old = {...prior};
    // Newly verified metadata can fill a seed record without an unverified
    // legacy note erasing it. Two verified contradictory claims remain a gap.
    const useIncoming = incoming.roleStatus === "verified" && old.roleStatus !== "verified";
    for (const [key, value] of Object.entries(incoming)) {
      if (value === null || value === "" || value === undefined || (Array.isArray(value) && !value.length)) continue;
      if (useIncoming || prior[key] === undefined || prior[key] === null || prior[key] === "") prior[key] = value;
    }
    prior.sourceIds = [...new Set([...old.sourceIds, ...incoming.sourceIds])];
    if (old.roleStatus === "verified" && incoming.roleStatus === "verified") {
      prior.roleSourceIds = [...new Set([...old.roleSourceIds, ...incoming.roleSourceIds])];
      prior.advisorRoles = [...new Set([...old.advisorRoles, ...incoming.advisorRoles])];
      if (Boolean(old.advisorRoles.length) !== Boolean(incoming.advisorRoles.length)) prior.roleStatus = "conflict";
      if (old.date && incoming.date && old.date !== incoming.date) prior.dateStatus = "conflict";
    }
    if ([old.roleStatus, incoming.roleStatus].includes("conflict")) prior.roleStatus = "conflict";
    if (old.relationToMainline && (!incoming.relationToMainline || /未评估|未判断|未核验/.test(incoming.relationToMainline))) prior.relationToMainline = old.relationToMainline;
  }
  return result;
}

export function collectPublications(mainline = {}, evidence = [], advisorId = "", window = null) {
  const works = mergePublicationRecords([], [
    ...list(get(mainline, "representativeWorks")), ...list(get(mainline, "latestPapers")), ...list(mainline.preprints).map(p => ({...p, isPreprint:true})),
  ]);
  return works.filter(work => {
    if (!work.isPreprint || !work.publishedVersionDoi || work.versionStatus !== "verified"
      || !evidenceSupports(work.versionSourceIds, evidence, advisorId, ["verified"], /publishedVersionDoi|published_version_doi|versionLink|version_link|版本关联/)) return true;
    const final = works.find(row => !row.isPreprint && doiKey(row.doi) === doiKey(work.publishedVersionDoi)
      && row.roleStatus === "verified" && row.advisorRoles.length && dateWithinWindow(row, window)
      && evidenceSupports(row.roleSourceIds, evidence, advisorId, ["verified"], roleFields));
    if (!final) return true;
    final.sourceIds = [...new Set([...final.sourceIds, ...work.sourceIds, ...work.versionSourceIds])];
    return false;
  });
}

export function normalizePublicationSearches(value) {
  return list(value).filter(row => row && typeof row === "object").map(row => ({
    ...row, database: row.database || null, query: row.query || null,
    checkedAt: get(row, "checkedAt") || null, windowStart: get(row, "windowStart") || null, windowEnd: get(row, "windowEnd") || null,
    resultsExhausted: get(row, "resultsExhausted") === true,
    status: row.status || "not_checked", sourceIds: refs(row), limitations: readableText(row.limitations),
  }));
}

function validDate(date) {
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsed = new Date(`${date}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
}

function dateWithinWindow(paper, window) {
  if (paper.dateStatus === "conflict") return false;
  if (validDate(paper.date)) return !window || (paper.date >= window.start && paper.date <= window.end);
  const year = Number(paper.year);
  return !paper.date && Number.isInteger(year) && year >= 1000 && year <= 9999
    && (!window || (`${year}-01-01` >= window.start && `${year}-12-31` <= window.end));
}

function fiveYearsBefore(date) {
  const start = new Date(`${date}T00:00:00Z`), month = start.getUTCMonth();
  start.setUTCFullYear(start.getUTCFullYear() - 5);
  if (start.getUTCMonth() !== month) start.setUTCDate(0);
  return start.toISOString().slice(0, 10);
}

function evidenceSupports(ids, evidence, advisorId, statuses, fieldPattern) {
  return ids.length > 0 && ids.every(id => evidence.some(row => {
    if ((row.evidence_id || row.evidenceId) !== id || !statuses.includes(row.status)) return false;
    if (advisorId && (row.entity_id || row.entityId || row.entity) !== advisorId) return false;
    if (fieldPattern && !list(row.fields_supported || row.fieldsSupported).some(field => fieldPattern.test(field))) return false;
    try { return ["http:", "https:"].includes(new URL(row.final_url || row.source_url || row.url).protocol); }
    catch { return false; }
  }));
}

export function publicationRoleLabel(work) {
  return normalizePublication(work).advisorRoles.map(role => roleNames[role]).join("、") || "署名待核验";
}

export function publicationReview(mainline = {}, evidence = [], advisorId = "") {
  const searches = normalizePublicationSearches(get(mainline, "publicationSearches"));
  const latest = searches.map(row => row.checkedAt).filter(validDate).sort().at(-1);
  const current = searches.filter(row => row.checkedAt === latest);
  const valid = current.length > 0 && current.every(row => row.windowEnd === latest && row.windowStart === fiveYearsBefore(latest));
  const window = valid ? {start:fiveYearsBefore(latest), end:latest} : null;
  const papers = [], pending = [], excluded = [];
  for (const paper of collectPublications(mainline, evidence, advisorId, window)) {
    let reason = "";
    if (paper.roleStatus === "verified" && !paper.advisorRoles.length && evidenceSupports(paper.roleSourceIds, evidence, advisorId, ["verified"], roleFields)) { excluded.push({paper, reason:"已核实为其他作者署名"}); continue; }
    if (paper.roleStatus === "conflict") reason = "导师署名来源存在冲突";
    else if (paper.roleStatus !== "verified" || !paper.advisorRoles.length || !evidenceSupports(paper.roleSourceIds, evidence, advisorId, ["verified"], roleFields)) reason = "导师署名或对应来源尚未核实";
    if (!reason && !window) reason = "未记录有效的五年检索范围";
    if (!reason && paper.dateStatus === "conflict") reason = "发表日期来源存在冲突";
    if (!reason && validDate(paper.date)) {
      if (paper.date < window.start || paper.date > window.end) { excluded.push({paper, reason:"不在本次五年范围内"}); continue; }
    } else if (!reason) {
      const year = Number(paper.year);
      if (paper.date || !Number.isInteger(year) || year < 1000 || year > 9999) reason = "发表日期待核实";
      else if (`${year}-12-31` < window.start || `${year}-01-01` > window.end) { excluded.push({paper, reason:"不在本次五年范围内"}); continue; }
      else if (`${year}-01-01` < window.start || `${year}-12-31` > window.end) reason = "边界年份的具体发表日期待核实";
    }
    if (reason) pending.push({paper, reason}); else papers.push(paper);
  }
  const order = (a, b) => String(b.date || b.year || "").localeCompare(String(a.date || a.year || "")) || a.title.localeCompare(b.title);
  papers.sort(order); pending.sort((a,b) => order(a.paper,b.paper));
  const searchComplete = Boolean(window) && !pending.length && current.every(row => row.database && row.query && row.resultsExhausted
    && ["found", "not_found"].includes(row.status)
    && evidenceSupports(row.sourceIds, evidence, advisorId, row.status === "not_found" ? ["not_found"] : ["verified"], /publicationSearches|publication_searches/))
    && !(current.every(row => row.status === "not_found") && papers.length);
  return {papers, pending, excluded, window, searchComplete, searches,
    // Per-query candidate counts precede version/seed reconciliation. The
    // report shows the current pending count once, beside the combined list.
    limitations:[...new Set(current.map(row => row.limitations.replace(/仍有\s*\d+\s*条候选/g, "仍有候选论文")).filter(Boolean))]};
}

export function mergePublicationMainline(previous = {}, incoming = {}) {
  const merged = {};
  for (const field of ["representativeWorks", "latestPapers", "preprints"]) {
    const prior = get(previous, field), additions = get(incoming, field);
    if (prior || additions) merged[field] = mergePublicationRecords(prior, additions);
  }
  const searches = [...normalizePublicationSearches(get(previous, "publicationSearches")), ...normalizePublicationSearches(get(incoming, "publicationSearches"))];
  if (searches.length) merged.publicationSearches = [...new Map(searches.map(row => [JSON.stringify([row.database,row.query,row.checkedAt,row.windowStart,row.windowEnd]), row])).values()];
  merged.sourceIds = [...new Set([...refs(previous), ...refs(incoming)])];
  return merged;
}
