import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { createProjectStore } from "../local-runtime/project-store.mjs";
import { verifyRunArtifacts } from "../local-runtime/run-artifacts.mjs";
import { readinessForProject } from "../../skills/advisor-pipeline/scripts/project-contract.mjs";
import { normalizeMedicalCandidate } from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";
import { buildMedicalWorkbookSheets } from "../../skills/advisor-pipeline/scripts/medical-workbook.mjs";
import { writePortableXlsx } from "../../skills/advisor-pipeline/scripts/workbook-runtime.mjs";
import { exportAdvisorReport } from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";

// Isolated fictional records test provenance gates, not medical conclusions.
const advisor = { advisor_id: "fixture-advisor", name: "Fictional Advisor" };
const program = { program_id: "fixture-phd", degree: "PhD", intake: "2027" };
const candidate = { advisorProgramId: "fixture-advisor-phd-2027", advisor_id: advisor.advisor_id,
  program_id: program.program_id, degree: "PhD", intake: "2027" };

async function withProject(run) {
  const root = await mkdtemp(resolve(tmpdir(), "medical-confirmation-"));
  await mkdir(resolve(root, "skills"));
  const store = createProjectStore(root);
  try {
    let project = await store.createProject({ name: "Fictional medical project", slug: "medical-gate",
      domainProfile: "medical", searchMode: "application", target: "日本", degree: "PhD", season: "2027",
      hardConstraints: "无自设条件", applicantBackground: { source: "self_reported", education: ["Fixture MSc"] },
      medicalProfile: { fields: ["免疫"], diseaseScope: "机制优先", researchModes: ["实验"] } });
    await writeJson(project, "candidates.json", [normalizeMedicalCandidate(candidate, project)]);
    await writeJson(project, "advisor_records.json", [advisor]);
    await writeJson(project, "program_records.json", [program]);
    project = await store.updateProject(project.id, { investigation: {
      selectedAdvisorProgramIds: [candidate.advisorProgramId], selectedSections: ["research_mainline_5y"],
    } });
    project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
    await writeDetective(project);
    await run({ root, store, project: await store.getProject(project.id) });
  } finally { await rm(root, { recursive: true, force: true }); }
}

async function writeJson(project, name, value) {
  await writeFile(resolve(project.path, "outputs", name), JSON.stringify(value));
}

async function writeDetective(project) {
  const confirmed = project.investigation.confirmed;
  await writeJson(project, "detective-results.json", {
    confirmedRevision: confirmed.revision, confirmedFingerprint: confirmed.fingerprint,
    selectedSections: confirmed.selectedSections,
    results: [{ advisorProgramId: candidate.advisorProgramId,
      sections: { research_mainline_5y: { status: "not_completed", summary: "Fictional test; no research performed" } } }],
  });
}

async function writeRanking(project) {
  await writeJson(project, "ranking.json", { rankingMode: "evidence_profile",
    confirmedRevision: project.investigation.confirmed.revision,
    confirmedFingerprint: project.investigation.confirmed.fingerprint,
    rankings: [normalizeMedicalCandidate(candidate, project)],
  });
}

test("medical comparison rejects changed scope and old Detective results after reconfirmation", () => withProject(async ({ root, store, project }) => {
  assert.equal(project.readiness.modes.ranking.ready, true);
  assert.equal(project.detectiveResults.confirmedFingerprint, project.investigation.confirmed.fingerprint);
  project = await store.updateProject(project.id, { medicalProfile: { researchQuestions: ["新的科学问题"] } });
  assert.equal(project.readiness.modes.detective.ready, false);
  assert.equal(project.readiness.modes.ranking.ready, false);
  project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
  assert.equal(project.readiness.modes.detective.ready, true);
  assert.equal(project.readiness.modes.ranking.ready, false);
  await writeDetective(project);
  const reopened = await createProjectStore(root).getProject(project.id);
  assert.equal(reopened.readiness.modes.ranking.ready, true);
  assert.equal(reopened.detectiveResults.confirmedRevision, reopened.investigation.confirmed.revision);
}));

test("medical application materials cannot reuse an old ranking after renewed investigation", () => withProject(async ({ store, project }) => {
  await writeFile(resolve(project.path, "inputs", "fixture.txt"), "Fictional test applicant CV");
  project = await store.setProjectCv(project.id, { path: "inputs/fixture.txt", name: "fixture.txt" });
  assert.equal(project.readiness.modes.ranking.ready, false, "Changed CV invalidates prior scope");
  project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
  await writeDetective(project);
  await writeRanking(project);
  project = await store.updateProject(project.id, { applicantName: "Test Applicant", applicationMaterials: {
    advisorProgramId: candidate.advisorProgramId, materials: ["outreach_email"], order: ["outreach_email"],
  } });
  project = await store.confirmApplicationMaterials(project.id, { draftRevision: project.applicationMaterials.draft.revision });
  assert.equal(project.readiness.modes.outreach_email.ready, true);
  project = await store.updateProject(project.id, { medicalProfile: { researchQuestions: ["新的科学问题"] } });
  assert.equal(project.rankings.length, 0);
  assert.equal(project.readiness.modes.outreach_email.ready, false);
  project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
  await writeDetective(project);
  project = await store.getProject(project.id);
  assert.equal(project.readiness.modes.ranking.ready, true);
  assert.equal(project.rankings.length, 0);
  assert.equal(project.readiness.modes.outreach_email.ready, false);
  await writeRanking(project);
  project = await store.getProject(project.id);
  assert.equal(project.rankings.length, 1);
  assert.equal(project.readiness.modes.outreach_email.ready, true);
}));

test("medical completion rejects an old launch snapshot and unstamped ranking arrays", () => withProject(async ({ store, project }) => {
  const launched = { confirmedRevision: project.investigation.confirmed.revision,
    confirmedFingerprint: project.investigation.confirmed.fingerprint };
  project = await store.updateProject(project.id, { medicalProfile: { researchQuestions: ["新的科学问题"] } });
  project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
  await writeDetective(project);
  await writeRanking(project);
  await writeJson(project, "matching-audit.json", { matchingContractVersion: 3, selectedCount: 1 });
  await writePortableXlsx({ sheets: buildMedicalWorkbookSheets({ project, candidates: [candidate], advisorRecords: [advisor] }) },
    resolve(project.path, "outputs", "advisor_application_ready_20260922.xlsx"));
  await exportAdvisorReport(project.path);
  const options = { projectPath: project.path, mode: "ranking" };
  const stale = await verifyRunArtifacts({ ...options, ...launched });
  assert.equal(stale.complete, false);
  assert.ok(stale.missing.some((item) => item.includes("运行期间已变化")));
  const current = await verifyRunArtifacts({ ...options, confirmedRevision: project.investigation.confirmed.revision,
    confirmedFingerprint: project.investigation.confirmed.fingerprint });
  assert.equal(current.complete, true, current.missing.join("; "));
  await writeJson(project, "ranking.json", [normalizeMedicalCandidate(candidate, project)]);
  const unstamped = await verifyRunArtifacts(options);
  assert.equal(unstamped.complete, false);
  assert.ok(unstamped.missing.some((item) => item.includes("必须绑定当前调查确认")));
  assert.equal((await store.getProject(project.id)).rankings.length, 0);
}));

test("general projects retain legacy result and bare-ranking compatibility", async () => {
  assert.equal(readinessForProject({ metadata: { domainProfile: "general" },
    detectiveResults: { results: [{ advisorProgramId: "legacy-row" }] } }).modes.ranking.ready, true);
  const root = await mkdtemp(resolve(tmpdir(), "general-ranking-compat-"));
  await mkdir(resolve(root, "skills"));
  try {
    const store = createProjectStore(root);
    const project = await store.createProject({ name: "Legacy", slug: "general-gate" });
    await writeJson(project, "ranking.json", [{ advisorProgramId: "legacy-row", totalScore: 8 }]);
    assert.equal((await store.getProject(project.id)).rankings[0].totalScore, 8);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("medical material completion keeps the investigation snapshot captured at launch", () => withProject(async ({ store, project }) => {
  await writeRanking(project);
  project = await store.updateProject(project.id, { applicationMaterials: {
    advisorProgramId: candidate.advisorProgramId, materials: ["outreach_email"], order: ["outreach_email"],
  } });
  project = await store.confirmApplicationMaterials(project.id, { draftRevision: project.applicationMaterials.draft.revision });
  const launched = { projectPath: project.path, mode: "outreach_email", advisorProgramId: candidate.advisorProgramId,
    confirmedRevision: project.applicationMaterials.confirmed.revision,
    confirmedFingerprint: project.applicationMaterials.confirmed.fingerprint,
    investigationConfirmedRevision: project.investigation.confirmed.revision,
    investigationConfirmedFingerprint: project.investigation.confirmed.fingerprint };
  // No applicant material is manufactured here: only freshness diagnostics are compared.
  const initial = await verifyRunArtifacts(launched);
  assert.ok(!initial.missing.some((item) => /比较结果已失效|医学调查确认在材料运行期间/.test(item)));
  project = await store.updateProject(project.id, { medicalProfile: { researchQuestions: ["新的科学问题"] } });
  const changed = await verifyRunArtifacts(launched);
  assert.equal(changed.complete, false);
  assert.ok(changed.missing.some((item) => item.includes("比较结果已失效")));
  project = await store.confirmInvestigation(project.id, { draftRevision: project.investigation.draft.revision });
  await writeDetective(project);
  await writeRanking(project);
  const renewed = await verifyRunArtifacts(launched);
  assert.equal(renewed.complete, false);
  assert.ok(renewed.missing.some((item) => item.includes("医学调查确认在材料运行期间已变化")));
}));
