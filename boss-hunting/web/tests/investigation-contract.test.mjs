import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  DEFAULT_DETECTIVE_SECTIONS,
  DETECTIVE_SECTIONS,
} from "../local-runtime/project-store.mjs";
import {
  getDetectiveSectionCatalog, GENERIC_DETECTIVE_SECTIONS, MEDICAL_DEFAULT_DETECTIVE_SECTIONS, MEDICAL_DETECTIVE_SECTION_CATALOG,
} from "../../skills/advisor-pipeline/scripts/project-contract.mjs";

const testDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(testDirectory, "../..");

function parseReferenceMenu(reference, pattern = /## CLI selection menu([\s\S]*?)## Cost level/) {
  const block = reference.match(pattern)?.[1];
  assert.ok(block, "canonical CLI selection menu is missing");
  return [...block.matchAll(
    /^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$/gm,
  )].map((match) => ({
    number: Number(match[1]),
    id: match[2],
    label: match[3].trim(),
    defaultSelected: match[4].trim() === "selected by default",
  }));
}

test("Web and CLI share one ordered investigation option contract", async () => {
  const [reference, pageSource, storeSource] = await Promise.all([
    readFile(
      resolve(
        repositoryRoot,
        "skills/advisor-detective/references/investigation-sections.md",
      ),
      "utf8",
    ),
    readFile(resolve(repositoryRoot, "web/app/page.tsx"), "utf8"),
    readFile(resolve(repositoryRoot, "web/local-runtime/project-store.mjs"), "utf8"),
  ]);

  const referenceOptions = parseReferenceMenu(reference);
  const frontendOptions = getDetectiveSectionCatalog({ domainProfile: "general" });
  assert.match(pageSource, /const detectiveSectionOptions = activeProject\?\.detectiveSectionCatalog/);
  assert.match(storeSource, /detectiveSectionCatalog: getDetectiveSectionCatalog\(metadata\)/);
  assert.deepEqual(getDetectiveSectionCatalog({ domainProfile: "medical" })
    .filter((section) => section.defaultSelected).map((section) => section.id), MEDICAL_DEFAULT_DETECTIVE_SECTIONS);
  const medicalReference = parseReferenceMenu(reference, /## Medical five-module menu([\s\S]*?)Module scope/);
  assert.deepEqual(medicalReference.map(({ id, label, defaultSelected }) => ({ id, label, defaultSelected })),
    MEDICAL_DETECTIVE_SECTION_CATALOG.map(({ id, label, defaultSelected }) => ({ id, label, defaultSelected })));
  assert.deepEqual(getDetectiveSectionCatalog({ domainProfile: "medical" }).map(({ id }) => id), medicalReference.map(({ id }) => id));

  assert.equal(referenceOptions.length, 11);
  assert.deepEqual(
    referenceOptions.map(({ id }) => id),
    GENERIC_DETECTIVE_SECTIONS,
  );
  assert.deepEqual(DETECTIVE_SECTIONS, [...GENERIC_DETECTIVE_SECTIONS, ...MEDICAL_DETECTIVE_SECTION_CATALOG.map(({ id }) => id)]);
  assert.deepEqual(
    referenceOptions.filter(({ defaultSelected }) => defaultSelected).map(({ id }) => id),
    DEFAULT_DETECTIVE_SECTIONS,
  );
  assert.deepEqual(
    frontendOptions,
    referenceOptions.map(({ id, label, defaultSelected }) => ({
      id,
      label,
      defaultSelected,
    })),
  );

  assert.match(reference, /low: work units <= 8/);
  assert.match(reference, /medium: work units 9-24/);
  assert.match(reference, /high: work units > 24/);
  assert.match(pageSource, /selected\.size \* selectedSections\.size > 24/);
  assert.match(pageSource, /selected\.size \* selectedSections\.size > 8/);

  const communityReference = reference.match(
    /## Community-source consent trigger([\s\S]*?)## Guidance/,
  )?.[1];
  assert.ok(communityReference, "community consent trigger list is missing");
  const communityIds = [...communityReference.matchAll(/^- `([^`]+)`$/gm)].map(
    (match) => match[1],
  );
  const frontendCommunityBlock = pageSource.match(
    /const communityRelevant = [^\n]*\[([\s\S]*?)\]\.some/,
  )?.[1];
  assert.ok(frontendCommunityBlock, "frontend community trigger list is missing");
  const frontendCommunityIds = [
    ...frontendCommunityBlock.matchAll(/"([^"]+)"/g),
  ].map((match) => match[1]);
  assert.deepEqual(frontendCommunityIds, communityIds);
});

test("Web saves draft first and refreshes community sources only after confirmation", async () => {
  const [pageSource, serverSource] = await Promise.all([
    readFile(resolve(repositoryRoot, "web/app/page.tsx"), "utf8"),
    readFile(resolve(repositoryRoot, "web/local-runtime/server.mjs"), "utf8"),
  ]);
  const saveFunction = pageSource.match(
    /async function saveInvestigationConfiguration\([\s\S]*?\r?\n  }\r?\n\r?\n  async function refreshCommunityKnowledge/,
  )?.[0];
  assert.ok(saveFunction, "draft save function is missing");
  assert.match(saveFunction, /investigation:\s*\{\s*draft:/);
  assert.doesNotMatch(saveFunction, /confirmed:/);

  const confirmFunction = pageSource.match(
    /async function confirmAndStartInvestigation\(\)[\s\S]*?\r?\n  }\r?\n\r?\n  function startRanking/,
  )?.[0];
  assert.ok(confirmFunction, "final confirmation function is missing");
  const confirmPosition = confirmFunction.indexOf("/investigation/confirm");
  const refreshPosition = confirmFunction.indexOf("refreshCommunityKnowledge");
  assert.ok(confirmPosition >= 0, "final confirmation endpoint is not called");
  assert.ok(
    refreshPosition > confirmPosition,
    "community refresh must happen only after final confirmation",
  );
  assert.match(serverSource, /communityRefreshEligibility\(project\.investigation\)/);
});
