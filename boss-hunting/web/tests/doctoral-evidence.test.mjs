import assert from "node:assert/strict";
import test from "node:test";
import {readFile} from "node:fs/promises";
import {doctoralCoverage, labWebsiteVerified, doctoralAdditions, doctoralWindow, firstAuthorPaperState, firstAuthorSummary, firstAuthorIdentity, mergeDoctoralAdditions} from "../../skills/advisor-pipeline/scripts/doctoral-evidence.mjs";
import {buildAdvisorReport} from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";
import {buildMedicalWorkbookSheets} from "../../skills/advisor-pipeline/scripts/medical-workbook.mjs";
import {mergeSubagentOutputs} from "../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs";

const paper = (overrides={}) => ({title:"Joint mechanisms paper", doi:"10.0000/fixture",url:"https://example.org/paper",date:"2025-06-01", firstAuthorRole:"first_author",advisorRole:"corresponding_author",roleStatus:"verified",sourceIds:["paper"],...overrides});
const raw = () => ({first_author_profiles:[{person_id:"person-1",name:"Same Name",public_role:"PhD student",identity_status:"not_checked",research_summary:"Mechanisms supported by joint work",summary_source_ids:["paper"],papers:[paper()]}],
  lab_websites:[{url:"https://example.org/lab",title:"Fixture Lab",relationship_status:"verified",status:"found",source_ids:["lab"],pages:[{url:"https://example.org/members",title:"Members",status:"found",accessed_at:"2026-09-23",source_ids:["lab"]}]}],
  searches:[{kind:"lab_website",database:"Official institution",query:"Fixture PI lab",checkedAt:"2026-09-23",status:"found",sourceIds:["lab"]},
    {kind:"corresponding_papers",database:"Publisher",query:"Fixture PI corresponding",checkedAt:"2026-09-23",windowStart:"2021-09-23",windowEnd:"2026-09-23",status:"found",sourceIds:["paper"]}]});
const fixture = async (name="medical-discovery") => JSON.parse(await readFile(new URL(`./fixtures/${name}.json`,import.meta.url),"utf8"));

test("five-year author eligibility requires both verified roles and precise boundary dates",()=>{
 const d=doctoralAdditions(raw()); const window=doctoralWindow(d);
 assert.deepEqual(window,{start:"2021-09-23",end:"2026-09-23"});
 for(const firstAuthorRole of ["first_author","co_first_author"]) for(const advisorRole of ["corresponding_author","co_corresponding_author"]) assert.equal(firstAuthorPaperState(paper({firstAuthorRole,advisorRole}),window),"eligible");
 for(const change of [{advisorRole:"last_author"},{roleStatus:"partial"},{sourceIds:[]},{firstAuthorRole:"coauthor"}]) assert.notEqual(firstAuthorPaperState(paper(change),window),"eligible");
 for(const date of ["2021-09-23","2026-09-23"]) assert.equal(firstAuthorPaperState(paper({date}),window),"eligible");
 for(const date of ["2021-09-22","2026-09-24"]) assert.equal(firstAuthorPaperState(paper({date}),window),"不在近五年范围内");
 assert.equal(firstAuthorPaperState(paper({date:null,year:2024}),window),"eligible");
 assert.match(firstAuthorPaperState(paper({date:null,year:2026}),window),/具体发表日期/);
 d.searches[1].windowStart="2020-01-01"; assert.equal(doctoralWindow(d),null);
 assert.deepEqual(doctoralWindow(doctoralAdditions({searches:[{kind:"corresponding_papers",checkedAt:"2024-02-29"}]})),{start:"2019-02-28",end:"2024-02-29"});
});

test("first authors are not inferred to be students and summaries require qualifying-paper references",()=>{
 const d=doctoralAdditions(raw()); const person=d.firstAuthorProfiles[0]; const window=doctoralWindow(d);
 assert.equal(firstAuthorIdentity(person),"身份待核实");
 person.identityStatus="verified"; assert.equal(firstAuthorIdentity(person),"身份待核实");
 person.identitySourceIds=["member-page"];assert.equal(firstAuthorIdentity(person),"PhD student");
 assert.equal(firstAuthorSummary(person,window),"Mechanisms supported by joint work");
 person.papers[0].advisorRole="last_author";assert.match(firstAuthorSummary(person,window),/待补充或核实/);
 person.papers[0].advisorRole="corresponding_author";person.summarySourceIds=["unrelated"];assert.match(firstAuthorSummary(person,window),/待补充或核实/);
});

test("doctoral additions merge papers by ID without merging same-name people or mutating inputs",()=>{
 const base=raw(); const before=structuredClone(base); const incoming=doctoralAdditions(raw());
 incoming.firstAuthorProfiles[0].papers.push(paper({doi:"10.0000/second",title:"Second paper",url:"https://example.org/second"}));
 incoming.firstAuthorProfiles.push({...incoming.firstAuthorProfiles[0],personId:"person-2"});
 incoming.firstAuthorProfiles[0].researchSummary="Conflicting interpretation";
 const conflicts=[];const merged=mergeDoctoralAdditions(base,incoming,(...args)=>conflicts.push(args));
 assert.deepEqual(base,before);assert.equal(merged.firstAuthorProfiles.length,2);assert.equal(merged.firstAuthorProfiles[0].papers.length,2);
 assert.equal(merged.firstAuthorProfiles[0].researchSummary,"Mechanisms supported by joint work");assert.ok(conflicts.some(([field])=>field.endsWith("researchSummary")));
 assert.equal(mergeDoctoralAdditions(merged,incoming).firstAuthorProfiles.length,2);
 const unknown=mergeDoctoralAdditions({firstAuthorProfiles:[{name:"Unknown",publicRole:"A"}]},{firstAuthorProfiles:[{name:"Unknown",publicRole:"B"}]});
 assert.equal(unknown.firstAuthorProfiles.length,2);
});

test("authoritative subagent merge preserves existing doctoral students and records new conflicts",()=>{
 const existing=[{advisor_id:"pi",evidence_profile:{doctoral_trajectory:{...raw(),currentDoctoral:[{name:"Existing student"}]},researchMainline:{longTermQuestion:"Preserve"}}}];
 const incoming=raw(); incoming.first_author_profiles[0].research_summary="Conflicting summary";
 const output={task_id:"doctoral",agent_role:"doctoral_trajectory_investigator",scope:{module:"doctoral_trajectory"},findings:[],new_entities:[{entity_type:"advisor",advisor_id:"pi",evidenceProfile:{doctoralTrajectory:incoming}}],conflicts:[],gaps:[],queries_executed:[],sources_checked:[]};
 const result=mergeSubagentOutputs([{fileName:"doctoral.json",output}],{advisorRecords:existing});
 assert.deepEqual(result.report.errors,[]);
 assert.equal(result.advisors[0].evidence_profile.doctoral_trajectory.currentDoctoral[0].name,"Existing student");
 assert.ok(result.evidence.some(row=>row.status==="conflict"));
 assert.equal(result.advisors[0].evidence_profile.researchMainline.longTermQuestion,"Preserve");
});

test("HTML and Excel retain new doctoral information and expose legacy gaps",async()=>{
 const input=await fixture();const advisor=input.advisors[0];
 assert.match(buildAdvisorReport(input),/未记录此项检索/);
 advisor.evidence_profile.doctoral_trajectory={...advisor.evidence_profile.doctoral_trajectory,...raw()};
 input.evidence.push(...["lab","paper"].map(id=>({evidence_id:id,entity_id:advisor.advisor_id,url:`https://example.org/${id}`,status:"verified",citation_label:id==="paper"?"共同研究论文":"实验室成员页"})));
 const report=buildAdvisorReport(input); const section=report.split('id="advisor-1-e"')[1].split("</article>")[0];
 assert.ok(section.indexOf("实验室官网与查阅情况")<section.indexOf("近五年通讯作者论文中的第一作者"));
 assert.ok(section.indexOf("近五年通讯作者论文中的第一作者")<section.indexOf("当前博士生（公开可见）"));
 assert.match(section,/页面更新时间：页面未注明/);assert.match(section,/身份待核实/);assert.match(section,/Mechanisms supported by joint work/);
 const item=section.match(/<li><a[^>]+>Joint mechanisms paper[\s\S]*?<\/li>/)[0];assert.equal((item.match(/href=/g)||[]).length,1);
 const sheets=buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,evidence:input.evidence});
 assert.match(JSON.stringify(sheets),/Joint mechanisms paper/);assert.match(JSON.stringify(sheets),/https:\/\/example.org\/members/);
});

test("lab failures and unsafe author/page text remain explicit and inert",async()=>{
 const input=await fixture();const doctoral=raw();
 doctoral.first_author_profiles[0].name='<img src=x onerror=alert(1)>';
 doctoral.lab_websites[0].url="javascript:alert(1)";doctoral.lab_websites[0].title="<script>bad</script>";
 doctoral.lab_websites[0].relationship_status="not_checked";
 doctoral.lab_websites[0].pages[0].status="inaccessible";
 input.advisors[0].evidence_profile.doctoral_trajectory=doctoral;
 for(const status of ["not_found","inaccessible","partial","not_checked"]){
  doctoral.searches[0].status=status;
  const report=buildAdvisorReport(input);
  assert.doesNotMatch(report,/<img|<script(?! id="report-navigation")|href="javascript:/);
  assert.match(report,/&lt;img/);assert.match(report,/与导师的归属关系待核实/);
 }
});

test("application snapshots cannot hide later advisor doctoral additions in HTML or Excel",async()=>{
 const input=await fixture("medical-application");input.advisors[0].evidence_profile={doctoral_trajectory:{...raw(),current_doctoral:[{name:"Advisor stored student"}]}};
 const report=buildAdvisorReport(input);assert.match(report,/Joint mechanisms paper/);assert.match(report,/Advisor stored student/);
 const sheets=buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,candidates:input.candidates,evidence:input.evidence});
 assert.match(JSON.stringify(sheets[0]),/Joint mechanisms paper/);assert.match(JSON.stringify(sheets[0]),/Advisor stored student/);
});


test("missing or unverified evidence cannot certify author roles, lab attribution or report completeness",()=>{
 const d=doctoralAdditions(raw());const window=doctoralWindow(d);
 assert.notEqual(firstAuthorPaperState(d.firstAuthorProfiles[0].papers[0],window,[]),"eligible");
 assert.equal(labWebsiteVerified(d.labWebsites[0],[]),false);
 assert.equal(doctoralCoverage(d,[]),false);
 const evidence=["paper","lab"].map(id=>({evidence_id:id,status:"verified",url:`https://example.org/${id}`}));
 assert.equal(doctoralCoverage(d,evidence),true);
 d.searches[0].status="inaccessible";assert.equal(doctoralCoverage(d,evidence),false);
 d.searches[0].status="found";d.labWebsites[0].pages[0].accessedAt=null;assert.equal(doctoralCoverage(d,evidence),false);
 assert.match(firstAuthorPaperState(paper({date:"2025-02-31",year:2025}),window),/日期待核实/);
});
