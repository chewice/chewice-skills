import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import {
  SUBAGENT_OUTPUT_KEYS, SUBAGENT_ROLES, mergeRunSubagents, mergeSubagentOutputs, validateSubagentOutput,
} from "../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs";

const execute = promisify(execFile);
const script = fileURLToPath(new URL("../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs", import.meta.url));
const FAKE = "fixture-secret-value-0123456789";
const credentials = { providers: {}, secrets: { OPENALEX_API_KEY: FAKE } };

// Fictional subagent output following the §4.4 schema.
function output(overrides = {}) {
  return {
    task_id: "identity-001", agent_role: "identity_resolver", scope: { module: "identity_research_positioning", network_round: 1, discovered_via: "collaboration" },
    findings: [{ entity: "fixture-pi", claim: "Fictional current institution", status: "verified", fields_supported: ["current_institution"], source_ids: ["s1"] }],
    new_entities: [{ entity_type: "advisor", advisor_id: "fixture-pi", name: "Fixture PI", identifiers: { orcid: "0000-0000-0000-0000" }, trainingFit: { status: "supported" }, lab_resources: ["x"] }],
    conflicts: [], gaps: ["Doctoral supervision listing not found"], queries_executed: ["fixture query"],
    sources_checked: [{ source_id: "s1", url: "https://example.org/fixture-profile", retrieval_method: "static_web", extraction_status: "success" }],
    ...overrides,
  };
}

test("T33 subagent output schema is validated field by field", () => {
  assert.deepEqual(SUBAGENT_OUTPUT_KEYS, ["task_id", "agent_role", "scope", "findings", "new_entities", "conflicts", "gaps", "queries_executed", "sources_checked"]);
  assert.equal(SUBAGENT_ROLES.length, 7);
  assert.deepEqual(validateSubagentOutput(output()), []);
  const errors = validateSubagentOutput({ ...output(), agent_role: "main_agent", findings: [{ claim: "", status: "verified", source_ids: ["missing"] }] }, "bad.json");
  assert.ok(errors.some((line) => /agent_role/.test(line)));
  assert.ok(errors.some((line) => /claim 缺失/.test(line)));
  assert.ok(errors.some((line) => /未在 sources_checked 中登记/.test(line)));
  assert.ok(validateSubagentOutput({ ...output(), findings: [{ entity: "x", claim: "c", status: "verified", source_ids: [] }] }).some((line) => /verified 主张必须有 source_ids/.test(line)));
  assert.deepEqual(validateSubagentOutput([]), ["subagent output: 顶层必须是对象"]);
});

test("T33 T34 T40 merge deduplicates advisors by id/ORCID, strips removed fields, records conflicts and blocks secrets", () => {
  const existing = [{ advisor_id: "fixture-pi", name: "Fixture PI", current_institution: "Fixture Institute" }];
  const second = output({ task_id: "trajectory-002", agent_role: "research_trajectory_mapper",
    new_entities: [{ entity_type: "advisor", advisor_id: "other-id", identifiers: { orcid: "0000-0000-0000-0000" }, current_institution: "Different Institute", research_directions: ["fixture direction"] }],
    findings: [{ entity: "fixture-pi", claim: "Fictional current institution", status: "verified", fields_supported: ["current_institution"], source_ids: ["s1"] }],
    conflicts: [{ entity: "fixture-pi", field: "current_position", claims: ["Professor", "Associate Professor"] }] });
  const leaked = output({ task_id: "leak-003", findings: [{ entity: "fixture-pi", claim: `Header ${FAKE}`, status: "verified", source_ids: ["s1"] }] });
  const { advisors, evidence, report } = mergeSubagentOutputs([
    { fileName: "b-trajectory.json", output: second }, { fileName: "a-identity.json", output: output() }, { fileName: "c-leak.json", output: leaked },
  ], { advisorRecords: existing, evidenceRecords: [], credentials });
  assert.equal(advisors.length, 1, "same ORCID merges into the existing advisor");
  assert.deepEqual(advisors[0].research_directions, ["fixture direction"]);
  assert.ok(!("trainingFit" in advisors[0]) && !("lab_resources" in advisors[0]));
  assert.deepEqual(report.droppedRemovedFields[0].fields, ["trainingFit", "lab_resources"]);
  assert.deepEqual(advisors[0].source_task_ids, ["identity-001", "trajectory-002"]);
  assert.equal(report.duplicateAdvisors.length, 2);
  // Field disagreement becomes a conflict evidence row, never a silent overwrite.
  assert.equal(advisors[0].current_institution, "Fixture Institute");
  const conflicts = evidence.filter((row) => row.status === "conflict");
  // advisor_id mismatch on a shared ORCID, institution mismatch, and the explicit position conflict.
  assert.deepEqual(conflicts.map((row) => row.fields_supported[0]).sort(), ["advisor_id", "current_institution", "current_position"]);
  assert.match(conflicts.find((row) => row.fields_supported.includes("current_institution")).claim, /Fixture Institute ⟷ Different Institute/);
  assert.ok(conflicts.every((row) => row.resolution === "pending_main_agent_adjudication"));
  // Same claim from two tasks is one evidence row.
  assert.equal(evidence.filter((row) => row.status === "verified").length, 1);
  assert.equal(report.duplicateEvidence.length, 1);
  assert.equal(evidence[0].url, "https://example.org/fixture-profile");
  assert.equal(evidence[0].agent_role, "identity_resolver");
  assert.deepEqual(report.secretsBlocked, ["c-leak.json"]);
  assert.ok(report.errors.some((line) => /credential secret/.test(line)));
  assert.doesNotMatch(JSON.stringify({ advisors, evidence, report }), new RegExp(FAKE));
  assert.deepEqual(report.gaps.map((gap) => gap.task_id), ["identity-001", "trajectory-002"]);
});

test("T33 run merge is the single writer of outputs and produces merge-report.json; --dry-run leaves outputs untouched", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "boss-merge-"));
  try {
    await mkdir(resolve(root, "outputs"), { recursive: true });
    await mkdir(resolve(root, "runs", "run-1", "subagents"), { recursive: true });
    await writeFile(resolve(root, "outputs", "advisor_records.json"), "[]\n");
    await writeFile(resolve(root, "runs", "run-1", "subagents", "identity-001.json"), JSON.stringify(output()));
    await writeFile(resolve(root, "runs", "run-1", "subagents", "broken.json"), "{not json");
    const dry = await mergeRunSubagents(root, "run-1", { dryRun: true, credentials });
    assert.equal(dry.dryRun, true);
    assert.equal(dry.advisorCount, 1);
    assert.equal(await readFile(resolve(root, "outputs", "advisor_records.json"), "utf8"), "[]\n");
    assert.ok(dry.errors.some((line) => /broken\.json/.test(line)));
    const { stdout } = await execute(process.execPath, [script, "--root", root, "--run-id", "run-1"]).catch((error) => error);
    const report = JSON.parse(stdout);
    assert.equal(report.writer, "main_agent_merge_layer");
    const advisors = JSON.parse(await readFile(resolve(root, "outputs", "advisor_records.json"), "utf8"));
    assert.equal(advisors[0].advisor_id, "fixture-pi");
    assert.equal(advisors[0].discovered_via, "collaboration");
    assert.equal(advisors[0].network_round, 1);
    const evidence = JSON.parse(await readFile(resolve(root, "outputs", "evidence.json"), "utf8"));
    assert.equal(evidence[0].subagent_task_id, "identity-001");
    const saved = JSON.parse(await readFile(resolve(root, "runs", "run-1", "merge-report.json"), "utf8"));
    assert.equal(saved.runId, "run-1");
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("nested grant additions preserve prior research, conflicts and inputs across profile naming conventions", () => {
  for (const profileKey of ["evidence_profile", "evidenceProfile"]) {
    const existing = [{advisor_id:"fixture-pi", name:"Fixture PI", [profileKey]: {
      researchMainline:{longTermQuestion:"Preserve this research fact"},
      latestSignals:{projects:[{projectId:"G1", source:"NIH", amount:10, sourceIds:["old"]}]},
    }}];
    const before = structuredClone(existing);
    const update = output({new_entities:[{entity_type:"advisor",advisor_id:"fixture-pi",evidence_profile:{
      researchMainline:{longTermQuestion:"Do not replace"}, latest_signals:{
        projects:[{projectId:"G1",source:"NIH",amount:20,sourceIds:["new"]},{projectId:"G2",source:"NIH",title:"New grant"}],
        project_searches:[{database:"NIH",query:"Fixture PI",checked_at:"2026-09-23",scope:"active",status:"found",source_ids:["new"]}],
      },
    }}], findings:[{entity:"fixture-pi", claim:"Grant query result", status:"verified", source_ids:["s1"], citation_label:"NIH 项目查询"}]});
    const result = mergeSubagentOutputs([{fileName:"grants.json",output:update}],{advisorRecords:existing});
    assert.deepEqual(existing,before);
    const profile = result.advisors[0][profileKey];
    assert.equal(profile.researchMainline.longTermQuestion,"Preserve this research fact");
    assert.equal(profile.latestSignals.projects.length,2);
    assert.equal(profile.latestSignals.projects[0].amount,10);
    assert.deepEqual(profile.latestSignals.projects[0].sourceIds,["old","new"]);
    assert.equal(profile.latestSignals.projectSearches.length,1);
    assert.ok(result.evidence.some(row=>row.status==="conflict" && row.fields_supported.includes("latestSignals.projects.amount")));
    assert.ok(result.evidence.some(row=>row.citation_label==="NIH 项目查询"));
    const again=mergeSubagentOutputs([{fileName:"grants.json",output:update}],{advisorRecords:result.advisors,evidenceRecords:result.evidence});
    assert.equal(again.advisors[0][profileKey].latestSignals.projects.length,2);
    assert.equal(again.advisors[0][profileKey].latestSignals.projectSearches.length,1);
  }
});

test("interactive query receipts survive merge and repeated attempts deduplicate", () => {
  const attempt={provider:"wisp_science_browser",tool:"web_execute_js",checkedAt:"2026-09-23",outcome:"submitted"};
  const search={database:"NSFC",query:"Fixture PI",scope:"five years",checkedAt:"2026-09-23",requiresInteraction:true,interactionAttempts:[attempt]};
  const existing=[{advisor_id:"fixture-pi",evidenceProfile:{latestSignals:{projectSearches:[search]}}}];
  const update=output({new_entities:[{entity_type:"advisor",advisor_id:"fixture-pi",evidenceProfile:{latestSignals:{projectSearches:[{...search,interactionAttempts:[attempt,{...attempt,outcome:"loaded"}]}]}}}],sources_checked:[{source_id:"s1",url:"https://example.org/results",retrieval_method:"browser",retrieval_provider:"wisp_science_browser",retrieval_tool:"web_scan",extraction_status:"success",interaction_required:true,query_submitted:true,filters_confirmed:true,results_loaded:true,pagination_complete:true,result_count:2}]});
  const merged=mergeSubagentOutputs([{fileName:"interactive.json",output:update}],{advisorRecords:existing});
  assert.deepEqual(merged.report.errors,[]);
  assert.equal(merged.advisors[0].evidenceProfile.latestSignals.projectSearches[0].interactionAttempts.length,2);
  assert.equal(merged.evidence[0].query_submitted,true);
  assert.equal(merged.evidence[0].result_count,2);
});
