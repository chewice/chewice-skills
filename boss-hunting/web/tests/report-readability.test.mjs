import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { buildAdvisorReport } from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";
import { projectSearchCoverage } from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";
const fixture = async () => JSON.parse(await readFile(new URL("./fixtures/medical-discovery.json", import.meta.url), "utf8"));
const search = (status = "found") => ({ database: "NIH RePORTER", query: "Fixture PI OR Name Variant; Fixture Institute", checkedAt: "2026-09-23", scope: "active + 2021-09-23 to 2026-09-23", status, sourceKind: "official_database", limitations: "所列机构范围", sourceIds: ["grant-search"] });
const source = (entity, status = "verified") => ({ evidence_id: "grant-search", entity_id: entity, status, url: "https://example.org/grant-search", citation_label: "NIH 姓名与机构查询", claim: "合成检索结果", accessed_at: "2026-09-23", source_updated_at: "2026-09-21" });

test("grant completeness requires official per-advisor process and matching evidence, not empty projects", async () => {
  const input = await fixture();
  const advisor = input.advisors[0];
  advisor.evidence_profile.latest_signals.projects = [];
  assert.match(buildAdvisorReport(input), /未记录检索过程/);
  for (const status of ["found", "not_found", "inaccessible", "partial", "not_checked"]) {
    const entry = search(status);
    const evidence = source(advisor.advisor_id, status === "not_found" ? "not_found" : "verified");
    input.evidence.push(evidence);
    advisor.evidence_profile.latest_signals.projectSearches = [entry];
    assert.equal(projectSearchCoverage([entry], [evidence], advisor.advisor_id).complete, ["found", "not_found"].includes(status));
    const report = buildAdvisorReport(input);
    assert.match(report, /NIH 姓名与机构查询/);
    assert.match(report, /未找到公开记录不等于没有基金/);
    input.evidence.pop();
  }
  for (const change of [{sourceKind:"supplementary"},{sourceKind:"unknown"},{sourceIds:[]},{query:null},{checkedAt:null}]) {
    assert.equal(projectSearchCoverage([{...search(), ...change}], [source(advisor.advisor_id)], advisor.advisor_id).complete, false);
  }
  assert.equal(projectSearchCoverage([search()], [source("another-pi")], advisor.advisor_id).complete, false);
  assert.equal(projectSearchCoverage([search()], [source(advisor.advisor_id,"not_found")], advisor.advisor_id).complete, false);
});

test("semantic citations deduplicate each block and source pages without losing claim states or dates", async () => {
  const input = await fixture();
  const advisor = input.advisors[0];
  advisor.last_verified_at = "1999-01-01";
  advisor.evidence_profile.identity.affiliationAsOf = "2026-09-20";
  advisor.evidence_profile.identity.source_ids = ["one", "two"];
  input.evidence = [
    {...source(advisor.advisor_id), evidence_id:"one", url:"https://example.org/profile", citation_label:"机构导师介绍", claim:"当前任职"},
    {...source(advisor.advisor_id,"partial"), evidence_id:"two", url:"https://example.org/profile#bio", citation_label:"机构导师介绍", claim:"指导关系仍需核实"},
  ];
  const report = buildAdvisorReport(input);
  const identity = report.split('id="advisor-1-a"')[1].split('id="advisor-1-b"')[0];
  assert.match(identity, /任职信息核对日期[\s\S]*2026-09-20/);
  assert.doesNotMatch(identity, /1999-01-01/);
  assert.doesNotMatch(report, />证据\s*\d+<\/a>/);
  const appendix = report.split("来源原文与查阅记录")[1];
  assert.equal((appendix.match(/class="source-detail"/g) || []).length, 1);
  assert.equal((appendix.match(/href="https:\/\/example.org\/profile/g) || []).length, 1);
  assert.match(appendix, /当前任职/);
  assert.match(appendix, /指导关系仍需核实/);
  assert.match(appendix, /部分核实/);
  assert.match(appendix, /网页查阅日期[\s\S]*2026-09-23/);
  assert.match(appendix, /页面更新时间[\s\S]*2026-09-21/);
  delete advisor.evidence_profile.identity.affiliationAsOf;
  const missing = buildAdvisorReport(input).split('id="advisor-1-a"')[1].split('id="advisor-1-b"')[0];
  assert.match(missing, /任职信息核对日期：未记录/);
});

test("grant process and citation labels cannot inject HTML or unsafe links", async () => {
  const input = await fixture();
  input.advisors[0].evidence_profile.latest_signals.projectSearches = [{...search(), database:'<img src=x onerror=alert(1)>', query:'</dd><script>bad()</script>'}];
  input.evidence.push({...source(input.advisors[0].advisor_id), citation_label:'<svg onload=alert(1)>', url:'javascript:alert(1)'});
  const report = buildAdvisorReport(input);
  assert.match(report, /&lt;img/);
  assert.doesNotMatch(report, /<img|<script(?! id="report-navigation")|<svg onload|href="javascript:/);
  assert.match(report, /部分完成：基金检索尚有缺口/);
});

test("application reports retain advisor grant follow-ups despite an older opportunity snapshot", async () => {
  const input = JSON.parse(await readFile(new URL("./fixtures/medical-application.json", import.meta.url), "utf8"));
  const advisor = input.advisors[0];
  advisor.evidence_profile = {latest_signals:{project_searches:[search()], projects:[{project_id:"NEW-GRANT",title:"New advisor grant",source:"NIH"}]}};
  input.evidence.push(source(advisor.advisor_id));
  const report = buildAdvisorReport(input);
  const table = report.match(/<table class="overview">[\s\S]*?<\/table>/)[0];
  assert.match(table,/已完成所列基金库检索/);
  assert.match(report,/NEW-GRANT/);
  assert.match(report,/FIX-APP-01/);
});

test("selected collaborator profiles show only identity, appointment, direction and linked joint work", async () => {
  const input=await fixture();
  input.advisors[0].evidence_profile.collaboration_network.core_collaborators=[{
    name:"Selected Scholar",current_institution:"Fixture University",current_position:"Professor",research_direction:"Mechanisms",
    recent_route:"DO NOT DISPLAY ROUTE",relation_to_mainline:"DO NOT DISPLAY ASSESSMENT",
    collaboration_evidence:[{type:"shared_project",title:"Shared grant",year:2025,sourceIds:["joint"]},
      {type:"coauthorship",title:"Joint paper",url:"https://example.org/joint",year:2026,sourceIds:["joint"]}],source_ids:["joint"]}];
  input.evidence.push({evidence_id:"joint",url:"https://example.org/joint",citation_label:"共同研究原文",status:"verified"});
  const report=buildAdvisorReport(input);
  const section=report.split('id="advisor-1-c"')[1].split('id="advisor-1-d"')[0];
  for(const value of ["Selected Scholar","Fixture University","Professor","Mechanisms","Shared grant","Joint paper"]) assert.ok(section.includes(value));
  assert.doesNotMatch(section,/<table|DO NOT DISPLAY|近期路线|核心合作者|研究方向相近/);
  assert.match(section,/href="https:\/\/example.org\/joint"/);
  const paper=section.match(/<li><a[^>]+>Joint paper[\s\S]*?<\/li>/)[0];
  assert.equal((paper.match(/href=/g)||[]).length,1);
});
