import { constants } from "node:fs";
import { mkdir, open, realpath } from "node:fs/promises";
import { basename, extname, resolve, sep } from "node:path";

// These helpers inspect host-provided capabilities; they never install tools,
// attach personal sessions, or infer availability from project/allowed-tools text.
const builtinWebToolNames = new Set(["web__run", "web.run", "web_run", "web_search", "web_search_preview"]);
// Wisp Science drives a real Chrome session through these bridge tools, so they are
// an interactive browser, never a stateless built-in web fetch. browser_setup only
// reports connection state and establishes no retrieval capability by itself.
const wispScienceBrowserTools = new Set(["web_open_tab", "web_scan", "web_execute_js", "web_screenshot",
  "web_save_assets", "web_agent_send", "web_agent_wait", "web_agent_read"]);
const wispScienceSetupTools = new Set(["browser_setup"]);

export function discoverResearchCapabilities(hostTools = {}, { backend = "builtin_web", requiresInteraction = false } = {}) {
  const names = Object.entries(hostTools).filter(([, tool]) => typeof tool === "function")
    .map(([name]) => name);
  // Only exact, host-owned callable names establish the built-in capability.
  // MCP names and documentation/configuration text do not establish provenance.
  const builtinWebTools = names.filter((name) => builtinWebToolNames.has(name));
  const browserTools = names.filter((name) => wispScienceBrowserTools.has(name) ||
    (/browser|playwright|puppeteer/i.test(name) &&
      /navigate|search|click|snapshot|screenshot|evaluate|read|extract|html|tabs|browser_use|(?:^|_)browser$/i.test(name) &&
      !/open_in_codex|(?:^|_)(?:install|configure|config|upload|send|purchase|create_account)(?:_|$)/i.test(name)));
  const staticTools = names.filter((name) => !builtinWebTools.includes(name) && !browserTools.includes(name) &&
    /web.*(run|fetch|search)|fetch|http/i.test(name));
  const requestedBackend = backend || "builtin_web";
  const wantsBrowser = requiresInteraction ||
    ["browser", "browser_use", "host-browser", "interactive_browser", "wisp_science_browser"].includes(requestedBackend) ||
    browserTools.includes(requestedBackend);
  const wantsStatic = ["static_web", "official_api"].includes(requestedBackend) || staticTools.includes(requestedBackend);
  const order = wantsBrowser ? ["browser", "builtin_web", "static_web"]
    : wantsStatic ? ["static_web", "builtin_web", "browser"] : ["builtin_web", "static_web", "browser"];
  const available = { builtin_web: builtinWebTools.length, static_web: staticTools.length, browser: browserTools.length };
  const preferredBackend = order.find((name) => available[name]) || "unavailable";
  const wispHost = names.some((name) => wispScienceBrowserTools.has(name) || wispScienceSetupTools.has(name));
  return { builtinWeb: builtinWebTools.length ? "available" : "unavailable", builtinWebTools,
    interactiveBrowser: browserTools.length ? "available" : "unavailable",
    browser: browserTools.length ? "available" : "unavailable", browserTools,
    browserProvider: browserTools.length ? (wispHost ? "wisp_science_browser" : "host_interactive_browser") : null,
    staticTools,
    requestedBackend, preferredBackend, liveTested: false, fallback: "static_web_or_official_api",
    limitations: browserTools.length ? [] : ["动态表单与渲染内容尚未通过交互浏览器核验"] };
}

const publicActions = new Set(["navigate", "search", "filter", "paginate", "expand", "read", "screenshot", "download", "reject_optional_cookies"]);
export function authorizePublicResearchAction(action, project = {}) {
  if (project.browserResearch?.enabled !== true) return { allowed: false, reason: "browser_research_not_enabled" };
  if (project.browserResearch.policy !== "public_read_only") return { allowed: false, reason: "public_research_policy_required" };
  if (!publicActions.has(action?.kind)) return { allowed: false, reason: "external_mutation_or_unknown_action" };
  if (action.externalMutation || action.requiresLogin || action.personalData || action.paidService || action.bypassAccessControl)
    return { allowed: false, reason: "separate_authorization_required" };
  if (action.kind === "download" && !project.browserResearch.allowPublicDownloads)
    return { allowed: false, reason: "public_downloads_not_enabled" };
  // Method is not authority: an explicitly read-only public search may use POST.
  if (action.publicReadOnly !== true) return { allowed: false, reason: "public_read_only_intent_required" };
  if (action.method && !["GET", "HEAD", "POST"].includes(String(action.method).toUpperCase()))
    return { allowed: false, reason: "external_mutation_method" };
  return { allowed: true, reason: "public_research" };
}

export function researchEvidence(observation) {
  const row = { ...observation, claim_type: observation.claim_type || "fact" };
  if (!["fact", "interpretation", "question"].includes(row.claim_type)) throw new Error("Invalid claim_type");
  if (!["static_web", "official_api", "browser"].includes(row.retrieval_method)) throw new Error("Actual retrieval_method required");
  for (const field of ["retrieval_provider", "retrieval_tool"]) {
    if (row[field] !== undefined && (typeof row[field] !== "string" || !row[field].trim()))
      throw new Error(`Actual ${field} must be a non-empty string`);
  }
  if ((builtinWebToolNames.has(row.retrieval_tool) || row.retrieval_provider === "gpt_builtin_web") && row.retrieval_method !== "static_web")
    throw new Error("GPT built-in web evidence must use static_web, not interactive browser");
  if ((wispScienceBrowserTools.has(row.retrieval_tool) || row.retrieval_provider === "wisp_science_browser") && row.retrieval_method !== "browser")
    throw new Error("Wisp Science browser evidence must use browser, not a static route");
  if (!Number.isFinite(Date.parse(row.accessed_at))) throw new Error("Actual accessed_at required");
  const url = new URL(row.final_url || row.source_url);
  if (!["http:", "https:"].includes(url.protocol)) throw new Error("Public source URL required");
  row.final_url = url.href;
  if (["blocked", "captcha", "login", "paywall"].includes(row.page_state) || [401, 403, 429].includes(Number(row.http_status))) {
    row.extraction_status = "blocked";
    row.status = "inaccessible";
  } else if (["loading", "empty_shell"].includes(row.page_state)) {
    row.extraction_status = "partial";
    row.status = "not_checked";
  }
  if (!["success", "partial", "blocked", "failed"].includes(row.extraction_status)) throw new Error("Actual extraction_status required");
  if (row.extraction_status === "blocked") row.status = "inaccessible";
  else if (row.extraction_status !== "success" && ["verified", "not_found"].includes(row.status)) row.status = "not_checked";
  row.failure_reason ||= row.extraction_status === "success" ? "" :
    `Observed ${row.page_state || row.extraction_status}${row.http_status ? ` (HTTP ${row.http_status})` : ""}`;
  row.fields_supported = Array.isArray(row.fields_supported) ? row.fields_supported : row.field ? [row.field] : [];
  row.excerpt = row.excerpt || row.supporting_excerpt || "";
  row.reading_depth = row.reading_depth || row.read_depth || "";
  if (row.status === "verified") {
    if (row.claim_type !== "fact" || !row.claim || !row.entity_id || !row.fields_supported.length || !row.page_title ||
        !row.excerpt || !row.page_locator || !["full_text", "detail", "abstract", "metadata"].includes(row.reading_depth) ||
        ["search_snippet", "search_result", "search_results"].includes(row.source_type) || row.page_state === "search_results")
      throw new Error("verified requires a specific fact and source detail; snippets cannot verify claims");
    if (row.reading_depth !== "detail" && row.reading_depth !== "full_text" &&
        row.fields_supported.some((field) => ["eligibility", "opportunity", "funding_guarantee", "contribution"].includes(field)))
      throw new Error("Key conditions require a detail/full-text source");
  }
  if (row.status === "not_found" && (!row.searched_sources?.length || !row.query_or_filter_summary || row.complete_results !== true))
    throw new Error("not_found requires completed documented search coverage");
  if (!["verified", "not_found", "not_checked", "inaccessible", "conflict", "stale", "not_applicable"].includes(row.status)) throw new Error("Invalid evidence status");
  if (row.source_type === "same_source_copy" && !row.same_source_group && !row.original_source_url)
    throw new Error("Reposts require a same-source group or known original URL");
  if (!row.same_source_group) {
    const original = new URL(row.original_source_url || row.final_url);
    if (!["http:", "https:"].includes(original.protocol)) throw new Error("Public original source URL required");
    original.hash = "";
    row.same_source_group = original.href;
  }
  return row;
}

function validateDownload(filename, bytes, contentType) {
  if (!filename || filename.length > 240 || filename !== basename(filename) || /[/:\\\x00-\x1f]/.test(filename) ||
      /%2e|%2f|%5c/i.test(filename) || /[. ]$/.test(filename) || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(filename))
    throw new Error("Unsafe download filename");
  const extension = extname(filename).toLowerCase();
  const mime = String(contentType).split(";")[0].trim().toLowerCase();
  const types = { ".pdf": ["application/pdf"], ".csv": ["text/csv", "application/csv"], ".txt": ["text/plain"], ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"] };
  if (!types[extension]?.includes(mime)) throw new Error("Unsupported or mismatched public file type");
  if (!bytes.length || bytes.length > 25 * 1024 * 1024) throw new Error("Public evidence file size limit");
  if (extension === ".pdf" && (!bytes.subarray(0, 5).equals(Buffer.from("%PDF-")) || /\/(JavaScript|JS|Launch|EmbeddedFile)\b/i.test(bytes.toString("latin1")))) throw new Error("Unsafe or invalid PDF");
  if ([".csv", ".txt"].includes(extension) && (bytes.includes(0) || bytes.subarray(0, 2).toString() === "MZ")) throw new Error("Binary file disguised as text");
  if (extension === ".xlsx") {
    // Inspect the central directory without executing/extracting any entry.
    const end = bytes.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
    if (end < 0 || end + 22 > bytes.length) throw new Error("Invalid XLSX archive");
    if (bytes.readUInt16LE(end + 4) || bytes.readUInt16LE(end + 6) ||
        bytes.readUInt16LE(end + 8) !== bytes.readUInt16LE(end + 10) ||
        end + 22 + bytes.readUInt16LE(end + 20) !== bytes.length)
      throw new Error("Unsupported XLSX archive layout");
    const names = [];
    let offset = bytes.readUInt32LE(end + 16);
    const count = bytes.readUInt16LE(end + 10);
    const directoryEnd = offset + bytes.readUInt32LE(end + 12);
    if (count === 0xffff || directoryEnd !== end) throw new Error("Invalid XLSX directory bounds");
    for (let i = 0; i < count; i++) {
      if (offset + 46 > end || bytes.readUInt32LE(offset) !== 0x02014b50) throw new Error("Invalid XLSX directory");
      const size = bytes.readUInt16LE(offset + 28);
      const entryEnd = offset + 46 + size + bytes.readUInt16LE(offset + 30) + bytes.readUInt16LE(offset + 32);
      if (entryEnd > directoryEnd) throw new Error("Invalid XLSX entry bounds");
      const name = bytes.subarray(offset + 46, offset + 46 + size).toString("utf8");
      if (/(^|[/\\])\.\.([/\\]|$)|^[/\\]|[:\x00]|vba|activex|embeddings|\.exe$|\.js$|\.bin$/i.test(name) ||
          (bytes.readUInt16LE(offset + 8) & 1) || ((bytes.readUInt32LE(offset + 38) >>> 16) & 0o170000) === 0o120000 ||
          names.includes(name)) throw new Error("Unsafe XLSX entry");
      const local = bytes.readUInt32LE(offset + 42);
      if (local + 30 > directoryEnd || bytes.readUInt32LE(local) !== 0x04034b50)
        throw new Error("Invalid XLSX local entry");
      const localNameSize = bytes.readUInt16LE(local + 26);
      const localEnd = local + 30 + localNameSize + bytes.readUInt16LE(local + 28);
      if (localEnd + bytes.readUInt32LE(offset + 20) > bytes.readUInt32LE(end + 16) ||
          bytes.subarray(local + 30, local + 30 + localNameSize).toString("utf8") !== name)
        throw new Error("XLSX local entry mismatch");
      names.push(name);
      offset = entryEnd;
    }
    if (offset !== directoryEnd) throw new Error("Invalid XLSX directory size");
    if (!names.includes("[Content_Types].xml") || !names.includes("xl/workbook.xml")) throw new Error("Not an XLSX workbook");
  }
}

export async function savePublicResearchDownload({ projectRoot, filename, data, contentType }) {
  const bytes = Buffer.from(data);
  validateDownload(filename, bytes, contentType);
  const root = await realpath(projectRoot);
  const outputs = resolve(root, "outputs");
  await mkdir(outputs, { recursive: true });
  const actualOutputs = await realpath(outputs);
  if (!actualOutputs.startsWith(`${root}${sep}`)) throw new Error("Download directory escapes project");
  const directory = resolve(actualOutputs, "browser-cache");
  await mkdir(directory, { recursive: true });
  const actual = await realpath(directory);
  if (!actual.startsWith(`${root}${sep}`)) throw new Error("Download directory escapes project");
  const target = resolve(actual, filename);
  const file = await open(target, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  try { await file.writeFile(bytes); } finally { await file.close(); }
  return target;
}
