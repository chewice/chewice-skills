import assert from "node:assert/strict";
import test from "node:test";
import { applicantBackgroundFromForm, backgroundEntriesText, medicalDraftReadiness,
  medicalProfileFromForm, prefillRequestedInputs, medicalTargetText, browserResearchFromForm } from "../app/medical-intake.mjs";
import { normalizeProjectMetadata, readinessForProject } from "../../skills/advisor-pipeline/scripts/project-contract.mjs";

const form = { fields: "肿瘤；免疫", diseaseScope: "泛癌", researchModes: "实验机制",
  desiredTraining: "实验验证", currentSkills: "基础数据整理", searchMode: "discovery" };
const application = { target: "日本; 瑞士", degree: "", season: "", hardConstraints: "" };

test("medical draft readiness agrees with saved discovery/application requirements without a CV", () => {
  const discovery = medicalDraftReadiness(form, application);
  assert.deepEqual(discovery.missing, []);
  assert.equal(discovery.completed, discovery.total);
  const incomplete = medicalDraftReadiness({ ...form, searchMode: "application" }, application);
  assert.equal(incomplete.missing.length, 4);
  assert.equal(incomplete.completed, 3);
  assert.equal(incomplete.total, 7);
  const completeForm = { ...form, searchMode: "application", education: "用户自述硕士" };
  const completeApplication = { ...application, degree: "PhD", season: "2027", hardConstraints: "全奖" };
  const draft = medicalDraftReadiness(completeForm, completeApplication);
  const stored = normalizeProjectMetadata({ domainProfile: "medical", searchMode: "application",
    ...completeApplication, medicalProfile: medicalProfileFromForm({ ...completeForm, target: application.target }),
    applicantBackground: applicantBackgroundFromForm(completeForm) });
  const readiness = readinessForProject({ metadata: stored, cvValid: false });
  assert.deepEqual(draft.missing, readiness.missing);
  assert.equal(draft.completed, readiness.completed);
  assert.equal(draft.total, readiness.total);
  assert.equal(readiness.phase1Ready, true);
});

test("editing one background field preserves untouched structured education and provenance", () => {
  const previous = { source: "documented", education: [{ degree: "MSc", provenance: "local transcript" }],
    researchExperience: ["data preparation"], qualifications: [], notes: "keep attribution" };
  const displayed = { education: backgroundEntriesText(previous.education), researchExperience: "data preparation", qualifications: "" };
  assert.ok(!displayed.education.includes("[object Object]"));
  assert.deepEqual(applicantBackgroundFromForm(displayed, previous), previous);
  const edited = applicantBackgroundFromForm({ ...displayed, researchExperience: "data preparation；new self-reported project" }, previous);
  assert.deepEqual(edited.education, previous.education);
  assert.equal(edited.notes, previous.notes);
  assert.equal(edited.source, "self_reported");
  assert.deepEqual(edited.researchExperience, ["data preparation", "new self-reported project"]);
});

test("continuation prefill reuses saved facts and valid CV while preserving current edits", () => {
  const project = { degree: "PhD", season: "2027", target: "日本; 瑞士", cv: { valid: true, path: "inputs/cv.pdf" },
    medicalProfile: { fields: ["免疫"], diseaseScope: "泛癌", researchModes: [], inputStatus: { researchModes: "undecided" } },
    applicantBackground: { source: "self_reported", education: ["硕士"] } };
  const fields = ["cv", "degree", "season", "target", "medicalFields", "researchModes", "applicantBackground"].map((id) => ({ id }));
  const answers = prefillRequestedInputs(fields, project, { season: "2028" });
  assert.equal(answers.cv, "inputs/cv.pdf");
  assert.equal(answers.degree, "PhD");
  assert.equal(answers.season, "2028");
  assert.equal(answers.medicalFields, "免疫");
  assert.equal(answers.researchModes, "未定");
  assert.equal(answers.applicantBackground, "硕士");
  assert.equal(prefillRequestedInputs([{ id: "cv" }], { ...project, cv: { ...project.cv, valid: false } }).cv, "");
  assert.equal(prefillRequestedInputs([{ id: "degree" }], project, { degree: "" }).degree, "");
});

test("restoring an explicit unrestricted or undecided region preserves it when another field is saved", () => {
  for (const [status, label] of [["unrestricted", "不限"], ["undecided", "未定"]]) {
    const project = { domainProfile: "medical", target: "", medicalProfile: { inputStatus: { regions: status } } };
    const target = medicalTargetText(project);
    assert.equal(target, label);
    assert.equal(prefillRequestedInputs([{ id: "target" }], project).target, label);
    const updated = medicalProfileFromForm({ ...form, target, desiredTraining: "新训练" }, project.medicalProfile);
    assert.equal(updated.inputStatus.regions, status);
  }
});

test("saving unrelated medical inputs preserves disabled downloads, chosen backend and extension fields", () => {
  const previous = { enabled: true, policy: "public_read_only", backend: "host-browser",
    allowPublicDownloads: false, customScope: "existing public sources" };
  const restored = { browserEnabled: previous.enabled, browserDownloads: previous.allowPublicDownloads, desiredTraining: "新训练" };
  assert.deepEqual(browserResearchFromForm(restored, previous), previous);
  const enabledDownload = browserResearchFromForm({ ...restored, browserDownloads: true }, previous);
  assert.equal(enabledDownload.allowPublicDownloads, true);
  assert.equal(enabledDownload.backend, "host-browser");
  assert.equal(browserResearchFromForm({ browserEnabled: true }).allowPublicDownloads, false);
  assert.equal(browserResearchFromForm({}).backend, "builtin_web");
  assert.equal(browserResearchFromForm({}, { backend: "auto" }).backend, "auto");
});
