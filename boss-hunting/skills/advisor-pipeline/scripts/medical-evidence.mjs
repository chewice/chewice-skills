// Shared projections only; advisor/program/evidence records remain the fact source.
//
// Medical / biomedical discovery describes each PI with an evidence profile
// built from three modules: identity, research papers and mainline, and
// corresponding-author papers with author profiles. Legacy records remain readable.
// Training fit, lab resources, doctoral personal funding, training environment,
// applicant ability and overall quality scores are intentionally absent.
import { doctoralAdditions } from "./doctoral-evidence.mjs";
import { academicEvents, mergeAcademicEvents } from "./academic-events.mjs";
import { hasStructuredApplicantBackground } from "./project-contract.mjs";
import { open, realpath } from "node:fs/promises";
import { isAbsolute, relative, resolve } from "node:path";

export const RESEARCH_QUESTION_FIT = ["direct", "partial", "adjacent", "weak", "insufficient_information"];
export const ROUTE_CONTINUITY = ["sustained_core", "active_emerging", "new_expansion", "occasional_participation", "unclear"];
export const PI_ROLE_CONFIDENCE = ["verified", "probable", "emerging", "identity_unresolved"];
export const PI_EVIDENCE_LEVELS = ["A", "B", "C", "D"];
export const EVIDENCE_SUFFICIENCY = ["strong", "adequate", "sparse", "conflicted"];
export const CURRENT_ACTIVITY = ["active", "recent_signal", "unclear", "apparently_inactive_in_checked_scope"];
export const DISCOVERY_ROUTES = ["research_seed", "map_seed", "collaboration", "research_neighbor", "official_roster", "unknown"];

// Fields the medical workflow no longer investigates. They are never copied
// into the current projection even when an older record still stores them.
export const REMOVED_MEDICAL_PROFILE_KEYS = [
  "collaborationNetwork", "collaboration_network",
  "trainingFit", "training_fit", "resources", "doctoralFunding", "doctoral_funding",
  "trainingEnvironment", "training_environment", "doctoralOutcomes", "doctoral_outcomes",
  "researchFunding", "research_funding", "supportedRisks", "supported_risks",
  "overallScore", "qualityScore", "mentoringSuccess", "placementRate",
];

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

function pick(source, ...keys) {
  for (const key of keys) {
    if (source && source[key] !== undefined && source[key] !== null) return source[key];
  }
  return undefined;
}

function sourceIds(value) {
  return [...new Set(list(pick(value || {}, "sourceIds", "source_ids")).map(String).filter((id) => id.trim()))];
}

function statusBlock(value, vocabulary, fallback, extra = {}) {
  const source = value && typeof value === "object" ? value : (typeof value === "string" ? { status: value } : {});
  return {
    status: vocabulary.includes(source.status) ? source.status : fallback,
    reasons: list(source.reasons).map(String),
    sourceIds: sourceIds(source),
    ...extra,
  };
}

function scalar(value, vocabulary, fallback) {
  const status = value && typeof value === "object" ? value.status : value;
  return vocabulary.includes(status) ? status : fallback;
}

export function evidenceProfile(row = {}) {
  return row.evidenceProfile || row.evidence_profile || {};
}

// Older medical records stored a `scientificFit` block. Direction fit is
// retained content, so it is carried forward under the new vocabulary.
const LEGACY_FIT = { strong: "direct", partial: "partial", adjacent: "adjacent", mismatch: "weak", insufficient_information: "insufficient_information" };

function researchQuestionFit(profile) {
  const current = pick(profile, "researchQuestionFit", "research_question_fit");
  if (current) return statusBlock(current, RESEARCH_QUESTION_FIT, "insufficient_information");
  const legacy = pick(profile, "scientificFit", "scientific_fit");
  if (!legacy) return statusBlock(undefined, RESEARCH_QUESTION_FIT, "insufficient_information");
  return statusBlock({ ...legacy, status: LEGACY_FIT[legacy.status] || "insufficient_information" },
    RESEARCH_QUESTION_FIT, "insufficient_information");
}

function representativeWork(item) {
  if (!item || typeof item !== "object") return { title: String(item ?? ""), sourceIds: [] };
  return {
    title: String(pick(item, "title") ?? ""),
    year: pick(item, "year", "date") ?? null,
    venue: pick(item, "venue", "journal", "journal_or_preprint") ?? null,
    doi: pick(item, "doi", "DOI") ?? null,
    url: pick(item, "url", "final_url") ?? null,
    verifiedRole: pick(item, "verifiedRole", "verified_role", "role") ?? "unknown",
    relationToMainline: pick(item, "relationToMainline", "relation_to_mainline", "relation") ?? null,
    isPreprint: pick(item, "isPreprint", "is_preprint") === true,
    publishedVersionDoi: pick(item, "publishedVersionDoi", "published_version_doi") ?? null,
    publicationStatus: pick(item, "publicationStatus", "publication_status") ?? null,
    sourceIds: sourceIds(item),
  };
}

function researchMainline(profile) {
  const source = pick(profile, "researchMainline", "research_mainline") || {};
  const legacy = pick(profile, "latestSignals", "latest_signals") || {};
  return {
    ...academicEvents(source),
    longTermQuestion: pick(source, "longTermQuestion", "long_term_question") ?? null,
    continuingThemes: list(pick(source, "continuingThemes", "continuing_themes")),
    newDirections: list(pick(source, "newDirections", "new_directions")),
    researchObjects: list(pick(source, "researchObjects", "research_objects")),
    methods: list(pick(source, "methods")),
    recentShift: pick(source, "recentShift", "recent_shift") ?? null,
    participationOnlyWorks: list(pick(source, "participationOnlyWorks", "participation_only_works")).map(representativeWork),
    representativeWorks: list(pick(source, "representativeWorks", "representative_works")).map(representativeWork),
    latestPapers: [...list(pick(source, "latestPapers", "latest_papers")), ...list(pick(legacy, "latestPapers", "latest_papers"))].map(representativeWork),
    preprints: [...list(source.preprints), ...list(legacy.preprints)].map(item => ({ ...representativeWork(item), isPreprint: true })),
    backSearchWindow: pick(source, "backSearchWindow", "back_search_window") ?? null,
    sourceIds: sourceIds(source),
  };
}

// Prefer a verified journal version when a preprint explicitly points to it.
// Similar titles alone do not establish a preprint-to-journal relationship.
export function researchPublications(mainline) {
  const doiKey = value => String(value || "").replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "").toLowerCase();
  const entries = [...mainline.representativeWorks, ...mainline.latestPapers, ...mainline.preprints];
  const published = new Set(entries.filter(work => !work.isPreprint).map(work => doiKey(work.doi)).filter(Boolean));
  const seen = new Map();
  for (const work of entries) {
    if (work.isPreprint && work.publishedVersionDoi && published.has(doiKey(work.publishedVersionDoi))) continue;
    const key = doiKey(work.doi) || work.url || JSON.stringify([work.title, work.year, work.isPreprint]);
    if (seen.has(key)) {
      const prior = seen.get(key);
      prior.sourceIds = [...new Set([...prior.sourceIds, ...work.sourceIds])];
    } else seen.set(key, { ...work, sourceIds: [...work.sourceIds] });
  }
  return [...seen.values()];
}

export function mergeResearchMainline(current, prior) {
  return {
    ...prior,
    ...Object.fromEntries(Object.entries(current).filter(([, value]) => Array.isArray(value) ? value.length : value)),
    representativeWorks: [...current.representativeWorks, ...prior.representativeWorks],
    latestPapers: [...current.latestPapers, ...prior.latestPapers],
    preprints: [...current.preprints, ...prior.preprints],
    ...mergeAcademicEvents(current, prior),
  };
}

function doctoralPerson(item) {
  const source = item && typeof item === "object" ? item : { name: String(item ?? "") };
  return {
    name: pick(source, "name") ?? null,
    supervisionEvidence: list(pick(source, "supervisionEvidence", "supervision_evidence")),
    degreeOrYear: pick(source, "degreeOrYear", "degree_or_year", "year") ?? null,
    topic: pick(source, "topic", "thesis", "researchTopic") ?? null,
    relationToMainline: pick(source, "relationToMainline", "relation_to_mainline") ?? null,
    outputs: list(pick(source, "outputs", "publications")),
    firstDestination: pick(source, "firstDestination", "first_destination") ?? null,
    latestPublicRole: pick(source, "latestPublicRole", "latest_public_role") ?? null,
    informationDate: pick(source, "informationDate", "information_date", "asOf") ?? null,
    sourceIds: sourceIds(source),
  };
}

function doctoralTrajectory(profile) {
  const source = pick(profile, "doctoralTrajectory", "doctoral_trajectory") || {};
  const graduate = pick(source, "graduateProgram", "graduate_program") || {};
  return {
    ...doctoralAdditions(source),
    currentDoctoral: list(pick(source, "currentDoctoral", "current_doctoral")).map(doctoralPerson),
    formerDoctoral: list(pick(source, "formerDoctoral", "former_doctoral")).map(doctoralPerson),
    graduateProgram: {
      graduateSchool: pick(graduate, "graduateSchool", "graduate_school") ?? null,
      doctoralProgram: pick(graduate, "doctoralProgram", "doctoral_program") ?? null,
      department: pick(graduate, "department") ?? null,
      supervisorListing: pick(graduate, "supervisorListing", "supervisor_listing") ?? null,
      institutionalRelationship: pick(graduate, "institutionalRelationship", "institutional_relationship") ?? null,
      sourceIds: sourceIds(graduate),
    },
    emergingPiNote: pick(source, "emergingPiNote", "emerging_pi_note") ?? null,
    sampleLimitation: pick(source, "sampleLimitation", "sample_limitation")
      ?? "已核实的公开案例，不代表完整博士生群体；不计算毕业率、去向率或培养成功率",
    sourceIds: sourceIds(source),
  };
}

function identity(profile, candidate) {
  const source = pick(profile, "identity") || {};
  return {
    currentInstitution: pick(source, "currentInstitution", "current_institution")
      ?? pick(candidate, "current_institution", "currentInstitution", "school", "schoolName") ?? null,
    department: pick(source, "department") ?? pick(candidate, "department") ?? null,
    currentPosition: pick(source, "currentPosition", "current_position") ?? pick(candidate, "title") ?? null,
    officialProfileUrl: pick(source, "officialProfileUrl", "official_profile_url") ?? pick(candidate, "homepage", "advisorHomepage") ?? null,
    researchPositioning: pick(source, "researchPositioning", "research_positioning") ?? null,
    doctoralSupervisionLink: pick(source, "doctoralSupervisionLink", "doctoral_supervision_link") ?? null,
    nameVariants: list(pick(source, "nameVariants", "name_variants")),
    identifiers: pick(source, "identifiers") && typeof source.identifiers === "object" ? source.identifiers : {},
    affiliationAsOf: pick(source, "affiliationAsOf", "affiliation_as_of") ?? null,
    sourceIds: sourceIds(source),
  };
}

export const IDENTITY_FIELDS = [
  ["currentInstitution", "当前机构"], ["department", "院系"], ["currentPosition", "职位"],
  ["researchPositioning", "主要研究方向"], ["doctoralSupervisionLink", "博士指导关联"],
  ["affiliationAsOf", "任职信息核对日期"],
];

// Audit explicit field evidence; never extract facts from citation labels or URLs.
export function identityCoverage(candidate = {}, evidence = []) {
  const profile = normalizeMedicalEvidenceProfile(candidate);
  const advisorId = candidate.advisor_id || candidate.advisorId;
  const canonical = (value) => String(value).split('.').at(-1).replaceAll('_', '').toLowerCase();
  const states = { not_checked: "未核验", not_found: "所查来源未提供", inaccessible: "访问受阻", conflict: "来源存在冲突", partial: "部分核验", stale: "信息可能过期", not_applicable: "不适用" };
  const fields = IDENTITY_FIELDS.map(([field, label]) => {
    const value = profile.identity[field];
    const present = typeof value === "string" && Boolean(value.trim());
    const rows = evidence.filter((row) => advisorId && (row.entity_id || row.entity) === advisorId
      && list(row.fields_supported || row.fieldsSupported).some((key) => canonical(key) === canonical(field)));
    const usable = (row) => {
      try {
        const url = new URL(row.final_url || row.source_url || row.url || "");
        return ["http:", "https:"].includes(url.protocol)
          && Boolean((row.evidence_id || row.evidenceId) && typeof row.claim === "string" && row.claim.trim())
          && !["empty_shell", "dynamic_form", "loading"].includes(row.page_state);
      } catch { return false; }
    };
    const limitation = rows.find((row) => row.status === "conflict")
      || rows.find((row) => Object.hasOwn(states, row.status));
    const verified = rows.some((row) => row.status === "verified" && usable(row));
    const dateValid = field !== "affiliationAsOf" || (/^\d{4}-\d{2}-\d{2}$/.test(value || "")
      && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value);
    const complete = present && dateValid && verified && !limitation;
    const reason = complete ? "" : limitation
      ? `${states[limitation.status]}：${limitation.limitations || limitation.reason || limitation.claim || "缺少具体说明"}`
      : !present ? verified ? "已有字段证据，尚未写入记录；需核对正文并补填" : "未核验：字段尚未记录"
      : !dateValid ? "核对日期格式无效，需记录实际核验日期" : "字段已记录，对应字段来源待核验";
    return { field, label, value, complete, reason,
      sourceIds: rows.map((row) => row.evidence_id || row.evidenceId).filter(Boolean) };
  });
  return { complete: fields.every((field) => field.complete), fields,
    gaps: fields.filter((field) => !field.complete).map(({ field, label, reason }) => ({ field, label, reason })) };
}

export function normalizeMedicalEvidenceProfile(candidate = {}) {
  const profile = evidenceProfile(candidate);
  const role = pick(profile, "piRoleConfidence", "pi_role_confidence") || {};
  const level = String(pick(role, "level") ?? pick(candidate, "pi_evidence_level", "piEvidenceLevel") ?? "").toUpperCase();
  return {
    researchQuestionFit: researchQuestionFit(profile),
    researchRouteContinuity: statusBlock(pick(profile, "researchRouteContinuity", "research_route_continuity"), ROUTE_CONTINUITY, "unclear"),
    piRoleConfidence: statusBlock(role, PI_ROLE_CONFIDENCE, "identity_unresolved",
      { level: PI_EVIDENCE_LEVELS.includes(level) ? level : null }),
    evidenceSufficiency: scalar(pick(profile, "evidenceSufficiency", "evidence_sufficiency"), EVIDENCE_SUFFICIENCY, "sparse"),
    currentActivity: scalar(pick(profile, "currentActivity", "current_activity"), CURRENT_ACTIVITY, "unclear"),
    identity: identity(profile, candidate),
    researchMainline: researchMainline(profile),
    doctoralTrajectory: doctoralTrajectory(profile),
    formalRecords: list(pick(profile, "formalRecords", "formal_records")),
    fitBoundary: pick(profile, "fitBoundary", "fit_boundary") ?? null,
    keyUnknowns: [...new Set(list(pick(profile, "keyUnknowns", "key_unknowns")).map(String))],
    nextVerification: list(pick(profile, "nextVerification", "next_verification")).map(String),
  };
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
  const profile = normalizeMedicalEvidenceProfile(candidate);
  const discovery = options.searchMode === "discovery";
  const constraints = String(options.hardConstraints || "").trim();
  const hasAdditionalConstraints = Boolean(constraints) && !new Set([
    "无自设硬条件", "无自设条件", "无附加约束", "无附加硬约束", "none", "no additional constraints",
  ]).has(constraints.toLowerCase());
  const hasBackground = options.cvValid === true || hasStructuredApplicantBackground(options);
  const reasons = profile.keyUnknowns.slice();
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
  let action = "verify_eligibility";
  if (excluded) action = "exclude";
  else if (discovery) action = "continue_investigation";
  else if (pathway === "unknown") action = "verify_pathway";
  else if (hasAdditionalConstraints && hardConstraintStatus === "unknown") action = "verify_constraints";
  else if (actionable) action = pathway === "advertised_position" ? "apply_vacancy" :
    pathway === "supervisor_led" ? "contact_supervisor" : "apply_program";
  else if (feasibility === "eligible") action = "verify_opportunity";
  const discoveredVia = String(candidate.discovered_via || candidate.discoveredVia || "unknown");
  const row = { ...candidate };
  for (const key of REMOVED_MEDICAL_PROFILE_KEYS) delete row[key];
  return {
    ...row,
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
    discoveredVia: DISCOVERY_ROUTES.includes(discoveredVia) ? discoveredVia : "unknown",
    networkRound: Math.max(0, Number(candidate.network_round ?? candidate.networkRound) || 0),
    comparisonGroup: excluded ? "not_applicable" : actionable ? "actionable" :
      profile.researchQuestionFit.status === "weak" ? "follow_up" : "needs_verification",
    evidenceProfile: { ...profile, keyUnknowns: [...new Set(reasons)] },
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

// Research-question fit and route continuity define the display /
// further-investigation order. This is never a PI quality ranking; citations,
// H-index, prestige, grant totals and network centrality do not participate.
export function compareMedicalCandidates(left, right) {
  const fit = RESEARCH_QUESTION_FIT;
  const continuity = ROUTE_CONTINUITY;
  return fit.indexOf(left.evidenceProfile.researchQuestionFit.status) - fit.indexOf(right.evidenceProfile.researchQuestionFit.status) ||
    continuity.indexOf(left.evidenceProfile.researchRouteContinuity.status) - continuity.indexOf(right.evidenceProfile.researchRouteContinuity.status) ||
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

// Discovery stops when a round adds few validated PIs and no new scientific
// structure. The 10% ratio is a configurable engineering default.
export function saturationReached({ existingValidated = 0, newValidated = 0, newSubdirections = 0, newClusters = 0, round = 1, maxRounds = 2, ratio = 0.10 } = {}) {
  const base = Math.max(1, Number(existingValidated) || 0);
  const growth = (Number(newValidated) || 0) / base;
  const structural = (Number(newSubdirections) || 0) > 0 || (Number(newClusters) || 0) > 0;
  const piSaturated = (Number(newValidated) || 0) === 0;
  const engineering = growth < ratio && !structural;
  const roundLimit = Number(round) >= Number(maxRounds);
  const stop = piSaturated || engineering || roundLimit;
  return {
    stop,
    reason: piSaturated ? "pi_saturation" : engineering ? "engineering_heuristic" : roundLimit ? "max_rounds" : "continue",
    growthRatio: Number(growth.toFixed(3)),
    ratioThreshold: ratio,
    structuralNovelty: structural,
    note: "10% is a configurable engineering default, not a scientific standard",
  };
}
