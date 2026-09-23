import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import {
  CREDENTIAL_PROVIDERS, CREDENTIAL_STATUSES, CREDENTIAL_VARIABLES, containsSecret, credentialStatuses,
  defaultCredentialsPath, loadCredentials, parseDotenv, redactSecrets, renderCredentialStatus, resolveCredentialsPath,
  findRepositoryRoot, registeredRepositoryRoot, repositoryPointerPath,
} from "../../skills/advisor-pipeline/scripts/credentials.mjs";

const execute = promisify(execFile);
const script = fileURLToPath(new URL("../../skills/advisor-pipeline/scripts/credentials.mjs", import.meta.url));

// All key material here is synthetic and never used against a real provider.
const FAKE = "fixture-secret-value-0123456789";

test("T35 seven optional variables resolve process env -> override file -> OS default without disk scanning", async () => {
  assert.deepEqual(CREDENTIAL_VARIABLES, ["OPENALEX_API_KEY", "NCBI_API_KEY", "ORCID_CLIENT_ID", "ORCID_CLIENT_SECRET", "CINII_APP_ID", "SEMANTIC_SCHOLAR_API_KEY", "WOS_API_KEY"]);
  assert.equal(defaultCredentialsPath({ platform: "win32", env: { APPDATA: "C:\\Users\\fixture\\AppData\\Roaming" } }).replace(/\\/g, "/").endsWith("boss-hunting/credentials.env"), true);
  assert.equal(defaultCredentialsPath({ platform: "linux", env: { HOME: "/home/fixture" } }), "/home/fixture/.config/boss-hunting/credentials.env");
  assert.equal(defaultCredentialsPath({ platform: "linux", env: { XDG_CONFIG_HOME: "/xdg" } }), "/xdg/boss-hunting/credentials.env");
  assert.deepEqual(resolveCredentialsPath({ platform: "linux", env: { BOSS_HUNTING_CREDENTIALS_FILE: "/tmp/custom.env" } }), { path: "/tmp/custom.env", source: "override" });

  const read = [];
  const credentials = await loadCredentials({
    repositoryRoot: null,
    platform: "linux",
    env: { HOME: "/home/fixture", NCBI_API_KEY: FAKE },
    readFileImpl: async (path) => { read.push(path); return `OPENALEX_API_KEY="${FAKE}"\nNCBI_API_KEY=from-file-should-lose\n# comment\nWOS_API_KEY=\n`; },
  });
  // Only the resolved file is read; no other path is probed.
  assert.deepEqual(read, ["/home/fixture/.config/boss-hunting/credentials.env"]);
  assert.equal(credentials.providers.ncbi.origin, "process_env");
  assert.equal(credentials.secrets.NCBI_API_KEY, FAKE);
  assert.equal(credentials.providers.openalex.origin, "os_default_file");
  assert.equal(credentials.providers.wos.status, "unavailable");
});

test("T34 T36 statuses are only the four capability words; partial ORCID pair and placeholders are invalid", async () => {
  const credentials = await loadCredentials({ repositoryRoot: null, platform: "linux", env: { HOME: "/h", ORCID_CLIENT_ID: "only-id", SEMANTIC_SCHOLAR_API_KEY: "your_key", WOS_API_KEY: FAKE },
    readFileImpl: async () => { throw Object.assign(new Error("missing"), { code: "ENOENT" }); } });
  const statuses = credentialStatuses(credentials);
  assert.equal(statuses.orcid, "invalid");
  assert.equal(statuses.semantic_scholar, "invalid");
  assert.equal(statuses.wos, "configured");
  assert.equal(statuses.openalex, "unavailable");
  assert.equal(credentials.file.status, "missing");
  for (const status of Object.values(statuses)) assert.ok(CREDENTIAL_STATUSES.includes(status));
  assert.equal(Object.keys(statuses).length, CREDENTIAL_PROVIDERS.length);
  // The human table never echoes a value.
  const rendered = renderCredentialStatus(credentials);
  assert.match(rendered, /Web of Science\s+configured/);
  assert.match(rendered, /可继续运行/);
  assert.doesNotMatch(rendered, new RegExp(FAKE));
});

test("shared Skill credentials override legacy values without copying secrets to a project", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "boss-source-"));
  try {
    const central = resolve(root, "skills/boss-hunting/credentials.env");
    const read = [];
    const loaded = await loadCredentials({
      repositoryRoot: root, platform: "linux", env: { HOME: "/home/fixture", NCBI_API_KEY: FAKE },
      readFileImpl: async (path) => {
        read.push(path);
        return path === central ? "OPENALEX_API_KEY=fixture-central-key\n" : "OPENALEX_API_KEY=fixture-legacy-key\nCINII_APP_ID=fixture-legacy-cinii\n";
      },
    });
    assert.equal(loaded.file.path, central);
    assert.equal(loaded.providers.openalex.origin, "skill_file");
    assert.equal(loaded.secrets.OPENALEX_API_KEY, "fixture-central-key");
    assert.equal(loaded.providers.ncbi.origin, "process_env");
    assert.equal(loaded.providers.cinii.origin, "legacy_user_file");
    assert.deepEqual(read, [central, "/home/fixture/.config/boss-hunting/credentials.env"]);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("copied project Skills locate the one registered source repository", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "boss-source-"));
  try {
    const { mkdir } = await import("node:fs/promises");
    await mkdir(resolve(root, "skills/boss-hunting"), { recursive: true });
    await writeFile(resolve(root, "pixi.toml"), "[workspace]\nname = 'boss-hunting'\n");
    await mkdir(resolve(root, "config"), { recursive: true });
    await writeFile(resolve(root, "config/credentials.example.env"), "OPENALEX_API_KEY=\n");
    await writeFile(resolve(root, "skills/boss-hunting/SKILL.md"), "# Boss Hunting\n");
    const configHome = resolve(root, "user-config");
    const pointer = repositoryPointerPath({ platform: "linux", env: { XDG_CONFIG_HOME: configHome } });
    assert.equal(await registeredRepositoryRoot({ platform: "linux", env: { XDG_CONFIG_HOME: configHome }, readFileImpl: async (path) => path === pointer ? root + "\n" : "" }), root);
    assert.equal(findRepositoryRoot(resolve(root, "projects/p/.agents/skills/advisor-pipeline/scripts/credentials.mjs")), root);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("T34 secrets are redacted from text and detected inside nested subagent output", async () => {
  const credentials = await loadCredentials({ repositoryRoot: null, platform: "linux", env: { HOME: "/h", OPENALEX_API_KEY: FAKE }, readFileImpl: async () => "" });
  assert.equal(redactSecrets(`Authorization: ${FAKE} ok`, credentials), "Authorization: [REDACTED] ok");
  assert.equal(containsSecret({ findings: [{ excerpt: `token ${FAKE}` }] }, credentials), true);
  assert.equal(containsSecret({ findings: [{ excerpt: "no secret here" }] }, credentials), false);
  assert.equal(parseDotenv("export A='x y'\nB=c=d\nbad line\n").A, "x y");
  assert.equal(parseDotenv("B=c=d").B, "c=d");
});

test("credentials CLI --json reports statuses only and tolerates an unreadable override file", async () => {
  const scratch = await mkdtemp(resolve(tmpdir(), "boss-credentials-"));
  try {
    const file = resolve(scratch, "credentials.env");
    await writeFile(file, `CINII_APP_ID=${FAKE}\n`);
    const env = Object.fromEntries(Object.entries(process.env).filter(([name]) => !CREDENTIAL_VARIABLES.includes(name)));
    const { stdout } = await execute(process.execPath, [script, "--json"], { env: { ...env, BOSS_HUNTING_CREDENTIALS_FILE: file } });
    const parsed = JSON.parse(stdout);
    assert.equal(parsed.providers.cinii, "configured");
    assert.equal(parsed.file.source, "override");
    assert.doesNotMatch(stdout, new RegExp(FAKE));
    const unreadable = await loadCredentials({ repositoryRoot: null, platform: "linux", env: { HOME: "/h", BOSS_HUNTING_CREDENTIALS_FILE: scratch }, readFileImpl: async () => { throw Object.assign(new Error("EISDIR"), { code: "EISDIR" }); } });
    assert.equal(unreadable.file.status, "unreadable");
    assert.equal(credentialStatuses(unreadable).cinii, "unavailable");
  } finally { await rm(scratch, { recursive: true, force: true }); }
});
