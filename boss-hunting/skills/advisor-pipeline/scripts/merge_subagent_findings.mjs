#!/usr/bin/env node
// Deterministic merge layer between subagent outputs and authoritative JSON.
//
// Subagents write only run-local files under runs/<run-id>/subagents/*.json.
// This script (run by the Main Agent) validates them, removes anything that
// looks like a secret, deduplicates advisors and evidence, records conflicts as
// `conflict` evidence, and is the single writer of outputs/advisor_records.json
// and outputs/evidence.json for that merge.
import { mergeDoctoralAdditions } from "./doctoral-evidence.mjs";
import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, rename, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { containsSecret, loadCredentials } from "./credentials.mjs";
import { isExecutedDirectly } from "./direct-execution.mjs";
import { EVIDENCE_STATUSES } from "./project-contract.mjs";
import { REMOVED_MEDICAL_PROFILE_KEYS } from "./medical-evidence.mjs";
import { withProjectFileLock } from "./project-file-lock.mjs";

export const SUBAGENT_ROLES = [
  "seed_scout", "identity_resolver", "research_trajectory_mapper", "network_expander",
  "regional_project_investigator", "doctoral_trajectory_investigator", "evidence_auditor",
];

export const SUBAGENT_OUTPUT_KEYS = ["task_id", "agent_role", "scope", "findings", "new_entities", "conflicts", "gaps", "queries_executed", "sources_checked"];

const REMOVED_RECORD_KEYS = new Set([
  ...REMOVED_MEDICAL_PROFILE_KEYS, "lab_resources", "student_funding", "doctoral_personal_funding",
  "mentoring_style", "work_hours", "personality", "team_atmosphere", "quality_score", "overall_score",
]);

function list(value) { return Array.isArray(value) ? value : []; }
function hash(value) { return createHash("sha256").update(JSON.stringify(value)).digest("hex").slice(0, 16); }

export function validateSubagentOutput(output, fileName = "subagent output") {
  const errors = [];
  if (!output || typeof output !== "object" || Array.isArray(output)) return [`${fileName}: 顶层必须是对象`];
  for (const key of SUBAGENT_OUTPUT_KEYS) {
    if (!(key in output)) errors.push(`${fileName}: 缺少字段 ${key}`);
  }
  if (typeof output.task_id !== "string" || !output.task_id.trim()) errors.push(`${fileName}: task_id 必须是非空字符串`);
  if (!SUBAGENT_ROLES.includes(output.agent_role)) errors.push(`${fileName}: agent_role 必须是 ${SUBAGENT_ROLES.join("|")}`);
  for (const key of ["findings", "new_entities", "conflicts", "gaps", "queries_executed", "sources_checked"]) {
    if (key in output && !Array.isArray(output[key])) errors.push(`${fileName}: ${key} 必须是数组`);
  }
  const sourceIds = new Set(list(output.sources_checked).map((source) => String(source?.source_id || source?.id || "")).filter(Boolean));
  list(output.findings).forEach((finding, index) => {
    if (!finding || typeof finding !== "object") { errors.push(`${fileName}: findings[${index}] 必须是对象`); return; }
    if (typeof finding.claim !== "string" || !finding.claim.trim()) errors.push(`${fileName}: findings[${index}].claim 缺失`);
    if (!finding.entity && !finding.entity_id) errors.push(`${fileName}: findings[${index}] 缺少 entity`);
    if (!EVIDENCE_STATUSES.includes(finding.status)) errors.push(`${fileName}: findings[${index}].status 非法`);
    const ids = list(finding.source_ids);
    if (finding.status === "verified" && !ids.length) errors.push(`${fileName}: findings[${index}] verified 主张必须有 source_ids`);
    for (const id of ids) if (!sourceIds.has(String(id))) errors.push(`${fileName}: findings[${index}] 引用了未在 sources_checked 中登记的来源 ${id}`);
  });
  list(output.sources_checked).forEach((source, index) => {
    if (!source || typeof source !== "object") { errors.push(`${fileName}: sources_checked[${index}] 必须是对象`); return; }
    if (!source.source_id && !source.id) errors.push(`${fileName}: sources_checked[${index}] 缺少 source_id`);
    if (!source.url && !source.final_url) errors.push(`${fileName}: sources_checked[${index}] 缺少 url`);
  });
  return errors;
}

function stripRemovedFields(record, dropped) {
  const cleaned = {};
  for (const [key, value] of Object.entries(record || {})) {
    if (REMOVED_RECORD_KEYS.has(key)) { dropped.push(key); continue; }
    cleaned[key] = value;
  }
  return cleaned;
}

function advisorKey(record) {
  const identifiers = record.identifiers || {};
  return [record.advisor_id || record.advisorId, identifiers.orcid || record.orcid, identifiers.openalex || record.openalex_id]
    .map((value) => String(value || "").trim().toLowerCase()).filter(Boolean);
}

// Same URL + entity + fields + claim is one piece of evidence regardless of
// which task reported it; generated ids never defeat deduplication.
function evidenceKey(row) {
  const url = String(row.final_url || row.url || "").toLowerCase();
  if (url || row.claim) return `${url}|${row.entity_id || ""}|${list(row.fields_supported).join(",")}|${row.claim || ""}`;
  return row.evidence_id || row.evidenceId || JSON.stringify(row);
}

function findingToEvidence(finding, output, sourcesById, index) {
  const primary = sourcesById.get(String(list(finding.source_ids)[0] || ""));
  return {
    evidence_id: finding.evidence_id || `ev_${hash([output.task_id, index, finding.claim])}`,
    entity_id: finding.entity_id || finding.entity,
    fields_supported: list(finding.fields_supported).length ? finding.fields_supported : finding.field ? [finding.field] : [],
    claim_type: ["fact", "interpretation", "question"].includes(finding.claim_type) ? finding.claim_type : "fact",
    claim: finding.claim,
    status: finding.status,
    url: primary?.url || primary?.final_url || null,
    final_url: primary?.final_url || primary?.url || null,
    page_title: primary?.page_title || primary?.title || null,
    citation_label: finding.citation_label || primary?.citation_label || null,
    accessed_at: primary?.accessed_at || null,
    source_updated_at: primary?.source_updated_at || null,
    retrieval_method: primary?.retrieval_method || null,
    retrieval_provider: primary?.retrieval_provider || null,
    retrieval_tool: primary?.retrieval_tool || null,
    ...Object.fromEntries(["interaction_required", "query_submitted", "filters_confirmed", "results_loaded",
      "pagination_complete", "result_count", "page_state", "complete_results", "searched_sources"]
      .filter(key => primary?.[key] !== undefined).map(key => [key, primary[key]])),
    extraction_status: primary?.extraction_status || null,
    reading_depth: finding.reading_depth || primary?.reading_depth || null,
    page_locator: finding.page_locator || primary?.page_locator || null,
    excerpt: finding.excerpt || null,
    query_or_filter_summary: primary?.query_or_filter_summary || null,
    additional_source_ids: list(finding.source_ids).slice(1).map(String),
    same_source_group: finding.same_source_group || primary?.same_source_group || null,
    limitations: finding.limitations || primary?.failure_reason || null,
    subagent_task_id: output.task_id,
    agent_role: output.agent_role,
    module: finding.module || output.scope?.module || null,
  };
}

function conflictToEvidence(conflict, output, index) {
  return {
    evidence_id: conflict.evidence_id || `ev_conflict_${hash([output.task_id, index, conflict])}`,
    entity_id: conflict.entity_id || conflict.entity || null,
    fields_supported: conflict.field ? [conflict.field] : list(conflict.fields_supported),
    claim_type: "fact",
    claim: `冲突：${list(conflict.claims).map((claim) => typeof claim === "string" ? claim : claim?.claim || JSON.stringify(claim)).join(" ⟷ ")}`,
    status: "conflict",
    conflict_claims: list(conflict.claims),
    resolution: conflict.resolution || "pending_main_agent_adjudication",
    subagent_task_id: output.task_id,
    agent_role: output.agent_role,
  };
}

// Only grant additions are merged here; other profile interpretation remains
// Main Agent-owned. Never replace a whole existing evidence profile.
function mergeProjectFindings(existing, record, output, report, evidence) {
  const current = existing.evidenceProfile || existing.evidence_profile;
  const incoming = record.evidenceProfile || record.evidence_profile;
  if (!current || !incoming) return;
  const addition = incoming.latestSignals || incoming.latest_signals;
  if (!addition) return;
  const key = current.latestSignals ? "latestSignals" : current.latest_signals ? "latest_signals" : "latestSignals";
  const target = current[key] ||= {};
  for (const aliases of [["projects", "grants"], ["projectSearches", "project_searches"]]) {
    const updates = addition[aliases[0]] || addition[aliases[1]];
    if (!Array.isArray(updates)) continue;
    const storageKey = target[aliases[0]] ? aliases[0] : target[aliases[1]] ? aliases[1] : aliases[0];
    const rows = target[storageKey] ||= [];
    const identity = (item) => aliases[0] === "projects"
      ? JSON.stringify([item.source || item.sourceName || item.fundingBody || item.funding_body, item.projectId || item.project_id || item.grant_id || item.title || item.project_title])
      : JSON.stringify([item.database || item.sourceName, item.query || item.query_or_filter_summary, item.scope, item.checkedAt || item.checked_at]);
    for (const update of updates) {
      if (!update || typeof update !== "object") continue;
      const found = rows.find((row) => identity(row) === identity(update));
      if (!found) { rows.push(structuredClone(update)); continue; }
      for (const [inputField, value] of Object.entries(update)) {
        const groups = [["projectId", "project_id", "grant_id"], ["title", "project_title"],
          ["fundingBody", "funding_body"], ["piRole", "pi_role", "role"], ["period", "project_period"],
          ["amount", "published_amount"], ["amountUnit", "amount_unit", "currency"], ["amountBasis", "amount_basis"],
          ["requiresInteraction", "requires_interaction"], ["interactionAttempts", "interaction_attempts"],
          ["source", "sourceName"], ["checkedAt", "checked_at"], ["sourceKind", "source_kind"], ["query", "query_or_filter_summary"]];
        const aliasesForField = groups.find((names) => names.includes(inputField)) || [inputField];
        const field = aliasesForField.find((name) => Object.hasOwn(found, name)) || inputField;
        if (value === null || value === undefined || value === "") continue;
        if (["interactionAttempts", "interaction_attempts"].includes(field)) {
          found[field] = [...new Map([...list(found[field]), ...list(value)].map(row => [JSON.stringify(row), row])).values()];
        } else if (field === "sourceIds" || field === "source_ids") {
          const refKey = found.sourceIds ? "sourceIds" : found.source_ids ? "source_ids" : field;
          found[refKey] = [...new Set([...list(found[refKey]), ...list(value)])];
        } else if (found[field] === undefined || found[field] === null || found[field] === "") found[field] = structuredClone(value);
        else if (JSON.stringify(found[field]) !== JSON.stringify(value)) {
          const conflict = { entity_id: existing.advisor_id || existing.advisorId,
            field: `latestSignals.${aliases[0]}.${field}`, claims: [String(found[field]), String(value)] };
          report.conflicts.push({ task_id: output.task_id, ...conflict });
          evidence.push(conflictToEvidence(conflict, output, evidence.length));
        }
      }
    }
  }
}

export function mergeSubagentOutputs(outputs, { advisorRecords = [], evidenceRecords = [], credentials = null } = {}) {
  const report = { files: [], errors: [], droppedRemovedFields: [], duplicateAdvisors: [], duplicateEvidence: [], conflicts: [], gaps: [], queries: [], secretsBlocked: [] };
  const advisors = structuredClone(list(advisorRecords));
  const evidence = list(evidenceRecords).map((row) => ({ ...row }));
  const advisorIndex = new Map();
  for (const advisor of advisors) for (const key of advisorKey(advisor)) advisorIndex.set(key, advisor);
  const evidenceIndex = new Set(evidence.map(evidenceKey));

  const ordered = [...outputs].sort((left, right) => String(left.fileName).localeCompare(String(right.fileName)));
  for (const { fileName, output } of ordered) {
    if (credentials && containsSecret(output, credentials)) {
      report.secretsBlocked.push(fileName);
      report.errors.push(`${fileName}: 输出包含 credential secret，整份文件拒绝合并`);
      continue;
    }
    const errors = validateSubagentOutput(output, fileName);
    if (errors.length) { report.errors.push(...errors); continue; }
    report.files.push({ fileName, task_id: output.task_id, agent_role: output.agent_role, scope: output.scope ?? null });
    report.queries.push(...list(output.queries_executed).map((query) => ({ task_id: output.task_id, query })));
    report.gaps.push(...list(output.gaps).map((gap) => ({ task_id: output.task_id, gap })));
    const sourcesById = new Map(list(output.sources_checked).map((source) => [String(source.source_id || source.id), source]));

    for (const entity of list(output.new_entities)) {
      const type = entity?.entity_type || entity?.type || (entity?.advisor_id ? "advisor" : entity?.evidence_id ? "evidence" : "unknown");
      const dropped = [];
      const record = stripRemovedFields(entity?.record || entity, dropped);
      delete record.entity_type;
      if (dropped.length) report.droppedRemovedFields.push({ task_id: output.task_id, entity: record.advisor_id || record.evidence_id || null, fields: dropped });
      if (type === "advisor") {
        const keys = advisorKey(record);
        if (!keys.length) { report.errors.push(`${fileName}: 新导师实体缺少 advisor_id / ORCID / OpenAlex 标识`); continue; }
        const existing = keys.map((key) => advisorIndex.get(key)).find(Boolean);
        if (existing) {
          mergeProjectFindings(existing, record, output, report, evidence);
          const currentProfile = existing.evidenceProfile || existing.evidence_profile;
          const incomingProfile = record.evidenceProfile || record.evidence_profile;
          const addition = incomingProfile?.doctoralTrajectory || incomingProfile?.doctoral_trajectory;
          if (currentProfile && addition) {
            const key = currentProfile.doctoralTrajectory ? "doctoralTrajectory" : currentProfile.doctoral_trajectory ? "doctoral_trajectory" : "doctoralTrajectory";
            const previous = currentProfile[key] || {};
            currentProfile[key] = { ...previous, ...mergeDoctoralAdditions(previous, addition, (field, before, after) => {
              const conflict = {entity_id: existing.advisor_id || existing.advisorId, field, claims: [before, after]};
              report.conflicts.push({task_id: output.task_id, ...conflict});
              evidence.push(conflictToEvidence(conflict, output, evidence.length));
            }) };
          }
          report.duplicateAdvisors.push({ task_id: output.task_id, advisor_id: existing.advisor_id, merged_from: record.advisor_id || keys[0] });
          for (const [key, value] of Object.entries(record)) {
            if (["evidenceProfile", "evidence_profile"].includes(key) && (existing.evidenceProfile || existing.evidence_profile)) continue;
            if (value === null || value === undefined || value === "") continue;
            if (existing[key] === undefined || existing[key] === null || existing[key] === "" || (Array.isArray(existing[key]) && !existing[key].length)) {
              existing[key] = value;
            } else if (Array.isArray(existing[key]) && Array.isArray(value)) {
              const seen = new Set(existing[key].map((item) => JSON.stringify(item)));
              for (const item of value) if (!seen.has(JSON.stringify(item))) existing[key].push(item);
            } else if (typeof existing[key] !== "object" && typeof value !== "object" && existing[key] !== value) {
              report.conflicts.push({ task_id: output.task_id, advisor_id: existing.advisor_id, field: key, claims: [existing[key], value] });
              evidence.push(conflictToEvidence({ entity_id: existing.advisor_id, field: key, claims: [existing[key], value] }, output, evidence.length));
            }
          }
                existing.source_task_ids = [...new Set([...list(existing.source_task_ids), output.task_id])];
                // Newly learned identifiers (ORCID / OpenAlex) must also resolve to this advisor.
                for (const key of advisorKey(existing)) advisorIndex.set(key, existing);
        } else {
          const created = { ...record, discovered_via: record.discovered_via || output.scope?.discovered_via || "unknown",
            network_round: Number(record.network_round ?? output.scope?.network_round ?? 0) || 0, source_task_ids: [output.task_id] };
          advisors.push(created);
          for (const key of keys) advisorIndex.set(key, created);
        }
      } else if (type === "evidence") {
        const key = evidenceKey(record);
        if (evidenceIndex.has(key)) { report.duplicateEvidence.push({ task_id: output.task_id, key }); continue; }
        evidenceIndex.add(key);
        evidence.push({ ...record, subagent_task_id: output.task_id, agent_role: output.agent_role });
      } else {
        report.errors.push(`${fileName}: 不支持的 new_entities 类型 ${type}`);
      }
    }

    list(output.findings).forEach((finding, index) => {
      const row = findingToEvidence(finding, output, sourcesById, index);
      const key = evidenceKey(row);
      if (evidenceIndex.has(key)) { report.duplicateEvidence.push({ task_id: output.task_id, key }); return; }
      evidenceIndex.add(key);
      evidence.push(row);
    });
    list(output.conflicts).forEach((conflict, index) => {
      report.conflicts.push({ task_id: output.task_id, ...conflict });
      evidence.push(conflictToEvidence(conflict, output, index));
    });
  }
  return { advisors, evidence, report };
}

async function readJson(path, fallback) {
  try { return JSON.parse(await readFile(path, "utf8")); }
  catch (error) { if (error.code === "ENOENT" && fallback !== undefined) return fallback; throw error; }
}

async function writeJsonAtomic(path, value) {
  const temporary = `${path}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`);
  await rename(temporary, path);
}

export async function mergeRunSubagents(projectRoot, runId, { dryRun = false, credentials } = {}) {
  const root = resolve(projectRoot);
  const runDirectory = resolve(root, "runs", String(runId));
  const subagentDirectory = resolve(runDirectory, "subagents");
  const names = (await readdir(subagentDirectory).catch((error) => { if (error.code === "ENOENT") return []; throw error; }))
    .filter((name) => name.endsWith(".json")).sort();
  const outputs = [];
  for (const name of names) {
    try { outputs.push({ fileName: name, output: JSON.parse(await readFile(resolve(subagentDirectory, name), "utf8")) }); }
    catch (error) { outputs.push({ fileName: name, output: { __parse_error: error.message } }); }
  }
  const resolvedCredentials = credentials ?? await loadCredentials();
  return withProjectFileLock(root, async () => {
    const [advisorRecords, evidenceRecords] = await Promise.all([
      readJson(resolve(root, "outputs", "advisor_records.json"), []),
      readJson(resolve(root, "outputs", "evidence.json"), []),
    ]);
    if (!Array.isArray(advisorRecords) || !Array.isArray(evidenceRecords)) throw new Error("advisor_records.json / evidence.json 顶层必须是数组");
    const result = mergeSubagentOutputs(outputs, { advisorRecords, evidenceRecords, credentials: resolvedCredentials });
    const report = { runId: String(runId), mergedAt: new Date().toISOString(), dryRun, writer: "main_agent_merge_layer",
      advisorCount: result.advisors.length, evidenceCount: result.evidence.length, ...result.report };
    if (!dryRun) {
      await mkdir(resolve(root, "outputs"), { recursive: true });
      await writeJsonAtomic(resolve(root, "outputs", "advisor_records.json"), result.advisors);
      await writeJsonAtomic(resolve(root, "outputs", "evidence.json"), result.evidence);
    }
    await mkdir(runDirectory, { recursive: true });
    await writeJsonAtomic(resolve(runDirectory, "merge-report.json"), report);
    return report;
  });
}

if (isExecutedDirectly(import.meta.url)) {
  const rootIndex = process.argv.indexOf("--root");
  const runIndex = process.argv.indexOf("--run-id");
  if (rootIndex < 0 || runIndex < 0) throw new Error("Usage: merge_subagent_findings.mjs --root <project> --run-id <run-id> [--dry-run]");
  const report = await mergeRunSubagents(process.argv[rootIndex + 1], process.argv[runIndex + 1], { dryRun: process.argv.includes("--dry-run") });
  console.log(JSON.stringify(report, null, 2));
  if (report.errors.length) process.exitCode = 1;
}
