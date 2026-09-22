#!/usr/bin/env node

import { readFile, rename, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import {
  normalizeApplicationPathway,
  normalizeHardConstraintStatus,
  normalizeOpportunityStatus,
  normalizePortfolioStrategy,
  normalizeShortlistTarget,
  recommendedActionForCandidate,
  isSafeAdvisorProgramId,
} from "../../advisor-pipeline/scripts/project-contract.mjs";
import { isExecutedDirectly } from "../../advisor-pipeline/scripts/direct-execution.mjs";
import {
  buildMedicalDiscoveryView,
  hasReadableProjectCv,
  compareMedicalCandidates,
  isMedicalEvidenceProfile,
  normalizeMedicalCandidate,
  validateMedicalCandidateMappings,
} from "../../advisor-pipeline/scripts/medical-evidence.mjs";

export const MATCHING_CONTRACT_VERSION = 3;

const REACH_CAPS = {
  conservative: 0.2,
  balanced: 0.3,
  ambitious: 0.5,
};

function optionalScore(value) {
  if (value === null || value === undefined || value === "") return null;
  const score = Number(value);
  return Number.isFinite(score) ? Math.max(0, Math.min(10, score)) : null;
}

function stringList(value) {
  return Array.isArray(value) ? value.map(String).map((item) => item.trim()).filter(Boolean) : [];
}

export function deterministicOverallMatch(fit, profileMatch) {
  const research = optionalScore(fit);
  const profile = optionalScore(profileMatch);
  if (research === null || profile === null) return null;
  return Math.round((research * 0.6 + profile * 0.4) * 10) / 10;
}

export function normalizeMatchingCandidate(candidate, index = 0) {
  const fit = optionalScore(candidate?.fit);
  const profileMatch = optionalScore(candidate?.profileMatch);
  const normalized = {
    ...candidate,
    rank: index + 1,
    fit,
    profileMatch,
    overallMatch: deterministicOverallMatch(fit, profileMatch),
    competitiveness: ["reach", "match", "safer", "unknown"].includes(
      String(candidate?.competitiveness),
    )
      ? String(candidate.competitiveness)
      : "unknown",
    hardConstraintStatus: normalizeHardConstraintStatus(candidate?.hardConstraintStatus),
    hardConstraintReasons: stringList(candidate?.hardConstraintReasons),
    applicationPathway: normalizeApplicationPathway(candidate?.applicationPathway),
    opportunityStatus: normalizeOpportunityStatus(candidate?.opportunityStatus),
    matchReasons: stringList(candidate?.matchReasons),
    feasibility: ["eligible", "ineligible", "needs_confirmation"].includes(
      String(candidate?.feasibility),
    )
      ? String(candidate.feasibility)
      : "needs_confirmation",
    matchingContractVersion: MATCHING_CONTRACT_VERSION,
  };
  normalized.recommendedAction = recommendedActionForCandidate(normalized);
  return normalized;
}

function sortScore(candidate) {
  if (candidate.overallMatch !== null) return candidate.overallMatch;
  const components = [candidate.fit, candidate.profileMatch].filter((value) => value !== null);
  return components.length
    ? components.reduce((sum, value) => sum + value, 0) / components.length
    : -1;
}

function exclusionReason(candidate, selectedIds) {
  if (candidate.recommendedAction === "exclude") {
    if (candidate.hardConstraintStatus === "fail") return "hard_constraint";
    if (candidate.opportunityStatus === "verified_closed") return "verified_closed";
    return "ineligible";
  }
  return selectedIds.has(candidate.advisorProgramId) ? "" : "shortlist_or_portfolio_limit";
}

export function buildPortfolioShortlist(rawCandidates, options = {}) {
  if (isMedicalEvidenceProfile(options)) return buildEvidenceProfileShortlist(rawCandidates, options);
  const strategy = normalizePortfolioStrategy(options.portfolioStrategy);
  const shortlistTarget = normalizeShortlistTarget(options.shortlistTarget);
  const hasHardConstraints = Boolean(String(options.hardConstraints || "").trim());
  const normalized = (Array.isArray(rawCandidates) ? rawCandidates : []).map(
    (candidate, index) => {
      const row = normalizeMatchingCandidate(candidate, index);
      if (!hasHardConstraints && row.hardConstraintStatus === "unknown") {
        row.hardConstraintStatus = "pass";
        row.recommendedAction = recommendedActionForCandidate(row);
      }
      return row;
    },
  );
  const ids = normalized.map((candidate) => String(candidate.advisorProgramId || "").trim());
  if (ids.some((id) => !id)) throw new Error("候选缺少稳定的 advisorProgramId");
  if (new Set(ids).size !== ids.length) throw new Error("候选的 advisorProgramId 有重复");
  const comparable = normalized
    .filter((candidate) => candidate.recommendedAction !== "exclude")
    .sort((left, right) => sortScore(right) - sortScore(left) || left.rank - right.rank);
  const reachCap = Math.floor(shortlistTarget * REACH_CAPS[strategy]);
  const selected = [];
  const deferredReach = [];
  let reachCount = 0;

  for (const candidate of comparable) {
    if (selected.length >= shortlistTarget) break;
    if (candidate.competitiveness === "reach" && reachCount >= reachCap) {
      deferredReach.push(candidate);
      continue;
    }
    selected.push(candidate);
    if (candidate.competitiveness === "reach") reachCount += 1;
  }
  for (const candidate of deferredReach) {
    if (selected.length >= shortlistTarget) break;
    selected.push(candidate);
    reachCount += 1;
  }

  const selectedIds = new Set(selected.map((candidate) => candidate.advisorProgramId));
  const ranked = selected.map((candidate, index) => ({
    ...candidate,
    rank: index + 1,
    portfolioSelected: true,
  }));
  const excluded = normalized
    .filter((candidate) => !selectedIds.has(candidate.advisorProgramId))
    .map((candidate) => ({
      ...candidate,
      portfolioSelected: false,
      exclusionReason: exclusionReason(candidate, selectedIds),
    }));
  const knownTierCount = ranked.filter((candidate) => candidate.competitiveness !== "unknown").length;
  const audit = {
    matchingContractVersion: MATCHING_CONTRACT_VERSION,
    strategy,
    shortlistTarget,
    inputCount: normalized.length,
    selectedCount: ranked.length,
    excludedCount: excluded.length,
    reachCap,
    reachCount,
    unknownTierCount: ranked.length - knownTierCount,
    unknownPathwayCount: ranked.filter((candidate) => candidate.applicationPathway === "unknown").length,
    unknownOpportunityCount: ranked.filter((candidate) => candidate.opportunityStatus === "unknown").length,
    portfolioDeviation:
      reachCount > reachCap
        ? "insufficient_non_reach_candidates"
        : ranked.length < shortlistTarget
          ? "insufficient_eligible_candidates"
          : null,
  };
  return { selected: ranked, excluded, audit };
}

export function buildEvidenceProfileShortlist(rawCandidates, options = {}) {
  if (options.advisorRecords || options.programRecords) {
    const errors = validateMedicalCandidateMappings(rawCandidates, options);
    if (errors.length) throw new Error(errors.join("; "));
  }
  const shortlistTarget = normalizeShortlistTarget(options.shortlistTarget);
  const normalized = (Array.isArray(rawCandidates) ? rawCandidates : []).map((row, index) => ({
    ...normalizeMedicalCandidate(row, options, index),
    matchingContractVersion: MATCHING_CONTRACT_VERSION,
  }));
  const ids = normalized.map((row) => String(row.advisorProgramId || "").trim());
  if (ids.some((id) => !id)) throw new Error("候选缺少稳定的 advisorProgramId；未映射项目的导师请使用 advisor_records.json 探索视图");
  if (ids.some((id) => !isSafeAdvisorProgramId(id))) throw new Error("候选 advisorProgramId 含不安全路径字符");
  if (new Set(ids).size !== ids.length) throw new Error("候选的 advisorProgramId 有重复");
  const selected = normalized.filter((row) => row.recommendedAction !== "exclude")
    .sort(compareMedicalCandidates).slice(0, shortlistTarget)
    .map((row, index) => ({ ...row, rank: index + 1, portfolioSelected: true }));
  const selectedIds = new Set(selected.map((row) => row.advisorProgramId));
  const excluded = normalized.filter((row) => !selectedIds.has(row.advisorProgramId)).map((row) => ({
    ...row,
    portfolioSelected: false,
    exclusionReason: row.recommendedAction === "exclude" ? exclusionReason(row, selectedIds) : "research_budget_deferred",
  }));
  return {
    selected,
    excluded,
    audit: {
      matchingContractVersion: MATCHING_CONTRACT_VERSION,
      rankingMode: "evidence_profile",
      rankSemantics: "display_order",
      strategy: "research_and_training_evidence",
      shortlistTarget,
      inputCount: normalized.length,
      selectedCount: selected.length,
      excludedCount: excluded.filter((row) => row.recommendedAction === "exclude").length,
      deferredCount: excluded.filter((row) => row.recommendedAction !== "exclude").length,
      reachCap: null,
      reachCount: null,
      competitivenessAssessed: false,
      selectionBasis: "scientificFit, trainingFit; ties use stable names; evidence coverage is not a quality score",
    },
  };
}

export function mergePriorSelectionForRerun(candidates, excluded) {
  const current = Array.isArray(candidates) ? candidates : [];
  const priorExcluded = Array.isArray(excluded) ? excluded : [];
  const isPriorSelection =
    current.length > 0 &&
    current.every(
      (candidate) =>
        [2, MATCHING_CONTRACT_VERSION].includes(candidate?.matchingContractVersion) &&
        candidate?.portfolioSelected === true,
    );
  if (!isPriorSelection) return current;
  const currentIds = new Set(current.map((candidate) => candidate?.advisorProgramId));
  return [
    ...current,
    ...priorExcluded.filter(
      (candidate) =>
        [2, MATCHING_CONTRACT_VERSION].includes(candidate?.matchingContractVersion) &&
        !currentIds.has(candidate?.advisorProgramId),
    ),
  ];
}

async function writeJsonAtomic(path, value) {
  const temporary = `${path}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`);
  await rename(temporary, path);
}

async function main() {
  const rootIndex = process.argv.indexOf("--project-root");
  const rawProjectRoot = rootIndex >= 0 ? process.argv[rootIndex + 1] || "" : "";
  if (!rawProjectRoot) {
    throw new Error("Usage: apply_matching_strategy.mjs --project-root <project-directory>");
  }
  const projectRoot = resolve(rawProjectRoot);
  const project = JSON.parse(await readFile(resolve(projectRoot, "project.json"), "utf8"));
  const medical = isMedicalEvidenceProfile(project);
  const [candidates, previousExcluded, advisorRecords, programRecords, evidenceRecords] = await Promise.all([
    readFile(resolve(projectRoot, "outputs", "candidates.json"), "utf8").then(JSON.parse)
      .catch((error) => { if (medical && project.searchMode === "discovery" && error.code === "ENOENT") return []; throw error; }),
    readFile(resolve(projectRoot, "outputs", "candidates-excluded.json"), "utf8")
      .then(JSON.parse)
      .catch(() => []),
    medical
      ? readFile(resolve(projectRoot, "outputs", "advisor_records.json"), "utf8").then(JSON.parse)
        .catch((error) => { if (error.code === "ENOENT") return []; throw error; })
      : [],
    medical
      ? readFile(resolve(projectRoot, "outputs", "program_records.json"), "utf8").then(JSON.parse)
        .catch((error) => { if (error.code === "ENOENT") return []; throw error; })
      : [],
    medical
      ? readFile(resolve(projectRoot, "outputs", "evidence.json"), "utf8").then(JSON.parse)
        .catch((error) => { if (error.code === "ENOENT") return []; throw error; })
      : [],
  ]);
  if (!Array.isArray(candidates)) throw new Error("outputs/candidates.json 顶层必须是数组");
  if (medical && [advisorRecords, programRecords, evidenceRecords].some((records) => !Array.isArray(records))) {
    throw new Error("医学 advisor_records/program_records/evidence.json 顶层必须是数组");
  }
  const result = buildPortfolioShortlist(
    mergePriorSelectionForRerun(candidates, previousExcluded),
    medical ? { ...project, advisorRecords, programRecords, evidenceRecords,
      cvValid: await hasReadableProjectCv(projectRoot, project.cv) } : project,
  );
  const generatedAt = new Date().toISOString();
  if (medical && project.searchMode === "discovery") {
    if (!Array.isArray(advisorRecords)) throw new Error("outputs/advisor_records.json 顶层必须是数组");
    const discoveryView = buildMedicalDiscoveryView(advisorRecords, project);
    await writeJsonAtomic(resolve(projectRoot, "outputs", "discovery-view.json"), discoveryView);
    result.audit.discoveryCount = discoveryView.length;
  }
  await Promise.all([
    writeJsonAtomic(resolve(projectRoot, "outputs", "candidates.json"), result.selected),
    writeJsonAtomic(resolve(projectRoot, "outputs", "candidates-excluded.json"), result.excluded),
    writeJsonAtomic(resolve(projectRoot, "outputs", "matching-audit.json"), {
      ...result.audit,
      generatedAt,
    }),
  ]);
  console.log(JSON.stringify({ ...result.audit, generatedAt }));
}

if (isExecutedDirectly(import.meta.url)) {
  await main();
}
