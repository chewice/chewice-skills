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
  const missing = buildAdvisorReport(input).split('id="advisor-1-u"')[1].split("</article>")[0];
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
  const section = report.split('id="advisor-1-p"')[1].split('id="advisor-1-u"')[0];
  assert.match(section,/New advisor paper/);
  assert.match(section,/Fixture Journal/);
  assert.match(report,/真实申请入口（申请筛选模式）/);
  const sheets=buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,candidates:input.candidates,evidence:input.evidence});
  assert.match(JSON.stringify(sheets.find(sheet => sheet.name === "待核验论文")),/New advisor paper/);
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

test("paper section and Excel collapse supported journal versions and retain unverified version associations", async () => {
  const input=await fixture();
  const advisorId=input.advisors[0].advisor_id;
  const profile=input.advisors[0].evidence_profile;
  profile.research_mainline={representative_works:[{title:"Journal version",doi:"10.0000/final",venue:"Verified Journal",date:"2026-06-01",
      advisorRoles:["corresponding_author"],roleStatus:"verified",roleSourceIds:["final-role"],sourceIds:["final-role"]}],
    latest_papers:[{title:"Journal version",doi:"https://doi.org/10.0000/final",year:2026}],
    publicationSearches:[{database:"Fictional publisher",query:"Fixture author complete catalogue",checkedAt:"2026-10-15",windowStart:"2021-10-15",windowEnd:"2026-10-15",status:"found",resultsExhausted:true,sourceIds:["version-search"]}],
    preprints:[{title:"Earlier preprint",doi:"10.0000/preprint",published_version_doi:"10.0000/final",version_status:"verified",version_source_ids:["version-link"]},
      {title:"Unverified version association",doi:"10.0000/unverified",publishedVersionDoi:"10.0000/final",versionStatus:"not_checked"},
      {title:"Unpublished preprint",doi:"10.0000/open",venue:"bioRxiv",publication_status:"所查范围未发现期刊正式版"}]};
  profile.latest_signals={latest_papers:[{title:"Legacy recent paper",doi:"10.0000/old",year:2025}],
    preprints:[{title:"Legacy preprint",doi:"10.0000/legacy",venue:"medRxiv"}]};
  input.evidence.push(
    {evidence_id:"final-role",entity_id:advisorId,fields_supported:["advisorRoles"],status:"verified",url:"https://doi.org/10.0000/final",claim:"Publisher confirms the fictional advisor's corresponding authorship"},
    {evidence_id:"version-link",entity_id:advisorId,fields_supported:["publishedVersionDoi"],status:"verified",url:"https://example.org/verified-version-link",claim:"Publisher explicitly links this preprint to the journal version"},
    {evidence_id:"version-search",entity_id:advisorId,fields_supported:["publicationSearches"],status:"verified",url:"https://example.org/verified-version-search",claim:"Fictional publication catalogue checked"},
  );
  const paperSection = () => buildAdvisorReport(input).split('id="advisor-1-p"')[1].split('id="advisor-1-u"')[0];
  const paperSheets = () => buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,evidence:input.evidence})
    .filter(sheet => ["近五年论文","待核验论文"].includes(sheet.name));
  const section=paperSection();
  for(const value of ["Journal version","Verified Journal","Unverified version association","Unpublished preprint","Legacy recent paper","Legacy preprint","所查范围未发现期刊正式版","期刊发表状态待核实"]) assert.ok(section.includes(value),value);
  assert.equal((section.match(/>Journal version<\/a>/g)||[]).length,1);
  assert.doesNotMatch(section,/Earlier preprint/);
  assert.match(section,/href="https:\/\/example.org\/verified-version-link"/,"version-link evidence survives on the retained journal entry");
  const sheets=paperSheets();
  const verified=sheets.find(sheet=>sheet.name==="近五年论文");
  assert.deepEqual(verified.rows.map(row=>row[2]),["Journal version"]);
  const titles=sheets.flatMap(sheet=>sheet.rows.map(row=>row[2]));
  for(const value of ["Journal version","Unverified version association","Unpublished preprint","Legacy recent paper","Legacy preprint"]) assert.ok(titles.includes(value),value);
  assert.equal(titles.filter(title=>title==="Journal version").length,1);
  assert.ok(!titles.includes("Earlier preprint"));
  // A claimed link without verified source evidence cannot hide the preprint.
  input.evidence.find(row=>row.evidence_id==="version-link").status="partial";
  assert.match(paperSection(),/Earlier preprint/);
  assert.ok(paperSheets().find(sheet=>sheet.name==="待核验论文").rows.some(row=>row[2]==="Earlier preprint"));
});

test('compact citations retain full provenance, deduplicate URLs and keep hidden-source warnings visible', async () => {
  const input=await fixture();
  const profile=input.advisors[0].evidence_profile;
  profile.research_question_fit.source_ids=['c1','c2','c3','c4','duplicate','missing'];
  input.evidence=Array.from({length:4},(_,i)=>({evidence_id:`c${i+1}`,url:`https://example.org/c${i+1}`,source_type:'institutional_profile',page_title:'完整来源标题 <不应执行>',accessed_at:'2026-10-02',status:i===3?'partial':'verified'}));
  input.evidence.push({...input.evidence[0],evidence_id:'duplicate',url:'https://example.org/c1#bio'});
  const report=buildAdvisorReport(input);
  const block=report.match(/与您的研究需求：[\s\S]*?<\/p>/)[0];
  assert.equal((block.match(/class="citation-chip"/g)||[]).length,4);
  assert.equal((block.match(/href="https:\/\/example.org\/c1"/g)||[]).length,1);
  assert.match(block,/aria-label="展开其余 2 个来源">\+2<\/button>/);
  assert.match(block,/class="citation-extra">/); // Visible without JavaScript.
  assert.match(block,/<\/span> <span class="citation-state">部分核实、部分来源关联尚待补齐/);
  assert.match(block,/完整来源标题 &lt;不应执行&gt; · example.org · 查阅：2026-10-02/);
  assert.doesNotMatch(block,/<br>|已核实|<不应执行>/);
});

test('retired modules no longer appear in normalized profiles while legacy publications remain collected', async () => {
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

function publicationFixture() {
  const advisorId = "synthetic-human-pi";
  const titles = ["Most recent verified paper", "Another verified paper", "Third verified paper", "Fourth verified paper", "Fifth verified paper", "Sixth verified paper"];
  const dates = ["2026-10-01", "2025-06-01", "2025-05-01", "2024-06-01", "2023-06-01", "2022-06-01"];
  const roles = ["first_author", "co_first_author", "corresponding_author", "co_corresponding_author", "first_author", "corresponding_author"];
  const papers = titles.map((title, index) => ({title, date: dates[index], venue: "Synthetic Journal", url: `https://example.org/paper-${index}`,
    advisorRoles: [roles[index]], roleStatus: "verified", roleSourceIds: [`paper-${index}`], sourceIds: [`paper-${index}`], relationToMainline: {text: "跨疾病比较，不能视为抑郁症患者验证", sourceIds: [`paper-${index}`]}}));
  const identity = {currentInstitution:"Synthetic Institute", department:"Psychiatry", currentPosition:"Professor", affiliationAsOf:"2026-10-15", officialProfileUrl:"https://example.org/identity", sourceIds:["identity"]};
  return {
    project: {domainProfile:"medical",searchMode:"discovery",evaluationMode:"evidence_profile",medicalProfile:{fields:["精神病学"], diseasesOrMechanisms:["抑郁症"],regions:["美国"]}},
    advisors:[{advisor_id:advisorId,name:"Synthetic Advisor",region:"美国",evidence_profile:{identity,
      researchQuestionFit:{status:"direct",reasons:[{text:"评估跨疾病神经机制",sourceIds:["identity"]}],sourceIds:["identity"]},
      researchMainline:{longTermQuestion:{text:"可读的长期科学问题",sourceIds:["identity"]},continuingThemes:[{text:"持续主题以中文呈现",sourceIds:["identity"]}],
        latestPapers:papers, publicationSearches:[{database:"Synthetic Publisher",query:"HIDDEN QUERY OR NAME VARIANTS",checkedAt:"2026-10-15",windowStart:"2021-10-15",windowEnd:"2026-10-15",resultsExhausted:true,status:"found",sourceIds:["search"]}]}}}],
    evidence:[{evidence_id:"identity",entity_id:advisorId,fields_supported:Object.keys(identity),claim:"Synthetic institution and employment evidence",status:"verified",url:identity.officialProfileUrl},
      {evidence_id:"search",entity_id:advisorId,fields_supported:["publicationSearches"],claim:"Synthetic publication scope checked",status:"verified",url:"https://example.org/search"},
      ...papers.map((paper,index)=>({evidence_id:`paper-${index}`,entity_id:advisorId,fields_supported:["advisorRoles"],claim:"Synthetic author role verified",status:"verified",url:paper.url}))],
    candidates:[],programs:[],ranking:[],audit:{completionTier:"complete"},
  };
}

test("human report uses one shared eligible-paper count, shows newest three and retains all other verified papers by year", () => {
  const input = publicationFixture();
  const report = buildAdvisorReport(input);
  const section = report.split('id="advisor-1-p"')[1].split('id="advisor-1-u"')[0];
  const visible = section.split('<details class="publication-list">')[0];
  assert.match(visible, /Most recent verified paper/);
  assert.match(visible, /Third verified paper/);
  assert.doesNotMatch(visible, /Fourth verified paper/);
  assert.match(section, /其余已核实论文（3 篇，按年份）[\s\S]*2024[\s\S]*Fourth verified paper[\s\S]*2022[\s\S]*Sixth verified paper/);
  assert.match(section, /第一作者/); assert.match(section, /共同第一作者/);
  assert.match(section, /通讯作者/); assert.match(section, /共同通讯作者/);
  assert.match(report, /已完成所列来源范围的身份与论文核查/);
  assert.match(report, /可读的长期科学问题/);
  assert.match(report, /持续主题以中文呈现/);
  assert.match(report, /跨疾病比较，不能视为抑郁症患者验证/);
  assert.doesNotMatch(report, /\[object Object\]|sourceIds|advisor_id|advisorRoles|HIDDEN QUERY|<pre>|not_checked|corresponding_author|class="author-appendix"|class="supplement"/);
  const sheets = buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,evidence:input.evidence});
  assert.deepEqual(sheets.map(sheet=>sheet.name), ["导师概览","近五年论文","来源说明"]);
  assert.equal(sheets[0].headers.length,8);
  assert.equal(sheets[0].rows[0][5],6);
  assert.equal(sheets[1].rows.length,6);
  assert.deepEqual(sheets[1].rows.map(row=>row[2]), input.advisors[0].evidence_profile.researchMainline.latestPapers.map(paper=>paper.title));
  assert.doesNotMatch(JSON.stringify(sheets), /\[object Object\]|sourceIds|advisor_id|advisorRoles|HIDDEN QUERY|not_checked|corresponding_author/);
});

test("boundary and unsupported authorship leads remain readable, separate, and excluded from verified totals", () => {
  const input = publicationFixture();
  const mainline = input.advisors[0].evidence_profile.researchMainline;
  mainline.latestPapers.push({...mainline.latestPapers[0],title:"Boundary date requires review",doi:"10.0000/boundary",url:"https://example.org/boundary",date:null,year:2021});
  const report = buildAdvisorReport(input);
  const section = report.split('id="advisor-1-p"')[1].split('id="advisor-1-u"')[0];
  assert.match(section,/已核实 6 篇/);
  assert.match(section,/class="pending-publications"[\s\S]*Boundary date requires review[\s\S]*未纳入：边界年份的具体发表日期待核实/);
  assert.match(report,/部分完成：近五年论文检索或署名核验尚有缺口/);
  const sheets = buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,evidence:input.evidence});
  assert.equal(sheets[0].rows[0][5],6);
  assert.equal(sheets.find(sheet=>sheet.name==='近五年论文').rows.length,6);
  const pending = sheets.find(sheet=>sheet.name==='待核验论文');
  assert.equal(pending.rows.length,1);
  assert.match(pending.rows[0][6],/边界年份/);
});
