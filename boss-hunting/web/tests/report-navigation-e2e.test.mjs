import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile, mkdir, writeFile, mkdtemp, rm} from 'node:fs/promises';
import {resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {buildAdvisorReport} from '../../skills/advisor-pipeline/scripts/build_advisor_report.mjs';

test('report navigation: desktop, mobile, print, keyboard and offline without JavaScript', {skip:!process.env.BOSS_TEST_PLAYWRIGHT}, async () => {
 const {chromium}=await import(process.env.BOSS_TEST_PLAYWRIGHT);
 const temporary=!process.env.BOSS_REPORT_PREVIEW_DIR;
 const directory=temporary?await mkdtemp(resolve(tmpdir(),'boss-report-nav-')):resolve(process.env.BOSS_REPORT_PREVIEW_DIR);
 await mkdir(directory,{recursive:true});
 const input=JSON.parse(await readFile(new URL('./fixtures/medical-discovery.json',import.meta.url),'utf8'));
 const seed=input.advisors[0];
 input.advisors=Array.from({length:9},(_,i)=>({...structuredClone(seed),advisor_id:`synthetic-${i}`,name:i<2?'同名导师（虚构样例）':`合成导师 ${i+1} · 较长姓名用于检查目录换行与多导师阅读`}));
 const file=resolve(directory,'医学-模块导航-合成预览.html');
 await writeFile(file,buildAdvisorReport(input));
 const browser=await chromium.launch({executablePath:process.env.BOSS_TEST_CHROMIUM,headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  const external=[];page.on('request',request=>{if(/^https?:/.test(request.url()))external.push(request.url());});
  await page.goto(pathToFileURL(file).href);
  const nav=page.locator('.report-toc');
  assert.equal(await nav.evaluate(el=>getComputedStyle(el).position),'fixed');
  assert.equal((await nav.boundingBox()).width,240);
  assert.ok((await page.locator('main').boundingBox()).x+(await page.locator('main').boundingBox()).width < (await nav.boundingBox()).x);
  await page.locator('[data-advisor="advisor-1"]>summary').click({position:{x:3,y:16}});
  await page.locator('nav a[href="#advisor-1-d"]').click();
  await page.waitForFunction(()=>document.querySelector('a[aria-current]')?.hash==='#advisor-1-d');
  const top=await page.locator('#advisor-1-d').evaluate(el=>el.getBoundingClientRect().top);
  assert.ok(top>=0 && top<100);
  assert.equal(await page.locator('#advisor-1-d h5').first().isVisible(),true);
  await page.screenshot({path:resolve(directory,'desktop.png')});
  // Focus inside the directory must keep manually opened groups available.
  await page.locator('[data-advisor="advisor-2"]>summary').focus();
  await page.keyboard.press('Enter');
  await page.evaluate(()=>window.scrollBy(0,100));
  await page.waitForTimeout(100);
  assert.equal(await page.locator('[data-advisor="advisor-2"]').evaluate(el=>el.open),true);
  assert.equal(await page.evaluate(()=>document.activeElement.matches('[data-advisor="advisor-2"]>summary')),true);
  // Scroll-follow resumes after leaving navigation.
  await page.locator('#advisor-1-d').focus();
  await page.locator('#advisor-3-b').evaluate(el=>el.scrollIntoView());
  await page.waitForFunction(()=>document.querySelector('a[aria-current]')?.hash==='#advisor-3-b');
  assert.equal(await page.locator('[data-advisor="advisor-3"]').evaluate(el=>el.open),true);
  for(const width of [1200,1024,768,375]) {
   await page.setViewportSize({width,height:900});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
  }
  assert.equal(await nav.evaluate(el=>getComputedStyle(el).position),'sticky');
  await page.locator('.toc-shell>summary').click();
  await page.locator('[data-advisor="advisor-1"]>summary').click({position:{x:3,y:16}});
  await page.locator('nav a[href="#advisor-1-d"]').click();
  await page.waitForFunction(()=>!document.querySelector('.toc-shell').open);
  const mobileTop=await page.locator('#advisor-1-d').evaluate(el=>el.getBoundingClientRect().top);
  assert.ok(mobileTop>=50 && mobileTop<130,`mobile target at ${mobileTop}`);
  await page.screenshot({path:resolve(directory,'mobile.png')});
  await page.emulateMedia({media:'print'});
  assert.equal(await nav.isVisible(),false);
  await page.pdf({path:resolve(directory,'print-preview.pdf'),format:'A4'});
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const nojs=await browser.newPage({javaScriptEnabled:false,viewport:{width:1440,height:1000}});
  await nojs.goto(pathToFileURL(file).href);
  await nojs.locator('[data-advisor="advisor-1"]>summary').click({position:{x:3,y:16}});
  await nojs.locator('nav a[href="#advisor-1-e"]').click();
  assert.equal(new URL(nojs.url()).hash,'#advisor-1-e');
  assert.ok(await nojs.locator('#advisor-1-e').evaluate(el=>el.getBoundingClientRect().top<100));
 } finally {await browser.close();if(temporary)await rm(directory,{recursive:true,force:true});}
});
