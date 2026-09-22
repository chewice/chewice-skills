// Shared projections only; advisor/program/evidence records remain the fact source.
import { hasStructuredApplicantBackground } from "./project-contract.mjs";
import { open, realpath } from "node:fs/promises";
import { isAbsolute, relative, resolve } from "node:path";

export async function hasReadableProjectCv(projectRoot, cv) {
  if (!cv || typeof cv.path !== "string" || !cv.path.trim()) return false;
  let file;
  try {
    const root = await realpath(resolve(projectRoot));
    const candidate = await realpath(resolve(projectRoot, cv.path));
    const insideInputs = relative(resolve(root, "inputs"), candidate);
    if (!insideInputs || insideInputs === ".." || insideInputs.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`) || isAbsolute(insideInputs)) return false;
    file = await open(candidate, "r");
    const metadata = await file.stat();
    if (!metadata.isFile() || metadata.size === 0) return false;
    // Check readability without parsing or logging personal document contents.
    const result = await file.read(Buffer.alloc(1), 0, 1, 0);
    return result.bytesRead === 1;
  } catch { return false; }
  finally { if (file) await file.close(); }
}

export function isMedicalEvidenceProfile(project = {}) {
  // Medical projects currently have one supported comparison contract. Even a
  // stale weighted_score field must not silently activate the legacy selector.
  return project.domainProfile === "medical";
}

export function medicalProject(input = {}) {
  return input.project || input.config || input;
}

function list(value) {
  return Array.isArray(value) ? value : [];
}

export function evidenceProfile(row = {}) {
  return row.evidenceProfile || row.evidence_profile || {};
}

function scopedEvidence(row, field, options = {}) {
  const snake = field.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
  const evidence = row[field] || row[snake] || evidenceProfile(row)[field] || evidenceProfile(row)[snake] || {};
  const sources = evidence.sourceIds || evidence.source_ids || [];
  const scoped = evidence.status === "verified" && Array.isArray(sources) && sources.some((source) => String(source).trim()) &&
    (evidence.advisorProgramId || evidence.advisor_program_id) === row.advisorProgramId &&
    Boolean(row.advisorProgramId) &&
    (!evidence.intake || evidence.intake === row.intake);
  if (!scoped || !("evidenceRecords" in options)) return scoped;
  if (!Array.isArray(options.evidenceRecords)) return false;
  const records = new Map(options.evidenceRecords.map((record) => [record.evidence_id || record.evidenceId, record]));
  const cited = sources.map((id) => records.get(id));
  if (cited.some((record) => !record || record.status !== "verified" ||
    (record.claim_type || record.claimType) !== "fact" ||
    (record.extraction_status && record.extraction_status !== "success"))) return false;
  const supportedFields = {
    eligibilityEvidence: ["eligibility", "feasibility"],
    opportunityEvidence: ["opportunity", "opportunity_status", "opportunityStatus"],
    hardConstraintEvidence: ["hard_constraint", "hard_constraints", "hardConstraintStatus"],
  }[field];
  const entities = [row.advisorProgramId, row.program_id || row.programId, row.advisor_id || row.advisorId].filter(Boolean);
  return cited.some((record) => {
    const fields = record.fields_supported || (record.field ? [record.field] : []);
    return Array.isArray(fields) && supportedFields.some((key) => fields.includes(key)) &&
      entities.includes(record.entity_id || record.entityId) &&
      (record.applicable_intake || record.intake) === row.intake && Boolean(row.intake);
  });
}

export function normalizeMedicalCandidate(candidate, options = {}, index = 0) {
  const profile = evidenceProfile(candidate);
  const scientific = profile.scientificFit || profile.scientific_fit || {};
  const training = profile.trainingFit || profile.training_fit || {};
  const discovery = options.searchMode === "discovery";
  const constraints = String(options.hardConstraints || "").trim();
  const hasAdditionalConstraints = Boolean(constraints) && !new Set([
    "无自设硬条件", "无自设条件", "无附加约束", "无附加硬约束", "none", "no additional constraints",
  ]).has(constraints.toLowerCase());
  const hasBackground = options.cvValid === true || hasStructuredApplicantBackground(options);
  const reasons = list(profile.keyUnknowns || profile.key_unknowns).slice();
  let feasibility = ["eligible", "ineligible", "needs_confirmation"].includes(candidate.feasibility) ? candidate.feasibility : "needs_confirmation";
  let hardConstraintStatus = ["pass", "fail", "unknown"].includes(candidate.hardConstraintStatus) ? candidate.hardConstraintStatus : "unknown";
  let opportunityStatus = ["verified_open", "verified_closed", "signal_only", "unknown"].includes(candidate.opportunityStatus) ? candidate.opportunityStatus : "unknown";
  if (discovery || !hasBackground || !scopedEvidence(candidate, "eligibilityEvidence", options)) {
    feasibility = "needs_confirmation";
  }
  if (!scopedEvidence(candidate, "hardConstraintEvidence", options)) hardConstraintStatus = "unknown";
  if (["verified_open", "verified_closed"].includes(opportunityStatus) &&
      !scopedEvidence(candidate, "opportunityEvidence", options)) {
    reasons.push("招生结论缺少本项目批次的已核实证据");
    opportunityStatus = "unknown";
  }
  const excluded = hardConstraintStatus === "fail" || feasibility === "ineligible" ||
    opportunityStatus === "verified_closed";
  const pathway = ["committee_led", "structured_program", "supervisor_led", "advertised_position", "unknown"].includes(candidate.applicationPathway) ? candidate.applicationPathway : "unknown";
  const usablePathway = ["committee_led", "structured_program"].includes(pathway) ||
    opportunityStatus === "verified_open";
  const actionable = !discovery && !excluded && feasibility === "eligible" &&
    (hardConstraintStatus === "pass" || !hasAdditionalConstraints) &&
    pathway !== "unknown" && usablePathway;
  const scientificStatus = ["strong", "partial", "adjacent", "mismatch", "insufficient_information"].includes(scientific.status)
    ? scientific.status : "insufficient_information";
  let action = "verify_eligibility";
  if (excluded) action = "exclude";
  else if (discovery) action = "verify_research_or_pathway";
  else if (pathway === "unknown") action = "verify_pathway";
  else if (hasAdditionalConstraints && hardConstraintStatus === "unknown") action = "verify_constraints";
  else if (actionable) action = pathway === "advertised_position" ? "apply_vacancy" :
    pathway === "supervisor_led" ? "contact_supervisor" : "apply_program";
  else if (feasibility === "eligible") action = "verify_opportunity";
  return {
    ...candidate,
    rank: index + 1,
    rankingMode: "evidence_profile",
    rankSemantics: "display_order",
    fit: null,
    profileMatch: null,
    overallMatch: null,
    totalScore: null,
    competitiveness: "unknown",
    feasibility,
    hardConstraintStatus,
    opportunityStatus,
    applicationPathway: pathway,
    recommendedAction: action,
    comparisonGroup: excluded ? "not_applicable" : actionable ? "actionable" :
      scientificStatus === "mismatch" ? "follow_up" : "needs_verification",
    evidenceProfile: {
      ...profile,
      scientificFit: { ...scientific, status: scientificStatus },
      trainingFit: { ...training, status: ["supported", "partial", "unknown"].includes(training.status) ? training.status : "unknown" },
      resources: list(profile.resources || candidate.resources),
      researchFunding: list(profile.researchFunding || profile.research_funding || candidate.research_funding),
      doctoralFunding: list(profile.doctoralFunding || profile.doctoral_funding || candidate.doctoral_funding),
      doctoralOutcomes: profile.doctoralOutcomes || profile.doctoral_outcomes || candidate.doctoral_outcomes || null,
      trainingEnvironment: profile.trainingEnvironment || profile.training_environment || candidate.training_environment || null,
      supportedRisks: list(profile.supportedRisks || profile.supported_risks || candidate.risksAndGaps),
      nextVerification: list(profile.nextVerification || profile.next_verification),
      keyUnknowns: [...new Set(reasons)],
    },
  };
}

export function validateMedicalCandidateMappings(candidates, { advisorRecords = [], programRecords = [] } = {}) {
  const advisors = new Map(list(advisorRecords).map((row) => [row.advisor_id || row.advisorId, row]));
  const programs = new Map(list(programRecords).map((row) => [row.program_id || row.programId, row]));
  const errors = [];
  for (const [index, row] of list(candidates).entries()) {
    const label = row.advisorProgramId || `row ${index + 1}`;
    const advisorId = row.advisor_id || row.advisorId;
    const programId = row.program_id || row.programId;
    if (!advisorId || !advisors.has(advisorId)) errors.push(`${label}: advisor_id 未映射真实 advisor_records`);
    const program = programs.get(programId);
    if (!programId || !program) errors.push(`${label}: program_id 未映射真实 program_records`);
    else {
      if (!program.degree || !program.intake) errors.push(`${label}: 真实项目记录缺少学位或批次`);
      if (!row.intake || row.intake !== program.intake) errors.push(`${label}: intake 与真实项目批次不一致`);
      if (row.degree && row.degree !== program.degree) errors.push(`${label}: degree 与真实项目学位不一致`);
    }
  }
  return errors;
}

// Research/desired training take priority over webpage volume or applicant scores.
// Categories are an explicit investigation order, never an overall quality score.
export function compareMedicalCandidates(left, right) {
  const scientific = ["strong", "partial", "adjacent", "insufficient_information", "mismatch"];
  const training = ["supported", "partial", "unknown"];
  return scientific.indexOf(left.evidenceProfile.scientificFit.status) - scientific.indexOf(right.evidenceProfile.scientificFit.status) ||
    training.indexOf(left.evidenceProfile.trainingFit.status) - training.indexOf(right.evidenceProfile.trainingFit.status) ||
    String(left.name || left.advisorName || left.advisor_id || "").localeCompare(String(right.name || right.advisorName || right.advisor_id || "")) ||
    String(left.advisorProgramId || left.advisor_id || "").localeCompare(String(right.advisorProgramId || right.advisor_id || ""));
}

export function buildMedicalDiscoveryView(records, options = {}) {
  const advisors = list(records);
  const ids = advisors.map((row) => String(row.advisor_id || row.advisorId || "").trim());
  if (ids.some((id) => !id) || new Set(ids).size !== ids.length) {
    throw new Error("医学探索需要唯一真实 advisor_id；不得用虚构项目代替导师身份");
  }
  return advisors.map((advisor, index) => {
    const row = normalizeMedicalCandidate(advisor, { ...options, searchMode: "discovery" }, index);
    // This advisor-level view cannot be selected by application-material consumers.
    for (const key of ["advisorProgramId", "advisor_program_id", "programId", "program_id", "program", "intake"]) delete row[key];
    return { ...row, advisor_id: ids[index], view: "research_discovery" };
  }).sort(compareMedicalCandidates).map((row, index) => ({ ...row, rank: index + 1 }));
}
