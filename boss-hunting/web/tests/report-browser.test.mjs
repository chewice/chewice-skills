import assert from 'node:assert/strict';
import test from 'node:test';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { buildAdvisorReport } from '../../skills/advisor-pipeline/scripts/build_advisor_report.mjs';

// Optional real-browser check: use an existing Chromium; never download a browser.
test('report browser: floating long directory, anchors, keyboard, mobile and print', { skip: !process.env.BOSS_REPORT_BROWSER, timeout: 30000 }, async () => {
  const root = await mkdtemp(join(tmpdir(), 'boss-report-browser-'));
  const child = spawn(process.env.BOSS_REPORT_BROWSER, ['--headless', '--no-sandbox', '--disable-gpu', '--remote-debugging-port=0', `--user-data-dir=${root}/profile`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
  let socket;
  try {
    const endpoint = await new Promise((resolve, reject) => {
      let log = '';
      const timer = setTimeout(() => reject(new Error('Chromium startup timeout: ' + log.slice(-1000))), 10000);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.stderr.on('data', chunk => { log += chunk; const match = log.match(/DevTools listening on (ws:\/\/\S+)/); if (match) { clearTimeout(timer); resolve(match[1]); } });
    });
    socket = new WebSocket(endpoint); await once(socket, 'open');
    let sequence = 0;
    const pending = new Map();
    socket.addEventListener('message', event => { const message = JSON.parse(event.data); const request = pending.get(message.id); if (request) { pending.delete(message.id); if (message.error) request.reject(new Error(JSON.stringify(message.error))); else request.resolve(message.result); } });
    const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({id, method, params, sessionId})); });
    const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
    const page = (method, params) => send(method, params, sessionId);
    const evaluate = async expression => { const result = await page('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true}); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; };
    const settle = () => evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
    const input = JSON.parse(await readFile(new URL('./fixtures/medical-discovery.json', import.meta.url), 'utf8'));
    input.advisors = Array.from({length: 18}, (_, i) => ({ ...structuredClone(input.advisors[0]), advisor_id: `fictional-${i}`, name: `测试导师 ${String(i + 1).padStart(2, '0')}` }));
    input.candidates = [];
    const citationIds = ['ui-source-1','ui-source-2','ui-source-3'];
    input.advisors[0].evidence_profile.research_question_fit.source_ids = citationIds;
    input.evidence.push(...citationIds.map((id,index)=>({evidence_id:id,url:`https://example.org/${id}`,source_type:'official_profile',page_title:'完整机构来源标题',status:index===2?'partial':'verified',accessed_at:'2026-10-02'})));
    const file = join(root, 'report.html'); await writeFile(file, buildAdvisorReport(input));
    await page('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
    await page('Page.navigate', {url: pathToFileURL(file).href});
    for (let i = 0; i < 100; i++) { if (await evaluate('document.readyState === "complete" && !!document.querySelector(".report-toc")')) break; await new Promise(resolve => setTimeout(resolve, 30)); }
    await settle();
    assert.equal(await evaluate(`document.querySelector('#advisor-1 .citation-more').getAttribute('aria-expanded')`), 'false');
    assert.equal(await evaluate(`document.querySelector('#advisor-1 .citation-extra').hidden`), true);
    await evaluate(`document.querySelector('#advisor-1 .citation-more').focus()`);
    assert.equal(await evaluate(`document.activeElement.matches('.citation-more')`), true, await evaluate(`document.activeElement.outerHTML.slice(0,200)`));
    await page('Input.dispatchKeyEvent', {type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
    await page('Input.dispatchKeyEvent', {type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    assert.equal(await evaluate(`document.querySelector('#advisor-1 .citation-extra').hidden`), false);
    await evaluate(`document.querySelector('#advisor-1 .citation-more').click()`);
    assert.equal(await evaluate(`document.querySelector('#advisor-1 .citation-extra').hidden`), true);
    const geometry = await evaluate(`(() => { const n=document.querySelector('.report-toc'), r=n.getBoundingClientRect(), c=n.querySelector('.toc-content'); return {left:r.left,width:r.width,height:r.height,center:r.top+r.height/2,main:document.querySelector('main').getBoundingClientRect().left,right:r.right,scrollable:c.scrollHeight>c.clientHeight}; })()`);
    assert.equal(geometry.left, 16); assert.equal(geometry.width, 216); assert.ok(geometry.height <= 630); assert.equal(geometry.center, 450); assert.ok(geometry.main > geometry.right); assert.ok(geometry.scrollable);
    await evaluate(`document.getElementById('advisor-16-b').scrollIntoView()`); await settle();
    assert.equal(await evaluate(`document.querySelector('.toc-advisor[data-advisor="advisor-16"]').open`), true);
    assert.equal(await evaluate(`document.querySelector('.report-toc a[aria-current]').hash`), '#advisor-16-b');
    assert.ok(await evaluate(`(() => {const a=document.querySelector('.report-toc a[aria-current]').getBoundingClientRect(), c=document.querySelector('.toc-content').getBoundingClientRect();return a.top>=c.top && a.bottom<=c.bottom;})()`));
    await evaluate(`document.querySelector('.report-toc a[href="#overview"]').focus()`);
    await page('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await page('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 }); await settle();
    assert.equal(await evaluate('document.activeElement.id'), 'overview');
    assert.equal(await evaluate('getComputedStyle(document.activeElement).outlineStyle'), 'solid');
    await page('Emulation.setDeviceMetricsOverride', {width: 375, height: 844, deviceScaleFactor: 1, mobile: true}); await settle();
    assert.equal(await evaluate(`document.querySelector('.toc-shell').open`), false);
    assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'));
    await evaluate(`document.querySelector('.toc-shell').open=true;document.querySelector('.report-toc a[href="#advisor-3"]').click()`); await settle();
    assert.equal(await evaluate(`document.querySelector('.toc-shell').open`), false);
    assert.equal(await evaluate('document.activeElement.id'), 'advisor-3');
    assert.ok(await evaluate(`document.getElementById('advisor-3').getBoundingClientRect().top >= document.querySelector('.report-toc').getBoundingClientRect().bottom`), 'mobile anchor must not be covered by sticky navigation');
    await page('Emulation.setEmulatedMedia', {media: 'print'});
    assert.equal(await evaluate(`getComputedStyle(document.querySelector('.report-toc')).display`), 'none');
    assert.equal(await evaluate(`getComputedStyle(document.querySelector('#advisor-1 .citation-extra')).display`), 'inline');
    if (process.env.BOSS_REPORT_SCREENSHOT) {
      await page('Emulation.setEmulatedMedia', {media: 'screen'});
      await page('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
      await evaluate(`document.getElementById('advisor-1').scrollIntoView()`); await settle();
      const shot = await page('Page.captureScreenshot', {format: 'png'});
      await writeFile(process.env.BOSS_REPORT_SCREENSHOT, Buffer.from(shot.data, 'base64'));
    }
    await page('Emulation.setScriptExecutionDisabled', {value:true});
    await page('Page.reload');
    for (let i=0;i<100;i++) { if (await evaluate(`document.readyState === 'complete' && !!document.querySelector('.citation-extra') && !document.querySelector('.citation-extra').id`)) break; await new Promise(resolve=>setTimeout(resolve,30)); }
    assert.equal(await evaluate(`document.querySelector('.citation-extra').hidden`),false);
    assert.equal(await evaluate(`document.querySelector('.citation-more').hidden`),true);
  } finally {
    socket?.close(); child.kill(); await once(child, 'exit').catch(() => {});
    await rm(root, { recursive: true, force: true });
  }
});
