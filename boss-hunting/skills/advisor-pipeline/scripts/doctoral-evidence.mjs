// Additive doctoral evidence; first authors are never inferred to be students.
const list = (v) => Array.isArray(v) ? v : [];
const value = (row, key, fallback = null) => row?.[key] ?? row?.[key.replace(/[A-Z]/g, c => `_${c.toLowerCase()}`)] ?? fallback;
const refs = (row, key = "sourceIds") => [...new Set(list(value(row, key, [])).map(String))];
const objects = (v) => list(v).filter(row => row && typeof row === "object" && !Array.isArray(row));
const statuses = new Set(["found", "not_found", "inaccessible", "partial", "not_checked"]);
const status = (row) => statuses.has(row?.status) ? row.status : "not_checked";

export function doctoralAdditions(source = {}) {
  return {
    firstAuthorProfiles: objects(value(source, "firstAuthorProfiles", [])).map(person => ({
      personId: value(person, "personId"), name: person.name || null,
      identityStatus: value(person, "identityStatus", "not_checked"), publicRole: value(person, "publicRole"),
      identitySourceIds: refs(person, "identitySourceIds"), researchSummary: value(person, "researchSummary"),
      summarySourceIds: refs(person, "summarySourceIds"), sourceIds: refs(person),
      papers: objects(person.papers).map(paper => ({title: paper.title || null, doi: paper.doi || null, url: paper.url || null,
        date: paper.date || null, year: paper.year || null, firstAuthorRole: value(paper, "firstAuthorRole", "unknown"),
        advisorRole: value(paper, "advisorRole", "unknown"), roleStatus: value(paper, "roleStatus", "not_checked"), sourceIds: refs(paper)})),
    })),
    labWebsites: objects(value(source, "labWebsites", [])).map(site => ({url: site.url || null, title: site.title || "实验室网站", status: status(site),
      relationshipStatus: value(site, "relationshipStatus", "not_checked"), sourceIds: refs(site),
      pages: objects(site.pages).map(page => ({url: page.url || null, title: page.title || "实验室页面", status: status(page),
        accessedAt: value(page, "accessedAt"), updatedAt: value(page, "updatedAt"), sourceIds: refs(page), limitations: page.limitations || null})),
    })),
    searches: objects(source.searches).map(search => ({kind: search.kind || null, database: search.database || null, query: search.query || null,
      checkedAt: value(search, "checkedAt"), windowStart: value(search, "windowStart"), windowEnd: value(search, "windowEnd"),
      status: status(search), limitations: search.limitations || null, sourceIds: refs(search)})),
  };
}

function validDate(date) {
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsed = new Date(`${date}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
}

export function doctoralWindow(doctoral) {
  const search = [...doctoral.searches].filter(row => row.kind === "corresponding_papers" && validDate(row.checkedAt))
    .sort((a, b) => b.checkedAt.localeCompare(a.checkedAt))[0];
  if (!search) return null;
  const date = new Date(`${search.checkedAt}T00:00:00Z`);
  const month = date.getUTCMonth();
  date.setUTCFullYear(date.getUTCFullYear() - 5);
  if (date.getUTCMonth() !== month) date.setUTCDate(0);
  const start = date.toISOString().slice(0, 10);
  if ((search.windowStart && search.windowStart !== start) || (search.windowEnd && search.windowEnd !== search.checkedAt)) return null;
  return {start, end: search.checkedAt};
}

function supported(ids, evidence, statuses = ["verified"]) {
  if (!ids.length) return false;
  if (evidence === undefined) return true;
  return ids.every(id => evidence.some(row => {
    if ((row.evidence_id || row.evidenceId) !== id || !statuses.includes(row.status)) return false;
    try { return ["http:", "https:"].includes(new URL(row.final_url || row.source_url || row.url).protocol); }
    catch { return false; }
  }));
}

export function firstAuthorPaperState(paper, window, evidence) {
  if (paper.roleStatus !== "verified" || !supported(paper.sourceIds, evidence)
    || !["first_author", "co_first_author"].includes(paper.firstAuthorRole)
    || !["corresponding_author", "co_corresponding_author"].includes(paper.advisorRole)) return "作者角色尚未核实或不符合条件";
  if (!window) return "未记录有效的近五年检索范围";
  if (validDate(paper.date)) return paper.date >= window.start && paper.date <= window.end ? "eligible" : "不在近五年范围内";
  if (paper.date) return "发表日期待核实";
  const year = Number(paper.year);
  if (!Number.isInteger(year) || year < 1000 || year > 9999) return "发表日期待核实";
  if (`${year}-01-01` > window.end || `${year}-12-31` < window.start) return "不在近五年范围内";
  return `${year}-01-01` >= window.start && `${year}-12-31` <= window.end ? "eligible" : "边界年份的具体发表日期待核实";
}

export function firstAuthorSummary(person, window, evidence) {
  const allowed = new Set(person.papers.filter(paper => firstAuthorPaperState(paper, window, evidence) === "eligible").flatMap(paper => paper.sourceIds));
  return person.researchSummary && person.summarySourceIds.length && person.summarySourceIds.every(id => allowed.has(id))
    ? person.researchSummary : "研究方向总结待补充或核实来源";
}

export function firstAuthorIdentity(person, evidence) {
  return person.identityStatus === "verified" && supported(person.identitySourceIds, evidence) && person.publicRole ? person.publicRole : "身份待核实";
}

export function labWebsiteVerified(site, evidence) {
  return site.relationshipStatus === "verified" && supported(site.sourceIds, evidence);
}

export function doctoralCoverage(doctoral, evidence) {
  if (!doctoralWindow(doctoral)) return false;
  for (const kind of ["corresponding_papers", "lab_website"]) {
    const searches = doctoral.searches.filter(row => row.kind === kind);
    if (!searches.length || !searches.every(row => row.database && row.query && validDate(row.checkedAt)
      && ["found", "not_found"].includes(row.status)
      && supported(row.sourceIds, evidence, row.status === "found" ? ["verified"] : ["not_found"]))) return false;
  }
  const window = doctoralWindow(doctoral);
  if (doctoral.firstAuthorProfiles.some(person => person.papers.some(paper => firstAuthorPaperState(paper, window, evidence) !== "eligible"))) return false;
  if (doctoral.searches.some(row => row.kind === "corresponding_papers" && row.status === "found") && !doctoral.firstAuthorProfiles.length) return false;
  if (doctoral.searches.some(row => row.kind === "lab_website" && row.status === "found") && !doctoral.labWebsites.length) return false;
  return doctoral.labWebsites.every(site => labWebsiteVerified(site, evidence) && site.pages.length > 0
    && site.pages.every(page => ["found", "not_found"].includes(page.status) && validDate(page.accessedAt)
      && supported(page.sourceIds, evidence, page.status === "found" ? ["verified"] : ["not_found"])));
}

export function doctoralWorkbookSummary(doctoral, evidence) {
  const window = doctoralWindow(doctoral);
  const rows = ["实验室网站与第一作者检索"];
  for (const kind of ["lab_website", "corresponding_papers"]) {
    const searches = doctoral.searches.filter(row => row.kind === kind);
    rows.push(searches.length ? searches.map(row => `${kind} | ${row.status} | ${row.query || ""} | ${row.checkedAt || ""} | ${row.limitations || ""} | ${row.sourceIds.join(", ")}`).join("\n") : `${kind}：未记录此项检索`);
  }
  rows.push(...doctoral.labWebsites.map(site => `${site.title} | ${site.url || ""} | 归属核验：${labWebsiteVerified(site, evidence) ? "已核实" : "待核实"} | ${site.sourceIds.join(", ")}\n${site.pages.map(page => `${page.title} | ${page.url || ""} | ${page.status} | 查阅 ${page.accessedAt || "未记录"} | 更新 ${page.updatedAt || "未注明"}`).join("\n")}`));
  for (const person of doctoral.firstAuthorProfiles) {
    rows.push(`${person.name || "姓名待核实"} | ${firstAuthorIdentity(person, evidence)} | 基于这些共同论文的总结：${firstAuthorSummary(person, window, evidence)} | ${person.identitySourceIds.join(", ")}`);
    rows.push(...person.papers.map(paper => `${paper.title || "标题待核实"} | ${paper.date || paper.year || "日期待核实"} | ${firstAuthorPaperState(paper, window, evidence) === "eligible" ? "署名与日期符合范围" : firstAuthorPaperState(paper, window, evidence)} | ${paper.firstAuthorRole} / ${paper.advisorRole} | ${paper.url || paper.doi || ""} | ${paper.sourceIds.join(", ")}`));
  }
  return rows.join("\n");
}

// Person IDs, not names, identify people. Missing IDs only deduplicate exact rows.
export function mergeDoctoralAdditions(base, incoming, onConflict = () => {}) {
  const target = doctoralAdditions(base);
  const additions = doctoralAdditions(incoming);
  const key = (row, field) => {
    if (field === "firstAuthorProfiles") return row.personId;
    if (field === "labWebsites" || field === "pages") return row.url;
    if (field === "papers") return row.doi?.toLowerCase().replace(/^https?:\/\/doi.org\//, "") || row.url || (row.title && (row.date || row.year) ? `${row.title}|${row.date || row.year}` : null);
    if (field === "searches") return row.checkedAt && row.query ? JSON.stringify([row.kind, row.database, row.query, row.checkedAt]) : null;
    return null;
  };
  function mergeArray(rows, updates, field, path) {
    for (const update of updates) {
      if (rows.some(row => JSON.stringify(row) === JSON.stringify(update))) continue;
      const id = key(update, field);
      const found = id ? rows.find(row => key(row, field) === id) : null;
      if (!found) { rows.push(structuredClone(update)); continue; }
      for (const [name, val] of Object.entries(update)) {
        if (val === null || val === "" || val === undefined) continue;
        if (Array.isArray(val)) {
          if (name.endsWith("SourceIds") || name === "sourceIds") found[name] = [...new Set([...found[name], ...val])];
          else mergeArray(found[name], val, name, `${path}.${id}.${name}`);
        } else if (found[name] === null || found[name] === "" || found[name] === undefined) found[name] = val;
        else if (found[name] !== val) onConflict(`${path}.${id}.${name}`, found[name], val);
      }
    }
  }
  for (const field of Object.keys(target)) mergeArray(target[field], additions[field], field, `doctoralTrajectory.${field}`);
  return target;
}

// Empty normalized defaults must not erase authoritative student records.
export function overlayDoctoralProfile(base = {}, other = {}) {
  const result = {...other, ...base, ...mergeDoctoralAdditions(base, other)};
  for (const key of ["currentDoctoral", "formerDoctoral", "graduateProgram", "emergingPiNote", "sampleLimitation"]) {
    const primary = value(base, key);
    const nonempty = Array.isArray(primary) ? primary.length > 0 : primary && (typeof primary !== "object" || Object.values(primary).some(item => Array.isArray(item) ? item.length : item));
    result[key] = nonempty ? primary : value(other, key);
  }
  result.sourceIds = [...new Set([...refs(base), ...refs(other)])];
  return result;
}
