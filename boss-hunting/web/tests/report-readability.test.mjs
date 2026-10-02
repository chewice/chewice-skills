import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { buildAdvisorReport } from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";
import { buildMedicalWorkbookSheets } from "../../skills/advisor-pipeline/scripts/medical-workbook.mjs";
const fixture = async () => JSON.parse(await readFile(new URL("./fixtures/medical-discovery.json", import.meta.url), "utf8"));
const search = (status = "found") => ({ database: "NIH RePORTER", query: "Fixture PI OR Name Variant; Fixture Institute", checkedAt: "2026-09-23", scope: "active + 2021-09-23 to 2026-09-23", status, sourceKind: "official_database", limitations: "所列机构范围", sourceIds: ["grant-search"] });
const source = (entity, status = "verified") => ({ evidence_id: "grant-search", entity_id: entity, status, url: "https://example.org/grant-search", citation_label: "NIH 姓名与机构查询", claim: "合成检索结果", accessed_at: "2026-09-23", source_updated_at: "2026-09-21" });

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
  assert.match(missing, /任职信息核对日期[\s\S]*未核验：字段尚未记录/);
});

test("omitted grant records and unsafe source labels cannot inject HTML", async () => {
  const input = await fixture();
  input.advisors[0].evidence_profile.latest_signals.projectSearches = [{...search(), database:'<img src=x onerror=alert(1)>', query:'</dd><script>bad()</script>'}];
  input.evidence.push({...source(input.advisors[0].advisor_id), citation_label:'<svg onload=alert(1)>', url:'javascript:alert(1)'});
  const report = buildAdvisorReport(input);
  assert.doesNotMatch(report, /&lt;img/);
  assert.doesNotMatch(report, /<img|<script(?! id="report-navigation")|<svg onload|href="javascript:/);
  assert.doesNotMatch(report, /部分完成：基金检索尚有缺口/);
});

test("application reports and Excel retain recent papers despite an older opportunity snapshot", async () => {
  const input = JSON.parse(await readFile(new URL("./fixtures/medical-application.json", import.meta.url), "utf8"));
  input.advisors[0].evidence_profile = {researchMainline:{latestPapers:[{title:"New advisor paper",journal:"Fixture Journal",doi:"10.0000/new",year:2026,sourceIds:[]}]}};
  const report = buildAdvisorReport(input);
  const section = report.split('id="advisor-1-b"')[1].split('id="advisor-1-e"')[0];
  assert.match(section,/New advisor paper/);
  assert.match(section,/Fixture Journal/);
  assert.match(report,/真实申请入口（申请筛选模式）/);
  const sheets=buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,candidates:input.candidates,evidence:input.evidence});
  assert.match(JSON.stringify(sheets[0]),/New advisor paper/);
});

test("historical collaborator and grant records are preserved but absent from report sections", async () => {
  const input=await fixture();
  input.advisors[0].evidence_profile.collaboration_network.core_collaborators=[{name:"Omitted collaborator"}];
  input.advisors[0].evidence_profile.latest_signals.projects=[{title:"Omitted grant",projectId:"HIDDEN-GRANT"}];
  const before=structuredClone(input);
  const report=buildAdvisorReport(input);
  assert.doesNotMatch(report,/Omitted collaborator|Omitted grant|HIDDEN-GRANT|id="advisor-1-[cd]"/);
  assert.deepEqual(input,before);
});

test("module 02 and Excel collect old and new publications and deduplicate explicit journal versions", async () => {
  const input=await fixture();
  const profile=input.advisors[0].evidence_profile;
  profile.research_mainline={representative_works:[{title:"Journal version",doi:"10.0000/final",venue:"Verified Journal",year:2026}],
    latest_papers:[{title:"Journal version",doi:"https://doi.org/10.0000/final",year:2026}],
    preprints:[{title:"Earlier preprint",doi:"10.0000/preprint",published_version_doi:"10.0000/final"},
      {title:"Unpublished preprint",doi:"10.0000/open",venue:"bioRxiv",publication_status:"所查范围未发现期刊正式版"}]};
  profile.latest_signals={latest_papers:[{title:"Legacy recent paper",doi:"10.0000/old",year:2025}],
    preprints:[{title:"Legacy preprint",doi:"10.0000/legacy",venue:"medRxiv"}]};
  const report=buildAdvisorReport(input);
  const section=report.split('id="advisor-1-b"')[1].split('id="advisor-1-e"')[0];
  for(const text of ["Journal version","Verified Journal","Unpublished preprint","Legacy recent paper","Legacy preprint","所查范围未发现期刊正式版","期刊发表状态待核实"]) assert.ok(section.includes(text),text);
  assert.equal((section.match(/>Journal version<\/a>/g)||[]).length,1);
  assert.doesNotMatch(section,/Earlier preprint/);
  const sheet=buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,evidence:input.evidence})[0];
  const cell=sheet.rows[0][sheet.headers.indexOf("B 代表性与近期论文 / 预印本（含期刊信息）")];
  for(const text of ["Journal version","Unpublished preprint","Legacy recent paper","Legacy preprint"]) assert.ok(cell.includes(text),text);
  assert.equal((cell.match(/Journal version/g)||[]).length,1);
  assert.doesNotMatch(cell,/Earlier preprint/);
});

test('retired modules no longer appear in normalized profiles while legacy publications remain in module 02', async () => {
  const {normalizeMedicalEvidenceProfile}=await import('../../skills/advisor-pipeline/scripts/medical-evidence.mjs');
  const input=await fixture();
  const advisor=input.advisors[0];
  advisor.evidence_profile.latest_signals.latest_papers=[{title:'Retained legacy paper'}];
  const before=structuredClone(advisor);
  const profile=normalizeMedicalEvidenceProfile(advisor);
  assert.equal(profile.collaborationNetwork,undefined);
  assert.equal(profile.latestSignals,undefined);
  assert.ok(profile.researchMainline.latestPapers.some(row=>row.title==='Retained legacy paper'));
  assert.deepEqual(advisor,before);
});
