// Spec §36–§38 acceptance scenarios T01–T40.
//
// Cases that can be decided deterministically from contracts, normalizers and
// generated artefacts are asserted here. Cases that require live retrieval or
// Agent judgement are declared with test.todo and the reason is stated inline;
// their behavioural rules live in SKILL.md / references and in the prompts.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  MEDICAL_DETECTIVE_SECTIONS, PROJECT_SCHEMA_VERSION, medicalIntakeStatus, normalizeProjectMetadata, readinessForProject,
} from "../../skills/advisor-pipeline/scripts/project-contract.mjs";
import {
  PI_ROLE_CONFIDENCE, REMOVED_MEDICAL_PROFILE_KEYS, buildMedicalDiscoveryView, compareMedicalCandidates, normalizeMedicalCandidate, normalizeMedicalEvidenceProfile,
} from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";
import { buildAdvisorReport } from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";
import { buildMedicalWorkbookSheets } from "../../skills/advisor-pipeline/scripts/medical-workbook.mjs";
import { buildEgoNetwork, saturationReached } from "../../skills/advisor-pipeline/scripts/collaboration-network.mjs";
import { buildProviderCapabilities, selectRoute } from "../../skills/advisor-pipeline/scripts/provider-capabilities.mjs";
import { containsSecret, loadCredentials, redactSecrets, resolveCredentialsPath } from "../../skills/advisor-pipeline/scripts/credentials.mjs";
import { mergeSubagentOutputs } from "../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs";
import { researchEvidence } from "../../skills/advisor-pipeline/scripts/browser-research.mjs";
import { buildRunPrompt } from "../local-runtime/run-prompt.mjs";

const fixture = async (name) => JSON.parse(await readFile(new URL(`./fixtures/${name}.json`, import.meta.url), "utf8"));
const now = "2026-09-22T12:00:00.000Z";
const minimal = { id: "fixture", name: "Fixture", domainProfile: "medical", target: "日本",
  medicalProfile: { fields: ["肿瘤学"], diseaseScope: "pan_cancer", researchQuestions: ["Fictional question"] } };
const credentials = (secrets = {}) => ({ providers: {}, secrets });
const FAKE = "fixture-secret-value-0123456789";

test("T01 three inputs only: discovery starts without CV, grades, papers or applicant ability", () => {
  const project = normalizeProjectMetadata(minimal, { now });
  assert.equal(project.schemaVersion, PROJECT_SCHEMA_VERSION);
  assert.equal(medicalIntakeStatus(project).ready, true);
  assert.equal(readinessForProject({ metadata: project, cvValid: false }).phase1Ready, true);
  assert.ok(!("currentSkills" in project.medicalProfile) && !("desiredTraining" in project.medicalProfile));
  const prompt = buildRunPrompt({ project: { ...project, path: "/fictional" }, userPrompt: "go", runDirectory: "/run", provider: "codex", mode: "finder" });
  assert.match(prompt, /discovery 不读取 CV、成绩或申请者能力/);
});

test("T02 identical direction with different ability yields identical comparison basis", async () => {
  const bundle = await fixture("medical-discovery");
  const base = normalizeProjectMetadata(bundle.project, { now });
  const withAbility = normalizeProjectMetadata({ ...bundle.project, medicalProfile: { ...bundle.project.medicalProfile, currentSkills: ["单细胞分析"], desiredTraining: ["因果推断"] } }, { now });
  assert.deepEqual(withAbility.medicalProfile, base.medicalProfile);
  const left = buildMedicalDiscoveryView(bundle.advisors, base);
  const right = buildMedicalDiscoveryView(bundle.advisors, withAbility);
  assert.deepEqual(left, right);
  assert.ok(!JSON.stringify(left).includes("单细胞分析"));
});

test("T03 advisor id only: advisor-level report without invented programme or intake", async () => {
  const bundle = await fixture("medical-discovery");
  assert.equal(bundle.candidates.length, 0);
  const rows = buildMedicalDiscoveryView(bundle.advisors, bundle.project);
  assert.ok(rows.every((row) => !("advisorProgramId" in row) && !("intake" in row) && !("program" in row)));
  const report = buildAdvisorReport(bundle);
  assert.match(report, /B\. 近五年科研主线与研究路线/);
  assert.doesNotMatch(report, /advisorProgramId/);
});

test("T04 legacy funding/resource/environment/training fields are kept in storage but absent from the current pipeline", async () => {
  const legacy = { advisor_id: "legacy-pi", name: "Legacy PI", evidence_profile: {
    scientificFit: { status: "strong" }, trainingFit: { status: "supported", reasons: ["legacy training"] },
    resources: [{ level: "institution_owned" }], doctoralFunding: [{ status: "verified" }], trainingEnvironment: { culture: "legacy" },
    researchFunding: [{ amount: 1 }], doctoralOutcomes: { placementRate: 0.9 } } };
  const view = buildMedicalDiscoveryView([legacy], minimal)[0];
  for (const key of REMOVED_MEDICAL_PROFILE_KEYS) assert.ok(!(key in view.evidenceProfile), key);
  assert.equal(view.evidenceProfile.researchQuestionFit.status, "direct", "direction fit is retained content");
  assert.ok(legacy.evidence_profile.trainingFit, "the stored record is not mutated");
  const project = normalizeProjectMetadata({ ...minimal, investigation: { draft: { selectedSections: ["recent_research", "resources_career_support"] } } }, { now });
  assert.deepEqual(project.investigation.draft.selectedSections, MEDICAL_DETECTIVE_SECTIONS);
  const report = buildAdvisorReport({ project, advisors: [legacy], evidence: [] });
  assert.doesNotMatch(report, /legacy training|institution_owned|placementRate|培养制度与环境|博士生资助/);
  const sheets = buildMedicalWorkbookSheets({ project, advisorRecords: [legacy] });
  assert.doesNotMatch(JSON.stringify(sheets), /legacy training|institution_owned|placementRate/);
});

test("T05 a method description explains the route without triggering resource or method-quality audits", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { research_mainline: { methods: ["Fictional single-cell method"], research_objects: ["fixture object"] } } });
  assert.deepEqual(profile.researchMainline.methods, ["Fictional single-cell method"]);
  assert.ok(!("methodQuality" in profile) && !("resources" in profile));
  assert.ok(!MEDICAL_DETECTIVE_SECTIONS.some((id) => /resource|method_quality/.test(id)));
});

test("T06 a single same-disease hit cannot claim a sustained mainline", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { research_mainline: { representative_works: [{ title: "one hit" }] } } });
  assert.equal(profile.researchRouteContinuity.status, "unclear", "continuity defaults to unclear until back-search evidence exists");
  assert.equal(profile.researchMainline.backSearchWindow, null);
});

test("T07 identity block keeps affiliation as-of date and name variants", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { identity: { current_institution: "Current Institute", affiliation_as_of: "2026-06", name_variants: ["Fixture, A.", "A Fixture"] } } });
  assert.equal(profile.identity.affiliationAsOf, "2026-06");
  assert.deepEqual(profile.identity.nameVariants, ["Fixture, A.", "A Fixture"]);
  assert.equal(profile.piRoleConfidence.status, "identity_unresolved", "unresolved identity is the default");
});

test("T08 abstract-only reading cannot verify contribution and unknown roles stay unknown", () => {
  assert.throws(() => researchEvidence({ retrieval_method: "static_web", accessed_at: now, final_url: "https://example.org/paper", extraction_status: "success",
    status: "verified", claim: "corresponding author", entity_id: "pi", fields_supported: ["contribution"], page_title: "t", excerpt: "e", page_locator: "p", reading_depth: "abstract" }), /snippets cannot verify|detail/);
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { research_mainline: { representative_works: [{ title: "Fixture paper" }] } } });
  assert.equal(profile.researchMainline.representativeWorks[0].verifiedRole, "unknown");
});

test("T09 preprint flag is preserved and a missing preprint does not degrade any status", () => {
  const withPreprint = normalizeMedicalEvidenceProfile({ evidence_profile: { latest_signals: { preprints: [{ title: "Fixture preprint", is_preprint: true }] } } });
  assert.equal(withPreprint.latestSignals.preprints[0].isPreprint, true);
  const without = normalizeMedicalEvidenceProfile({ evidence_profile: { research_question_fit: { status: "direct" }, latest_signals: { preprints: [] } } });
  assert.equal(without.researchQuestionFit.status, "direct");
  assert.equal(without.latestSignals.preprints.length, 0);
});

test("T10 project amounts keep their basis/unit and never become doctoral personal funding", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { latest_signals: { projects: [{ title: "Fixture grant", amount: 500000, amount_unit: "CNY", amount_basis: "annual_parent_award", pi_role: "Co-I" }] } } });
  const project = profile.latestSignals.projects[0];
  assert.equal(project.amountBasis, "annual_parent_award");
  assert.equal(project.amountUnit, "CNY");
  assert.equal(project.piRole, "Co-I");
  assert.ok(!("doctoralFunding" in profile));
  const sheets = buildMedicalWorkbookSheets({ project: minimal, advisorRecords: [{ advisor_id: "pi", name: "PI", evidence_profile: { latest_signals: { projects: [project] } } }] });
  const sheet = sheets.find((item) => /导师探索视图/.test(item.name));
  assert.ok(!sheet.headers.some((header) => /博士生资助|经费/.test(header)));
  assert.match(JSON.stringify(sheet.rows[0]), /500000 CNY/);
});

test("T11 registries and trials are recorded separately from doctoral recruitment", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { latest_signals: { trials: [{ id: "FIX-TRIAL", status: "recruiting" }] } } });
  assert.equal(profile.latestSignals.trials.length, 1);
  const candidate = normalizeMedicalCandidate({ advisorProgramId: "x", evidenceProfile: profile, opportunityStatus: "verified_open" }, { ...minimal, searchMode: "application" });
  assert.equal(candidate.opportunityStatus, "unknown", "a recruiting trial is not verified doctoral recruitment");
});

test("T12 doctoral people carry supervision evidence, information date and current/former separation", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { doctoral_trajectory: {
    current_doctoral: [{ name: "Current fixture", supervision_evidence: ["official listing"], information_date: "2026-05" }],
    former_doctoral: [{ name: "Former fixture", first_destination: "Fixture postdoc", latest_public_role: "Fixture PI", information_date: "2024-01" }] } } });
  assert.equal(profile.doctoralTrajectory.currentDoctoral[0].informationDate, "2026-05");
  assert.equal(profile.doctoralTrajectory.formerDoctoral[0].firstDestination, "Fixture postdoc");
  assert.match(profile.doctoralTrajectory.sampleLimitation, /不计算毕业率、去向率或培养成功率/);
});

test("T13 search or homepage links are not item-level verification", () => {
  assert.throws(() => researchEvidence({ retrieval_method: "static_web", accessed_at: now, final_url: "https://example.org/search?q=pi", extraction_status: "success",
    status: "verified", claim: "c", entity_id: "pi", fields_supported: ["latest_signals_projects"], page_title: "t", excerpt: "e", page_locator: "p", reading_depth: "detail", source_type: "search_result" }), /snippets cannot verify/);
});

test("T14 missing or wrong-entity source ids downgrade instead of silently verifying", async () => {
  const bundle = await fixture("medical-application");
  const candidate = { ...bundle.candidates[0], eligibilityEvidence: { status: "verified", advisorProgramId: bundle.candidates[0].advisorProgramId, intake: "2027", sourceIds: ["missing-id"] } };
  const result = normalizeMedicalCandidate(candidate, { ...bundle.project, cvValid: true, evidenceRecords: bundle.evidence });
  assert.equal(result.feasibility, "needs_confirmation");
  const wrongEntity = normalizeMedicalCandidate({ ...candidate, eligibilityEvidence: { ...candidate.eligibilityEvidence, sourceIds: ["fixture-terms"] } },
    { ...bundle.project, cvValid: true, evidenceRecords: bundle.evidence.map((row) => row.evidence_id === "fixture-terms" ? { ...row, entity_id: "someone-else" } : row) });
  assert.equal(wrongEntity.feasibility, "needs_confirmation");
});

test("T15 blocked pages stay inaccessible and are never reported as verified", () => {
  const row = researchEvidence({ retrieval_method: "browser", accessed_at: now, final_url: "https://example.org/dynamic", http_status: 403, extraction_status: "success", status: "verified", claim: "c" });
  assert.equal(row.status, "inaccessible");
  assert.equal(row.extraction_status, "blocked");
  assert.match(row.failure_reason, /HTTP 403/);
});

test("T16 unsafe protocols and injected text are inert in the report", async () => {
  const bundle = await fixture("medical-discovery");
  bundle.advisors[0].evidence_profile.identity.official_profile_url = "javascript:alert(1)";
  bundle.advisors[0].evidence_profile.fit_boundary = "<script>alert(1)</script>";
  const report = buildAdvisorReport(bundle);
  assert.doesNotMatch(report, /href="javascript:|<script>alert/);
  assert.match(report, /&lt;script&gt;alert/);
  assert.match(report, /Content-Security-Policy/);
});

test("T17 formal records are bound to the PI record and rendered without misconduct inference", async () => {
  const bundle = await fixture("medical-discovery");
  bundle.advisors[0].evidence_profile.formal_records = ["Fictional correction notice (bound to this record)"];
  const report = buildAdvisorReport(bundle);
  assert.match(report, /Fictional correction notice/);
  assert.doesNotMatch(report, /不端|misconduct/);
});

test("T18 unchecked, not-found and blocked evidence remain distinguishable", async () => {
  const bundle = await fixture("medical-discovery");
  bundle.evidence.push({ evidence_id: "blocked", entity_id: bundle.advisors[0].advisor_id, status: "inaccessible", url: "https://example.org/blocked", failure_reason: "HTTP 403" },
    { evidence_id: "none", entity_id: bundle.advisors[0].advisor_id, status: "not_found", url: "https://example.org/none" });
  const report = buildAdvisorReport(bundle);
  assert.match(report, /inaccessible/);
  assert.match(report, /not_found/);
  assert.match(report, /not_checked/);
  assert.match(report, /未检索、未找到、受阻、部分、冲突和过期分别保留/);
});

test("T19 review inflation: a single review cannot make a core collaborator", () => {
  const network = buildEgoNetwork("pi", [{ id: "review", type: "coauthorship", year: 2025, participants: ["pi", "reviewer"], directionRelevant: true }], { referenceYear: 2026 });
  assert.equal(network.coreCollaborators.length, 0);
  assert.deepEqual(network.leads.map((row) => row.collaboratorId), ["reviewer"]);
});

test("T20 consortium false positive is filtered", () => {
  const participants = ["pi", ...Array.from({ length: 300 }, (_, index) => `member-${index}`)];
  const network = buildEgoNetwork("pi", [{ id: "consortium", type: "coauthorship", year: 2025, authorCount: 301, participants }], { referenceYear: 2026 });
  assert.equal(network.coreCollaborators.length, 0);
  assert.equal(network.excluded.length, 300);
});

test("T21 citation is a research-neighbor edge, never a collaboration edge", () => {
  const network = buildEgoNetwork("A", [{ id: "cite", type: "citation", participants: ["A", "B"] }, { id: "cite2", type: "co_citation", participants: ["A", "B"] }], { referenceYear: 2026 });
  assert.equal(network.edges.length, 0);
  assert.deepEqual(network.researchNeighbors.map((row) => row.collaboratorId), ["B"]);
});

test("T22 emerging PI is not excluded by seniority metrics", () => {
  const junior = { advisor_id: "junior", name: "Junior Fixture", evidence_profile: { research_question_fit: { status: "direct" }, pi_role_confidence: { status: "emerging", level: "C" },
    doctoral_trajectory: { former_doctoral: [], emerging_pi_note: "No graduated doctoral students yet" } } };
  const senior = { advisor_id: "senior", name: "Senior Fixture", citations: 100000, h_index: 120, evidence_profile: { research_question_fit: { status: "adjacent" } } };
  const rows = buildMedicalDiscoveryView([senior, junior], minimal);
  assert.equal(rows[0].advisor_id, "junior", "direction fit orders display; citations and h-index do not participate");
  assert.equal(rows[0].comparisonGroup, "needs_verification");
  assert.ok(PI_ROLE_CONFIDENCE.includes("emerging"));
});

test("T23 last-author ambiguity caps at probable, never auto-verified", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { pi_role_confidence: { status: "probable", level: "B", reasons: ["last author without contribution statement"] } } });
  assert.equal(profile.piRoleConfidence.status, "probable");
  const bogus = normalizeMedicalEvidenceProfile({ evidence_profile: { pi_role_confidence: { status: "confirmed_by_position" } } });
  assert.equal(bogus.piRoleConfidence.status, "identity_unresolved", "unknown vocabulary never upgrades to verified");
});

test("T24 first-author transition can enter emerging PI validation", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { research_route_continuity: { status: "active_emerging" }, pi_role_confidence: { status: "emerging", level: "C" } } });
  assert.equal(profile.researchRouteContinuity.status, "active_emerging");
  assert.equal(compareMedicalCandidates({ evidenceProfile: { ...profile, researchQuestionFit: { status: "direct" } } },
    { evidenceProfile: { ...profile, researchQuestionFit: { status: "direct" }, researchRouteContinuity: { status: "occasional_participation" } } }) < 0, true);
});

test("T25 network recursion: ego network is depth 1 and the report does not expand collaborators", async () => {
  const bundle = await fixture("medical-discovery");
  const network = normalizeMedicalEvidenceProfile(bundle.advisors[0]).collaborationNetwork;
  assert.equal(network.depth, 1);
  const report = buildAdvisorReport(bundle);
  assert.equal((report.match(/<svg viewBox/g) || []).length, 1, "one ego network per advisor, none for collaborators");
});

test("T26 saturation stops when a round adds only duplicates", () => {
  assert.equal(saturationReached({ existingValidated: 12, newValidated: 0, round: 2 }).stop, true);
});

test("T27 WoS key with limited entitlement degrades to the probed tier", () => {
  const route = selectRoute("wos", { credentialStatus: "configured", probe: { wosTier: "limited" } });
  assert.equal(route.capability_tier, "limited");
  assert.equal(route.expanded_api, false);
});

test("T28 API failure degrades the route and never becomes not_found", () => {
  const route = selectRoute("openalex", { credentialStatus: "configured", probe: { authenticatedApi: false, anonymousApi: false }, hostTools: { builtinWeb: true } });
  assert.equal(route.selected_route, "browser");
  const capabilities = buildProviderCapabilities({ credentials: credentials(), probes: { openalex: { anonymousApi: false } } });
  assert.equal(capabilities.providers.openalex.selected_route, "alternative_sources");
  assert.ok(capabilities.principles.some((line) => /not_found in a public database != the PI has no funding/.test(line)));
});

test("T29 NSFC no-hit stays not_found with coverage limitation, never 'no NSFC'", () => {
  const observation = { retrieval_method: "static_web", accessed_at: now, final_url: "https://example.org/nsfc-search", extraction_status: "success", status: "not_found",
    claim: "No public NSFC record found in the checked scope", entity_id: "pi", fields_supported: ["latest_signals_projects"], limitations: "public coverage limited" };
  // not_found without documented search coverage is rejected outright.
  assert.throws(() => researchEvidence(observation), /not_found requires completed documented search coverage/);
  const row = researchEvidence({ ...observation, searched_sources: ["nsfc_public_query"], query_or_filter_summary: "name + institution", complete_results: true });
  assert.equal(row.status, "not_found");
  assert.doesNotMatch(row.claim, /无 NSFC|no NSFC funding/);
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { latest_signals: { projects: [] } } });
  assert.equal(profile.latestSignals.projects.length, 0);
  assert.equal(profile.currentActivity, "unclear");
});

test("T30 a bare student name without supervision evidence is recorded without doctoral status", () => {
  const profile = normalizeMedicalEvidenceProfile({ evidence_profile: { doctoral_trajectory: { current_doctoral: [{ name: "Name only" }] } } });
  assert.deepEqual(profile.doctoralTrajectory.currentDoctoral[0].supervisionEvidence, []);
  assert.equal(profile.doctoralTrajectory.currentDoctoral[0].degreeOrYear, null);
});

test("T31 junior PI without alumni gets a sample limitation, not a negative conclusion", async () => {
  const bundle = await fixture("medical-discovery");
  bundle.advisors[0].evidence_profile.doctoral_trajectory.former_doctoral = [];
  const report = buildAdvisorReport(bundle);
  assert.match(report, /新兴 PI/);
  assert.doesNotMatch(report, /培养成功率低|no successful/);
});

test("T32 no mentoring-style or personality inference exists in the medical vocabulary", async () => {
  const bundle = await fixture("medical-discovery");
  const report = buildAdvisorReport(bundle);
  assert.doesNotMatch(report, /指导风格|人格|培养氛围|mentoring style/);
  assert.ok(!MEDICAL_DETECTIVE_SECTIONS.some((id) => /work_style|guidance|atmosphere/.test(id)));
});

test("T33 subagents never write authoritative JSON; the merge layer is deterministic", () => {
  const output = { task_id: "t1", agent_role: "seed_scout", scope: {}, findings: [], new_entities: [{ entity_type: "advisor", advisor_id: "pi-1", name: "PI" }], conflicts: [], gaps: [], queries_executed: [], sources_checked: [] };
  const first = mergeSubagentOutputs([{ fileName: "b.json", output: { ...output, task_id: "t2" } }, { fileName: "a.json", output }], { credentials: credentials() });
  const second = mergeSubagentOutputs([{ fileName: "a.json", output }, { fileName: "b.json", output: { ...output, task_id: "t2" } }], { credentials: credentials() });
  assert.deepEqual(first.advisors, second.advisors);
  assert.deepEqual(first.advisors[0].source_task_ids, ["t1", "t2"]);
});

test("T34 secrets never reach prompts, subagent output, evidence or reports", async () => {
  const loaded = await loadCredentials({ repositoryRoot: null, platform: "linux", env: { HOME: "/h", OPENALEX_API_KEY: FAKE }, readFileImpl: async () => "" });
  const prompt = buildRunPrompt({ project: { ...normalizeProjectMetadata(minimal, { now }), path: "/fictional" }, userPrompt: "go", runDirectory: "/run", provider: "codex", mode: "finder" });
  assert.doesNotMatch(prompt, new RegExp(FAKE));
  assert.match(prompt, /key 值不得进入提示、Subagent 输出、evidence、日志或报告/);
  assert.equal(redactSecrets(`x ${FAKE}`, loaded).includes(FAKE), false);
  const merged = mergeSubagentOutputs([{ fileName: "leak.json", output: { task_id: "t", agent_role: "seed_scout", scope: {}, findings: [], new_entities: [{ entity_type: "advisor", advisor_id: "pi", note: FAKE }], conflicts: [], gaps: [], queries_executed: [], sources_checked: [] } }], { credentials: loaded });
  assert.equal(merged.advisors.length, 0);
  assert.equal(containsSecret(merged, loaded), false);
});

test("T35 credential discovery honours OS defaults and the override variable", () => {
  assert.equal(resolveCredentialsPath({ platform: "darwin", env: { HOME: "/Users/fixture" } }).path, "/Users/fixture/.config/boss-hunting/credentials.env");
  assert.equal(resolveCredentialsPath({ platform: "win32", env: { APPDATA: "C:\\AppData\\Roaming" } }).path, "C:\\AppData\\Roaming\\boss-hunting\\credentials.env");
  assert.equal(resolveCredentialsPath({ platform: "linux", env: { BOSS_HUNTING_CREDENTIALS_FILE: "/custom/creds.env" } }).source, "override");
});

test("T36 all credentials missing still yields a runnable public-only mode", () => {
  const capabilities = buildProviderCapabilities({ credentials: credentials(), hostTools: { builtinWeb: true } });
  assert.equal(capabilities.mode, "public_only");
  assert.ok(Object.values(capabilities.providers).every((route) => route.selected_route !== "authenticated_api"));
  assert.ok(Object.values(capabilities.providers).every((route) => ["anonymous_api", "browser", "alternative_sources"].includes(route.selected_route)));
});

test("T37 missing NCBI key prefers anonymous E-utilities over browser scraping", () => {
  assert.equal(selectRoute("ncbi", { credentialStatus: "unavailable", hostTools: { interactiveBrowser: true, builtinWeb: true } }).selected_route, "anonymous_api");
});

test("T38 missing CiNii App ID falls back to Browser Use with the actual retrieval method recorded", () => {
  assert.equal(selectRoute("cinii", { credentialStatus: "unavailable", hostTools: { interactiveBrowser: true } }).selected_route, "browser");
  const row = researchEvidence({ retrieval_method: "browser", retrieval_provider: "interactive_browser", retrieval_tool: "fixture_browser", accessed_at: now, final_url: "https://example.org/cinii-record", extraction_status: "success", status: "not_checked", claim: "c" });
  assert.equal(row.retrieval_method, "browser");
  assert.throws(() => researchEvidence({ retrieval_method: "official_api", retrieval_provider: "gpt_builtin_web", accessed_at: now, final_url: "https://example.org/x", extraction_status: "success" }), /static_web/);
});

test("T39 WoS API unavailable never pretends paid data via browser without authorized web access", () => {
  const route = selectRoute("wos", { credentialStatus: "unavailable", hostTools: { interactiveBrowser: true } });
  assert.equal(route.selected_route, "alternative_sources");
  assert.equal(route.authorized_browser, false);
  assert.deepEqual(route.alternatives, ["openalex", "semantic_scholar", "pubmed"]);
});

test("T40 API vs browser affiliation disagreement is kept as a conflict for Main Agent adjudication", () => {
  const output = (task, institution, method) => ({ task_id: task, agent_role: "identity_resolver", scope: {}, findings: [], conflicts: [], gaps: [], queries_executed: [],
    new_entities: [{ entity_type: "advisor", advisor_id: "pi", current_institution: institution, affiliation_as_of: method }], sources_checked: [] });
  const { advisors, evidence, report } = mergeSubagentOutputs([{ fileName: "api.json", output: output("api", "API Institute", "2024-01 api") }, { fileName: "web.json", output: output("web", "Official Web Institute", "2026-06 browser") }], { credentials: credentials() });
  assert.equal(advisors.length, 1);
  assert.equal(advisors[0].current_institution, "API Institute", "first value is kept, not overwritten");
  const conflict = evidence.find((row) => row.status === "conflict" && row.fields_supported.includes("current_institution"));
  assert.match(conflict.claim, /API Institute ⟷ Official Web Institute/);
  assert.equal(conflict.resolution, "pending_main_agent_adjudication");
  assert.equal(report.conflicts.length, 2);
});

// Live-behaviour scenarios: they depend on real retrieval or Agent judgement
// and are covered by SKILL.md / references / prompts rather than unit tests.
test.todo("T06 live: the author back-search must actually run against OpenAlex/PubMed before continuity is claimed");
test.todo("T07 live: real-world same-name disambiguation requires ORCID/OpenAlex/official-page retrieval");
test.todo("T19/T26 live: seed → PI extraction and saturation across real network rounds");
test.todo("T28/T38 live: real API outages and CiNii Browser Use sessions cannot be reproduced offline");
