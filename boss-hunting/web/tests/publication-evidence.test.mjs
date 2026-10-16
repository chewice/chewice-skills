import test from "node:test";
import assert from "node:assert/strict";
import { publicationReview, collectPublications, mergePublicationRecords, readableText } from "../../skills/advisor-pipeline/scripts/publication-evidence.mjs";
import { normalizeMedicalEvidenceProfile, mergeResearchMainline } from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";
import { mergeSubagentOutputs } from "../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs";
import { defaultDetectiveSections, getDetectiveSectionCatalog } from "../../skills/advisor-pipeline/scripts/project-contract.mjs";

const paper = (overrides = {}) => ({title:"A verified study", doi:"10.0000/study", date:"2025-06-18", venue:"A Journal", advisorRoles:["first_author"], roleStatus:"verified", roleSourceIds:["role"], sourceIds:["role"], ...overrides});
const search = (overrides = {}) => ({database:"Publication database", query:"Exact resolved author; all directions", checkedAt:"2026-10-15", windowStart:"2021-10-15", windowEnd:"2026-10-15", status:"found", resultsExhausted:true, sourceIds:["query"], ...overrides});
const evidence = () => [
  {evidence_id:"role", entity_id:"pi", fields_supported:["researchMainline.publications.advisorRoles"], status:"verified", url:"https://example.org/paper", claim:"Full byline identifies the advisor as the first author."},
  {evidence_id:"query", entity_id:"pi", fields_supported:["researchMainline.publicationSearches"], status:"verified", url:"https://example.org/search", claim:"All pages of the recorded author query were reviewed."},
];
const mainline = (work = paper(), receipt = search()) => ({latestPapers:[work], publicationSearches:[receipt]});

test("all four explicitly verified author roles qualify without author profiles", () => {
  for (const role of ["first_author", "co_first_author", "corresponding_author", "co_corresponding_author"]) {
    const result = publicationReview(mainline(paper({advisorRoles:[role]})), evidence(), "pi");
    assert.equal(result.papers.length, 1, role);
    assert.equal(result.pending.length, 0);
    assert.equal(result.searchComplete, true);
  }
});

test("free-form negations, last/co-senior roles and known roles without verification are not silently upgraded", () => {
  for (const role of ["not corresponding author", "co-senior; NOT corresponding", "last_author", "co-corresponding", "first_author"]) {
    const result = publicationReview(mainline({title:"Legacy seed", year:2025, verifiedRole:role, sourceIds:["role"]}), evidence(), "pi");
    assert.equal(result.papers.length, 0, role);
    assert.equal(result.pending.length, 1);
  }
});

test("authorship references must resolve to verified role evidence for the same advisor", () => {
  for (const change of [{entity_id:"different-pi"}, {status:"partial"}, {fields_supported:["identity.currentPosition"]}, {url:"javascript:alert(1)"}]) {
    const sources = evidence(); Object.assign(sources[0], change);
    assert.equal(publicationReview(mainline(), sources, "pi").papers.length, 0);
  }
  assert.equal(publicationReview(mainline(paper({roleSourceIds:[]})), evidence(), "pi").papers.length, 0);
});

test("precise date boundaries, unknown boundary years and leap-day windows", () => {
  for (const date of ["2021-10-15", "2026-10-15"]) assert.equal(publicationReview(mainline(paper({date})), evidence(), "pi").papers.length, 1);
  for (const date of ["2021-10-14", "2026-10-16"]) assert.equal(publicationReview(mainline(paper({date})), evidence(), "pi").excluded.length, 1);
  for (const year of [2021, 2026]) assert.match(publicationReview(mainline(paper({date:null, year})), evidence(), "pi").pending[0].reason, /边界/);
  assert.equal(publicationReview(mainline(paper({date:null, year:2024})), evidence(), "pi").papers.length, 1);
  assert.equal(publicationReview(mainline(paper({date:"2025-02-30"})), evidence(), "pi").papers.length, 0);
  const leap = publicationReview(mainline(paper({date:"2023-01-01"}), search({checkedAt:"2024-02-29",windowStart:"2019-02-28",windowEnd:"2024-02-29"})), evidence(), "pi");
  assert.deepEqual(leap.window, {start:"2019-02-28",end:"2024-02-29"});
});

test("actual query receipts gate completion independently of optional author information", () => {
  for (const change of [{resultsExhausted:false}, {status:"partial"}, {sourceIds:[]}, {query:""}, {windowStart:"2021-01-01"}]) {
    assert.equal(publicationReview(mainline(paper(), search(change)), evidence(), "pi").searchComplete, false);
  }
  assert.equal(publicationReview({latestPapers:[paper()], backSearchWindow:"2021-10-15/2026-10-15"}, evidence(), "pi").searchComplete, false);
  const m = mainline(); m.publicationSearches.unshift(search({checkedAt:"2026-10-04",windowStart:"2021-10-04",windowEnd:"2026-10-04",status:"partial",resultsExhausted:false}));
  assert.equal(publicationReview(m, evidence(), "pi").searchComplete, true);
});

test("ordinary verified coauthors are excluded, while unverified empty roles stay pending", () => {
  const result = publicationReview(mainline(paper({advisorRoles:[]})), evidence(), "pi");
  assert.equal(result.papers.length, 0); assert.equal(result.pending.length, 0); assert.equal(result.excluded.length, 1);
  assert.equal(publicationReview(mainline(paper({advisorRoles:[],roleSourceIds:[]})), evidence(), "pi").pending.length, 1);
});

test("updated verification survives seed deduplication and explicit preprint/version reconciliation", () => {
  const legacy = {title:"A verified study", doi:"https://doi.org/10.0000/STUDY", year:2025, verifiedRole:"unknown", sourceIds:["old"],relationToMainline:"已读摘要支持的相关方向"};
  const version = {title:"Earlier version",doi:"10.0000/preprint",publishedVersionDoi:"10.0000/study",versionStatus:"verified",versionSourceIds:["version"]};
  const sources = [...evidence(), {evidence_id:"version",entity_id:"pi",status:"verified",fields_supported:["researchMainline.publications.publishedVersionDoi"],url:"https://example.org/preprint",claim:"The preprint server explicitly links this published version."}];
  const works = collectPublications({representativeWorks:[legacy],latestPapers:[paper()],preprints:[version]}, sources, "pi");
  assert.equal(works.length, 1); assert.equal(works[0].roleStatus, "verified"); assert.equal(works[0].date, "2025-06-18");
  assert.deepEqual(works[0].sourceIds, ["old","role","version"]);
  assert.equal(collectPublications({latestPapers:[paper()],preprints:[{title:"A verified study",doi:"10.0000/unlinked"}]}).length, 2);
  assert.equal(collectPublications({latestPapers:[paper()],preprints:[version]}).length, 2, "an unchecked DOI association alone must not hide the preprint");
  assert.equal(collectPublications({latestPapers:[paper({roleStatus:"not_checked"})],preprints:[version]}, sources, "pi").length, 2, "keep the preprint until the final version is eligible");
  assert.equal(collectPublications({latestPapers:[paper()],preprints:[{...version,versionSourceIds:["role"]}]}, sources, "pi").length, 2, "authorship evidence does not prove version linkage");
  const outOfWindowFinal = publicationReview({publicationSearches:[search()],latestPapers:[paper({date:"2026-10-16"})],preprints:[{...paper(),...version,date:"2025-01-01"}]}, sources, "pi");
  assert.equal(outOfWindowFinal.papers.length, 1);
  assert.equal(outOfWindowFinal.papers[0].doi, "10.0000/preprint", "a future journal version must not hide an eligible preprint");
});

test("verified role and date disagreements remain unresolved", () => {
  const roles = mergePublicationRecords([paper()], [paper({advisorRoles:[]})]);
  assert.equal(roles[0].roleStatus, "conflict");
  const dates = mergePublicationRecords([paper()], [paper({date:"2025-07-01"})]);
  assert.equal(publicationReview(mainline(dates[0]), evidence(), "pi").papers.length, 0);
});

test("content objects produce prose while retaining sources and exact dates", () => {
  const profile = normalizeMedicalEvidenceProfile({evidence_profile:{researchQuestionFit:{status:"direct",reasons:[{text:"患者脑组织研究",sourceIds:["fit"]}]},researchMainline:{longTermQuestion:{text:"细胞机制问题",sourceIds:["question"]},recentShift:{text:"增加空间研究",sourceIds:["shift"]},continuingThemes:[{text:"脑细胞机制",sourceIds:["theme"]},"空间组学"],latestPapers:[paper()]}}});
  assert.deepEqual(profile.researchMainline.continuingThemes, ["脑细胞机制","空间组学"]);
  assert.deepEqual(profile.researchMainline.sourceIds, ["question","shift","theme"]);
  assert.deepEqual(profile.researchQuestionFit.sourceIds, ["fit"]);
  assert.equal(profile.researchMainline.latestPapers[0].date, "2025-06-18");
  assert.equal(readableText({sourceIds:["do-not-render"], advisor_id:"internal-id"}), "");
  assert.equal(readableText([{text:"主题",sourceIds:["id"]},"另一主题"]), "主题；另一主题");
  assert.deepEqual(["epublish","ppublish","aheadofprint"].map(readableText), ["在线发表","正式出版","在线优先发表"]);
  assert.equal(collectPublications({latestPapers:[paper({title:"Role of <i>CNN2</i> &amp; disease"})]})[0].title, "Role of CNN2 & disease");
});

test("existing advisor incremental merges retain added papers, receipts and original research facts", () => {
  const advisors = [{advisor_id:"pi",evidence_profile:{researchMainline:{longTermQuestion:"Keep this scientific question",representativeWorks:[{title:"Older seed",year:2023}]}}}];
  const output = {task_id:"papers",agent_role:"research_trajectory_mapper",scope:{module:"research_mainline_5y"},findings:[],conflicts:[],gaps:[],queries_executed:[],sources_checked:[],new_entities:[{entity_type:"advisor",advisor_id:"pi",evidence_profile:{researchMainline:mainline()}}]};
  const result = mergeSubagentOutputs([{fileName:"papers.json",output}], {advisorRecords:advisors});
  assert.deepEqual(result.report.errors, []);
  const m = result.advisors[0].evidence_profile.researchMainline;
  assert.equal(m.longTermQuestion, "Keep this scientific question"); assert.equal(m.latestPapers.length, 1); assert.equal(m.publicationSearches.length, 1);
  const twice = mergeSubagentOutputs([{fileName:"papers.json",output}], {advisorRecords:result.advisors});
  assert.equal(twice.advisors[0].evidence_profile.researchMainline.latestPapers.length, 1);
  const current = normalizeMedicalEvidenceProfile({evidence_profile:{researchMainline:{longTermQuestion:"Current description",latestPapers:[paper()]}}}).researchMainline;
  const old = normalizeMedicalEvidenceProfile({evidence_profile:{researchMainline:{longTermQuestion:"Old snapshot"}}}).researchMainline;
  assert.equal(mergeResearchMainline(current, old).longTermQuestion, "Current description");
});

test("author appendix is optional in new medical selections but remains selectable", () => {
  assert.deepEqual(defaultDetectiveSections({domainProfile:"medical"}), ["identity_research_positioning","research_mainline_5y"]);
  assert.equal(getDetectiveSectionCatalog({domainProfile:"medical"}).find(row=>row.id === "doctoral_trajectory").defaultSelected, false);
});

test("deduplicating an incoming authorship finding preserves the publication citation", () => {
  const existing = evidence();
  const output = {task_id:"rerun",agent_role:"research_trajectory_mapper",scope:{},conflicts:[],gaps:[],queries_executed:[],
    sources_checked:[{source_id:"web",url:existing[0].url}],
    findings:[{...existing[0],evidence_id:"new-role",source_ids:["web"]}],
    new_entities:[{entity_type:"advisor",advisor_id:"pi",evidence_profile:{researchMainline:mainline(paper({roleSourceIds:["new-role"],sourceIds:["new-role"]}))}}]};
  const result = mergeSubagentOutputs([{fileName:"rerun.json",output}], {advisorRecords:[{advisor_id:"pi",evidence_profile:{researchMainline:{}}}],evidenceRecords:existing});
  assert.deepEqual(result.report.errors, []);
  assert.equal(result.evidence.length, 2);
  const m = result.advisors[0].evidence_profile.researchMainline;
  assert.deepEqual(m.latestPapers[0].roleSourceIds, ["role"]);
  assert.equal(publicationReview(m, result.evidence, "pi").papers.length, 1);
});
