// Form projection only. project.json remains the authoritative profile.
export const listInput = (value) => String(value || "").split(/[\n,，;；]+/).map((item) => item.trim()).filter(Boolean);
export const safeCsvText = (value) => {
  const text = String(value ?? "");
  return /^[\s\uFEFF]*[=+@-]/.test(text) ? `'${text}` : text;
};

export const backgroundEntriesText = (entries) => (Array.isArray(entries) ? entries : [])
  .map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("；");

export function medicalTargetText(project = {}) {
  if (project.target?.trim()) return project.target;
  const status = project.medicalProfile?.inputStatus?.regions;
  return status === "unrestricted" ? "不限" : status === "undecided" ? "未定" : "";
}

export function browserResearchFromForm(form, previous = {}) {
  return { ...previous, enabled: form.browserEnabled === true,
    policy: "public_read_only", backend: previous.backend || "builtin_web",
    allowPublicDownloads: form.browserDownloads === true };
}

export function applicantBackgroundFromForm(form, previous = {}) {
  const background = { ...previous };
  let changed = false;
  for (const key of ["education", "researchExperience", "qualifications"]) {
    const value = String(form[key] || "");
    const same = value === backgroundEntriesText(previous[key]);
    background[key] = same ? previous[key] || [] : listInput(value);
    changed ||= !same;
  }
  background.source = changed ? "self_reported" : previous.source || "not_provided";
  return background;
}

export function medicalDraftReadiness(form, application, previousBackground = {}, cvValid = false) {
  const background = applicantBackgroundFromForm(form, previousBackground);
  const hasBackground = ["self_reported", "documented"].includes(background.source) &&
    ["education", "researchExperience", "qualifications"].some((key) => background[key].some((item) =>
      typeof item === "string" ? item.trim() : item && typeof item === "object" && Object.keys(item).length));
  // Three required steps: field -> disease/mechanism/question -> region.
  // Research object, scale, paradigm and method preference are optional.
  const checks = [
    [Boolean(form.fields?.trim()), "明确生物医学领域或大方向，或填写不限"],
    [Boolean(form.diseaseScope?.trim() || form.researchQuestions?.trim()), "明确希望研究的疾病、机制或科学问题，或填写未定"],
    [Boolean(application.target?.trim()), "明确目标国家/地区，或填写不限"],
  ];
  const objectiveChecks = [
    [Boolean(application.degree?.trim()), "填写目标学位"],
    [Boolean(application.season?.trim()), "填写申请季"],
    [cvValid || hasBackground, "提供相关真实背景（CV 或标注来源的结构化背景）"],
    [Boolean(application.hardConstraints?.trim()), "明确资金及其他硬约束，或明确无附加约束"],
  ];
  const applicationMode = form.searchMode === "application";
  const required = applicationMode ? [...checks, ...objectiveChecks] : checks;
  return {
    completed: required.filter(([complete]) => complete).length,
    total: required.length,
    missing: required.filter(([complete]) => !complete).map(([, label]) => label),
    objectiveMissing: [...(applicationMode ? [] : ["切换到申请筛选模式"]),
      ...objectiveChecks.filter(([complete]) => !complete).map(([, label]) => label)],
  };
}

export function prefillRequestedInputs(fields, project, current = {}) {
  const profile = project.medicalProfile || {};
  const background = project.applicantBackground || {};
  const profileAnswer = (key) => (profile[key] || []).join("；") ||
    (profile.inputStatus?.[key] === "undecided" ? "未定" : profile.inputStatus?.[key] === "unrestricted" ? "不限" : "");
  const stored = {
    degree: project.degree, degreeLevel: project.degree, season: project.season,
    target: medicalTargetText(project), hardConstraints: project.hardConstraints, shortlistTarget: project.shortlistTarget,
    cv: project.cv?.valid ? project.cv.absolutePath || project.cv.path : "",
    medicalFields: profileAnswer("fields"),
    diseaseScope: profile.diseaseScope === "unasked" ? "" : profile.diseaseScope,
    researchModes: profileAnswer("researchModes"),
    interests: (project.interests || []).map((item) => typeof item === "string" ? item : item.name).join("；"),
    applicantBackground: ["education", "researchExperience", "qualifications"].map((key) => backgroundEntriesText(background[key])).filter(Boolean).join("；"),
  };
  return Object.fromEntries(fields.map(({ id }) => [id, current[id] ?? String(stored[id] ?? "")]));
}

export const MEDICAL_FORM_LIST_KEYS = ["fields", "diseasesOrMechanisms", "researchQuestions", "researchObjects", "researchScales", "researchModes", "methodPreferences", "adjacentInterests", "exclusions"];

export function medicalProfileFromForm(form, previous = {}) {
  const profile = { ...previous, inputStatus: { ...previous.inputStatus } };
  // Applicant skills and desired training are no longer part of discovery.
  delete profile.currentSkills;
  delete profile.desiredTraining;
  for (const key of MEDICAL_FORM_LIST_KEYS) {
    profile[key] = listInput(form[key]);
    if (["fields", "researchModes", "exclusions"].includes(key)) {
      profile.inputStatus[key] = ["未定", "undecided"].includes(String(form[key]).trim()) ? "undecided"
        : ["不限", "无", "unrestricted"].includes(String(form[key]).trim()) ? "unrestricted"
          : profile[key].length ? "answered" : "unasked";
    }
  }
  profile.diseaseScope = String(form.diseaseScope || "").trim() || "unasked";
  profile.inputStatus.diseaseScope = ["未定", "undecided"].includes(profile.diseaseScope) ? "undecided"
    : profile.diseaseScope === "unasked" ? "unasked" : "answered";
  // An edited target must not inherit an old explicit 'unrestricted' status.
  profile.regions = listInput(form.target);
  profile.inputStatus.regions = ["未定", "undecided"].includes(String(form.target).trim()) ? "undecided"
    : ["不限", "unrestricted"].includes(String(form.target).trim()) ? "unrestricted"
    : profile.regions.length ? "answered" : "unasked";
  return profile;
}

export function medicalInputPatch(field, value, project) {
  if (field === "applicantBackground") return { applicantBackground: {
    ...project.applicantBackground, source: "self_reported", researchExperience: [value],
  } };
  const key = field === "medicalFields" ? "fields" : field;
  const profile = { ...project.medicalProfile, inputStatus: { ...project.medicalProfile?.inputStatus } };
  profile[key] = key === "diseaseScope" ? value : listInput(value);
  profile.inputStatus[key] = ["未定", "undecided"].includes(value) ? "undecided"
    : ["不限", "unrestricted"].includes(value) ? "unrestricted" : "answered";
  return { medicalProfile: profile };
}
