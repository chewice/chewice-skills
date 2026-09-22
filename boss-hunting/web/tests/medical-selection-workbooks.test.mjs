import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { buildPortfolioShortlist, mergePriorSelectionForRerun } from "../../skills/advisor-finder/scripts/apply_matching_strategy.mjs";
import { buildMedicalDiscoveryView, hasReadableProjectCv, normalizeMedicalCandidate, validateMedicalCandidateMappings } from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";
import { buildMedicalWorkbookSheets } from "../../skills/advisor-pipeline/scripts/medical-workbook.mjs";
import { readStoredZipEntries, writeWorkbook, formulaCell, safeSpreadsheetText } from "../../skills/advisor-pipeline/scripts/workbook-runtime.mjs";

const execute = promisify(execFile);
const repository = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
// All identities, projects and evidence IDs in this test are fictional fixtures.
const project = {
  domainProfile: "medical", searchMode: "application", evaluationMode: "evidence_profile",
  shortlistTarget: 5, hardConstraints: "", portfolioStrategy: "conservative",
  applicantBackground: { source: "self_reported", education: ["Fixture master's qualification"] },
  medicalProfile: { diseasesOrMechanisms: ["泛癌"], researchModes: ["计算与数据"], desiredTraining: ["统计方法"] },
};
function evidence(id, intake = "2027") {
  return { status: "verified", advisorProgramId: id, intake, sourceIds: ["fixture-official-evidence"] };
}
function candidate(id, override = {}) {
  return {
    advisorProgramId: id, advisor_id: `advisor-${id}`, name: `Fixture ${id}`, school: "Fixture University",
    program: "Fixture PhD", degree: "PhD", intake: "2027", applicationPathway: "committee_led",
    fit: 10, profileMatch: 10, overallMatch: 10, totalScore: 99, competitiveness: "reach",
    evidenceProfile: { scientificFit: { status: "strong", sourceIds: ["fixture-paper"] }, trainingFit: { status: "unknown" } },
    ...override,
  };
}

test("T28 medical evidence selection ignores numeric fallback and reach quotas", () => {
  const result = buildPortfolioShortlist(Array.from({ length: 6 }, (_, index) => candidate(String(index))), project);
  assert.equal(result.selected.length, 5);
  assert.equal(result.audit.reachCap, null);
  for (const row of result.selected) {
    assert.equal(row.overallMatch, null);
    assert.equal(row.profileMatch, null);
    assert.equal(row.fit, null);
    assert.equal(row.totalScore, null);
    assert.equal(row.competitiveness, "unknown");
    assert.equal(row.rankSemantics, "display_order");
  }
  assert.equal(result.excluded[0].exclusionReason, "research_budget_deferred");
});

test("T30 T31 sparse strong relevance survives rich weak pages and unknowns stay unknown", () => {
  const sparse = candidate("sparse", { fit: null, profileMatch: null });
  const rich = Array.from({ length: 5 }, (_, index) => candidate(`rich-${index}`, {
    feasibility: "eligible", hardConstraintStatus: "pass", sourceIds: Array(25).fill("fixture-copy"),
    evidenceProfile: { scientificFit: { status: "adjacent" }, trainingFit: { status: "supported" } },
  }));
  const result = buildPortfolioShortlist([...rich, sparse], project);
  assert.equal(result.selected[0].advisorProgramId, "sparse");
  assert.equal(result.selected[0].hardConstraintStatus, "unknown");
  assert.equal(result.selected[0].feasibility, "needs_confirmation");
  assert.equal(result.selected[0].comparisonGroup, "needs_verification");
});

test("T24 T29 exclusion requires verified evidence scoped to this exact opportunity", () => {
  const input = [
    candidate("ineligible", { feasibility: "ineligible", eligibilityEvidence: evidence("ineligible") }),
    candidate("hard-fail", { hardConstraintStatus: "fail", hardConstraintEvidence: evidence("hard-fail") }),
    candidate("closed", { opportunityStatus: "verified_closed", opportunityEvidence: evidence("closed") }),
    candidate("new-intake", { opportunityStatus: "verified_closed", opportunityEvidence: evidence("new-intake", "2026") }),
    candidate("wrong-program", { opportunityStatus: "verified_closed", opportunityEvidence: evidence("old-program") }),
    candidate("unsupported", { feasibility: "ineligible", hardConstraintStatus: "fail" }),
  ];
  const result = buildPortfolioShortlist(input, project);
  assert.deepEqual(result.excluded.map((row) => row.advisorProgramId), ["ineligible", "hard-fail", "closed"]);
  assert.equal(result.selected.find((row) => row.advisorProgramId === "new-intake").opportunityStatus, "unknown");
  assert.equal(result.selected.find((row) => row.advisorProgramId === "wrong-program").opportunityStatus, "unknown");
  assert.equal(result.selected.find((row) => row.advisorProgramId === "unsupported").feasibility, "needs_confirmation");
});

test("T25 committee and rotation paths do not require a PI vacancy advert", () => {
  const row = normalizeMedicalCandidate(candidate("committee", {
    feasibility: "eligible", eligibilityEvidence: evidence("committee"), rotation: "required",
  }), project);
  assert.equal(row.comparisonGroup, "actionable");
  assert.equal(row.recommendedAction, "apply_program");
  assert.equal(row.opportunityStatus, "unknown");
});

test("T04 applicant eligibility stays pending without real background even when an old row says eligible", () => {
  const row = normalizeMedicalCandidate(candidate("without-background", {
    feasibility: "eligible", eligibilityEvidence: evidence("without-background"),
  }), { ...project, applicantBackground: null, cv: null });
  assert.equal(row.feasibility, "needs_confirmation");
  assert.equal(row.comparisonGroup, "needs_verification");
});

test("CV-only eligibility requires actual readable project input, not persisted path or valid flag", async () => {
  const scratch = await mkdtemp(resolve(tmpdir(), "medical-cv-readability-"));
  try {
    await mkdir(resolve(scratch, "inputs"));
    await writeFile(resolve(scratch, "inputs/nonempty.txt"), "Fictional CV input");
    await writeFile(resolve(scratch, "inputs/empty.txt"), "");
    await writeFile(resolve(scratch, "outside.txt"), "Not an accepted input");
    await symlink(resolve(scratch, "outside.txt"), resolve(scratch, "inputs/escaped.txt"));
    for (const path of ["inputs/missing.txt", "inputs/empty.txt", "inputs", "outside.txt", "inputs/escaped.txt"]) {
      assert.equal(await hasReadableProjectCv(scratch, { path, valid: true }), false, path);
    }
    assert.equal(await hasReadableProjectCv(scratch, { path: "inputs/nonempty.txt" }), true);
    const row = candidate("cv-only", { feasibility: "eligible", eligibilityEvidence: evidence("cv-only") });
    const options = { ...project, applicantBackground: null, cv: { path: "inputs/nonempty.txt", valid: true } };
    assert.equal(normalizeMedicalCandidate(row, options).feasibility, "needs_confirmation");
    assert.equal(normalizeMedicalCandidate(row, { ...options, cvValid: true }).feasibility, "eligible");
  } finally { await rm(scratch, { recursive: true, force: true }); }
});

test("explicit no-additional-constraints declaration does not invent a blocked hard condition", () => {
  const result = normalizeMedicalCandidate(candidate("unconstrained", {
    feasibility: "eligible", eligibilityEvidence: evidence("unconstrained"),
  }), { ...project, hardConstraints: "无自设硬条件" });
  assert.equal(result.hardConstraintStatus, "unknown");
  assert.equal(result.comparisonGroup, "actionable");
});

test("production evidence references cannot exclude with missing, stale, inaccessible or wrong-intake facts", () => {
  const row = candidate("scoped", { program_id: "fixture-program", opportunityStatus: "verified_closed", opportunityEvidence: evidence("scoped") });
  const source = { evidence_id: "fixture-official-evidence", entity_id: "fixture-program", status: "verified",
    claim_type: "fact", fields_supported: ["opportunity"], intake: "2027", extraction_status: "success" };
  assert.equal(normalizeMedicalCandidate(row, { ...project, evidenceRecords: [source] }).recommendedAction, "exclude");
  for (const evidenceRecords of [[], [{ ...source, status: "stale" }], [{ ...source, status: "inaccessible" }],
    [{ ...source, extraction_status: "partial" }], [{ ...source, intake: "2026" }],
    [{ ...source, claim_type: "interpretation" }], [{ ...source, fields_supported: ["grant_role"] }]]) {
    const result = normalizeMedicalCandidate(row, { ...project, evidenceRecords });
    assert.equal(result.opportunityStatus, "unknown");
    assert.notEqual(result.recommendedAction, "exclude");
  }
});

test("T02 T32 discovery records have real advisor identity and no fabricated material target", () => {
  const input = [{ advisor_id: "fixture-advisor", name: "Fixture Advisor", feasibility: "eligible",
    evidence_profile: { scientific_fit: { status: "strong" }, training_fit: { status: "unknown" } } }];
  const rows = buildMedicalDiscoveryView(input, { ...project, searchMode: "discovery" });
  assert.equal(rows[0].advisor_id, "fixture-advisor");
  assert.equal(rows[0].evidenceProfile.scientificFit.status, "strong");
  assert.equal(rows[0].feasibility, "needs_confirmation");
  assert.ok(!("advisorProgramId" in rows[0]));
  assert.ok(!("program" in rows[0]));
  assert.ok(!("intake" in rows[0]));
  assert.throws(() => buildMedicalDiscoveryView([{ name: "anonymous fixture" }]), /advisor_id/);
  assert.throws(() => buildPortfolioShortlist([candidate("../unsafe")], project), /不安全/);
  assert.throws(() => buildPortfolioShortlist(input, project), /advisorProgramId/);
});

test("T45 medical rerun preserves exclusions and deterministic tie ordering", () => {
  const input = [candidate("z"), candidate("a"), candidate("excluded", {
    feasibility: "ineligible", eligibilityEvidence: evidence("excluded"),
  })];
  const first = buildPortfolioShortlist(input, project);
  const second = buildPortfolioShortlist(mergePriorSelectionForRerun(first.selected, first.excluded), project);
  assert.deepEqual(second.selected, first.selected);
  assert.deepEqual(second.excluded, first.excluded);
  assert.deepEqual(first.selected.map((row) => row.advisorProgramId), ["a", "z"]);
});

test("medical real program validation rejects invented IDs and mismatched intakes", () => {
  const valid = candidate("real", { program_id: "fixture-phd-2027" });
  const records = {
    advisorRecords: [{ advisor_id: valid.advisor_id }],
    programRecords: [{ program_id: "fixture-phd-2027", degree: "PhD", intake: "2027" }],
  };
  assert.deepEqual(validateMedicalCandidateMappings([valid], records), []);
  assert.match(validateMedicalCandidateMappings([{ ...valid, intake: "2026" }], records).join(";"), /intake/);
  assert.throws(() => buildPortfolioShortlist([candidate("invented")], { ...project, ...records }), /advisor_id|program_id/);
  const result = buildPortfolioShortlist([valid], { ...project, ...records, evaluationMode: "weighted_score" });
  assert.equal(result.selected[0].overallMatch, null, "stale mode cannot enable old numeric fallback");
});

test("medical workbook preserves grants, student funding and denominator limitations separately", () => {
  const input = { project, applicationRows: [candidate("funding", {
    evidenceProfile: { scientificFit: { status: "strong" },
      resources: [{ level: "institution_owned", doctoral_access: "unknown" }],
      researchFunding: [{ amount: 1000000, currency: "USD", role: "Co-I", scope: "annual_parent_award" }],
      doctoralFunding: [{ status: "not_checked", tuition: null }],
      doctoralOutcomes: { sample: "no_historical_sample", denominator: null, limitation: "No success rate can be calculated" },
    },
  })] };
  const sheet = buildMedicalWorkbookSheets(input)[0];
  const byHeader = Object.fromEntries(sheet.headers.map((header, index) => [header, sheet.rows[0][index]]));
  assert.match(byHeader["研究项目经费"], /annual_parent_award/);
  assert.doesNotMatch(byHeader["博士生资助"], /1000000/);
  assert.match(byHeader["研究资源及访问证据层级"], /doctoral_access: unknown/);
  assert.match(byHeader["博士培养公开样本与局限"], /no_historical_sample/);
  assert.ok(!sheet.headers.some((header) => /综合匹配分|申请定位|QS/.test(header)));
});

test("T42 spreadsheet text and serialized formula objects cannot inject executable formulas", async () => {
  const scratch = await mkdtemp(resolve(tmpdir(), "medical-xlsx-safety-"));
  try {
    const target = resolve(scratch, "safe.xlsx");
    await writeWorkbook({ sheets: [{ name: "Safety", headers: ["Text"], widths: [40], rows: [
      ["=HYPERLINK(\"https://invalid.example\",\"bad\")"], [" +SUM(1,2)"], ["@SUM(1,2)"],
      [{ kind: "formula", formula: 'WEBSERVICE("https://invalid.example")' }],
      [formulaCell("1+1", 2)], [null],
    ] }] }, target, { forcePortable: true });
    const xml = (await readStoredZipEntries(target)).get("xl/worksheets/sheet1.xml").toString();
    assert.equal((xml.match(/<f>/g) || []).length, 1);
    assert.match(xml, /<f>1\+1<\/f>/);
    assert.match(xml, /&apos;=HYPERLINK/);
    assert.equal(safeSpreadsheetText("\t=1+1"), "'\t=1+1");
  } finally { await rm(scratch, { recursive: true, force: true }); }
});

test("all existing builders export medical discovery without CV or application-ready sheets", async () => {
  const scratch = await mkdtemp(resolve(tmpdir(), "medical-discovery-builders-"));
  try {
    const inputPath = resolve(scratch, "fixture.json");
    await writeFile(inputPath, JSON.stringify({
      project: { ...project, searchMode: "discovery" },
      advisorRecords: [{ advisor_id: "fixture-advisor", name: "=malicious external label", school: "Fixture Institute",
        homepage: "https://example.org/fictional-fixture", evidence_profile: { scientificFit: { status: "strong" } } }],
      evidence: [{ evidence_id: "fixture-evidence", status: "inaccessible", retrieval_method: "static_web",
        extraction_status: "blocked", url: "https://example.org/fictional-fixture", limitations: "fixture 403" }],
    }));
    for (const script of ["advisor-finder/scripts/build_advisor_excel.mjs", "advisor-detective/scripts/build_detective_excel.mjs", "advisor-evaluator/scripts/build_application_ready_excel.mjs"]) {
      const output = resolve(scratch, `${script.split("/")[0]}.xlsx`);
      await execute(process.execPath, [resolve(repository, "skills", script), "--input", inputPath, "--output", output], {
        env: { ...process.env, ADVISOR_ATLAS_FORCE_PORTABLE_XLSX: "1" },
      });
      const entries = await readStoredZipEntries(output);
      const workbook = entries.get("xl/workbook.xml").toString();
      const xml = [...entries].filter(([key]) => /^xl\/worksheets\//.test(key)).map(([, data]) => data.toString()).join("\n");
      assert.match(workbook, /医学方向探索/);
      assert.doesNotMatch(workbook, /申请就绪/);
      assert.match(xml, /本次未核验/);
      assert.match(xml, /inaccessible/);
      assert.match(xml, /&apos;=malicious/);
      assert.match(xml, /<f>HYPERLINK/);
      assert.doesNotMatch(xml, /综合匹配分|相对稳妥/);
    }
  } finally { await rm(scratch, { recursive: true, force: true }); }
});

test("T32 T45 matching CLI derives advisor view and keeps candidate IDs empty when unmapped", async () => {
  const scratch = await mkdtemp(resolve(tmpdir(), "medical-discovery-cli-"));
  try {
    await mkdir(resolve(scratch, "outputs"));
    await writeFile(resolve(scratch, "project.json"), JSON.stringify({ ...project, searchMode: "discovery" }));
    const raw = [{ advisor_id: "fixture-pi", name: "Fixture PI", evidence_profile: { scientificFit: { status: "strong" } } }];
    await writeFile(resolve(scratch, "outputs/advisor_records.json"), JSON.stringify(raw));
    const cli = resolve(repository, "skills/advisor-finder/scripts/apply_matching_strategy.mjs");
    await execute(process.execPath, [cli, "--project-root", scratch]);
    const first = await readFile(resolve(scratch, "outputs/discovery-view.json"), "utf8");
    await execute(process.execPath, [cli, "--project-root", scratch]);
    assert.equal(await readFile(resolve(scratch, "outputs/discovery-view.json"), "utf8"), first);
    assert.deepEqual(JSON.parse(await readFile(resolve(scratch, "outputs/candidates.json"), "utf8")), []);
    assert.deepEqual(JSON.parse(await readFile(resolve(scratch, "outputs/advisor_records.json"), "utf8")), raw);
    assert.ok(!("advisorProgramId" in JSON.parse(first)[0]));
  } finally { await rm(scratch, { recursive: true, force: true }); }
});

test("shipped fictional medical application example exports categorical comparison", async () => {
  const scratch = await mkdtemp(resolve(tmpdir(), "medical-application-example-"));
  try {
    const target = resolve(scratch, "medical-comparison.xlsx");
    await execute(process.execPath, [
      resolve(repository, "skills/advisor-evaluator/scripts/build_application_ready_excel.mjs"),
      "--input", resolve(repository, "skills/advisor-evaluator/tests/sample_medical_records.json"),
      "--output", target,
    ], { env: { ...process.env, ADVISOR_ATLAS_FORCE_PORTABLE_XLSX: "1" } });
    const entries = await readStoredZipEntries(target);
    assert.match(entries.get("xl/workbook.xml").toString(), /医学申请比较/);
    const sheet = entries.get("xl/worksheets/sheet1.xml").toString();
    assert.match(sheet, /eligible/);
    assert.match(sheet, /actionable/);
    assert.match(sheet, /fixture-pi--fixture-school-phd-2027/);
    assert.doesNotMatch(sheet, /综合匹配分|申请定位|保底/);
  } finally { await rm(scratch, { recursive: true, force: true }); }
});
