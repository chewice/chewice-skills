import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { createTemplate, renderFirstUse } from "../../skills/advisor-pipeline/scripts/first-use.mjs";
import { findRepositoryRoot } from "../../skills/advisor-pipeline/scripts/credentials.mjs";

test("first-use creates one ignored-source credential template and never overwrites user values", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "boss-onboarding-"));
  try {
    await mkdir(resolve(root, "config"), { recursive: true });
    await mkdir(resolve(root, "skills/boss-hunting"), { recursive: true });
    await writeFile(resolve(root, "pixi.toml"), "[workspace]\n");
    await writeFile(resolve(root, "skills/boss-hunting/SKILL.md"), "# Boss Hunting\n");
    await writeFile(resolve(root, "config/credentials.example.env"), "OPENALEX_API_KEY=\n");
    const pointer = resolve(root, "user-config/boss-hunting/repository.path");
    const created = await createTemplate(root, { pointer });
    assert.equal(created.created, true);
    assert.equal(created.path, resolve(root, "skills/boss-hunting/credentials.env"));
    assert.equal(await readFile(created.path, "utf8"), "OPENALEX_API_KEY=\n");
    assert.equal((await stat(created.path)).mode & 0o777, 0o600);
    assert.equal(await readFile(pointer, "utf8"), root + "\n");

    await writeFile(created.path, "OPENALEX_API_KEY=fixture-private-value\n");
    assert.equal((await createTemplate(root, { pointer })).created, false);
    assert.equal(await readFile(created.path, "utf8"), "OPENALEX_API_KEY=fixture-private-value\n");
    assert.equal(findRepositoryRoot(resolve(root, "projects/p/.agents/skills/advisor-pipeline/scripts/first-use.mjs")), root);
    await rm(resolve(root, "config/credentials.example.env"));
    assert.equal(findRepositoryRoot(resolve(root, "projects/p/.agents/skills/advisor-pipeline/scripts/first-use.mjs")), null);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("first-use feedback orders environment, optional keys and prompt without exposing values", () => {
  const statuses = Object.fromEntries(["openalex", "ncbi", "orcid", "cinii", "semantic_scholar", "wos"].map((id) => [id, "unavailable"]));
  const report = {
    repositoryRoot: "/fixture/boss-hunting",
    environment: {
      platform: "linux-64", supportedPlatform: true, pixi: "pixi 0.63",
      runtime: { ready: true, detail: "node v22; python 3.12" },
      skills: Object.fromEntries(["boss-hunting", "advisor-pipeline", "advisor-finder", "advisor-detective", "advisor-evaluator", "advisor-research-proposal", "advisor-outreach"].map((id) => [id, true])),
      webDependencies: "missing_optional",
    },
    credentials: { file: { path: "/fixture/boss-hunting/skills/boss-hunting/credentials.env", status: "loaded" }, sharedFileMode: 0o777, created: true, providers: statuses },
  };
  const text = renderFirstUse(report);
  assert.ok(text.indexOf("1. 依赖环境") < text.indexOf("2. 可选 API 凭据"));
  assert.ok(text.indexOf("2. 可选 API 凭据") < text.indexOf("3. 首次使用 prompt 示例"));
  assert.match(text, /https:\/\/openalex\.org\/settings\/api/);
  assert.match(text, /skills\/boss-hunting\/credentials\.env/);
  assert.match(text, /文件系统报告凭据文件权限为 0777/);
  assert.match(text, /\$boss-hunting 探索/);
  assert.doesNotMatch(text, /fixture-private-value/);
  report.environment.runtime.ready = false;
  assert.doesNotMatch(renderFirstUse(report), /\$boss-hunting 探索/);
});
