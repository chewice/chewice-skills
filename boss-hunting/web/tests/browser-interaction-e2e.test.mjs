import test from 'node:test';
import assert from 'node:assert/strict';
import {executePublicResearchStep, discoverResearchCapabilities} from '../../skills/advisor-pipeline/scripts/browser-research.mjs';
test('real browser synthetic dynamic query: input, submit, wait, paginate and zero results', {skip:!process.env.BOSS_TEST_PLAYWRIGHT}, async () => {
  const {chromium}=await import(process.env.BOSS_TEST_PLAYWRIGHT);
  const browser=await chromium.launch({executablePath:process.env.BOSS_TEST_CHROMIUM,headless:true});
  try {
    const page=await browser.newPage();
    await page.setContent(`<label>Name<input id="name"></label><label>Institution<input id="institution"></label><label>Since<input id="since"></label><button id="query">Search</button><main></main><button id="next">Next</button><script>
      let rows=[],index=0;
      const render=()=>document.querySelector('main').textContent=JSON.stringify({count:rows.length,record:rows[index]||null,institution:document.querySelector('#institution').value,since:document.querySelector('#since').value});
      document.querySelector('#query').onclick=()=>{document.querySelector('main').textContent='Loading';setTimeout(()=>{rows=document.querySelector('#name').value==='Fixture PI'?['Project one','Project two']:[];index=0;render()},50)};
      document.querySelector('#next').onclick=()=>{index++;render()};
    </script>`);
    const hostTools={browser_navigate:args=>page.goto(args.url),browser_fill:args=>page.locator(args.selector).fill(args.value),browser_click:args=>page.locator(args.selector).click(),browser_read:()=>page.locator('main').innerText()};
    assert.equal(discoverResearchCapabilities(hostTools,{requiresInteraction:true}).preferredBackend,'browser');
    const dispatch=(tool,args,kind)=>executePublicResearchStep({hostTools,tool,args,action:{kind,publicReadOnly:true},project:{browserResearch:{enabled:true,policy:'public_read_only'}}});
    for(const [selector,value] of [['#name','Fixture PI'],['#institution','Fixture University'],['#since','2021-09-23']]) await dispatch('browser_fill',{selector,value},'fill');
    await dispatch('browser_click',{selector:'#query'},'submit_query');
    await page.waitForFunction(()=>document.querySelector('main').textContent.startsWith('{'));
    let result=JSON.parse(await dispatch('browser_read',{},'read'));
    assert.deepEqual(result,{count:2,record:'Project one',institution:'Fixture University',since:'2021-09-23'});
    await dispatch('browser_click',{selector:'#next'},'paginate');
    result=JSON.parse(await dispatch('browser_read',{},'read')); assert.equal(result.record,'Project two');
    await dispatch('browser_fill',{selector:'#name',value:'Missing PI'},'fill');
    await dispatch('browser_click',{selector:'#query'},'submit_query');
    await page.waitForFunction(()=>document.querySelector('main').textContent.startsWith('{'));
    assert.equal(JSON.parse(await dispatch('browser_read',{},'read')).count,0);
  } finally {await browser.close();}
});
