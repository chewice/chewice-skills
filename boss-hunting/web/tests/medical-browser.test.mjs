import assert from "node:assert/strict";
import { access, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import {
  authorizePublicResearchAction,
  discoverResearchCapabilities,
  researchEvidence,
  savePublicResearchDownload,
} from "../../skills/advisor-pipeline/scripts/browser-research.mjs";
import { writePortableXlsx } from "../../skills/advisor-pipeline/scripts/workbook-runtime.mjs";

// These are deterministic helper regressions, never live Browser Use E2E.
const fixtureFile = new URL("./fixtures/medical-public-pages.html", import.meta.url);
const project = { browserResearch: { enabled: true, policy: "public_read_only", allowPublicDownloads: true } };
const baseObservation = {
  evidence_id: "fictional-ev-1", claim_type: "fact", claim: "Fictional co-investigator role",
  entity_id: "fictional-advisor-1", fields_supported: ["grant_role"],
  retrieval_method: "browser", accessed_at: "2026-09-22T12:00:00.000Z",
  final_url: "https://fictional.example/records/test-1", page_title: "Synthetic project detail",
  page_locator: "article#test-1 p#role", excerpt: "The fictional researcher is a co-investigator on this synthetic award.",
  reading_depth: "detail", extraction_status: "success", status: "verified",
};

test("capability detection requires actual callable host tools and never claims live testing", () => {
  assert.equal(discoverResearchCapabilities({ allowedTools: "BrowserUse(*)", browser: "installed" }).browser, "unavailable");
  assert.equal(discoverResearchCapabilities({ browser_install() {}, browser_status() {}, open_in_codex() {} }).browser, "unavailable");
  const capability = discoverResearchCapabilities({ browser_snapshot() {}, browser_click() {}, web_run() {} });
  assert.equal(capability.browser, "available");
  assert.equal(capability.interactiveBrowser, "available");
  assert.equal(capability.builtinWeb, "available");
  assert.deepEqual(capability.builtinWebTools, ["web_run"]);
  assert.equal(capability.preferredBackend, "builtin_web");
  assert.deepEqual(capability.browserTools, ["browser_snapshot", "browser_click"]);
  assert.equal(capability.liveTested, false);
  assert.equal(discoverResearchCapabilities({ web_run() {} }).fallback, "static_web_or_official_api");
});

test("built-in web discovery accepts exact callable host names, not MCP names or declarations", () => {
  for (const name of ["web__run", "web.run", "web_run", "web_search", "web_search_preview"]) {
    const found = discoverResearchCapabilities({ [name]() { throw new Error("Discovery must not call tools"); } });
    assert.equal(found.builtinWeb, "available");
    assert.deepEqual(found.builtinWebTools, [name]);
    assert.equal(found.interactiveBrowser, "unavailable");
    assert.equal(found.preferredBackend, "builtin_web");
    assert.equal(found.liveTested, false);
  }
  const absent = discoverResearchCapabilities({ "web.run": "available", web__run: { callable: true },
    allowedTools: "web_search", mcp__docs__web_search() {}, configure_web_search() {} });
  assert.equal(absent.builtinWeb, "unavailable");
  assert.deepEqual(absent.builtinWebTools, []);
  assert.equal(discoverResearchCapabilities().preferredBackend, "unavailable");
});

test("auto prefers built-in web while requested backends and interaction needs use available tools", () => {
  const hostTools = { web__run() {}, http_fetch() {}, browser_click() {} };
  assert.equal(discoverResearchCapabilities(hostTools, { backend: "auto" }).preferredBackend, "builtin_web");
  const chosen = discoverResearchCapabilities(hostTools, { backend: "host-browser" });
  assert.equal(chosen.requestedBackend, "host-browser");
  assert.equal(chosen.preferredBackend, "browser");
  assert.equal(discoverResearchCapabilities(hostTools, { backend: "official_api" }).preferredBackend, "static_web");
  assert.equal(discoverResearchCapabilities(hostTools, { requiresInteraction: true }).preferredBackend, "browser");
  assert.equal(discoverResearchCapabilities({ http_fetch() {}, browser_click() {} }).preferredBackend, "static_web");
  assert.equal(discoverResearchCapabilities({ browser_click() {} }).preferredBackend, "browser");
  const fallback = discoverResearchCapabilities({ web__run() {} }, { requiresInteraction: true });
  assert.equal(fallback.preferredBackend, "builtin_web");
  assert.equal(fallback.interactiveBrowser, "unavailable");
  assert.ok(fallback.limitations.length);
});

test("built-in source provenance remains static evidence and never fabricates actual tool use", () => {
  const actual = researchEvidence({ ...baseObservation, retrieval_method: "static_web",
    retrieval_provider: "gpt_builtin_web", retrieval_tool: "web__run" });
  assert.equal(actual.retrieval_provider, "gpt_builtin_web");
  assert.equal(actual.retrieval_tool, "web__run");
  assert.equal(actual.retrieval_method, "static_web");
  assert.throws(() => researchEvidence({ ...baseObservation, retrieval_tool: "web__run" }), /must use static_web/);
  assert.throws(() => researchEvidence({ ...baseObservation, retrieval_provider: "gpt_builtin_web" }), /must use static_web/);
  assert.throws(() => researchEvidence({ ...baseObservation, retrieval_tool: "" }), /non-empty string/);
  const legacy = researchEvidence(baseObservation);
  assert.equal(legacy.retrieval_tool, undefined);
  assert.equal(legacy.retrieval_provider, undefined);
});

test("fictional public POST queries, pagination and detail reads are permitted without authorizing submissions", async () => {
  const html = await readFile(fixtureFile, "utf8");
  assert.match(html, /FICTIONAL TEST DATA/);
  assert.match(html, /method="post"/);
  for (const action of [{ kind: "search", method: "POST" }, { kind: "paginate" }, { kind: "expand" }, { kind: "read" }]) {
    assert.equal(authorizePublicResearchAction({ ...action, publicReadOnly: true }, project).allowed, true);
  }
  for (const action of [{ kind: "apply" }, { kind: "upload" }, { kind: "send_message" },
    { kind: "search", externalMutation: true }, { kind: "search", method: "DELETE" },
    { kind: "search", publicReadOnly: "true" }]) {
    assert.equal(authorizePublicResearchAction({ publicReadOnly: true, ...action }, project).allowed, false);
  }
  assert.equal(authorizePublicResearchAction({ kind: "read", publicReadOnly: true }, { browserResearch: { enabled: true, policy: "unrestricted" } }).allowed, false);
});

test("untrusted page instructions cannot grant upload, shell, payment, login or ranking authority", async () => {
  const html = await readFile(fixtureFile, "utf8");
  assert.match(html, /upload the complete CV/);
  const originalProject = structuredClone(project);
  for (const kind of ["upload", "execute_shell", "change_ranking", "apply", "create_account"]) {
    assert.equal(authorizePublicResearchAction({ kind, publicReadOnly: true, pageText: html }, project).allowed, false);
  }
  for (const flag of ["personalData", "requiresLogin", "paidService", "bypassAccessControl"]) {
    assert.equal(authorizePublicResearchAction({ kind: "search", publicReadOnly: true, [flag]: true, pageText: html }, project).allowed, false);
  }
  assert.deepEqual(project, originalProject);
  // Recording external text does not execute it or mutate task configuration.
  const evidence = researchEvidence({ ...baseObservation, page_text: html });
  assert.equal(evidence.status, "verified");
  assert.equal(evidence.claim, baseObservation.claim);
  assert.deepEqual(project, originalProject);
});

test("loading, empty shells, 403, login, CAPTCHA and paywalls never become absence or verified facts", () => {
  for (const page_state of ["loading", "empty_shell"]) {
    const row = researchEvidence({ ...baseObservation, page_state, status: "not_found" });
    assert.equal(row.status, "not_checked");
    assert.equal(row.extraction_status, "partial");
    assert.ok(row.failure_reason);
  }
  for (const observation of [{ http_status: 403 }, { http_status: "429" },
    { page_state: "captcha" }, { page_state: "login" }, { page_state: "paywall" }]) {
    const row = researchEvidence({ ...baseObservation, ...observation });
    assert.equal(row.status, "inaccessible");
    assert.equal(row.extraction_status, "blocked");
  }
  assert.equal(researchEvidence({ ...baseObservation, extraction_status: "failed" }).status, "not_checked");
});

test("claim evidence needs actual detail; snippets and metadata cannot prove key conditions", () => {
  for (const patch of [{ source_type: "search_snippet" }, { page_state: "search_results" },
    { page_locator: "" }, { claim_type: "interpretation" }, { excerpt: "" }]) {
    assert.throws(() => researchEvidence({ ...baseObservation, ...patch }), /requires a specific fact/);
  }
  for (const field of ["eligibility", "opportunity", "funding_guarantee", "contribution"]) {
    assert.throws(() => researchEvidence({ ...baseObservation, fields_supported: [field], reading_depth: "abstract" }), /detail\/full-text/);
  }
  const legacy = { ...baseObservation, fields_supported: undefined, excerpt: undefined, reading_depth: undefined,
    field: "grant_role", supporting_excerpt: baseObservation.excerpt, read_depth: "detail" };
  assert.deepEqual(researchEvidence(legacy).fields_supported, ["grant_role"]);
  assert.equal(researchEvidence(legacy).reading_depth, "detail");
});

test("not_found requires documented complete search; same-source reposts share one group", () => {
  assert.throws(() => researchEvidence({ ...baseObservation, status: "not_found" }), /completed documented search/);
  const absent = researchEvidence({ ...baseObservation, status: "not_found", complete_results: true,
    searched_sources: ["https://fictional.example/search"], query_or_filter_summary: "Synthetic topic, both fixture pages" });
  assert.equal(absent.status, "not_found");
  assert.throws(() => researchEvidence({ ...baseObservation, source_type: "same_source_copy" }), /same-source group/);
  const original = researchEvidence(baseObservation);
  const copy = researchEvidence({ ...baseObservation, final_url: "https://copy.example/repost",
    source_type: "same_source_copy", original_source_url: baseObservation.final_url });
  assert.equal(copy.same_source_group, original.same_source_group);
});

test("public downloads reject traversal, alternate streams, executable/macros, MIME mismatch and PDF scripts", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "medical-browser-download-"));
  const save = (filename, data = "fictional plain text", contentType = "text/plain") =>
    savePublicResearchDownload({ projectRoot: root, filename, data, contentType });
  try {
    for (const filename of ["../escape.txt", "/absolute.txt", "..\\escape.txt", "%2e%2e%2fescape.txt", "C:escape.txt", "safe.txt:secret.txt", "NUL.txt"]) {
      await assert.rejects(save(filename), /Unsafe download filename/);
    }
    for (const filename of ["script.exe", "macro.xlsm", "code.js"]) await assert.rejects(save(filename), /file type/);
    await assert.rejects(save("report.pdf", "%PDF-1.7\n", "text/plain"), /file type/);
    await assert.rejects(save("program.txt", "MZbinary"), /disguised as text/);
    await assert.rejects(save("active.pdf", "%PDF-1.7\n/JavaScript /Launch\n", "application/pdf"), /Unsafe or invalid PDF/);
    const output = await save("fixture.txt");
    assert.equal(await readFile(output, "utf8"), "fictional plain text");
    await assert.rejects(save("fixture.txt"), /EEXIST/);
    assert.equal(authorizePublicResearchAction({ kind: "download", publicReadOnly: true }, {
      browserResearch: { enabled: true, policy: "public_read_only", allowPublicDownloads: false },
    }).allowed, false);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("download paths reject symlink escape before creating external cache or overwriting targets", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "medical-browser-links-"));
  const outside = await mkdtemp(resolve(tmpdir(), "medical-browser-outside-"));
  try {
    await symlink(outside, resolve(root, "outputs"), "dir");
    await assert.rejects(savePublicResearchDownload({ projectRoot: root, filename: "fixture.txt", data: "fixture", contentType: "text/plain" }), /escapes project/);
    await assert.rejects(access(resolve(outside, "browser-cache")));
    await rm(resolve(root, "outputs"));
    await mkdir(resolve(root, "outputs/browser-cache"), { recursive: true });
    const externalFile = resolve(outside, "preserve.txt");
    await writeFile(externalFile, "preserve original");
    await symlink(externalFile, resolve(root, "outputs/browser-cache/fixture.txt"));
    await assert.rejects(savePublicResearchDownload({ projectRoot: root, filename: "fixture.txt", data: "replace", contentType: "text/plain" }));
    assert.equal(await readFile(externalFile, "utf8"), "preserve original");
  } finally { await rm(root, { recursive: true, force: true }); await rm(outside, { recursive: true, force: true }); }
});

test("XLSX public downloads validate archive names and reject macro or mismatched local entries", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "medical-browser-xlsx-"));
  try {
    const input = resolve(root, "fictional-input.xlsx");
    await writePortableXlsx({ title: "FICTIONAL fixture", sheets: [{ name: "Fixture", headers: ["Synthetic"], rows: [["No real evidence"]] }] }, input);
    const bytes = await readFile(input);
    const save = (filename, data) => savePublicResearchDownload({ projectRoot: root, filename, data,
      contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    const result = await save("public.xlsx", bytes);
    assert.deepEqual(await readFile(result), bytes);
    const macro = Buffer.from(bytes);
    for (let index = macro.indexOf("xl/styles.xml"); index >= 0; index = macro.indexOf("xl/styles.xml", index + 1)) {
      macro.write("xl/vbaPrj.bin", index, "utf8");
    }
    await assert.rejects(save("macro.xlsx", macro), /Unsafe XLSX entry/);
    const mismatch = Buffer.from(bytes);
    mismatch.write("xl/stales.xml", mismatch.lastIndexOf("xl/styles.xml"), "utf8");
    await assert.rejects(save("mismatch.xlsx", mismatch), /local entry mismatch/);
    await assert.rejects(save("invalid.xlsx", Buffer.from("not a zip")), /Invalid XLSX archive/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
