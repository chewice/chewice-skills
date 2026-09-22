import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import {
  ACCESS_ROUTES, PROVIDER_REGISTRY, RUN_MODES, WOS_TIERS, buildProviderCapabilities, runMode, selectRoute, writeProviderCapabilities,
} from "../../skills/advisor-pipeline/scripts/provider-capabilities.mjs";

const FAKE = "fixture-secret-value-0123456789";
const credentials = (statuses, secrets = {}) => ({
  file: { path: "/fixture/credentials.env", status: "loaded", source: "override" },
  providers: Object.fromEntries(Object.entries(statuses).map(([id, status]) => [id, { status }])),
  secrets,
});

test("T36 T37 T38 four-level fallback: authenticated API -> anonymous API -> browser -> alternative sources", () => {
  assert.deepEqual(ACCESS_ROUTES, ["authenticated_api", "anonymous_api", "browser", "alternative_sources"]);
  assert.equal(selectRoute("openalex", { credentialStatus: "configured" }).selected_route, "authenticated_api");
  assert.equal(selectRoute("openalex", { credentialStatus: "unavailable" }).selected_route, "anonymous_api");
  // A 401/403 probe demotes even a configured key.
  assert.equal(selectRoute("openalex", { credentialStatus: "configured", probe: { authenticatedApi: false } }).selected_route, "anonymous_api");
  // CiNii has no keyless API: browser on official pages, otherwise alternatives.
  assert.equal(selectRoute("cinii", { credentialStatus: "unavailable", hostTools: { builtinWeb: true } }).selected_route, "browser");
  assert.equal(selectRoute("cinii", { credentialStatus: "unavailable" }).selected_route, "alternative_sources");
  assert.deepEqual(selectRoute("cinii", { credentialStatus: "unavailable" }).alternatives, ["researchmap", "official_institution_page"]);
  // Missing NCBI key never means PubMed browser scraping.
  assert.equal(selectRoute("ncbi", { credentialStatus: "unavailable", hostTools: { interactiveBrowser: true } }).selected_route, "anonymous_api");
  assert.match(PROVIDER_REGISTRY.ncbi.note, /never means PubMed browser scraping/);
  assert.throws(() => selectRoute("scopus"), /未知 provider/);
});

test("T27 T39 Web of Science tier is unknown until probed; key != entitlement; browser only with the user's own lawful access", () => {
  assert.deepEqual(WOS_TIERS, ["starter", "researcher", "expanded", "limited", "unavailable"]);
  const configured = selectRoute("wos", { credentialStatus: "configured" });
  assert.equal(configured.capability_tier, "unknown_until_probed");
  assert.equal(configured.expanded_api, false);
  assert.equal(configured.selected_route, "authenticated_api");
  const starter = selectRoute("wos", { credentialStatus: "configured", probe: { wosTier: "starter" } });
  assert.equal(starter.starter_api, true);
  assert.equal(starter.expanded_api, false);
  const none = selectRoute("wos", { credentialStatus: "unavailable", hostTools: { interactiveBrowser: true } });
  assert.equal(none.selected_route, "alternative_sources", "browser is not assumed without explicit authorization");
  const authorized = selectRoute("wos", { credentialStatus: "unavailable", hostTools: { interactiveBrowser: true }, authorizedBrowser: true });
  assert.equal(authorized.selected_route, "browser");
  assert.equal(authorized.authorized_browser, true);
  const revoked = selectRoute("wos", { credentialStatus: "configured", probe: { authenticatedApi: false, wosTier: "unavailable" } });
  assert.equal(revoked.selected_route, "alternative_sources");
  assert.equal(selectRoute("google_scholar", { hostTools: { builtinWeb: true } }).authority, "discovery_backcheck_only");
});

test("T34 T36 run mode and run metadata never contain secrets and mark credentials as optional", async () => {
  assert.deepEqual(RUN_MODES, ["api_enriched", "hybrid", "public_only", "browser_fallback"]);
  const all = Object.fromEntries(Object.keys(PROVIDER_REGISTRY).filter((id) => PROVIDER_REGISTRY[id].credential).map((id) => [id, "configured"]));
  assert.equal(buildProviderCapabilities({ credentials: credentials(all), hostTools: { builtinWeb: true }, probes: { wos: { wosTier: "researcher" } } }).mode, "api_enriched");
  const hybrid = buildProviderCapabilities({ credentials: credentials({ openalex: "configured" }), hostTools: { builtinWeb: true } });
  assert.equal(hybrid.mode, "hybrid");
  const publicOnly = buildProviderCapabilities({ credentials: credentials({}), hostTools: {} });
  assert.equal(publicOnly.mode, "public_only");
  assert.equal(publicOnly.providers.openalex.selected_route, "anonymous_api");
  assert.equal(publicOnly.providers.cinii.selected_route, "alternative_sources");
  assert.equal(runMode({ cinii: { selected_route: "browser" }, wos: { selected_route: "browser" }, openalex: { selected_route: "anonymous_api" } }), "browser_fallback");
  assert.ok(publicOnly.principles.some((line) => /optional accelerators/.test(line)));
  assert.ok(publicOnly.principles.some((line) => /not_found in a public database != the PI has no funding/.test(line)));

  const root = await mkdtemp(resolve(tmpdir(), "boss-capabilities-"));
  try {
    const path = await writeProviderCapabilities(root, "run-1", buildProviderCapabilities({ credentials: credentials({ ncbi: "configured" }, { NCBI_API_KEY: FAKE }), now: "2026-09-22T00:00:00.000Z" }));
    assert.equal(path, resolve(root, "runs", "run-1", "provider-capabilities.json"));
    const written = await readFile(path, "utf8");
    assert.doesNotMatch(written, new RegExp(FAKE));
    assert.match(written, /"credential_status": "configured"/);
    assert.equal(JSON.parse(written).providers.google_scholar.credential_status, "not_applicable");
    await assert.rejects(writeProviderCapabilities(root, "run-2", { leaked: { api_key: "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456" } }), /secret/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
