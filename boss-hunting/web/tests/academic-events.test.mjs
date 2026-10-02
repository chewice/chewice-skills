import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {academicEvents, academicTalkRows, talkSearchComplete, talkWindow} from '../../skills/advisor-pipeline/scripts/academic-events.mjs';
import {buildAdvisorReport} from '../../skills/advisor-pipeline/scripts/build_advisor_report.mjs';
import {buildMedicalWorkbookSheets} from '../../skills/advisor-pipeline/scripts/medical-workbook.mjs';
import {mergeSubagentOutputs} from '../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs';

const search = () => ({database:'Fictional conference site',query:'Fixture PI + institution + invited talk',checkedAt:'2026-10-02',windowStart:'2024-10-02',windowEnd:'2026-10-02',status:'found',sourceIds:['search']});
const talk = (overrides={}) => ({eventName:'Fictional Symposium',date:'2026-09-15',role:'invited',talkTitle:'Mechanisms of adaptation',talkTitleZh:'适应机制',url:'https://example.org/event',identityStatus:'verified',participationStatus:'scheduled',sourceIds:['programme'],...overrides});
const evidence = () => [
  {evidence_id:'search',entity_id:'pi',status:'verified',url:'https://example.org/search'},
  {evidence_id:'programme',entity_id:'pi',status:'verified',source_type:'conference_programme',url:'https://example.org/programme'},
  {evidence_id:'recording',entity_id:'pi',status:'verified',source_type:'recording',url:'https://example.org/recording'},
];
const mainline = talks => academicEvents({academicTalks:talks,talkSearches:[search()]});
const fixture = async name => JSON.parse(await readFile(new URL(`./fixtures/${name}.json`,import.meta.url),'utf8'));

test('conference programmes never prove delivery; future events and non-speakers remain separate',()=>{
 const data=mainline([
  talk({participationStatus:'delivered'}),
  talk({participationStatus:'delivered',sourceIds:['recording']}),
  talk({date:'2026-11-10',participationStatus:'delivered',sourceIds:['recording']}),
  talk({role:'chair',talkTitle:'Session theme'}),
  talk({talkTitle:null}),
  talk({identityStatus:'not_checked'}),
 ]);
 const rows=academicTalkRows(data,evidence(),'pi');
 assert.equal(rows[0].status,'预告安排（实际报告待核实）');
 assert.equal(rows[1].status,'已确认报告');
 assert.equal(rows[2].timing,'即将举行');
 assert.match(rows[2].status,/日期与报告证据冲突/);
 assert.doesNotMatch(rows[3].title,/Session theme/);
 assert.match(rows[3].title,/未确认个人演讲/);
 assert.equal(rows[4].title,'演讲标题未公开／未查到');
 assert.match(rows[5].status,/导师身份/);
 assert.equal(talkSearchComplete(data,evidence(),'pi'),false);
 assert.match(academicTalkRows(mainline([talk()]),evidence(),'another-pi')[0].status,/证据待核实/);
 assert.notEqual(academicTalkRows(mainline([talk({participationStatus:'delivered',sourceIds:['search']})]),evidence(),'pi')[0].status,'已确认报告');
});

test('two-year scope uses the recorded query date; missing, blocked and not-found searches differ',()=>{
 const data=mainline([talk()]);
 assert.deepEqual(talkWindow(data.talkSearches),{start:'2024-10-02',end:'2026-10-02'});
 assert.equal(talkSearchComplete(data,evidence(),'pi'),true);
 assert.equal(talkSearchComplete(mainline([]),evidence(),'pi'),false);
 for(const status of ['not_checked','inaccessible','partial']) assert.equal(talkSearchComplete({...data,talkSearches:[{...search(),status}]},evidence(),'pi'),false);
 const negative={academicTalks:[],talkSearches:[{...search(),status:'not_found'}]};
 assert.equal(talkSearchComplete(negative,[{...evidence()[0],status:'not_found'}],'pi'),true);
 assert.equal(talkSearchComplete(negative,[],'pi'),false);
 assert.equal(talkWindow([{...search(),windowStart:'2021-10-02'}]),null);
 assert.deepEqual(talkWindow([{...search(),checkedAt:'2024-02-29',windowStart:'2022-02-28',windowEnd:'2024-02-29'}]),{start:'2022-02-28',end:'2024-02-29'});
});

test('HTML and Excel retain advisor talks in module 02 despite older application snapshots',async()=>{
 const input=await fixture('medical-application');
 const advisor=input.advisors[0];
 advisor.evidence_profile={research_mainline:{academic_talks:[talk(),talk({eventName:'Future Forum',date:'2026-12-01'})],talk_searches:[search()]}};
 input.evidence.push(...evidence().map(row=>({...row,entity_id:advisor.advisor_id})));
 const before=structuredClone(input);
 const report=buildAdvisorReport(input);
 const section=report.split('id="advisor-1-b"')[1].split('id="advisor-1-e"')[0];
 assert.match(section,/近期学术会议与演讲/);
 assert.match(section,/Mechanisms of adaptation/);
 assert.match(section,/适应机制/);
 assert.match(section,/即将举行[\s\S]*Future Forum/);
 assert.match(section,/href="https:\/\/example.org\/programme"/);
 assert.doesNotMatch(section,/已确认报告/);
 const sheet=buildMedicalWorkbookSheets({project:input.project,advisorRecords:input.advisors,candidates:input.candidates,evidence:input.evidence})[0];
 const cell=sheet.rows[0][sheet.headers.indexOf('B 近期学术会议与演讲')];
 assert.match(cell,/Mechanisms of adaptation/);
 assert.match(cell,/即将举行.*Future Forum/);
 assert.doesNotMatch(cell,/已确认报告/);
 assert.deepEqual(input,before);
});

test('unsafe titles and URLs remain inert; legacy records do not imply no conference activity',async()=>{
 const input=await fixture('medical-discovery');
 assert.match(buildAdvisorReport(input),/未记录会议与演讲检索，不代表没有活动/);
 input.advisors[0].evidence_profile.research_mainline={...mainline([talk({talkTitle:'<script>bad()</script>',url:'javascript:alert(1)'})])};
 const report=buildAdvisorReport(input);
 assert.match(report,/&lt;script&gt;bad/);
 assert.doesNotMatch(report,/<script>bad|href="javascript:/);
});

test('subagent merge adds talks without replacing research or duplicating the same receipt',()=>{
 const original={advisor_id:'pi',evidence_profile:{research_mainline:{longTermQuestion:'Preserve this question',representativeWorks:[{title:'Existing paper'}]}}};
 const output={task_id:'talks',agent_role:'research_trajectory_mapper',scope:{module:'research_mainline_5y'},findings:[],new_entities:[{entity_type:'advisor',advisor_id:'pi',evidenceProfile:{researchMainline:mainline([talk()])}}],conflicts:[],gaps:[],queries_executed:[],sources_checked:[]};
 const result=mergeSubagentOutputs([{fileName:'talks.json',output}],{advisorRecords:[original]});
 assert.deepEqual(result.report.errors,[]);
 const stored=result.advisors[0].evidence_profile.research_mainline;
 assert.equal(stored.longTermQuestion,'Preserve this question');
 assert.equal(stored.representativeWorks[0].title,'Existing paper');
 assert.equal(stored.academicTalks[0].talkTitle,'Mechanisms of adaptation');
 const again=mergeSubagentOutputs([{fileName:'talks.json',output}],{advisorRecords:result.advisors});
 assert.equal(again.advisors[0].evidence_profile.research_mainline.academicTalks.length,1);
 assert.equal(again.advisors[0].evidence_profile.research_mainline.talkSearches.length,1);
});
