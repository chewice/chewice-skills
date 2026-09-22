import { readFile, readdir, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { verifyApplicationMaterialArtifacts } from "../../skills/advisor-pipeline/scripts/application-materials-artifacts.mjs";
import { recommendedActionForCandidate, normalizeProjectMetadata, readinessForProject, isMedicalRankingCurrent, isApplicationMaterialsConfirmationCurrent } from "../../skills/advisor-pipeline/scripts/project-contract.mjs";
import { normalizeMedicalCandidate, buildMedicalDiscoveryView, validateMedicalCandidateMappings, hasReadableProjectCv, REMOVED_MEDICAL_PROFILE_KEYS } from "../../skills/advisor-pipeline/scripts/medical-evidence.mjs";
import { reportFilename } from "../../skills/advisor-pipeline/scripts/build_advisor_report.mjs";
import { researchEvidence } from "../../skills/advisor-pipeline/scripts/browser-research.mjs";

export const RUN_MODES = [
  "finder",
  "detective",
  "ranking",
  "research_proposal",
  "outreach_email",
];

// A run is only `completed` when the phase's real artifact is on disk. Every
// other outcome has to say what is missing instead of claiming success.
export const RUN_STATUSES = [
  "completed",
  "partial",
  "needs_input",
  "failed",
  "cancelled",
  "interrupted",
];

export const RUN_MODE_LABELS = {
  finder: "Phase 1 候选导师",
  detective: "Phase 2 背调结果",
  ranking: "Phase 3 综合排名",
  research_proposal: "Research Proposal",
  outreach_email: "陶瓷信",
};

async function readJsonFile(projectPath, ...segments) {
  const filePath = resolve(projectPath, ...segments);
  try {
    const raw = await readFile(filePath, "utf8");
    try {
      return { exists: true, value: JSON.parse(raw), filePath };
    } catch {
      return { exists: true, value: null, invalid: true, filePath };
    }
  } catch {
    return { exists: false, value: null, filePath };
  }
}

async function verifyWorkbook(projectPath, prefix, startedAt = null) {
  const outputDirectory = resolve(projectPath, "outputs");
  let names = [];
  try {
    names = await readdir(outputDirectory);
  } catch {
    return { missing: [`outputs/${prefix}_YYYYMMDD.xlsx 尚未生成`] };
  }
  const candidates = [];
  for (const name of names) {
    if (!name.startsWith(`${prefix}_`) || !name.toLowerCase().endsWith(".xlsx")) continue;
    const filePath = resolve(outputDirectory, name);
    try {
      const details = await stat(filePath);
      if (details.isFile()) candidates.push({ name, filePath, details });
    } catch {
      // A concurrently replaced file is simply not a valid completion artifact yet.
    }
  }
  candidates.sort((left, right) => right.details.mtimeMs - left.details.mtimeMs);
  const workbook = candidates[0];
  if (!workbook) return { missing: [`outputs/${prefix}_YYYYMMDD.xlsx 尚未生成`] };
  if (startedAt) {
    const startedAtMs = Date.parse(startedAt);
    if (Number.isFinite(startedAtMs) && workbook.details.mtimeMs + 2_000 < startedAtMs) {
      return { missing: [`${workbook.name} 是本次运行之前的旧工作簿`] };
    }
  }
  const bytes = await readFile(workbook.filePath);
  const startsWithZip = bytes.length >= 4 && bytes.readUInt32LE(0) === 0x04034b50;
  const endSearchStart = Math.max(0, bytes.length - 65_557);
  const hasZipEnd = bytes.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06])) >= endSearchStart;
  const packageText = bytes.toString("latin1");
  const hasWorkbookParts =
    packageText.includes("[Content_Types].xml") &&
    packageText.includes("xl/workbook.xml") &&
    packageText.includes("xl/worksheets/sheet1.xml");
  if (bytes.length < 512 || !startsWithZip || !hasZipEnd || !hasWorkbookParts) {
    return { missing: [`${workbook.name} 不是完整可打开的 XLSX 文件`] };
  }
  return { missing: [], workbookPath: workbook.filePath };
}

function combineArtifactChecks(primary, workbook) {
  return {
    missing: [...primary.missing, ...workbook.missing],
    counts: {
      ...primary.counts,
      workbookCount: workbook.missing.length ? 0 : 1,
    },
    ...(workbook.workbookPath ? { workbookPath: workbook.workbookPath } : {}),
  };
}

async function withHtmlReport(outcome, projectPath, project, startedAt) {
  const file = resolve(projectPath, "outputs", reportFilename(project));
  const missing = [...outcome.missing];
  try {
    const [html, info] = await Promise.all([readFile(file, "utf8"), stat(file)]);
    if (!/<!doctype html>/i.test(html) || !/<\/html>/i.test(html) || html.length < 400)
      missing.push("HTML 报告不完整");
    if (startedAt && info.mtimeMs + 2000 < Date.parse(startedAt)) missing.push("HTML 报告是本次运行前的旧文件");
  } catch { missing.push(`主题 HTML 报告尚未生成：${reportFilename(project)}`); }
  return { ...outcome, missing, complete: missing.length === 0, ...(missing.length ? {} : { reportPath: file }) };
}

function verifyFinder(file, auditFile) {
  const missing = [];
  if (!file.exists) {
    missing.push("outputs/candidates.json 尚未生成");
    return { missing, counts: {} };
  }
  if (file.invalid || !Array.isArray(file.value)) {
    missing.push("outputs/candidates.json 不是合法的候选数组");
    return { missing, counts: {} };
  }
  if (!file.value.length) {
    missing.push("outputs/candidates.json 中没有任何候选导师");
    return { missing, counts: { candidateCount: 0 } };
  }
  const ids = file.value.map((candidate) =>
    String(candidate?.advisorProgramId || "").trim(),
  );
  if (ids.some((id) => !id)) {
    missing.push("部分候选缺少稳定的 advisorProgramId");
  }
  if (new Set(ids.filter(Boolean)).size !== ids.filter(Boolean).length) {
    missing.push("candidates.json 中的 advisorProgramId 有重复");
  }
  if (file.value.some((candidate) => ![2, 3].includes(candidate?.matchingContractVersion))) {
    missing.push("部分候选未经过 matching contract v2 确定性筛选");
  }
  const requiredFields = [
    "fit",
    "profileMatch",
    "overallMatch",
    "competitiveness",
    "hardConstraintStatus",
    "applicationPathway",
    "opportunityStatus",
    "recommendedAction",
    "feasibility",
  ];
  if (
    file.value.some((candidate) =>
      requiredFields.some((field) => !Object.hasOwn(candidate || {}, field)),
    )
  ) {
    missing.push("部分候选没有完整的 matching contract v2 字段");
  }
  const allowed = {
    competitiveness: new Set(["reach", "match", "safer", "unknown"]),
    hardConstraintStatus: new Set(["pass", "fail", "unknown"]),
    applicationPathway: new Set([
      "supervisor_led",
      "committee_led",
      "advertised_position",
      "structured_program",
      "unknown",
    ]),
    opportunityStatus: new Set([
      "verified_open",
      "signal_only",
      "unknown",
      "verified_closed",
    ]),
    feasibility: new Set(["eligible", "ineligible", "needs_confirmation"]),
  };
  const scoreIsValid = (value) =>
    value === null ||
    (typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 10);
  if (
    file.value.some(
      (candidate) =>
        ![candidate?.fit, candidate?.profileMatch, candidate?.overallMatch].every(scoreIsValid) ||
        Object.entries(allowed).some(([field, values]) => !values.has(candidate?.[field])),
    )
  ) {
    missing.push("部分候选含有超范围分数或非法匹配分类");
  }
  const inconsistent = file.value.some((candidate) => {
    const fit = candidate?.fit;
    const profile = candidate?.profileMatch;
    const hasScore = (value) =>
      value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
    const hasComponents = hasScore(fit) && hasScore(profile);
    const expectedOverall = hasComponents
      ? Math.round((Number(fit) * 0.6 + Number(profile) * 0.4) * 10) / 10
      : null;
    const overallMatches = expectedOverall === null
      ? candidate?.overallMatch === null
      : Number(candidate?.overallMatch) === expectedOverall;
    return (
      !overallMatches ||
      candidate?.recommendedAction !== recommendedActionForCandidate(candidate)
    );
  });
  if (inconsistent) {
    missing.push("部分候选的综合分或下一步与确定性匹配规则不一致");
  }
  if (file.value.some((candidate) => candidate?.recommendedAction === "exclude")) {
    missing.push("candidates.json 仍包含应由确定性筛选排除的候选");
  }
  if (!auditFile.exists) {
    missing.push("outputs/matching-audit.json 尚未生成");
  } else if (
    auditFile.invalid ||
    !auditFile.value ||
    ![2, 3].includes(auditFile.value.matchingContractVersion)
  ) {
    missing.push("outputs/matching-audit.json 不是合法的 matching contract v2 审计");
  } else if (Number(auditFile.value.selectedCount) !== file.value.length) {
    missing.push("matching-audit.json 的 selectedCount 与 candidates.json 不一致");
  } else if (
    Number(auditFile.value.reachCount) !==
    file.value.filter((candidate) => candidate?.competitiveness === "reach").length
  ) {
    missing.push("matching-audit.json 的 reachCount 与 candidates.json 不一致");
  } else if (
    Number(auditFile.value.reachCount) > Number(auditFile.value.reachCap) &&
    auditFile.value.portfolioDeviation !== "insufficient_non_reach_candidates"
  ) {
    missing.push("matching-audit.json 没有解释冲刺比例为何超过上限");
  }
  return { missing, counts: { candidateCount: file.value.length } };
}

function verifyDetective(file, { confirmedRevision, confirmedFingerprint, selectedAdvisorProgramIds, selectedSections }) {
  const missing = [];
  if (!file.exists) {
    missing.push("outputs/detective-results.json 尚未生成");
    return { missing, counts: {} };
  }
  if (file.invalid || !file.value || typeof file.value !== "object") {
    missing.push("outputs/detective-results.json 不是合法的 JSON 对象");
    return { missing, counts: {} };
  }
  const results = Array.isArray(file.value.results) ? file.value.results : [];
  if (!results.length) {
    missing.push("outputs/detective-results.json 中没有任何背调结果");
    return { missing, counts: { resultCount: 0 } };
  }

  // The artifact must belong to *this* confirmation. An agent that leaves an
  // older file untouched must not be reported as having finished this round.
  const artifactRevision = Number.isInteger(file.value.confirmedRevision)
    ? file.value.confirmedRevision
    : null;
  const artifactFingerprint = String(file.value.confirmedFingerprint || "").trim();
  if (Number.isInteger(confirmedRevision)) {
    if (artifactRevision !== confirmedRevision) {
      missing.push(
        artifactRevision === null
          ? `背调结果没有记录本次确认版本 ${confirmedRevision}`
          : `背调结果属于确认版本 ${artifactRevision}，本次确认版本是 ${confirmedRevision}`,
      );
    }
  } else if (artifactRevision === null) {
    missing.push("背调结果没有记录确认版本");
  }
  if (confirmedFingerprint) {
    if (artifactFingerprint !== confirmedFingerprint) {
      missing.push("背调结果的配置指纹与本次确认不一致");
    }
  }

  const coveredIds = new Set(
    results
      .map((item) => String(item?.advisorProgramId || "").trim())
      .filter(Boolean),
  );
  const uncovered = (selectedAdvisorProgramIds || []).filter(
    (id) => !coveredIds.has(id),
  );
  if (uncovered.length) {
    missing.push(`以下导师—项目组合还没有结果：${uncovered.join("、")}`);
  }

  // Unfinished dimensions are allowed, but they have to say so explicitly.
  const unmarked = [];
  for (const result of results) {
    const sections = result?.sections && typeof result.sections === "object"
      ? result.sections
      : {};
    for (const section of selectedSections || []) {
      const value = sections[section];
      const filled =
        (typeof value === "string" && value.trim()) ||
        (value && typeof value === "object" && (value.status || value.summary));
      if (!filled) {
        unmarked.push(
          `${result?.advisorProgramId || result?.name || "未知对象"} 的 ${section}`,
        );
      }
    }
  }
  if (unmarked.length) {
    missing.push(
      `以下维度既没有结论也没有标记未完成：${unmarked.slice(0, 8).join("、")}${
        unmarked.length > 8 ? ` 等 ${unmarked.length} 项` : ""
      }`,
    );
  }

  return { missing, counts: { resultCount: results.length } };
}

function verifyRanking(file) {
  const missing = [];
  if (!file.exists) {
    missing.push("outputs/ranking.json 尚未生成");
    return { missing, counts: {} };
  }
  if (file.invalid) {
    missing.push("outputs/ranking.json 不是合法 JSON");
    return { missing, counts: {} };
  }
  const value = file.value;
  const rankings = Array.isArray(value)
    ? value
    : Array.isArray(value?.rankings)
      ? value.rankings
      : Array.isArray(value?.ranking)
        ? value.ranking
        : null;
  if (!rankings) {
    missing.push("outputs/ranking.json 里找不到排名数组");
    return { missing, counts: {} };
  }
  if (!rankings.length) {
    missing.push("outputs/ranking.json 中没有任何排名结果");
    return { missing, counts: { rankingCount: 0 } };
  }
  const sortable = rankings.filter(
    (item) =>
      Number.isFinite(Number(item?.rank)) ||
      Number.isFinite(Number(item?.totalScore ?? item?.score)),
  );
  if (!sortable.length) {
    missing.push("排名结果既没有 rank 也没有可比较的分数");
  }
  const ids = rankings.map((item) => String(item?.advisorProgramId || "").trim());
  if (ids.some((id) => !id) || new Set(ids).size !== ids.length) {
    missing.push("排名结果缺少唯一稳定的 advisorProgramId");
  }
  const matchingFields = [
    "profileMatch",
    "overallMatch",
    "competitiveness",
    "hardConstraintStatus",
    "applicationPathway",
    "opportunityStatus",
    "recommendedAction",
  ];
  if (
    rankings.some((item) =>
      matchingFields.some((field) => !Object.hasOwn(item || {}, field)),
    )
  ) {
    missing.push("排名结果没有完整保留 Finder 的匹配、硬条件、申请路径与行动字段");
  }
  return { missing, counts: { rankingCount: rankings.length } };
}

async function verifyMedicalArtifacts(projectPath, project, mode, startedAt) {
  const [candidateFile, advisorFile, evidenceFile, auditFile, programFile, rankingFile] = await Promise.all([
    readJsonFile(projectPath, "outputs/candidates.json"),
    readJsonFile(projectPath, "outputs/advisor_records.json"),
    readJsonFile(projectPath, "outputs/evidence.json"),
    readJsonFile(projectPath, "outputs/matching-audit.json"),
    readJsonFile(projectPath, "outputs/program_records.json"),
    mode === "ranking" ? readJsonFile(projectPath, "outputs/ranking.json") : null,
  ]);
  const missing = [];
  const candidates = Array.isArray(candidateFile.value) ? candidateFile.value : [];
  if (!Array.isArray(candidateFile.value)) missing.push("candidates.json 不是候选数组");
  missing.push(...validateMedicalCandidateMappings(candidates, { advisorRecords: advisorFile.value, programRecords: programFile.value }));
  const discovery = project.searchMode === "discovery";
  let advisors = [];
  try {
    if (!Array.isArray(advisorFile.value)) throw new Error("advisor_records.json 不是导师数组");
    advisors = buildMedicalDiscoveryView(advisorFile.value, project);
  } catch (error) { missing.push(error.message); }
  if (!Array.isArray(evidenceFile.value)) missing.push("evidence.json 不是证据数组");
  for (const evidence of Array.isArray(evidenceFile.value) ? evidenceFile.value : []) {
    if (!evidence.retrieval_method) continue; // Applicant self-reports may have no web retrieval.
    try {
      const checked = researchEvidence({ ...evidence, final_url: evidence.final_url || evidence.source_url || evidence.url, page_title: evidence.page_title || evidence.title });
      if (checked.status !== evidence.status) missing.push(`${evidence.evidence_id || "证据"} 的状态与实际页面提取状态不一致`);
    } catch (error) { missing.push(`${evidence.evidence_id || "证据"}: ${error.message}`); }
  }
  const audit = auditFile.value;
  if (!audit || audit.matchingContractVersion !== 3 || audit.selectedCount !== candidates.length)
    missing.push("医学匹配审计缺失或与候选数量不一致");
  const rawRanking = rankingFile?.value;
  const rows = mode === "ranking" ? (Array.isArray(rawRanking?.rankings) ? rawRanking.rankings : []) : candidates;
  if (mode === "ranking" && (!rankingFile.exists || rankingFile.invalid)) missing.push("ranking.json 缺失或损坏");
  if (mode === "ranking" && !isMedicalRankingCurrent(project, rawRanking))
    missing.push("医学比较结果必须绑定当前调查确认版本与指纹");
  if (!rows.length && (!discovery || !advisors.length)) missing.push("没有实际医学候选或导师探索记录");
  const ids = rows.map((row) => row.advisorProgramId);
  if (ids.some((id) => !id) || new Set(ids).size !== ids.length) missing.push("医学项目候选必须有唯一真实 advisorProgramId");
  const candidateIds = new Set(candidates.map((row) => row.advisorProgramId));
  if (mode === "ranking" && ids.some((id) => !candidateIds.has(id))) missing.push("比较结果包含不在真实候选表的材料目标");
  const cvValid = await hasReadableProjectCv(projectPath, project.cv);
  for (const row of rows) {
    const expected = normalizeMedicalCandidate(row, { ...project, cvValid, evidenceRecords: evidenceFile.value });
    if (row.overallMatch !== null || row.profileMatch !== null || row.fit !== null || row.totalScore != null || row.competitiveness !== "unknown")
      missing.push("医学画像不得包含旧综合分、履历分或竞争分组");
    if (!row.evidenceProfile || row.rankingMode !== "evidence_profile") missing.push("缺少医学分维度证据画像");
    if (row.evidenceProfile && REMOVED_MEDICAL_PROFILE_KEYS.some((key) => key in row.evidenceProfile))
      missing.push("医学画像包含已删除的训练/资源/资助/环境维度");
    if (row.evidenceProfile && !row.evidenceProfile.researchQuestionFit && !row.evidenceProfile.research_question_fit)
      missing.push("医学画像缺少 researchQuestionFit");
    if (["feasibility", "opportunityStatus", "hardConstraintStatus", "recommendedAction"].some((key) => row[key] !== expected[key]))
      missing.push("医学机会、资格或下一步缺少适用的已核实证据");
  }
  const workbook = await verifyWorkbook(projectPath, discovery ? "advisor_research_discovery"
    : mode === "ranking" ? "advisor_application_ready" : "advisor_shortlist", startedAt);
  const outcome = combineArtifactChecks({ missing: [...new Set(missing)], counts: {
    candidateCount: candidates.length, discoveryCount: advisors.length,
    ...(mode === "ranking" ? { rankingCount: rows.length } : {}),
  } }, workbook);
  return withHtmlReport({ complete: outcome.missing.length === 0, completionScope: discovery ? "research_discovery" : "application_screening", ...outcome }, projectPath, project, startedAt);
}

export async function verifyRunArtifacts({
  projectPath,
  mode,
  confirmedRevision = null,
  confirmedFingerprint = null,
  investigationConfirmedRevision = null,
  investigationConfirmedFingerprint = null,
  selectedAdvisorProgramIds = [],
  selectedSections = [],
  advisorProgramId = "",
  expectedAdvisorName = "",
  applicantName = "",
  cvValid = false,
  startedAt = null,
}) {
  const projectFile = await readJsonFile(projectPath, "project.json");
  if (mode === "research_proposal" || mode === "outreach_email") {
    const outcome = await verifyApplicationMaterialArtifacts({
      projectPath,
      mode,
      advisorProgramId,
      confirmedRevision,
      confirmedFingerprint,
      expectedAdvisorName,
      applicantName,
      cvValid,
      startedAt,
    });
    if (projectFile.value?.domainProfile === "medical") {
      const project = normalizeProjectMetadata(projectFile.value);
      const [detectiveFile, rankingFile] = await Promise.all([
        readJsonFile(projectPath, "outputs", "detective-results.json"),
        readJsonFile(projectPath, "outputs", "ranking.json"),
      ]);
      outcome.missing.push(...readinessForProject({ metadata: project,
        detectiveResults: detectiveFile.value }).modes.ranking.missing);
      const investigation = project.investigation.confirmed;
      if ((investigationConfirmedRevision !== null && investigationConfirmedRevision !== investigation?.revision) ||
          (investigationConfirmedFingerprint && investigationConfirmedFingerprint !== investigation?.fingerprint)) {
        outcome.missing.push("医学调查确认在材料运行期间已变化，请按当前范围重新生成");
      }
      if (!isMedicalRankingCurrent(project, rankingFile.value) ||
          !rankingFile.value.rankings.some((row) => row.advisorProgramId === advisorProgramId)) {
        outcome.missing.push("医学申请材料依赖的比较结果已失效，请先按当前范围重新评价");
      }
      const confirmed = project.applicationMaterials.confirmed;
      if (!isApplicationMaterialsConfirmationCurrent(project.applicationMaterials) ||
          confirmed?.revision !== confirmedRevision || confirmed?.fingerprint !== confirmedFingerprint ||
          confirmed?.advisorProgramId !== advisorProgramId) {
        outcome.missing.push("医学申请材料确认在运行期间已变化，请重新确认后生成");
      }
      outcome.missing = [...new Set(outcome.missing)];
      outcome.complete = outcome.missing.length === 0;
    }
    return outcome;
  }
  if (["finder", "ranking"].includes(mode) && projectFile.value?.domainProfile === "medical") {
    const project = normalizeProjectMetadata(projectFile.value);
    const outcome = await verifyMedicalArtifacts(projectPath, project, mode, startedAt);
    if (mode === "ranking") {
      const detectiveFile = await readJsonFile(projectPath, "outputs", "detective-results.json");
      const readiness = readinessForProject({ metadata: project, detectiveResults: detectiveFile.value });
      outcome.missing.push(...readiness.modes.ranking.missing);
      const confirmed = project.investigation.confirmed;
      if ((confirmedRevision !== null && confirmedRevision !== confirmed?.revision) ||
          (confirmedFingerprint && confirmedFingerprint !== confirmed?.fingerprint)) {
        outcome.missing.push("医学调查确认在比较运行期间已变化，请按当前范围重新运行");
      }
      outcome.missing = [...new Set(outcome.missing)];
      outcome.complete = outcome.missing.length === 0;
    }
    return outcome;
  }
  if (mode === "detective") {
    const file = await readJsonFile(projectPath, "outputs", "detective-results.json");
    const primary = verifyDetective(file, {
      confirmedRevision,
      confirmedFingerprint,
      selectedAdvisorProgramIds,
      selectedSections,
      startedAt,
    });
    const workbook = await verifyWorkbook(projectPath, "advisor_detective", startedAt);
    const outcome = combineArtifactChecks(primary, workbook);
    return { complete: outcome.missing.length === 0, ...outcome };
  }
  if (mode === "ranking") {
    const file = await readJsonFile(projectPath, "outputs", "ranking.json");
    const primary = verifyRanking(file);
    const workbook = await verifyWorkbook(projectPath, "advisor_application_ready", startedAt);
    const outcome = combineArtifactChecks(primary, workbook);
    return withHtmlReport({ complete: outcome.missing.length === 0, ...outcome }, projectPath, projectFile.value || {}, startedAt);
  }
  const file = await readJsonFile(projectPath, "outputs", "candidates.json");
  const auditFile = await readJsonFile(projectPath, "outputs", "matching-audit.json");
  const primary = verifyFinder(file, auditFile);
  const workbook = await verifyWorkbook(projectPath, "advisor_shortlist", startedAt);
  const outcome = combineArtifactChecks(primary, workbook);
  return withHtmlReport({ complete: outcome.missing.length === 0, ...outcome }, projectPath, projectFile.value || {}, startedAt);
}

// Structured request for information the agent cannot proceed without. The web
// runner has no free-text channel, so the agent emits this instead of asking a
// question the user can only answer after the round ends.
export function parseInputRequest(payload) {
  const source =
    payload && typeof payload === "object"
      ? payload.type === "input.requested"
        ? payload
        : payload.input_request || payload.inputRequest
      : null;
  if (!source || typeof source !== "object") return null;
  const rawFields = Array.isArray(source.fields) ? source.fields : [];
  const allowed = new Set([
    "cv",
    "degreeLevel",
    "degree",
    "season",
    "target",
    "interests",
    "shortlistTarget",
    "medicalFields", "diseaseScope", "researchModes", "applicantBackground", "hardConstraints",
  ]);
  const fields = rawFields
    .map((field) => ({
      id: String(field?.id || "").trim(),
      label: String(field?.label || "").trim(),
      required: field?.required !== false,
      hint: String(field?.hint || "").trim() || null,
    }))
    .filter((field) => field.id && allowed.has(field.id));
  if (!fields.length) return null;
  return {
    reason: String(source.reason || source.message || "").trim() || null,
    fields,
    requestedAt: new Date().toISOString(),
  };
}

// Agents usually surface the request inside an assistant message rather than as
// a bare protocol line, so pull the first balanced JSON object that mentions it.
export function extractInputRequest(text) {
  const haystack = typeof text === "string" ? text : "";
  const marker = haystack.indexOf("input.requested");
  if (marker === -1) return null;
  let start = haystack.lastIndexOf("{", marker);
  while (start !== -1) {
    let depth = 0;
    for (let index = start; index < haystack.length; index += 1) {
      const character = haystack[index];
      if (character === "{") depth += 1;
      else if (character === "}") {
        depth -= 1;
        if (depth === 0) {
          try {
            const parsed = parseInputRequest(JSON.parse(haystack.slice(start, index + 1)));
            if (parsed) return parsed;
          } catch {
            // Not a complete JSON object; try an earlier opening brace.
          }
          break;
        }
      }
    }
    start = haystack.lastIndexOf("{", start - 1);
  }
  return null;
}
