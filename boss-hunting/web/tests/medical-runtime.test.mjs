import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { createProjectStore } from "../local-runtime/project-store.mjs";
import { buildRunPrompt } from "../local-runtime/run-prompt.mjs";
import { parseInputRequest, verifyRunArtifacts } from "../local-runtime/run-artifacts.mjs";
import { medicalProfileFromForm, medicalInputPatch } from "../app/medical-intake.mjs";
import { buildPhaseOneTaskPrompt } from "../app/run-task-prompts.mjs";
import { MEDICAL_DEFAULT_DETECTIVE_SECTIONS } from "../../skills/advisor-pipeline/scripts/project-contract.mjs";
import { initializeProjectDirectory } from "../../skills/advisor-pipeline/scripts/init_project.mjs";
import { exportAdvisorReport } from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";
import { readStoredZipEntries } from "../../skills/advisor-pipeline/scripts/workbook-runtime.mjs";

const execute = promisify(execFile);
const repository = fileURLToPath(new URL("../../", import.meta.url));

// Fictional project inputs. These tests do not query or represent real advisors.
const input = { name: "Fixture medical discovery", slug: "medical-fixture", domainProfile: "medical", target: "日本; 瑞士",
  medicalProfile: { fields: ["免疫学"], diseaseScope: "机制优先", researchQuestions: ["Fixture question"], researchModes: ["实验机制"],
    // Legacy keys from schema 9 drafts must be dropped, never carried forward.
    currentSkills: ["数据整理"], desiredTraining: ["实验设计"] } };

async function withStore(run) {
  const root = await mkdtemp(resolve(tmpdir(), "boss-runtime-"));
  await mkdir(resolve(root, "skills"));
  try { await run(createProjectStore(root), root); } finally { await rm(root, { recursive: true, force: true }); }
}

test("T02 T05 T07 T09 T44 Web save/restart preserves medical discovery and authentic background", () => withStore(async (store, root) => {
  const created = await store.createProject(input);
  assert.equal(created.readiness.phase1Ready, true);
  assert.equal(created.cv, null);
  assert.equal(created.browserResearch.enabled, false);
  assert.deepEqual(created.investigation.draft.selectedSections, MEDICAL_DEFAULT_DETECTIVE_SECTIONS);
  assert.equal(created.investigation.draft.sourcePolicy, "public_only");
  const advisor = { advisor_id: "fictional-only", name: "Fictional Advisor", evidence_profile: { researchQuestionFit: { status: "direct" } } };
  await writeFile(resolve(created.path, "outputs/advisor_records.json"), JSON.stringify([advisor]));
  const restored = await createProjectStore(root).getProject(created.id);
  assert.equal(restored.discoveryAdvisors[0].advisor_id, advisor.advisor_id);
  assert.equal(restored.discoveryAdvisors[0].advisorProgramId, undefined);
  assert.equal(restored.candidates.length, 0);
  assert.equal(restored.medicalProfile.currentSkills, undefined);
  assert.equal(restored.medicalProfile.desiredTraining, undefined);
  assert.deepEqual(restored.medicalProfile.researchQuestions, ["Fixture question"]);
  assert.equal(restored.discoveryAdvisors[0].evidenceProfile.researchQuestionFit.status, "direct");
  const changed = await store.updateProject(created.id, { searchMode: "application", degree: "PhD", season: "2027", hardConstraints: "无自设条件",
    applicantBackground: { source: "self_reported", education: [{ degree: "Fictional MSc", provenance: "user" }] } });
  assert.equal(changed.readiness.modes.finder.ready, true);
  assert.equal(changed.readiness.modes.research_proposal.ready, false);
  assert.equal(await readFile(resolve(created.path, "outputs/advisor_records.json"), "utf8"), JSON.stringify([advisor]));
}));

test("medical switch never inherits general community scope or hidden scoring", () => withStore(async (store) => {
  const general = await store.createProject({ name: "General fixture", slug: "general-fixture" });
  const medical = await store.updateProject(general.id, { ...input, investigation: undefined });
  assert.equal(medical.investigation.draft.sourcePolicy, "public_only");
  assert.deepEqual(medical.investigation.draft.selectedSections, MEDICAL_DEFAULT_DETECTIVE_SECTIONS);
  assert.equal(medical.investigation.confirmed, null);
  assert.equal(medical.evaluationMode, "evidence_profile");
}));

test("T44 Web migration backs up old bytes once and preserves unrelated fields", () => withStore(async (store) => {
  const created = await store.createProject({ name: "Legacy fixture", slug: "legacy-fixture" });
  const file = resolve(created.path, "project.json");
  const raw = JSON.stringify({ ...JSON.parse(await readFile(file, "utf8")), schemaVersion: 8, customExtension: { keep: "yes" } });
  await writeFile(file, raw);
  await store.updateProject(created.id, { name: "Updated" });
  await store.updateProject(created.id, { name: "Updated again" });
  const backups = (await readdir(created.path)).filter((name) => name.startsWith("project.json.backup-"));
  assert.equal(backups.length, 1);
  assert.equal(await readFile(resolve(created.path, backups[0]), "utf8"), raw);
  const restored = await store.getProject(created.id);
  assert.equal(restored.customExtension.keep, "yes");
  assert.equal(restored.domainProfile, "general");
}));

test("T01 medical form retains undecided versus unasked and never stores skills or desired training", () => {
  const profile = medicalProfileFromForm({ fields: "肿瘤", diseaseScope: "泛癌", researchModes: "未定", methodPreferences: "单细胞", desiredTraining: "统计", currentSkills: "数据整理", target: "不限" });
  assert.equal(profile.inputStatus.researchModes, "undecided");
  assert.equal(profile.inputStatus.regions, "unrestricted");
  assert.deepEqual(profile.methodPreferences, ["单细胞"]);
  assert.ok(!("currentSkills" in profile) && !("desiredTraining" in profile));
  const cleared = medicalProfileFromForm({ target: "" }, profile);
  assert.equal(cleared.inputStatus.regions, "unasked");
  const patch = medicalInputPatch("medicalFields", "免疫;神经", { medicalProfile: profile });
  assert.deepEqual(patch.medicalProfile.fields, ["免疫", "神经"]);
  assert.deepEqual(patch.medicalProfile.methodPreferences, ["单细胞"]);
});

test("medical runtime prompts and continuation do not reinstate CV or numeric selector gates", () => {
  const medicalProfile = Object.fromEntries(Object.entries(input.medicalProfile).filter(([key]) => !["currentSkills", "desiredTraining"].includes(key)));
  const project = { ...input, medicalProfile, path: "/fictional/project", searchMode: "discovery", evaluationMode: "evidence_profile" };
  const prompt = buildRunPrompt({ project, userPrompt: "Find advisors", runDirectory: "/fictional/run", provider: "codex", mode: "finder" });
  assert.match(prompt, /discovery 不读取 CV、成绩或申请者能力/);
  assert.match(prompt, /Seeds/);
  assert.match(prompt, /merge_subagent_findings\.mjs/);
  assert.match(prompt, /credentials\.mjs --json/);
  assert.match(prompt, /configured \/ unavailable \/ invalid \/ capability-limited/);
  // Removed dimensions only appear inside the explicit deletion list.
  assert.match(prompt, /已删除范围：不评估训练匹配/);
  assert.doesNotMatch(prompt, /trainingFit|desiredTraining|currentSkills|scientificFit/);
  assert.match(prompt, /默认 builtin_web，旧 auto 也优先 GPT 内置网页工具/);
  assert.match(prompt, /retrieval_method=static_web、retrieval_provider=gpt_builtin_web/);
  assert.match(prompt, /保留用户显式 backend 与 enabled\/download 授权/);
  assert.match(prompt, /find 无匹配不等于站点查无/);
  assert.doesNotMatch(prompt, /必须依据 CV 证据把候选标成|会由确定性脚本重算为 60%/);
  assert.match(buildPhaseOneTaskPrompt({ project }), /探索不读取 CV、成绩或申请者能力/);
  const request = parseInputRequest({ type: "input.requested", fields: [{ id: "researchModes", label: "研究方式" }] });
  assert.equal(request.fields[0].id, "researchModes");
});

test("T46 incomplete discovery artifacts cannot claim completion", () => withStore(async (store) => {
  const project = await store.createProject(input);
  const outcome = await verifyRunArtifacts({ projectPath: project.path, mode: "finder" });
  assert.equal(outcome.complete, false);
  assert.equal(outcome.completionScope, "research_discovery");
  assert.ok(outcome.missing.some((message) => message.includes("没有实际")));
}));

test("direct medical discovery and application produce HTML and workbooks from shared fictional records", async (t) => {
  for (const name of ["medical-discovery", "medical-application"]) await t.test(name, async () => {
    const bundle = JSON.parse(await readFile(new URL(`./fixtures/${name}.json`, import.meta.url), "utf8"));
    const root = await mkdtemp(resolve(tmpdir(), "boss-direct-"));
    try {
      const initialized = await initializeProjectDirectory(root, { projectPatch: bundle.project });
      assert.equal(initialized.project.domainProfile, "medical");
      for (const [file, rows] of Object.entries({ "advisor_records.json": bundle.advisors, "program_records.json": bundle.programs, "candidates.json": bundle.candidates,
        "evidence.json": bundle.evidence.map((row) => ({ ...row, ...(row.retrieval_method ? { accessed_at: "2026-09-22T00:00:00Z", page_title: "Fictional observation fixture", failure_reason: "Synthetic fixture; no live retrieval" } : {}) })) })) {
        await writeFile(resolve(root, "outputs", file), JSON.stringify(rows));
      }
      await execute(process.execPath, [resolve(repository, "skills/advisor-finder/scripts/apply_matching_strategy.mjs"), "--project-root", root]);
      const selected = JSON.parse(await readFile(resolve(root, "outputs/candidates.json"), "utf8"));
      const exportedInput = resolve(root, "outputs/export-input.json");
      await writeFile(exportedInput, JSON.stringify({ project: initialized.project, advisorRecords: bundle.advisors, candidates: selected, evidence: bundle.evidence }));
      const prefix = bundle.project.searchMode === "discovery" ? "advisor_research_discovery" : "advisor_shortlist";
      await execute(process.execPath, [resolve(repository, "skills/advisor-finder/scripts/build_advisor_excel.mjs"), "--input", exportedInput, "--output", resolve(root, `outputs/${prefix}_20260922.xlsx`)]);
      const noHtml = await verifyRunArtifacts({ projectPath: root, mode: "finder" });
      assert.equal(noHtml.complete, false);
      assert.ok(noHtml.missing.some((message) => message.includes("HTML")));
      await exportAdvisorReport(root);
      const completed = await verifyRunArtifacts({ projectPath: root, mode: "finder" });
      assert.equal(completed.complete, true, completed.missing.join("; "));
      assert.equal(completed.completionScope, bundle.project.searchMode === "discovery" ? "research_discovery" : "application_screening");
      if (bundle.project.searchMode === "discovery") {
        assert.equal(selected.length, 0);
        assert.equal(completed.counts.discoveryCount, 1);
      }
      const unchanged = await initializeProjectDirectory(root, { projectPatch: bundle.project });
      assert.deepEqual(unchanged.changes, []);
    } finally { await rm(root, { recursive: true, force: true }); }
  });
});

test("CV-only medical application survives selection, export, confirmation and restart, then downgrades missing or escaped CV", () => withStore(async (store, root) => {
  const bundle = JSON.parse(await readFile(new URL("./fixtures/medical-application.json", import.meta.url), "utf8"));
  let project = await store.createProject({ ...bundle.project, name: "Fictional CV-only application", slug: "cv-only-fixture", applicantBackground: null });
  const cvPath = resolve(project.path, "inputs/fixture-cv.txt");
  await writeFile(cvPath, "Fictional CV: research master's qualification. Synthetic local test only.");
  project = await store.setProjectCv(project.id, { path: "inputs/fixture-cv.txt", name: "fixture-cv.txt" });
  assert.equal(project.readiness.cvValid, true);
  assert.equal(project.applicantBackground.source, "not_provided");
  assert.deepEqual(project.applicantBackground.education, []);
  const candidate = { ...bundle.candidates[0], eligibilityEvidence: {
    ...bundle.candidates[0].eligibilityEvidence, sourceIds: ["fixture-terms", "fixture-cv-review"],
  } };
  const evidence = [bundle.evidence[0], { evidence_id: "fixture-cv-review", claim_type: "fact", status: "verified",
    claim: "Synthetic fixture records the supplied CV qualification; no real applicant evaluated", source_type: "user_supplied_cv" }];
  for (const [file, rows] of Object.entries({ "advisor_records.json": bundle.advisors, "program_records.json": bundle.programs,
    "candidates.json": [candidate], "evidence.json": evidence })) {
    await writeFile(resolve(project.path, "outputs", file), JSON.stringify(rows));
  }
  await execute(process.execPath, [resolve(repository, "skills/advisor-finder/scripts/apply_matching_strategy.mjs"), "--project-root", project.path]);
  const selected = JSON.parse(await readFile(resolve(project.path, "outputs/candidates.json"), "utf8"));
  assert.equal(selected[0].feasibility, "eligible");
  project = await createProjectStore(root).getProject(project.id);
  assert.equal(project.candidates[0].feasibility, "eligible");
  assert.equal(project.readiness.modes.finder.ready, true);
  const exportInput = resolve(project.path, "outputs/cv-export-input.json");
  const workbookPath = resolve(project.path, "outputs/advisor_shortlist_cv-fixture.xlsx");
  await writeFile(exportInput, JSON.stringify({ project, cvValid: project.readiness.cvValid,
    advisorRecords: bundle.advisors, candidates: selected, evidence }));
  await execute(process.execPath, [resolve(repository, "skills/advisor-finder/scripts/build_advisor_excel.mjs"),
    "--input", exportInput, "--output", workbookPath], { env: { ...process.env, ADVISOR_ATLAS_FORCE_PORTABLE_XLSX: "1" } });
  const worksheet = (await readStoredZipEntries(workbookPath)).get("xl/worksheets/sheet1.xml").toString();
  assert.match(worksheet, /<t xml:space="preserve">eligible<\/t>/);
  let report = await exportAdvisorReport(project.path);
  assert.match(await readFile(report.output, "utf8"), /<div class="fact-item">符合已核实条件<\/div>/);
  const complete = await verifyRunArtifacts({ projectPath: project.path, mode: "finder" });
  assert.equal(complete.complete, true, complete.missing.join("; "));
  project = await store.updateProject(project.id, { investigation: {
    selectedAdvisorProgramIds: [candidate.advisorProgramId], selectedSections: ["research_mainline_5y"],
  } });
  // confirmInvestigation internally reloads candidates without a caller-provided cvValid.
  project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
  assert.equal(project.candidates[0].feasibility, "eligible");
  assert.deepEqual(project.investigation.confirmed.selectedAdvisorProgramIds, [candidate.advisorProgramId]);
  await rm(cvPath);
  for (const state of ["missing", "escaped symlink"]) {
    if (state === "escaped symlink") {
      const outside = resolve(root, "outside-cv.txt");
      await writeFile(outside, "Fictional document outside project inputs");
      await symlink(outside, cvPath);
    }
    const restored = await createProjectStore(root).getProject(project.id);
    assert.equal(restored.readiness.cvValid, false, state);
    assert.equal(restored.readiness.modes.finder.ready, false, state);
    assert.equal(restored.candidates[0].feasibility, "needs_confirmation", state);
    report = await exportAdvisorReport(project.path);
    assert.doesNotMatch(await readFile(report.output, "utf8"), /<div class="fact-item">符合已核实条件<\/div>/, state);
    const obsolete = await verifyRunArtifacts({ projectPath: project.path, mode: "finder" });
    assert.equal(obsolete.complete, false, state);
    assert.match(obsolete.missing.join("; "), /资格|已核实证据/, state);
  }
}));
