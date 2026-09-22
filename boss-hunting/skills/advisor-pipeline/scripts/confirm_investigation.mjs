#!/usr/bin/env node
import { copyFile, readFile, rename, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import { resolve } from "node:path";
import {
  confirmInvestigationDraft,
  PROJECT_SCHEMA_VERSION,
  normalizeProjectMetadata,
  updateInvestigationDraft,
  validateInvestigationDraftAgainstCandidates,
} from "./project-contract.mjs";
import { withProjectFileLock } from "./project-file-lock.mjs";
import { isExecutedDirectly } from "./direct-execution.mjs";

function valuesAfter(args, flag) {
  const values = [];
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] !== flag) continue;
    const value = args[index + 1];
    if (!value) throw new Error(`${flag} 后缺少值`);
    values.push(...value.split(",").map((item) => item.trim()).filter(Boolean));
  }
  return [...new Set(values)];
}

async function writeJsonAtomic(path, value) {
  const temporary = `${path}.tmp-${process.pid}`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`);
  await rename(temporary, path);
}

async function confirmInvestigationInProjectUnlocked(
  root,
  {
    advisorProgramIds,
    selectedSections,
    communityRequested = false,
    sourcePolicy,
    now = new Date().toISOString(),
  },
) {
  const projectRoot = resolve(root);
  const projectFile = resolve(projectRoot, "project.json");
  const candidatesFile = resolve(projectRoot, "outputs", "candidates.json");
  const [rawProject, candidates] = await Promise.all([
    readFile(projectFile, "utf8").then(JSON.parse),
    readFile(candidatesFile, "utf8").then(JSON.parse),
  ]);
  if (!Array.isArray(candidates)) {
    throw new Error("outputs/candidates.json 顶层必须是数组");
  }
  if (Number(rawProject.schemaVersion) > PROJECT_SCHEMA_VERSION) {
    throw new Error("项目 schemaVersion 高于当前支持版本；保留原文件，不能降级确认");
  }
  const metadata = normalizeProjectMetadata(rawProject, {
    fallbackId: rawProject.id || rawProject.slug || "local-project",
    now,
  });
  const investigation = updateInvestigationDraft(
    metadata.investigation,
    {
      draft: {
        ...(sourcePolicy ? { sourcePolicy } : {}),
        selectedAdvisorProgramIds: advisorProgramIds,
        selectedSections,
        communitySources: { requested: communityRequested },
      },
    },
    now,
  );
  const validation = validateInvestigationDraftAgainstCandidates(
    investigation,
    candidates,
  );
  if (!validation.valid) throw new Error(validation.errors.join("；"));
  const confirmedInvestigation = confirmInvestigationDraft(investigation, {
    expectedRevision: investigation.draft.revision,
    now,
  });
  const updated = {
    ...metadata,
    investigation: confirmedInvestigation,
    updatedAt: now,
  };
  const backupBase = resolve(
    projectRoot,
    `project.json.backup-${now.replace(/[:.]/g, "-")}`,
  );
  let backup = backupBase;
  for (let suffix = 0; ; suffix += 1) {
    backup = suffix ? `${backupBase}-${suffix}` : backupBase;
    try {
      await copyFile(projectFile, backup, constants.COPYFILE_EXCL);
      break;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
    }
  }
  await writeJsonAtomic(projectFile, updated);
  return { project: updated, backup };
}

export async function confirmInvestigationInProject(root, options) {
  const projectRoot = resolve(root);
  return withProjectFileLock(projectRoot, () =>
    confirmInvestigationInProjectUnlocked(projectRoot, options),
  );
}

async function main() {
  const args = process.argv.slice(2);
  if (!args.includes("--confirmed-by-user")) {
    throw new Error("缺少 --confirmed-by-user：必须先向用户展示最终摘要并得到明确确认");
  }
  const rootIndex = args.indexOf("--root");
  const root = rootIndex >= 0 ? args[rootIndex + 1] : process.cwd();
  if (!root) throw new Error("--root 后必须提供项目目录");
  const communityIndex = args.indexOf("--community");
  const community = communityIndex >= 0 ? args[communityIndex + 1] : "no";
  const policyIndex = args.indexOf("--source-policy");
  const sourcePolicy = policyIndex >= 0 ? args[policyIndex + 1] : undefined;
  if (sourcePolicy && !["public_only", "community_allowed"].includes(sourcePolicy)) {
    throw new Error("--source-policy 只能是 public_only 或 community_allowed");
  }
  if (policyIndex >= 0 && !sourcePolicy) throw new Error("--source-policy 后缺少值");
  if (!/^(yes|no)$/i.test(community || "")) {
    throw new Error("--community 只能是 yes 或 no");
  }
  const result = await confirmInvestigationInProject(root, {
    advisorProgramIds: valuesAfter(args, "--advisor-id"),
    selectedSections: valuesAfter(args, "--section"),
    communityRequested: community.toLowerCase() === "yes",
    sourcePolicy,
  });
  process.stdout.write(`${JSON.stringify({
    confirmed: result.project.investigation.confirmed,
    backup: result.backup,
  }, null, 2)}\n`);
}

if (isExecutedDirectly(import.meta.url)) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
