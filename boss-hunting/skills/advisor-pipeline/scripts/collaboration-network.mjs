// Scientific collaboration network helpers (depth = 1 ego network).
//
// Two edge families are kept apart:
//   collaboration edge  <- co-authorship, shared grant/project/trial, shared consortium leadership
//   research-neighbor   <- citation, co-citation, bibliographic coupling, semantic similarity, related papers
// A research neighbour is scientific proximity only. Network discovers; evidence validates.
import { COLLABORATION_EDGE_TYPES, RESEARCH_NEIGHBOR_EDGE_TYPES } from "./medical-evidence.mjs";

export const DEFAULT_NETWORK_THRESHOLDS = Object.freeze({
  // Configurable engineering defaults, not scientific standards.
  windowYears: 5,
  allowSingleDocumentedCollaboration: true,
  minDirectionRelatedJointStudies: 2,      // heuristic A
  minJointStudiesWithSharedProject: 1,     // heuristic B
  minDistinctYearsForContinuity: 2,        // heuristic C
  consortiumAuthorThreshold: 50,           // records above this are consortium papers
});

const PROJECT_LIKE = new Set(["shared_project", "shared_grant", "shared_trial"]);

function list(value) { return Array.isArray(value) ? value : []; }

function recordYear(record) {
  const year = Number(record.year ?? String(record.date || "").slice(0, 4));
  return Number.isFinite(year) ? year : null;
}

function inWindow(record, referenceYear, windowYears) {
  const year = recordYear(record);
  return year === null || !referenceYear ? true : referenceYear - year < windowYears;
}

function isConsortium(record, threshold) {
  return Number(record.authorCount ?? record.author_count) > threshold;
}

function meaningfulConsortiumLink(record, collaboratorId, repeatedWith) {
  // A single 500-author paper does not make 499 collaborators. Keep the link
  // only with independent evidence of a real scientific connection.
  const leadership = list(record.consortiumLeadership ?? record.consortium_leadership).map(String);
  const contributors = list(record.contributionStatementAuthors ?? record.contribution_statement_authors).map(String);
  return repeatedWith.has(collaboratorId) || leadership.includes(String(collaboratorId)) || contributors.includes(String(collaboratorId));
}

export function buildEgoNetwork(targetId, records, options = {}) {
  const thresholds = { ...DEFAULT_NETWORK_THRESHOLDS, ...(options.thresholds || {}) };
  const referenceYear = Number(options.referenceYear) || new Date().getFullYear();
  const target = String(targetId);
  const perCollaborator = new Map();
  const neighbors = new Map();
  const excluded = [];

  const collaborationRecords = list(records).filter((record) => COLLABORATION_EDGE_TYPES.includes(record.type)
    && list(record.participants ?? record.collaborators).map(String).includes(target));
  const repeatedWith = new Map();
  for (const record of collaborationRecords) {
    for (const participant of list(record.participants ?? record.collaborators).map(String)) {
      if (participant === target) continue;
      repeatedWith.set(participant, (repeatedWith.get(participant) || 0) + 1);
    }
  }
  const repeated = new Set([...repeatedWith.entries()].filter(([, count]) => count >= 2).map(([id]) => id));

  for (const record of list(records)) {
    const participants = list(record.participants ?? record.collaborators).map(String);
    if (RESEARCH_NEIGHBOR_EDGE_TYPES.includes(record.type)) {
      for (const other of participants.filter((id) => id !== target)) {
        const entry = neighbors.get(other) || { collaboratorId: other, name: record.names?.[other] || other, types: new Set(), sourceIds: new Set(), count: 0 };
        entry.types.add(record.type);
        entry.count += 1;
        for (const id of list(record.sourceIds ?? record.source_ids)) entry.sourceIds.add(String(id));
        neighbors.set(other, entry);
      }
      continue;
    }
    if (!COLLABORATION_EDGE_TYPES.includes(record.type) || !participants.includes(target)) continue;
    if (!inWindow(record, referenceYear, thresholds.windowYears)) {
      excluded.push({ record: record.id ?? null, reason: "outside_window" });
      continue;
    }
    const consortium = isConsortium(record, thresholds.consortiumAuthorThreshold);
    for (const other of participants.filter((id) => id !== target)) {
      if (consortium && !meaningfulConsortiumLink(record, other, repeated)) {
        excluded.push({ record: record.id ?? null, collaboratorId: other, reason: "consortium_without_independent_link" });
        continue;
      }
      const entry = perCollaborator.get(other) || {
        collaboratorId: other, name: record.names?.[other] || other, records: [], years: new Set(), topics: new Set(),
        edgeCounts: Object.fromEntries(COLLABORATION_EDGE_TYPES.map((type) => [type, 0])), sourceIds: new Set(),
      };
      entry.records.push(record);
      const year = recordYear(record);
      if (year !== null) entry.years.add(year);
      for (const topic of list(record.topics)) entry.topics.add(String(topic));
      entry.edgeCounts[record.type] += 1;
      for (const id of list(record.sourceIds ?? record.source_ids)) entry.sourceIds.add(String(id));
      perCollaborator.set(other, entry);
    }
  }

  const coreCollaborators = [];
  const leads = [];
  for (const entry of perCollaborator.values()) {
    const directionRelated = entry.records.filter((record) => record.directionRelevant !== false && record.direction_relevant !== false);
    const directionStudies = directionRelated.filter((record) => record.type === "coauthorship").length;
    const sharedProject = directionRelated.some((record) => PROJECT_LIKE.has(record.type));
    const topicConsistent = entry.topics.size > 0 && entry.records.every((record) => list(record.topics).length === 0 || list(record.topics).some((topic) => entry.topics.has(String(topic))));
    const heuristics = {
      A_repeated_direction_related_studies: directionStudies >= thresholds.minDirectionRelatedJointStudies,
      B_joint_study_plus_shared_project: directionStudies >= thresholds.minJointStudiesWithSharedProject && sharedProject,
      D_single_documented_collaboration: thresholds.allowSingleDocumentedCollaboration && directionRelated.some((record) =>
        (record.directionRelevant === true || record.direction_relevant === true)
        && list(record.sourceIds ?? record.source_ids).length > 0
        && !["not_checked", "inaccessible", "conflict", "not_found"].includes(record.status)),
      C_multi_year_topic_continuity: entry.years.size >= thresholds.minDistinctYearsForContinuity && topicConsistent && directionRelated.length > 0,
    };
    const years = [...entry.years].sort((left, right) => left - right);
    const summary = {
      collaboratorId: entry.collaboratorId,
      name: entry.name,
      jointRecordCount: directionRelated.length,
      firstYear: years[0] ?? null,
      lastYear: years[years.length - 1] ?? null,
      sharedTopics: [...entry.topics],
      collaborationEvidence: entry.records.map((record) => ({ type: record.type, id: record.id ?? null, title: record.title ?? record.project_title ?? null, url: record.url ?? record.final_url ?? null, year: recordYear(record), sourceIds: list(record.sourceIds ?? record.source_ids) })),
      heuristics,
      sourceIds: [...entry.sourceIds],
    };
    if (Object.values(heuristics).some(Boolean)) coreCollaborators.push(summary);
    else leads.push({ ...summary, reason: "insufficient_documented_collaboration" });
  }

  const edges = coreCollaborators.flatMap((collaborator) => {
    const entry = perCollaborator.get(collaborator.collaboratorId);
    return COLLABORATION_EDGE_TYPES.filter((type) => entry.edgeCounts[type] > 0).map((type) => ({
      source: target, target: collaborator.collaboratorId, type,
      // Edge weight is only the count of direction-related joint records.
      count: entry.records.filter((record) => record.type === type && record.directionRelevant !== false && record.direction_relevant !== false).length,
      years: [...entry.years].sort((left, right) => left - right),
      sourceIds: [...entry.sourceIds],
    })).filter((edge) => edge.count > 0);
  });

  // Neighbours stay in their own list even when the same person is also a
  // collaborator; the two relations are reported separately.
  const researchNeighbors = [...neighbors.values()]
    .map((entry) => ({ collaboratorId: entry.collaboratorId, name: entry.name, type: [...entry.types][0], types: [...entry.types], count: entry.count,
      alsoCoreCollaborator: coreCollaborators.some((core) => core.collaboratorId === entry.collaboratorId),
      sourceIds: [...entry.sourceIds], note: "research_neighbor_edge != collaboration_edge" }));

  return {
    targetId: target,
    depth: 1,
    coreCollaborators: coreCollaborators.sort((left, right) => right.jointRecordCount - left.jointRecordCount || String(left.name).localeCompare(String(right.name))),
    edges,
    researchNeighbors,
    leads,
    excluded,
    heuristics: { ...thresholds, note: "configurable engineering defaults, not scientific standards" },
  };
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
