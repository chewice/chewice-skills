import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import {
  MEDICAL_DEFAULT_DETECTIVE_SECTIONS,
  communityRefreshEligibility,
  confirmInvestigationDraft,
  getDetectiveSectionCatalog,
  investigationFingerprint,
  isInvestigationConfirmationCurrent,
  medicalIntakeStatus,
  normalizeProjectMetadata,
  readinessForProject,
  updateInvestigationDraft,
  validateInvestigationDraftAgainstCandidates,
  validateProjectMetadata,
} from "../../skills/advisor-pipeline/scripts/project-contract.mjs";
import { initializeProjectDirectory } from "../../skills/advisor-pipeline/scripts/init_project.mjs";
import { confirmInvestigationInProject } from "../../skills/advisor-pipeline/scripts/confirm_investigation.mjs";
import { buildInvestigationMenu, renderInvestigationMenu } from "../../skills/advisor-pipeline/scripts/render_investigation_menu.mjs";

const now = "2026-09-22T12:00:00.000Z";

test("built-in web is the default backend without enabling permissions or replacing explicit preferences", () => {
  const defaultPolicy = normalizeProjectMetadata({}).browserResearch;
  assert.equal(defaultPolicy.backend, "builtin_web");
  assert.equal(defaultPolicy.enabled, false);
  assert.equal(defaultPolicy.allowPublicDownloads, false);
  for (const backend of ["auto", "host-browser", "official_api"]) {
    const previous = { enabled: true, allowPublicDownloads: false, backend, policy: "public_read_only", extra: "keep" };
    assert.deepEqual(normalizeProjectMetadata({ browserResearch: previous }).browserResearch, previous);
  }
});

// Entirely synthetic configuration: no real advisor, CV or search result.
function medical(patch = {}) {
  return normalizeProjectMetadata({
    id: "medical-fixture", domainProfile: "medical", target: "中国大陆; 日本",
    medicalProfile: {
      fields: ["肿瘤学"], diseaseScope: "pan_disease", diseasesOrMechanisms: ["泛癌"],
      researchModes: ["计算与数据"], currentSkills: ["数据整理"], desiredTraining: ["统计方法"],
    }, ...patch,
  }, { now });
}

test("medical discovery accepts a completed profile without CV, degree or intake", () => {
  const project = medical();
  const ready = readinessForProject({ metadata: project });
  assert.equal(project.schemaVersion, 9);
  assert.equal(validateProjectMetadata(project).valid, true);
  assert.equal(ready.modes.finder.ready, true);
  assert.equal(ready.objectiveReady, false);
  assert.equal(ready.completionScope, "research_discovery");
  assert.equal(ready.modes.research_proposal.ready, false);
  assert.equal(project.cv, null);
  assert.equal(project.season, "");
  assert.equal(project.medicalProfile.diseaseScope, "pan_disease");
  assert.deepEqual(project.medicalProfile.currentSkills, ["数据整理"]);
  assert.deepEqual(project.medicalProfile.desiredTraining, ["统计方法"]);
  assert.equal(medicalIntakeStatus(project).nextStep, 4);
});

test("missing intake answers differ from explicit undecided and unrestricted", () => {
  const missing = medical({ target: "", medicalProfile: {} });
  assert.equal(readinessForProject({ metadata: missing }).phase1Ready, false);
  assert.equal(medicalIntakeStatus(missing).nextStep, 1);
  const explicit = medical({ target: "", medicalProfile: {
    fields: ["免疫学"], diseaseScope: "undecided",
    inputStatus: { researchModes: "undecided", regions: "unrestricted" },
  } });
  assert.equal(readinessForProject({ metadata: explicit }).phase1Ready, true);
  assert.deepEqual(explicit.medicalProfile.diseasesOrMechanisms, []);
  assert.equal(explicit.target, "");
});

test("medical application accepts sourced relevant background and preserves material gates", () => {
  const project = medical({ searchMode: "application", degree: "PhD", season: "2027",
    hardConstraints: "需要生活费支持", applicantBackground: {
      source: "self_reported", education: [{ degree: "MSc", evidence: "user statement" }],
      qualifications: [], researchExperience: [],
    } });
  const ready = readinessForProject({ metadata: project, candidates: [{ advisorProgramId: "fixture-real-mapping" }] });
  assert.equal(ready.phase1Ready, true);
  assert.equal(ready.modes.finder_objective.ready, true);
  assert.equal(ready.matchingSignal, "structured_background");
  assert.equal(ready.modes.outreach_email.ready, false);
  assert.equal(project.applicantBackground.source, "self_reported");
  assert.equal(project.cv, null);
  const unsourced = { ...project, applicantBackground: { education: ["MSc"] } };
  assert.equal(readinessForProject({ metadata: unsourced }).phase1Ready, false);
});

test("target is authoritative and medical fields survive repeated normalization", () => {
  const project = medical({ target: "美国; 瑞士", medicalProfile: {
    fields: ["免疫学"], diseaseScope: "mechanism_first", regions: ["Japan"],
    researchModes: ["实验机制"], futureField: { preserve: true },
  } });
  assert.deepEqual(project.medicalProfile.regions, ["美国", "瑞士"]);
  assert.deepEqual(normalizeProjectMetadata(project, { now }), project);
  assert.deepEqual(project.medicalProfile.futureField, { preserve: true });
  const cleared = normalizeProjectMetadata({ ...project, target: "", medicalProfile: {
    ...project.medicalProfile, inputStatus: { ...project.medicalProfile.inputStatus, regions: "unrestricted" },
  } }, { now });
  assert.equal(cleared.target, "");
  assert.deepEqual(cleared.medicalProfile.regions, []);
});

test("medical default sections remain public-only even with community resources requested", () => {
  const project = medical();
  assert.deepEqual(project.investigation.draft.selectedSections, MEDICAL_DEFAULT_DETECTIVE_SECTIONS);
  assert.deepEqual(getDetectiveSectionCatalog(project).filter((s) => s.defaultSelected).map((s) => s.id), MEDICAL_DEFAULT_DETECTIVE_SECTIONS);
  let investigation = updateInvestigationDraft(project.investigation, {
    selectedAdvisorProgramIds: ["fixture-real-mapping"], communitySources: { requested: true },
  }, now);
  assert.equal(investigation.draft.communitySources.requested, false);
  investigation = confirmInvestigationDraft(investigation, { expectedRevision: investigation.draft.revision, now });
  assert.equal(isInvestigationConfirmationCurrent(investigation), true);
  assert.equal(communityRefreshEligibility(investigation).allowed, false);
  assert.equal(investigation.confirmed.communitySources.consented, false);
  const extension = updateInvestigationDraft(investigation, { sourcePolicy: "community_allowed", communitySources: { requested: true } }, now);
  assert.equal(isInvestigationConfirmationCurrent(extension), false);
  assert.equal(communityRefreshEligibility(confirmInvestigationDraft(extension, { expectedRevision: extension.draft.revision, now })).allowed, true);
});

test("medical scope changes invalidate confirmation without losing the previous snapshot", () => {
  const project = medical();
  project.investigation = updateInvestigationDraft(project.investigation, { selectedAdvisorProgramIds: ["fixture-real-mapping"] }, now);
  project.investigation = confirmInvestigationDraft(project.investigation, { expectedRevision: project.investigation.draft.revision, now });
  assert.equal(isInvestigationConfirmationCurrent(normalizeProjectMetadata(project, { now }).investigation), true);
  for (const patch of [{ searchMode: "application" }, { target: "日本" }, { season: "2028" },
    { cv: { path: "inputs/revised-fixture-cv.txt", name: "Fixture CV", uploadedAt: now } },
    { medicalProfile: { ...project.medicalProfile, desiredTraining: ["实验技术"] } }]) {
    const changed = normalizeProjectMetadata({ ...project, ...patch }, { now });
    assert.equal(isInvestigationConfirmationCurrent(changed.investigation), false);
    assert.deepEqual(changed.investigation.confirmed, project.investigation.confirmed);
  }
});

test("schema 8 general projects retain legacy confirmation and gain no browser authority", () => {
  const selection = { selectedAdvisorProgramIds: ["fixture-real-mapping"], selectedSections: ["identity_current_role"], communitySources: { consented: false } };
  const confirmed = { ...selection, revision: 1, confirmedAt: now, source: "user_confirmed", fingerprint: investigationFingerprint(selection) };
  const project = normalizeProjectMetadata({ schemaVersion: 8, investigation: {
    draft: { ...selection, communitySources: { requested: false }, revision: 1, updatedAt: now }, confirmed,
  } }, { now });
  assert.equal(project.domainProfile, "general");
  assert.equal(project.evaluationMode, "weighted_score");
  assert.equal(project.browserResearch.enabled, false);
  assert.equal(project.browserResearch.allowPublicDownloads, false);
  assert.equal(project.investigation.confirmed.fingerprint, confirmed.fingerprint);
  assert.equal(isInvestigationConfirmationCurrent(project.investigation), true);
  assert.equal(readinessForProject({ metadata: project }).modes.finder.ready, false);
});

test("medical migration is reversible and idempotent; unmapped discovery does not create fake opportunities", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "medical-migration-fixture-"));
  try {
    const original = JSON.stringify({ ...medical(), schemaVersion: 8 });
    await writeFile(resolve(root, "project.json"), original);
    const first = await initializeProjectDirectory(root, { now });
    assert.equal(first.backups.length, 1);
    assert.equal(await readFile(first.backups[0], "utf8"), original);
    const advisorBytes = '[{"advisor_id":"synthetic-fixture-advisor","name":"Synthetic unmapped advisor"}]\n';
    await writeFile(resolve(root, "outputs/advisor_records.json"), advisorBytes);
    const second = await initializeProjectDirectory(root, { now: "2026-09-23T12:00:00.000Z" });
    assert.deepEqual(second.changes, []);
    assert.deepEqual(second.backups, []);
    assert.equal(await readFile(resolve(root, "outputs/advisor_records.json"), "utf8"), advisorBytes);
    assert.deepEqual(JSON.parse(await readFile(resolve(root, "outputs/candidates.json"), "utf8")), []);
    const menu = await buildInvestigationMenu(root);
    assert.equal(menu.candidates.length, 0);
    assert.match(renderInvestigationMenu(menu), /探索视图/);
    assert.doesNotMatch(renderInvestigationMenu(menu), /综合匹配/);
    assert.equal(validateInvestigationDraftAgainstCandidates(first.project.investigation, []).valid, false);
    assert.equal((await readdir(root)).filter((name) => name.includes("backup")).length, 1);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("initializer and direct confirmation reject future schemas without rewriting user files", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "medical-future-fixture-"));
  try {
    const original = '{"schemaVersion":99,"keep":"original"}';
    await writeFile(resolve(root, "project.json"), original);
    await assert.rejects(initializeProjectDirectory(root, { now }), /不能降级/);
    await mkdir(resolve(root, "outputs"), { recursive: true });
    await writeFile(resolve(root, "outputs/candidates.json"), "[]");
    await assert.rejects(confirmInvestigationInProject(root, {
      advisorProgramIds: [], selectedSections: [], now,
    }), /不能降级/);
    assert.equal(await readFile(resolve(root, "project.json"), "utf8"), original);
    assert.equal((await readdir(root)).some((name) => name.includes("backup")), false);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("migration never overwrites a same-timestamp backup", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "medical-backup-fixture-"));
  try {
    const previous = resolve(root, `project.json.backup-${now.replace(/[:.]/g, "-")}`);
    await writeFile(previous, "previous backup");
    await writeFile(resolve(root, "project.json"), '{"schemaVersion":8}');
    const result = await initializeProjectDirectory(root, { now });
    assert.notEqual(result.backups[0], previous);
    assert.equal(await readFile(previous, "utf8"), "previous backup");
    assert.equal(await readFile(result.backups[0], "utf8"), '{"schemaVersion":8}');
  } finally { await rm(root, { recursive: true, force: true }); }
});
