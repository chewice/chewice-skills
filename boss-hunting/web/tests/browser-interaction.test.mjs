import test from 'node:test';
import assert from 'node:assert/strict';
import {discoverResearchCapabilities, nextResearchAction, executePublicResearchStep, interactiveQueryComplete, researchEvidence} from '../../skills/advisor-pipeline/scripts/browser-research.mjs';
import {projectSearchCoverage} from '../../skills/advisor-pipeline/scripts/medical-evidence.mjs';
import {selectRoute} from '../../skills/advisor-pipeline/scripts/provider-capabilities.mjs';
const tools = {web_open_tab() {}, web_scan() {}, web_execute_js() {}};
const receipt = {retrieval_method:'browser', retrieval_provider:'wisp_science_browser', retrieval_tool:'web_scan', interaction_required:true, query_submitted:true, filters_confirmed:true, results_loaded:true, pagination_complete:true, result_count:0, extraction_status:'success', status:'not_found', accessed_at:'2026-09-23', final_url:'https://example.org/results', complete_results:true, searched_sources:['fixture'], query_or_filter_summary:'A; B; 2021–2026'};
test('forms need one complete session, not static tools, screenshots or mixed providers', () => {
  for (const host of [{web__run() {}}, {browser_snapshot() {}, browser_click() {}}, {a__browser_navigate() {}, b__browser_evaluate() {}}]) assert.equal(discoverResearchCapabilities(host,{requiresInteraction:true}).preferredBackend,'unavailable');
  assert.equal(discoverResearchCapabilities(tools,{requiresInteraction:true}).formInteraction,'available');
  const descriptors={computer:{provider:'gpt_builtin_browser',sessionGroup:'native',operations:['navigate','read','input','activate']}};
  assert.equal(discoverResearchCapabilities({computer() {}},{requiresInteraction:true,toolCapabilities:descriptors}).browserProvider,'gpt_builtin_browser');
  assert.equal(discoverResearchCapabilities({},{toolCapabilities:descriptors}).formInteraction,'unavailable');
});
test('dynamic shells force interaction; static failures never consume interactive attempts', () => {
  const cap=discoverResearchCapabilities(tools);
  assert.equal(nextResearchAction(cap,{page_state:'empty_shell'},[{retrieval_method:'static_web',executed:true},{retrieval_method:'static_web',executed:true}]).action,'interact');
  assert.equal(nextResearchAction(cap,{page_state:'captcha'}).action,'human_intervention');
  assert.equal(nextResearchAction(cap,{page_state:'dynamic_form'},[{retrieval_method:'browser',executed:true},{retrieval_method:'browser',executed:true}]).action,'record_gap');
  assert.equal(nextResearchAction(discoverResearchCapabilities(),{page_state:'empty_shell'}).action,'discover_interactive_tools');
});
test('actual dispatch is awaited; missing tools and denied mutations do not produce success', async () => {
  let submitted=false;
  const args={hostTools:{web_execute_js:async value => {submitted=value.query; return 3;}},tool:'web_execute_js',args:{query:'A'},action:{kind:'submit_query',publicReadOnly:true},project:{browserResearch:{enabled:true,policy:'public_read_only'}}};
  assert.equal(await executePublicResearchStep(args),3); assert.equal(submitted,'A');
  await assert.rejects(executePublicResearchStep({...args,tool:'absent'}),/unavailable/);
  await assert.rejects(executePublicResearchStep({...args,action:{kind:'upload',publicReadOnly:true}}),/rejected/);
});
test('dynamic grant completion requires query, filters, loading, pagination and correct zero result', () => {
  const search={database:'fixture',query:'A B',checkedAt:'2026-09-23',scope:'five years',status:'not_found',sourceKind:'official_database',sourceIds:['ev'],requiresInteraction:true};
  const ev={...receipt,evidence_id:'ev',entity_id:'pi'};
  assert.equal(projectSearchCoverage([search],[ev],'pi').complete,true);
  for (const field of ['query_submitted','filters_confirmed','results_loaded','pagination_complete']) {
    const bad={...ev,[field]:false};
    assert.equal(interactiveQueryComplete(bad),false);
    assert.equal(researchEvidence(bad).status,'not_checked');
    assert.equal(projectSearchCoverage([search],[bad],'pi').complete,false);
  }
  assert.equal(interactiveQueryComplete({...ev,result_count:1}),false);
  assert.equal(projectSearchCoverage([search],[{...ev,page_state:'empty_shell'}],'pi').complete,false);
  assert.equal(selectRoute('cinii',{hostTools:{builtinWeb:'unavailable',interactiveBrowser:'unavailable'}}).selected_route,'alternative_sources');
  assert.equal(selectRoute('cinii',{hostTools:{builtinWeb:true},probe:{requiresInteraction:true}}).selected_route,'alternative_sources');
});
