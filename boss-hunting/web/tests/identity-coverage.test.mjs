import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, mkdir, writeFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { IDENTITY_FIELDS, identityCoverage } from '../../skills/advisor-pipeline/scripts/medical-evidence.mjs';
import { buildAdvisorReport, exportAdvisorReport } from '../../skills/advisor-pipeline/scripts/build_advisor_report.mjs';
import { mergeSubagentOutputs } from '../../skills/advisor-pipeline/scripts/merge_subagent_findings.mjs';

const values = ['Example University', 'Neuroscience', 'Professor', 'Mood disorders', 'Official doctoral faculty listing', '2026-09-23'];
const advisor = () => ({ advisor_id: 'fictional-pi', name: 'Fictional PI', evidence_profile: { identity: Object.fromEntries(IDENTITY_FIELDS.map(([key], i) => [key, values[i]])) } });
const evidence = () => IDENTITY_FIELDS.map(([field], i) => ({ evidence_id: `identity-${i}`, entity_id: 'fictional-pi', fields_supported: [`identity.${field}`], claim: values[i], excerpt: `Fictional official profile: ${values[i]}`, status: 'verified', url: 'https://example.org/profile' }));
const project = { domainProfile: 'medical', searchMode: 'discovery', medicalProfile: { fields: ['Psychiatry'] } };

test('field evidence survives merge and renders recorded facts, not citation labels', () => {
  const merged = mergeSubagentOutputs([{ fileName: 'identity.json', output: {
    task_id: 'identity', agent_role: 'identity_resolver', scope: {}, conflicts: [], gaps: [], queries_executed: [],
    new_entities: [{ entity_type: 'advisor', ...advisor() }],
    sources_checked: [{ source_id: 'official', url: 'https://example.org/profile', citation_label: 'Official profile' }],
    findings: evidence().map(row => ({ ...row, entity: row.entity_id, source_ids: ['official'] })),
  } }]);
  assert.deepEqual(merged.report.errors, []);
  assert.equal(identityCoverage(merged.advisors[0], merged.evidence).complete, true);
  const html = buildAdvisorReport({ project, advisors: merged.advisors, evidence: merged.evidence, candidates: [], programs: [] });
  const identity = html.split('id="advisor-1-a"')[1].split('id="advisor-1-b"')[0];
  for (const value of values) assert.ok(identity.includes(value));
  assert.match(identity, /<dt>院系<\/dt>/);
  assert.match(identity, /<dt>职位<\/dt>/);
  assert.match(identity, /href="https:\/\/example.org\/profile"/);
  assert.doesNotMatch(identity, /字段尚未记录|对应字段来源待核验/);
});

test('missing facts, wrong entities, broad homepage links and invalid dates cannot pass', () => {
  const row = advisor(); const sources = evidence();
  delete row.evidence_profile.identity.currentPosition;
  sources[2].citation_label = 'Professor';
  assert.match(identityCoverage(row, sources).gaps.find(gap => gap.field === 'currentPosition').reason, /已有字段证据/);
  assert.equal(row.evidence_profile.identity.currentPosition, undefined);
  assert.equal(identityCoverage(advisor(), sources.map(row => ({...row, entity_id: 'another-pi'}))).complete, false);
  assert.equal(identityCoverage(advisor(), sources.map(row => ({...row, fields_supported: ['identity']}))).complete, false);
  for (const value of ['2026-02-30', 'not a date', '2026-09']) {
    row.evidence_profile.identity.affiliationAsOf = value;
    assert.ok(identityCoverage(row, sources).gaps.some(gap => gap.field === 'affiliationAsOf'));
  }
});

test('snake case is supported and missing or conflicting facts retain their reason', () => {
  const row = advisor();
  row.evidence_profile.identity.current_position = row.evidence_profile.identity.currentPosition;
  delete row.evidence_profile.identity.currentPosition;
  const sources = evidence(); sources[2].fields_supported = ['evidence_profile.identity.current_position'];
  assert.equal(identityCoverage(row, sources).complete, true);
  for (const [status, label] of [['not_found','所查来源未提供'], ['inaccessible','访问受阻'], ['conflict','来源存在冲突'], ['not_checked','未核验']]) {
    sources[2].status = status; sources[2].limitations = 'Specific search limitation';
    const result = identityCoverage(row, sources);
    assert.equal(result.complete, false);
    assert.match(result.gaps.find(gap => gap.field === 'currentPosition').reason, new RegExp(label));
    const html = buildAdvisorReport({ project, advisors: [row], evidence: sources, candidates: [], programs: [], audit: { completionTier: 'complete' } });
    assert.ok(html.includes('Specific search limitation'));
    assert.match(html, /身份信息待补查/);
    assert.doesNotMatch(html, /已完成本轮设定范围的检索/);
  }
});

test('identity preflight is read only and returns actionable gaps for old records', async () => {
  const root = await mkdtemp(join(tmpdir(), 'boss-identity-'));
  try {
    await mkdir(join(root, 'outputs'));
    await writeFile(join(root, 'project.json'), JSON.stringify(project));
    await writeFile(join(root, 'outputs/advisor_records.json'), JSON.stringify([{ advisor_id: 'old', name: 'Old PI', homepage: 'https://example.org/old' }]));
    const before = await readdir(join(root, 'outputs'));
    const result = await exportAdvisorReport(root, { checkIdentity: true });
    assert.equal(result.complete, false);
    assert.equal(result.identityChecks[0].gaps.length, 6);
    assert.deepEqual(await readdir(join(root, 'outputs')), before);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('identity gaps alone override a complete audit; completed facts restore completion', () => {
  const row = advisor(); const sources = evidence();
  row.evidence_profile.latest_signals = { projectSearches: [{ database: 'Official fixture database', sourceKind: 'official_database', query: 'Fictional PI + Example University', scope: 'active and past five years', checkedAt: '2026-09-23', status: 'not_found', sourceIds: ['search'] }] };
  row.evidence_profile.doctoral_trajectory = { searches: ['corresponding_papers', 'lab_website'].map(kind => ({ kind, database: 'Official fixture pages', query: 'Fictional PI', checkedAt: '2026-09-23', status: 'not_found', sourceIds: ['search'] })) };
  sources.push({ evidence_id: 'search', entity_id: row.advisor_id, status: 'not_found', url: 'https://example.org/search', claim: 'No results in the fictional checked scope' });
  const input = { project, advisors: [row], evidence: sources, programs: [], candidates: [], audit: { completionTier: 'complete' } };
  assert.match(buildAdvisorReport(input), /已完成本轮设定范围的检索/);
  delete row.evidence_profile.identity.currentPosition;
  assert.match(buildAdvisorReport(input), /部分完成：身份信息尚有缺口/);
  assert.doesNotMatch(buildAdvisorReport(input), /已完成本轮设定范围的检索/);
});
