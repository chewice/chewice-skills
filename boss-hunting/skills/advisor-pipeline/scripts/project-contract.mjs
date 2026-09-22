import { createHash } from "node:crypto";

export const PROJECT_SCHEMA_VERSION = 9;
export const STATUS_SCHEMA_VERSION = 2;

export const APPLICATION_MATERIAL_IDS = [
  "research_proposal",
  "outreach_email",
];

export const DEFAULT_DETECTIVE_SECTIONS = [
  "identity_current_role",
  "recent_research",
  "current_projects_recruiting",
];

export const DETECTIVE_SECTIONS = [
  ...DEFAULT_DETECTIVE_SECTIONS,
  "research_output_trend",
  "group_members_outcomes",
  "guidance_group_ecology",
  "work_style_pressure",
  "resources_career_support",
  "integrity_public_controversies",
  "international_student_support",
  "collaboration_industry_network",
];

// The single ordered catalog both the Web checkboxes and the CLI menu render.
export const DETECTIVE_SECTION_CATALOG = [
  { id: "identity_current_role", label: "基础身份与当前职位", defaultSelected: true },
  { id: "recent_research", label: "最近三年研究兴趣与方向", defaultSelected: true },
  {
    id: "current_projects_recruiting",
    label: "近期项目与招生状态",
    defaultSelected: true,
  },
  { id: "research_output_trend", label: "研究产出与趋势", defaultSelected: false },
  { id: "group_members_outcomes", label: "课题组成员及去向", defaultSelected: false },
  { id: "guidance_group_ecology", label: "指导环境与组内生态", defaultSelected: false },
  { id: "work_style_pressure", label: "工作方式与压力", defaultSelected: false },
  {
    id: "resources_career_support",
    label: "资源、funding、署名与职业支持",
    defaultSelected: false,
  },
  {
    id: "integrity_public_controversies",
    label: "学术诚信与公开争议",
    defaultSelected: false,
  },
  {
    id: "international_student_support",
    label: "国际学生支持",
    defaultSelected: false,
  },
  {
    id: "collaboration_industry_network",
    label: "合作者、产业和职业网络",
    defaultSelected: false,
  },
];

export const MEDICAL_DEFAULT_DETECTIVE_SECTIONS = [
  ...DEFAULT_DETECTIVE_SECTIONS,
  "research_output_trend",
  "group_members_outcomes",
  "resources_career_support",
  "collaboration_industry_network",
];

export const EVIDENCE_STATUSES = [
  "verified", "not_found", "not_checked", "inaccessible", "conflict", "stale", "not_applicable",
];

export function defaultDetectiveSections(project = {}) {
  return [...(project.domainProfile === "medical"
    ? MEDICAL_DEFAULT_DETECTIVE_SECTIONS : DEFAULT_DETECTIVE_SECTIONS)];
}

export function getDetectiveSectionCatalog(project = {}) {
  const defaults = defaultDetectiveSections(project);
  return DETECTIVE_SECTION_CATALOG.map((section) => ({
    ...section,
    label: project.domainProfile === "medical" && section.id === "recent_research"
      ? "近期科学问题、研究方式与训练匹配" : section.label,
    defaultSelected: defaults.includes(section.id),
  }));
}

export function investigationCostLevel(workUnits) {
  if (workUnits <= 8) return "low";
  if (workUnits <= 24) return "medium";
  return "high";
}

export const COMMUNITY_SECTION_IDS = [
  "guidance_group_ecology",
  "work_style_pressure",
  "resources_career_support",
];

export const STRUCTURED_OUTPUT_FILES = [
  "candidates.json",
  "advisor_records.json",
  "program_records.json",
  "evidence.json",
];

function text(value, limit = 500) {
  return String(value ?? "").trim().slice(0, limit);
}

function stringList(value) {
  return [...new Set((Array.isArray(value) ? value : [])
    .map((item) => text(item, 500)).filter(Boolean))];
}

export function normalizeMedicalProfile(input, target = "") {
  const source = input && typeof input === "object" && !Array.isArray(input) ? input : {};
  const normalized = { ...source };
  for (const key of ["fields", "diseasesOrMechanisms", "researchQuestions", "researchModes",
    "researchObjects", "currentSkills", "desiredTraining", "adjacentInterests", "exclusions"]) {
    normalized[key] = stringList(source[key]);
  }
  normalized.diseaseScope = text(source.diseaseScope, 120) || "unasked";
  // target is the authoritative region/school scope after initial import.
  normalized.regions = target ? stringList(target.split(/[;；\n]+/)) : stringList(source.regions);
  normalized.inputStatus = {};
  for (const key of ["fields", "diseaseScope", "researchModes", "regions", "desiredTraining", "exclusions"]) {
    const explicit = source.inputStatus?.[key];
    const hasValue = key === "diseaseScope"
      ? normalized.diseaseScope !== "unasked" : normalized[key].length > 0;
    normalized.inputStatus[key] = ["undecided", "unrestricted"].includes(explicit)
      ? explicit : key === "diseaseScope" && normalized.diseaseScope === "undecided"
        ? "undecided" : hasValue ? "answered" : "unasked";
  }
  return normalized;
}

export function hasStructuredApplicantBackground(project = {}) {
  const background = project.applicantBackground;
  return ["self_reported", "documented"].includes(background?.source) &&
    ["education", "researchExperience", "qualifications"].some((key) =>
      Array.isArray(background[key]) && background[key].some((item) =>
        typeof item === "string" ? item.trim() : item && typeof item === "object" && Object.keys(item).length));
}

export function medicalIntakeStatus(project = {}) {
  const profile = normalizeMedicalProfile(project.medicalProfile, project.target);
  const answered = (key) => profile.inputStatus[key] !== "unasked";
  const steps = [
    { key: "medical_fields", label: "明确医学领域或明确不限", complete: answered("fields") },
    { key: "medical_research", label: "明确疾病/机制和研究方式，或明确未定",
      complete: answered("diseaseScope") && answered("researchModes") },
    { key: "medical_regions", label: "明确目标地区或明确不限", complete: answered("regions") },
  ];
  return { ready: steps.every((step) => step.complete), steps,
    nextStep: steps.findIndex((step) => !step.complete) < 0 ? 4 : steps.findIndex((step) => !step.complete) + 1,
    missing: steps.filter((step) => !step.complete).map((step) => step.label) };
}

function medicalScopeFingerprint(project) {
  return createHash("sha256").update(JSON.stringify({
    domainProfile: project.domainProfile, searchMode: project.searchMode,
    evaluationMode: project.evaluationMode, medicalProfile: project.medicalProfile,
    target: project.target, degree: project.degree, season: project.season,
    hardConstraints: project.hardConstraints, applicantBackground: project.applicantBackground,
    cv: project.cv,
  })).digest("hex");
}

export function isUsableApplicantName(value) {
  const name = text(value, 160);
  if (name.length < 2) return false;
  const key = name
    .normalize("NFKC")
    .toLocaleLowerCase()
    .replace(/[\s_\-\[\]{}()<>:：]+/g, "");
  return !new Set([
    "name",
    "yourname",
    "applicantname",
    "fullname",
    "test",
    "testuser",
    "sample",
    "sampleuser",
    "placeholder",
    "姓名",
    "申请者姓名",
    "真实姓名",
    "待填写",
  ]).has(key);
}

export function isSafeAdvisorProgramId(value) {
  const id = String(value ?? "").trim();
  return Boolean(
    id &&
      id.length <= 500 &&
      id !== "." &&
      id !== ".." &&
      !id.includes("/") &&
      !id.includes("\\") &&
      !id.includes("\0"),
  );
}

function validTimestamp(value, fallback) {
  const candidate = text(value, 80);
  return candidate && Number.isFinite(Date.parse(candidate)) ? candidate : fallback;
}

export function normalizeShortlistTarget(value, fallback = 10) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(5, Math.min(50, Math.round(parsed)));
}

export function normalizePortfolioStrategy(value, fallback = "balanced") {
  const normalized = String(value || "").trim().toLowerCase();
  return ["balanced", "conservative", "ambitious"].includes(normalized)
    ? normalized
    : fallback;
}

export const APPLICATION_PATHWAYS = [
  "supervisor_led",
  "committee_led",
  "advertised_position",
  "structured_program",
  "unknown",
];

export const OPPORTUNITY_STATUSES = [
  "verified_open",
  "signal_only",
  "unknown",
  "verified_closed",
];

export const HARD_CONSTRAINT_STATUSES = ["pass", "fail", "unknown"];

export function normalizeApplicationPathway(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return APPLICATION_PATHWAYS.includes(normalized) ? normalized : "unknown";
}

export function normalizeOpportunityStatus(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return OPPORTUNITY_STATUSES.includes(normalized) ? normalized : "unknown";
}

export function normalizeHardConstraintStatus(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return HARD_CONSTRAINT_STATUSES.includes(normalized) ? normalized : "unknown";
}

export function recommendedActionForCandidate(candidate = {}) {
  const hardStatus = normalizeHardConstraintStatus(candidate.hardConstraintStatus);
  const pathway = normalizeApplicationPathway(candidate.applicationPathway);
  const opportunity = normalizeOpportunityStatus(candidate.opportunityStatus);
  const feasibility = String(candidate.feasibility || "needs_confirmation").trim();
  if (hardStatus === "fail" || feasibility === "ineligible" || opportunity === "verified_closed") {
    return "exclude";
  }
  if (pathway === "unknown") return "verify_pathway";
  if (hardStatus === "unknown") return "verify_constraints";
  if (feasibility === "needs_confirmation") return "verify_eligibility";
  if (pathway === "advertised_position") {
    return opportunity === "verified_open" || opportunity === "signal_only"
      ? "apply_vacancy"
      : "monitor";
  }
  if (pathway === "supervisor_led") return "contact_supervisor";
  if (pathway === "committee_led" || pathway === "structured_program") {
    return "apply_program";
  }
  return "verify_pathway";
}

export function normalizeInterests(input) {
  if (!Array.isArray(input)) return [];
  const interests = input
    .map((interest) =>
      typeof interest === "string"
        ? { name: text(interest, 120), weight: Number.NaN }
        : {
            name: text(interest?.name, 120),
            weight: Number(interest?.weight),
          },
    )
    .filter((interest) => interest.name);
  if (!interests.length) return [];

  const explicitTotal = interests.reduce(
    (sum, interest) =>
      sum + (Number.isFinite(interest.weight) && interest.weight > 0 ? interest.weight : 0),
    0,
  );
  const missingCount = interests.filter(
    (interest) => !Number.isFinite(interest.weight) || interest.weight <= 0,
  ).length;
  const explicitCount = interests.length - missingCount;
  const fallbackWeight =
    explicitTotal > 0 && explicitTotal < 100 && missingCount > 0
      ? (100 - explicitTotal) / missingCount
      : explicitTotal > 0 && explicitCount > 0
        ? explicitTotal / explicitCount
        : 1;
  const basis = interests.map((interest) => ({
    ...interest,
    weight:
      Number.isFinite(interest.weight) && interest.weight > 0
        ? interest.weight
        : fallbackWeight,
  }));
  const total = basis.reduce((sum, interest) => sum + interest.weight, 0);
  return basis.map((interest, index) => ({
    name: interest.name,
    weight:
      index === basis.length - 1
        ? Math.round(
            (100 -
              basis
                .slice(0, -1)
                .reduce(
                  (sum, item) => sum + Math.round((item.weight / total) * 1000) / 10,
                  0,
                )) * 10,
          ) / 10
        : Math.round((interest.weight / total) * 1000) / 10,
  }));
}

function normalizeSectionList(input, fallback = []) {
  if (!Array.isArray(input)) return [...fallback];
  return [
    ...new Set(input.map(String).filter((item) => DETECTIVE_SECTIONS.includes(item))),
  ];
}

function normalizeSelection(input, fallback = {}) {
  const source = input && typeof input === "object" ? input : {};
  const selectedIds =
    source.selectedAdvisorProgramIds ??
    source.selected_advisor_program_ids ??
    fallback.selectedAdvisorProgramIds ??
    [];
  const selectedSections =
    source.selectedSections ??
    source.selected_sections ??
    fallback.selectedSections;
  const community = source.communitySources ?? source.community_sources ?? {};
  const sourcePolicy = (source.sourcePolicy ?? fallback.sourcePolicy) === "public_only"
    ? "public_only" : "community_allowed";
  return {
    sourcePolicy,
    researchScopeFingerprint: text(source.researchScopeFingerprint ?? fallback.researchScopeFingerprint, 128),
    selectedAdvisorProgramIds: [
      ...new Set((Array.isArray(selectedIds) ? selectedIds : []).map(String).filter(Boolean)),
    ],
    selectedSections: normalizeSectionList(
      selectedSections,
      DEFAULT_DETECTIVE_SECTIONS,
    ),
    communitySources: {
      requested: sourcePolicy !== "public_only" && Boolean(
        community.requested ??
          community.consented ??
          fallback.communitySources?.requested ??
          false,
      ),
    },
  };
}

function sameSelection(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function normalizeConfirmed(input, now) {
  if (!input || typeof input !== "object") return null;
  const selection = normalizeSelection({
    ...input,
    communitySources: {
      requested: Boolean(input.communitySources?.consented),
    },
  });
  const consented =
    selection.sourcePolicy !== "public_only" &&
    hasCommunitySections(selection.selectedSections) &&
    Boolean(input.communitySources?.consented);
  return {
    sourcePolicy: selection.sourcePolicy,
    researchScopeFingerprint: selection.researchScopeFingerprint,
    selectedAdvisorProgramIds: selection.selectedAdvisorProgramIds,
    selectedSections: selection.selectedSections,
    communitySources: {
      consented,
      consentedAt: consented
        ? validTimestamp(input.communitySources?.consentedAt, now)
        : null,
    },
    revision: Math.max(0, Number(input.revision) || 0),
    confirmedAt: validTimestamp(input.confirmedAt, now),
    fingerprint:
      text(input.fingerprint, 128) ||
      investigationFingerprint({
        selectedAdvisorProgramIds: selection.selectedAdvisorProgramIds,
        selectedSections: selection.selectedSections,
        sourcePolicy: selection.sourcePolicy,
        researchScopeFingerprint: selection.researchScopeFingerprint,
        communitySources: { consented },
      }),
    source: input.source === "legacy_artifact" ? "legacy_artifact" : "user_confirmed",
  };
}

export function normalizeInvestigation(input, now = new Date().toISOString()) {
  const source = input && typeof input === "object" ? input : {};
  const draftSource = source.draft ?? source;
  const selection = normalizeSelection(draftSource);
  return {
    draft: {
      ...selection,
      revision: Math.max(0, Number(draftSource.revision) || 0),
      updatedAt: validTimestamp(draftSource.updatedAt, now),
    },
    confirmed: normalizeConfirmed(source.confirmed, now),
  };
}

export function updateInvestigationDraft(
  existing,
  patch,
  now = new Date().toISOString(),
) {
  const current = normalizeInvestigation(existing, now);
  const source = patch?.draft ?? patch ?? {};
  const nextSelection = normalizeSelection(source, current.draft);
  if (!hasCommunitySections(nextSelection.selectedSections)) {
    nextSelection.communitySources.requested = false;
  }
  const currentSelection = {
    sourcePolicy: current.draft.sourcePolicy,
    researchScopeFingerprint: current.draft.researchScopeFingerprint,
    selectedAdvisorProgramIds: current.draft.selectedAdvisorProgramIds,
    selectedSections: current.draft.selectedSections,
    communitySources: current.draft.communitySources,
  };
  const changed = !sameSelection(nextSelection, currentSelection);
  return {
    draft: {
      ...nextSelection,
      revision: changed ? current.draft.revision + 1 : current.draft.revision,
      updatedAt: changed ? now : current.draft.updatedAt,
    },
    confirmed: current.confirmed,
  };
}

export function hasCommunitySections(selectedSections) {
  return Array.isArray(selectedSections) &&
    selectedSections.some((section) => COMMUNITY_SECTION_IDS.includes(section));
}

export function investigationFingerprint(selection) {
  const canonical = {
    selectedAdvisorProgramIds: [
      ...new Set((selection?.selectedAdvisorProgramIds || []).map(String)),
    ].sort(),
    selectedSections: [
      ...new Set((selection?.selectedSections || []).map(String)),
    ].sort(),
    communityConsent: Boolean(selection?.communitySources?.consented),
  };
  // Preserve existing general-mode fingerprints during schema migration.
  if (selection?.sourcePolicy === "public_only" || selection?.researchScopeFingerprint) {
    canonical.sourcePolicy = selection?.sourcePolicy || "community_allowed";
    canonical.researchScopeFingerprint = selection?.researchScopeFingerprint || "";
  }
  return createHash("sha256").update(JSON.stringify(canonical)).digest("hex");
}

export function isInvestigationConfirmationCurrent(investigation) {
  const current = normalizeInvestigation(investigation);
  if (!current.confirmed) return false;
  return (
    current.confirmed.revision === current.draft.revision &&
    current.confirmed.fingerprint ===
      investigationFingerprint({
        selectedAdvisorProgramIds: current.draft.selectedAdvisorProgramIds,
        selectedSections: current.draft.selectedSections,
        sourcePolicy: current.draft.sourcePolicy,
        researchScopeFingerprint: current.draft.researchScopeFingerprint,
        communitySources: {
          consented:
            hasCommunitySections(current.draft.selectedSections) &&
            current.draft.communitySources.requested,
        },
      })
  );
}

export function isMedicalRankingCurrent(project, ranking) {
  const confirmed = project?.investigation?.confirmed;
  return Boolean(project?.domainProfile === "medical" &&
    isInvestigationConfirmationCurrent(project.investigation) &&
    ranking && !Array.isArray(ranking) && ranking.rankingMode === "evidence_profile" &&
    Array.isArray(ranking.rankings) &&
    ranking.confirmedRevision === confirmed?.revision &&
    ranking.confirmedFingerprint === confirmed?.fingerprint);
}

function normalizeMaterialList(input, fallback = []) {
  if (!Array.isArray(input)) return [...fallback];
  return [
    ...new Set(input.map(String).filter((item) => APPLICATION_MATERIAL_IDS.includes(item))),
  ];
}

function normalizeApplicationMaterialSelection(input, fallback = {}) {
  const source = input && typeof input === "object" ? input : {};
  const materials = normalizeMaterialList(source.materials, fallback.materials || []);
  const requestedOrder = normalizeMaterialList(source.order, fallback.order || []);
  const order = [
    ...requestedOrder.filter((item) => materials.includes(item)),
    ...materials.filter((item) => !requestedOrder.includes(item)),
  ];
  return {
    advisorProgramId: text(
      source.advisorProgramId ??
        source.advisor_program_id ??
        fallback.advisorProgramId ??
        "",
      500,
    ),
    materials,
    order,
    literaturePolicy: {
      advisorWorks: true,
      fieldWorks: true,
      downloadOpenAccess: true,
    },
  };
}

export function applicationMaterialsFingerprint(selection) {
  const normalized = normalizeApplicationMaterialSelection(selection);
  return createHash("sha256")
    .update(JSON.stringify(normalized))
    .digest("hex");
}

function normalizeApplicationMaterialsConfirmed(input, now) {
  if (!input || typeof input !== "object") return null;
  const selection = normalizeApplicationMaterialSelection(input);
  return {
    ...selection,
    revision: Math.max(0, Number(input.revision) || 0),
    confirmedAt: validTimestamp(input.confirmedAt, now),
    fingerprint:
      text(input.fingerprint, 128) || applicationMaterialsFingerprint(selection),
    source: input.source === "legacy_artifact" ? "legacy_artifact" : "user_confirmed",
  };
}

export function normalizeApplicationMaterials(
  input,
  now = new Date().toISOString(),
) {
  const source = input && typeof input === "object" ? input : {};
  const draftSource = source.draft ?? source;
  const selection = normalizeApplicationMaterialSelection(draftSource);
  return {
    draft: {
      ...selection,
      revision: Math.max(0, Number(draftSource.revision) || 0),
      updatedAt: validTimestamp(draftSource.updatedAt, now),
    },
    confirmed: normalizeApplicationMaterialsConfirmed(source.confirmed, now),
  };
}

export function updateApplicationMaterialsDraft(
  existing,
  patch,
  now = new Date().toISOString(),
) {
  const current = normalizeApplicationMaterials(existing, now);
  const source = patch?.draft ?? patch ?? {};
  const nextSelection = normalizeApplicationMaterialSelection(source, current.draft);
  const currentSelection = normalizeApplicationMaterialSelection(current.draft);
  const changed = !sameSelection(nextSelection, currentSelection);
  return {
    draft: {
      ...nextSelection,
      revision: changed ? current.draft.revision + 1 : current.draft.revision,
      updatedAt: changed ? now : current.draft.updatedAt,
    },
    confirmed: current.confirmed,
  };
}

export function isApplicationMaterialsConfirmationCurrent(applicationMaterials) {
  const current = normalizeApplicationMaterials(applicationMaterials);
  if (!current.confirmed) return false;
  return (
    current.confirmed.revision === current.draft.revision &&
    current.confirmed.fingerprint ===
      applicationMaterialsFingerprint(current.draft)
  );
}

export function validateApplicationMaterialsDraft(
  applicationMaterials,
  rankings,
) {
  const current = normalizeApplicationMaterials(applicationMaterials);
  const errors = [];
  if (!current.draft.advisorProgramId) {
    errors.push("请选择一个精确的导师—项目组合");
  } else if (!isSafeAdvisorProgramId(current.draft.advisorProgramId)) {
    errors.push("所选 advisorProgramId 含不安全的路径字符");
  }
  if (!current.draft.materials.length) {
    errors.push("请至少选择一种申请材料");
  }
  if (current.draft.order.length !== current.draft.materials.length) {
    errors.push("材料生成顺序与所选材料不一致");
  }
  const rankingIds = new Set(
    (Array.isArray(rankings) ? rankings : [])
      .map((item) => String(item?.advisorProgramId || "").trim())
      .filter(Boolean),
  );
  if (
    current.draft.advisorProgramId &&
    !rankingIds.has(current.draft.advisorProgramId)
  ) {
    errors.push("所选导师—项目组合不在当前最终排名中");
  }
  return { valid: errors.length === 0, errors, draft: current.draft };
}

export function confirmApplicationMaterialsDraft(
  applicationMaterials,
  { expectedRevision, now = new Date().toISOString() } = {},
) {
  const current = normalizeApplicationMaterials(applicationMaterials, now);
  if (!Number.isInteger(expectedRevision)) {
    const error = new Error("缺少有效的申请材料草稿版本，请重新检查最终摘要");
    error.code = "MISSING_DRAFT_REVISION";
    throw error;
  }
  if (expectedRevision !== current.draft.revision) {
    const error = new Error("申请材料草稿已发生变化，请重新检查最终摘要");
    error.code = "STALE_DRAFT";
    throw error;
  }
  const confirmed = {
    ...normalizeApplicationMaterialSelection(current.draft),
    revision: current.draft.revision,
    confirmedAt: now,
    fingerprint: "",
    source: "user_confirmed",
  };
  confirmed.fingerprint = applicationMaterialsFingerprint(confirmed);
  return { draft: current.draft, confirmed };
}

export function communityRefreshEligibility(investigation) {
  const current = normalizeInvestigation(investigation);
  if (current.draft.sourcePolicy === "public_only") {
    return { allowed: false, reason: "本次为公开资料调查，不使用社区缓存" };
  }
  if (!current.confirmed) {
    return { allowed: false, reason: "请先最终确认本次导师背调配置" };
  }
  if (!isInvestigationConfirmationCurrent(current)) {
    return { allowed: false, reason: "调查选择已发生变化，请重新确认后再刷新社区资料" };
  }
  if (!hasCommunitySections(current.confirmed.selectedSections)) {
    return { allowed: false, reason: "当前已确认的调查维度不需要社区资料" };
  }
  if (!current.confirmed.communitySources.consented) {
    return { allowed: false, reason: "请先明确同意在本地下载第三方社区资料" };
  }
  return { allowed: true, reason: null };
}

export function validateInvestigationDraftAgainstCandidates(
  investigation,
  candidates,
) {
  const current = normalizeInvestigation(investigation);
  const errors = [];
  if (!current.draft.selectedAdvisorProgramIds.length) {
    errors.push("请至少选择一个导师—项目组合");
  }
  if (!current.draft.selectedSections.length) {
    errors.push("请至少选择一个背调维度");
  }
  const candidateIds = new Set(
    (Array.isArray(candidates) ? candidates : [])
      .map((candidate) =>
        typeof candidate === "string"
          ? candidate
          : String(candidate?.advisorProgramId || ""),
      )
      .filter(Boolean),
  );
  const invalidIds = current.draft.selectedAdvisorProgramIds.filter(
    (id) => !candidateIds.has(id),
  );
  if (invalidIds.length) {
    errors.push(`以下导师—项目组合已不存在：${invalidIds.join("、")}`);
  }
  return { valid: errors.length === 0, errors, draft: current.draft };
}

export function confirmInvestigationDraft(
  investigation,
  { expectedRevision, now = new Date().toISOString(), source = "user_confirmed" } = {},
) {
  const current = normalizeInvestigation(investigation, now);
  if (source !== "legacy_artifact" && !Number.isInteger(expectedRevision)) {
    const error = new Error("缺少有效的调查草稿版本，请重新检查最终摘要");
    error.code = "MISSING_DRAFT_REVISION";
    throw error;
  }
  if (
    expectedRevision !== undefined &&
    Number(expectedRevision) !== current.draft.revision
  ) {
    const error = new Error("调查草稿已发生变化，请重新检查最终摘要");
    error.code = "STALE_DRAFT";
    throw error;
  }
  const consented =
    current.draft.sourcePolicy !== "public_only" &&
    hasCommunitySections(current.draft.selectedSections) &&
    current.draft.communitySources.requested;
  const confirmed = {
    sourcePolicy: current.draft.sourcePolicy,
    researchScopeFingerprint: current.draft.researchScopeFingerprint,
    selectedAdvisorProgramIds: [...current.draft.selectedAdvisorProgramIds],
    selectedSections: [...current.draft.selectedSections],
    communitySources: {
      consented,
      consentedAt: consented ? now : null,
    },
    revision: current.draft.revision,
    confirmedAt: now,
    fingerprint: "",
    source: source === "legacy_artifact" ? "legacy_artifact" : "user_confirmed",
  };
  confirmed.fingerprint = investigationFingerprint(confirmed);
  return { draft: current.draft, confirmed };
}

export function normalizeProjectMetadata(
  input,
  {
    fallbackId = "local-project",
    now = new Date().toISOString(),
    legacyDetectiveResults = null,
  } = {},
) {
  const source = input && typeof input === "object" && !Array.isArray(input) ? input : {};
  const id = text(source.id || source.slug || fallbackId, 120) || "local-project";
  const slug = text(source.slug || source.id || fallbackId, 120) || id;
  const createdAt = validTimestamp(source.createdAt, now);
  const domainProfile = source.domainProfile === "medical" ? "medical" : "general";
  const medical = domainProfile === "medical";
  const importRegionScope = !Object.hasOwn(source, "target") || Number(source.schemaVersion || 0) < PROJECT_SCHEMA_VERSION;
  const target = text(source.target, 500) || (medical && importRegionScope && source.medicalProfile?.inputStatus?.regions !== "unrestricted"
    ? stringList(source.medicalProfile?.regions).join("; ") : "");
  const normalized = {
    ...source,
    schemaVersion: PROJECT_SCHEMA_VERSION,
    id,
    slug,
    name: text(source.name || slug, 120) || "未命名申请项目",
    applicantName: text(source.applicantName ?? source.applicant_name, 160),
    domainProfile,
    searchMode: ["discovery", "application"].includes(source.searchMode)
      ? source.searchMode : medical ? "discovery" : "application",
    evaluationMode: medical ? "evidence_profile" : "weighted_score",
    medicalProfile: normalizeMedicalProfile({ ...source.medicalProfile, regions: target ? target.split(/[;；\n]+/) : [] }, target),
    applicantBackground: {
      ...(source.applicantBackground && typeof source.applicantBackground === "object"
        ? source.applicantBackground : {}),
      source: ["self_reported", "documented"].includes(source.applicantBackground?.source)
        ? source.applicantBackground.source : "not_provided",
      ...Object.fromEntries(["education", "researchExperience", "qualifications"].map((key) =>
        [key, Array.isArray(source.applicantBackground?.[key]) ? source.applicantBackground[key] : []])),
      notes: text(source.applicantBackground?.notes, 2000),
    },
    browserResearch: {
      ...(source.browserResearch && typeof source.browserResearch === "object" ? source.browserResearch : {}),
      enabled: source.browserResearch?.enabled === true,
      policy: "public_read_only",
      backend: text(source.browserResearch?.backend, 120) || "builtin_web",
      allowPublicDownloads: source.browserResearch?.allowPublicDownloads === true,
    },
    season: text(source.season, 80),
    degree: text(source.degree, 80),
    target,
    hardConstraints: text(source.hardConstraints ?? source.hard_constraints, 1000),
    interests: normalizeInterests(source.interests),
    shortlistTarget: normalizeShortlistTarget(
      source.shortlistTarget ?? source.shortlist_target,
    ),
    portfolioStrategy: normalizePortfolioStrategy(
      source.portfolioStrategy ?? source.portfolio_strategy,
    ),
    cv:
      source.cv && typeof source.cv === "object" && !Array.isArray(source.cv)
        ? {
            ...source.cv,
            name: text(source.cv.name, 240),
            path: text(source.cv.path, 2000),
            size: Math.max(0, Number(source.cv.size) || 0),
            type: text(source.cv.type || "application/octet-stream", 160),
            uploadedAt: validTimestamp(source.cv.uploadedAt, createdAt),
          }
        : null,
    investigation: normalizeInvestigation(source.investigation, now),
    applicationMaterials: normalizeApplicationMaterials(
      source.applicationMaterials,
      now,
    ),
    createdAt,
    updatedAt: validTimestamp(source.updatedAt, createdAt),
  };
  if (medical || normalized.investigation.draft.researchScopeFingerprint) {
    const draft = source.investigation?.draft ?? source.investigation ?? {};
    const policy = medical ? (draft.sourcePolicy === "community_allowed" ? "community_allowed" : "public_only")
      : "community_allowed";
    normalized.investigation = updateInvestigationDraft(normalized.investigation, {
      sourcePolicy: policy,
      researchScopeFingerprint: medicalScopeFingerprint(normalized),
      ...(!Array.isArray(draft.selectedSections) && !Array.isArray(draft.selected_sections)
        ? { selectedSections: defaultDetectiveSections(normalized) } : {}),
    }, now);
  }
  if (
    Number(source.schemaVersion || 0) < PROJECT_SCHEMA_VERSION &&
    Array.isArray(legacyDetectiveResults?.results) &&
    legacyDetectiveResults.results.length > 0
  ) {
    const legacyIds = legacyDetectiveResults.results
      .map((result) => text(result?.advisorProgramId, 500))
      .filter(Boolean);
    if (legacyIds.length > 0) {
      const legacySections = normalizeSectionList(
        legacyDetectiveResults.selectedSections,
        normalized.investigation.draft.selectedSections,
      );
      // Only the artifact records what a completed run was actually allowed to
      // use. A v3 project.json consent flag was written on checkbox click and
      // never proved confirmation, so it cannot authorize community sources.
      const legacyConsent = Boolean(
        legacyDetectiveResults.communitySources?.consented ??
          legacyDetectiveResults.community_sources?.consented,
      );
      normalized.investigation.draft = {
        ...normalized.investigation.draft,
        selectedAdvisorProgramIds: [...new Set(legacyIds)],
        selectedSections: legacySections,
        communitySources: { requested: legacyConsent },
      };
      normalized.investigation = confirmInvestigationDraft(
        normalized.investigation,
        { now, source: "legacy_artifact" },
      );
    }
  }
  delete normalized.shortlist_target;
  delete normalized.portfolio_strategy;
  delete normalized.hard_constraints;
  delete normalized.applicant_name;
  return normalized;
}

// Every stage has its own preconditions. Checking `phase1Ready` for all of
// them locked migrated projects — ones that already have candidates and
// detective results but a stale CV path — out of Phase 2 and Phase 3.
export const RUN_MODE_IDS = [
  "finder",
  "finder_objective",
  "detective",
  "ranking",
  "research_proposal",
  "outreach_email",
];

export function readinessForProject({
  metadata,
  candidates = [],
  detectiveResults = null,
  rankings = [],
  materialArtifacts = null,
  cvValid = false,
} = {}) {
  const source = metadata && typeof metadata === "object" ? metadata : {};
  const medical = source.domainProfile === "medical";
  const discovery = medical && source.searchMode !== "application";
  const hasInterests = Array.isArray(source.interests) && source.interests.length > 0;
  const hasCv = Boolean(cvValid);
  const structuredBackground = hasStructuredApplicantBackground(source);
  const checks = medical ? medicalIntakeStatus(source).steps : [
    { key: "target", label: "填写目标院校或地区范围", complete: Boolean(source.target) },
    {
      key: "cv",
      label: "上传可读取的真实 CV",
      complete: hasCv,
    },
  ];
  const objectiveChecks = [
    { key: "degree", label: "填写目标学位", complete: Boolean(source.degree) },
    { key: "season", label: "填写申请季", complete: Boolean(source.season) },
  ];
  if (medical) {
    objectiveChecks.push(
      { key: "application_mode", label: "切换到申请筛选模式", complete: !discovery },
      { key: "background", label: "提供相关真实背景（CV 或标注来源的结构化背景）", complete: hasCv || structuredBackground },
      { key: "constraints", label: "明确资金及其他硬约束，或明确无附加约束", complete: Boolean(source.hardConstraints?.trim()) },
    );
    if (!discovery) checks.push(...objectiveChecks.filter((item) => item.key !== "application_mode"));
  }
  const phase1Ready = checks.every((item) => item.complete);
  const objectiveReady = objectiveChecks.every((item) => item.complete);

  const candidateList = Array.isArray(candidates) ? candidates : [];
  const usableCandidates = candidateList.filter((candidate) =>
    String(candidate?.advisorProgramId || "").trim(),
  );
  const confirmationCurrent = isInvestigationConfirmationCurrent(source.investigation);
  const confirmed = normalizeInvestigation(source.investigation).confirmed;
  const detectiveDone =
    Array.isArray(detectiveResults?.results) && detectiveResults.results.length > 0;

  const finderMissing = checks
    .filter((item) => !item.complete)
    .map((item) => item.label);
  const objectiveMissing = objectiveChecks
    .filter((item) => !item.complete)
    .map((item) => item.label);

  const finderObjectiveMissing = [
    ...finderMissing,
    ...(usableCandidates.length ? [] : ["先完成 Phase 1 的导师发现"]),
    ...objectiveMissing,
  ];

  const detectiveMissing = [
    ...(usableCandidates.length ? [] : ["先产生带稳定 ID 的候选导师"]),
    ...(confirmed ? [] : ["最终确认本次背调配置"]),
    ...(confirmed && !confirmationCurrent
      ? ["调查选择已变化，请重新最终确认"]
      : []),
  ];

  const rankingMissing = detectiveDone ? [] : ["先完成一轮导师背调并生成结果"];
  if (medical) {
    if (!confirmed || !confirmationCurrent) {
      rankingMissing.push("请最终确认当前医学调查范围后再比较");
    } else if (detectiveDone && (
      detectiveResults.confirmedRevision !== confirmed.revision ||
      detectiveResults.confirmedFingerprint !== confirmed.fingerprint
    )) {
      rankingMissing.push("背调结果不属于当前确认范围，请先完成本轮调查");
    }
  }

  const ranked = Array.isArray(rankings) && rankings.length > 0;
  const materials = normalizeApplicationMaterials(source.applicationMaterials);
  const materialsConfirmationCurrent =
    isApplicationMaterialsConfirmationCurrent(materials);
  const materialBaseMissing = [
    ...(ranked ? [] : ["先完成最终排名"]),
    ...(medical ? rankingMissing : []),
    ...(hasCv ? [] : ["上传可读取的真实 CV"]),
    ...(isUsableApplicantName(source.applicantName)
      ? []
      : ["填写并确认申请者真实姓名"]),
    ...(materials.confirmed ? [] : ["最终确认申请材料配置"]),
    ...(materials.confirmed && !materialsConfirmationCurrent
      ? ["申请材料选择已变化，请重新最终确认"]
      : []),
  ];
  function materialModeMissing(materialId) {
    const missing = [...materialBaseMissing];
    if (
      materials.confirmed &&
      !materials.confirmed.materials.includes(materialId)
    ) {
      missing.push("当前确认快照没有选择此材料");
    }
    if (materials.confirmed && materialsConfirmationCurrent) {
      const position = materials.confirmed.order.indexOf(materialId);
      const earlier = position > 0 ? materials.confirmed.order.slice(0, position) : [];
      for (const earlierMaterial of earlier) {
        if (!materialArtifacts?.[earlierMaterial]?.complete) {
          missing.push(`请先完成 ${earlierMaterial}`);
        }
      }
    }
    return [...new Set(missing)];
  }
  const proposalMissing = materialModeMissing("research_proposal");
  const outreachMissing = materialModeMissing("outreach_email");

  const modes = {
    finder: { ready: !finderMissing.length, missing: finderMissing },
    finder_objective: {
      ready: !finderObjectiveMissing.length,
      missing: finderObjectiveMissing,
    },
    detective: { ready: !detectiveMissing.length, missing: detectiveMissing },
    ranking: { ready: !rankingMissing.length, missing: rankingMissing },
    research_proposal: {
      ready: !proposalMissing.length,
      missing: proposalMissing,
    },
    outreach_email: {
      ready: !outreachMissing.length,
      missing: outreachMissing,
    },
  };

  return {
    ready: phase1Ready,
    phase1Ready,
    objectiveReady,
    completed: checks.filter((item) => item.complete).length,
    total: checks.length,
    checks,
    missing: finderMissing,
    objectiveChecks,
    objectiveMissing,
    matchingSignal: hasCv ? "cv" : medical && structuredBackground ? "structured_background" : medical ? "research_profile" : "none",
    ...(medical ? { medicalIntake: medicalIntakeStatus(source), completionScope: discovery ? "research_discovery" : "application_screening" } : {}),
    interestWeightTotal: hasInterests ? 100 : 0,
    cvValid: hasCv,
    modes,
  };
}

export function createStatus(now = new Date().toISOString()) {
  return {
    schemaVersion: STATUS_SCHEMA_VERSION,
    phase: "intake",
    stage: "intake",
    candidateCount: 0,
    shortlistCount: 0,
    objectiveReadyCount: 0,
    selectedCount: 0,
    evidenceCount: 0,
    evidenceCoverage: 0,
    rankingCount: 0,
    updatedAt: now,
  };
}

export function normalizeStatus(input, now = new Date().toISOString()) {
  const source = input && typeof input === "object" && !Array.isArray(input) ? input : {};
  const defaults = createStatus(now);
  return {
    ...defaults,
    ...source,
    schemaVersion: STATUS_SCHEMA_VERSION,
    phase: text(source.phase || defaults.phase, 80),
    stage: text(source.stage || defaults.stage, 80),
    candidateCount: Math.max(0, Number(source.candidateCount) || 0),
    shortlistCount: Math.max(0, Number(source.shortlistCount ?? source.highMatchCount) || 0),
    objectiveReadyCount: Math.max(0, Number(source.objectiveReadyCount) || 0),
    selectedCount: Math.max(0, Number(source.selectedCount) || 0),
    evidenceCount: Math.max(0, Number(source.evidenceCount) || 0),
    evidenceCoverage: Math.max(0, Number(source.evidenceCoverage) || 0),
    rankingCount: Math.max(0, Number(source.rankingCount) || 0),
    updatedAt: validTimestamp(source.updatedAt, now),
  };
}

export function validateProjectMetadata(input) {
  const errors = [];
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return { valid: false, errors: ["project.json 顶层必须是对象"] };
  }
  if (input.schemaVersion !== PROJECT_SCHEMA_VERSION) {
    errors.push(`schemaVersion 必须为 ${PROJECT_SCHEMA_VERSION}`);
  }
  if (!["general", "medical"].includes(input.domainProfile)) {
    errors.push("domainProfile 必须为 general 或 medical");
  }
  if (!["discovery", "application"].includes(input.searchMode)) {
    errors.push("searchMode 必须为 discovery 或 application");
  }
  if (input.evaluationMode !== (input.domainProfile === "medical" ? "evidence_profile" : "weighted_score")) {
    errors.push("evaluationMode 必须与领域配置一致");
  }
  if (!input.medicalProfile || typeof input.medicalProfile !== "object" ||
      !Array.isArray(input.medicalProfile.fields) || !Array.isArray(input.medicalProfile.regions)) {
    errors.push("medicalProfile 必须包含 fields 和 regions 数组");
  }
  if (!input.browserResearch || typeof input.browserResearch.enabled !== "boolean" ||
      input.browserResearch.policy !== "public_read_only") {
    errors.push("browserResearch 必须包含显式 enabled 与 public_read_only policy");
  }
  for (const key of ["id", "slug", "name", "createdAt", "updatedAt"]) {
    if (typeof input[key] !== "string" || !input[key].trim()) {
      errors.push(`${key} 必须是非空字符串`);
    }
  }
  if (typeof input.applicantName !== "string") {
    errors.push("applicantName 必须是字符串");
  }
  if (typeof input.hardConstraints !== "string") {
    errors.push("hardConstraints 必须是字符串");
  }
  if (!["balanced", "conservative", "ambitious"].includes(input.portfolioStrategy)) {
    errors.push("portfolioStrategy 必须是 balanced、conservative 或 ambitious");
  }
  if (!Number.isInteger(input.shortlistTarget) || input.shortlistTarget < 5 || input.shortlistTarget > 50) {
    errors.push("shortlistTarget 必须是 5 到 50 的整数");
  }
  if (!Array.isArray(input.interests)) {
    errors.push("interests 必须是数组");
  } else if (
    input.interests.some(
      (item) =>
        !item ||
        typeof item !== "object" ||
        typeof item.name !== "string" ||
        !Number.isFinite(item.weight),
    )
  ) {
    errors.push("每个 interest 必须包含 name 和数值 weight");
  }
  if (!Array.isArray(input.investigation?.draft?.selectedAdvisorProgramIds)) {
    errors.push("investigation.draft.selectedAdvisorProgramIds 必须是数组");
  }
  if (!Array.isArray(input.investigation?.draft?.selectedSections)) {
    errors.push("investigation.draft.selectedSections 必须是数组");
  }
  if (
    input.investigation?.confirmed !== null &&
    input.investigation?.confirmed !== undefined &&
    (!Array.isArray(input.investigation.confirmed.selectedAdvisorProgramIds) ||
      !Array.isArray(input.investigation.confirmed.selectedSections) ||
      !input.investigation.confirmed.fingerprint)
  ) {
    errors.push("investigation.confirmed 必须是完整确认快照或 null");
  }
  if (typeof input.applicationMaterials?.draft?.advisorProgramId !== "string") {
    errors.push("applicationMaterials.draft.advisorProgramId 必须是字符串");
  }
  if (!Array.isArray(input.applicationMaterials?.draft?.materials)) {
    errors.push("applicationMaterials.draft.materials 必须是数组");
  }
  if (!Array.isArray(input.applicationMaterials?.draft?.order)) {
    errors.push("applicationMaterials.draft.order 必须是数组");
  }
  if (
    input.applicationMaterials?.confirmed !== null &&
    input.applicationMaterials?.confirmed !== undefined &&
    (!input.applicationMaterials.confirmed.advisorProgramId ||
      !Array.isArray(input.applicationMaterials.confirmed.materials) ||
      !Array.isArray(input.applicationMaterials.confirmed.order) ||
      !input.applicationMaterials.confirmed.fingerprint)
  ) {
    errors.push("applicationMaterials.confirmed 必须是完整确认快照或 null");
  }
  return { valid: errors.length === 0, errors };
}
