import assert from "node:assert/strict";
import test from "node:test";
import { DEFAULT_NETWORK_THRESHOLDS, buildEgoNetwork, saturationReached } from "../../skills/advisor-pipeline/scripts/collaboration-network.mjs";

// Fictional identifiers only.
const names = { pi: "Fixture PI", core: "Fixture Core Collaborator", once: "Fixture One-off", grant: "Fixture Grant Partner", neighbor: "Fixture Neighbor", consortium: "Fixture Consortium Member" };
const record = (overrides) => ({ names, participants: ["pi"], topics: ["fixture-topic"], sourceIds: ["src"], ...overrides });

test("T19 core collaborators satisfy heuristic A/B/C; one-off coauthors remain leads", () => {
  const network = buildEgoNetwork("pi", [
    record({ id: "p1", type: "coauthorship", year: 2023, participants: ["pi", "core", "once"] }),
    record({ id: "p2", type: "coauthorship", year: 2025, participants: ["pi", "core"] }),
    record({ id: "p3", type: "coauthorship", year: 2024, participants: ["pi", "grant"] }),
    record({ id: "g1", type: "shared_grant", year: 2024, participants: ["pi", "grant"] }),
    record({ id: "old", type: "coauthorship", year: 2015, participants: ["pi", "once"] }),
  ], { referenceYear: 2026 });
  assert.equal(network.depth, 1);
  assert.deepEqual(network.coreCollaborators.map((row) => row.collaboratorId), ["core", "grant"]);
  const core = network.coreCollaborators.find((row) => row.collaboratorId === "core");
  assert.equal(core.heuristics.A_repeated_direction_related_studies, true);
  assert.equal(core.jointRecordCount, 2);
  assert.deepEqual([core.firstYear, core.lastYear], [2023, 2025]);
  const grant = network.coreCollaborators.find((row) => row.collaboratorId === "grant");
  assert.equal(grant.heuristics.B_joint_study_plus_shared_project, true);
  assert.deepEqual(network.leads.map((row) => row.collaboratorId), ["once"]);
  assert.deepEqual(network.excluded, [{ record: "old", reason: "outside_window" }]);
  // Edge weight is the count of direction-related joint records per edge type.
  assert.deepEqual(network.edges.map((edge) => [edge.target, edge.type, edge.count]), [["core", "coauthorship", 2], ["grant", "coauthorship", 1], ["grant", "shared_grant", 1]]);
  assert.match(network.heuristics.note, /configurable engineering defaults/);
  assert.equal(network.heuristics.windowYears, DEFAULT_NETWORK_THRESHOLDS.windowYears);
});

test("T21 collaboration edges and research-neighbor edges are never merged", () => {
  const network = buildEgoNetwork("pi", [
    record({ id: "p1", type: "coauthorship", year: 2024, participants: ["pi", "core"] }),
    record({ id: "p2", type: "coauthorship", year: 2025, participants: ["pi", "core"] }),
    record({ id: "c1", type: "citation", participants: ["pi", "neighbor"] }),
    record({ id: "c2", type: "co_citation", participants: ["pi", "core"] }),
  ], { referenceYear: 2026 });
  assert.deepEqual(network.coreCollaborators.map((row) => row.collaboratorId), ["core"]);
  assert.deepEqual(network.researchNeighbors.map((row) => [row.collaboratorId, row.alsoCoreCollaborator]), [["neighbor", false], ["core", true]]);
  assert.ok(network.researchNeighbors.every((row) => /research_neighbor_edge != collaboration_edge/.test(row.note)));
  assert.ok(network.edges.every((edge) => edge.type === "coauthorship"));
  assert.ok(!network.coreCollaborators.some((row) => row.collaboratorId === "neighbor"));
});

test("T20 a single consortium paper does not create hundreds of collaborators", () => {
  const network = buildEgoNetwork("pi", [
    record({ id: "big", type: "coauthorship", year: 2024, authorCount: 500, participants: ["pi", "consortium", "core"], consortiumLeadership: ["core"] }),
    record({ id: "p2", type: "coauthorship", year: 2025, participants: ["pi", "core"] }),
  ], { referenceYear: 2026 });
  assert.deepEqual(network.coreCollaborators.map((row) => row.collaboratorId), ["core"]);
  assert.deepEqual(network.excluded, [{ record: "big", collaboratorId: "consortium", reason: "consortium_without_independent_link" }]);
  assert.ok(!network.leads.some((row) => row.collaboratorId === "consortium"));
  const lowered = buildEgoNetwork("pi", [record({ id: "big", type: "coauthorship", year: 2024, authorCount: 500, participants: ["pi", "consortium"] })],
    { referenceYear: 2026, thresholds: { consortiumAuthorThreshold: 1000, minDirectionRelatedJointStudies: 1 } });
  assert.deepEqual(lowered.coreCollaborators.map((row) => row.collaboratorId), ["consortium"], "thresholds are configurable");
});

test("T26 saturation stops on zero new validated PIs, low growth without new structure, or the round cap", () => {
  assert.equal(saturationReached({ existingValidated: 20, newValidated: 0, round: 1 }).reason, "pi_saturation");
  const engineering = saturationReached({ existingValidated: 20, newValidated: 1, newSubdirections: 0, round: 1 });
  assert.equal(engineering.stop, true);
  assert.equal(engineering.reason, "engineering_heuristic");
  assert.equal(engineering.growthRatio, 0.05);
  assert.match(engineering.note, /configurable engineering default/);
  const structural = saturationReached({ existingValidated: 20, newValidated: 1, newSubdirections: 1, round: 1 });
  assert.equal(structural.stop, false);
  assert.equal(structural.reason, "continue");
  assert.equal(saturationReached({ existingValidated: 20, newValidated: 8, round: 2 }).reason, "max_rounds");
  assert.equal(saturationReached({ existingValidated: 20, newValidated: 8, round: 1, ratio: 0.5 }).stop, true, "ratio is configurable");
});
