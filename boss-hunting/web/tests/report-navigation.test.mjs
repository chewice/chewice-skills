import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {buildAdvisorReport} from '../../skills/advisor-pipeline/scripts/build_advisor_report.mjs';
const fixture = async () => JSON.parse(await readFile(new URL('./fixtures/medical-discovery.json',import.meta.url),'utf8'));
test('navigation links resolve uniquely; same names and hostile labels cannot inject markup', async () => {
 const input=await fixture();
 input.advisors.forEach(row=>{row.name='同名导师 <script>bad()</script>';});
 const report=buildAdvisorReport(input);
 const nav=report.match(/<nav class="report-toc"[\s\S]*?<\/nav>/)[0];
 const ids=[...report.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
 assert.equal(ids.length,new Set(ids).size);
 for(const match of nav.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.includes(match[1]),match[1]);
 assert.doesNotMatch(nav,/<script>/);
 assert.match(nav,/&lt;script&gt;/);
 for(const key of 'abcde') assert.match(report,new RegExp('class="module module-'+key+'"'));
 const scripts=[...report.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)];
 assert.equal(scripts.length,1);
 const hash=createHash('sha256').update(scripts[0][1]).digest('base64');
 assert.ok(report.includes("script-src 'sha256-"+hash+"'"));
 assert.doesNotMatch(report,/script-src 'unsafe-inline'|<script src=/);
});
test('empty reports do not invent advisor or module destinations', async () => {
 const input=await fixture();input.advisors=[];input.candidates=[];
 const report=buildAdvisorReport(input);
 const nav=report.match(/<nav class="report-toc"[\s\S]*?<\/nav>/)[0];
 assert.doesNotMatch(nav,/href="#advisor-/);
 assert.match(nav,/href="#coverage"/);
});

test('general advisor reports only link actual chapters and advisor entries', () => {
 const report=buildAdvisorReport({project:{domainProfile:'general',interests:[{name:'Ecology'}]},advisors:[{advisor_id:'general-pi',name:'General fixture'}],candidates:[],programs:[],evidence:[]});
 const nav=report.match(/<nav class="report-toc"[\s\S]*?<\/nav>/)[0];
 assert.match(nav,/href="#advisor-1"/);
 assert.doesNotMatch(nav,/href="#advisor-1-[a-e]"|toc-advisor/);
});

test('report chrome follows the local console tokens without external assets', () => {
 const report=buildAdvisorReport({project:{domainProfile:'general',interests:[{name:'Ecology'}]},advisors:[{advisor_id:'general-pi',name:'General fixture'}],candidates:[],programs:[],evidence:[]});
 assert.match(report,/class="eyebrow"/);
 assert.match(report,/class="toc-brand"/);
 assert.match(report,/--canvas:#f6f5f2/);
 assert.match(report,/--violet:#6557d9/);
 assert.match(report,/--sidebar:#24222d/);
 assert.match(report,/Georgia,"Songti SC",serif/);
 assert.doesNotMatch(report,/fonts\.googleapis|cdn\.|@import|href="https:\/\/fonts/);
 assert.match(report,/min-width:1200px[\s\S]*left:0/);
});
