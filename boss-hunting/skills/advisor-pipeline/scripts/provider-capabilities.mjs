#!/usr/bin/env node
// Provider access state machine and run-level capability metadata.
//
//   authenticated API available?  -> use API
//   anonymous / keyless official API available? -> use keyless API
//   official public web usable?  -> Browser Use
//   otherwise                    -> alternative authoritative source
//
// The metadata written here is run metadata (runs/<run-id>/provider-capabilities.json).
// It never contains secret values, and a configured credential never implies a
// paid entitlement: Web of Science tiers are unknown until probed.
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { credentialStatuses, loadCredentials } from "./credentials.mjs";
import { isExecutedDirectly } from "./direct-execution.mjs";

export const ACCESS_ROUTES = ["authenticated_api", "anonymous_api", "browser", "alternative_sources"];
export const RUN_MODES = ["api_enriched", "hybrid", "public_only", "browser_fallback"];
export const WOS_TIERS = ["starter", "researcher", "expanded", "limited", "unavailable"];

// Static provider facts: whether a keyless official API exists and whether the
// official public web is usable through Browser Use without bypassing access
// controls. Google Scholar is discovery/backcheck only, never authoritative.
export const PROVIDER_REGISTRY = {
  openalex: { label: "OpenAlex", anonymousApi: true, browser: true, credential: "openalex",
    roles: ["researcher_discovery", "works_authors_institutions", "coauthor_graph", "author_back_search"],
    cannotProveAlone: ["current_position", "doctoral_supervision", "author_contribution", "current_project_status"],
    alternatives: ["pubmed", "orcid", "official_institution_page"] },
  ncbi: { label: "NCBI E-utilities / PubMed", anonymousApi: true, browser: true, credential: "ncbi",
    roles: ["biomedical_discovery", "pmid_mesh", "author_back_search", "publication_type_dates_abstracts"],
    note: "Anonymous E-utilities keep working at a lower rate; missing key never means PubMed browser scraping.",
    alternatives: ["europe_pmc", "openalex", "publisher_doi"] },
  orcid: { label: "ORCID", anonymousApi: true, browser: true, credential: "orcid",
    roles: ["identity_resolution", "name_variants", "affiliation_history", "public_works_linkage"],
    cannotProveAlone: ["current_affiliation"], alternatives: ["official_institution_page"] },
  cinii: { label: "CiNii / KAKEN", anonymousApi: false, browser: true, credential: "cinii",
    roles: ["jp_researchers", "jp_papers", "jp_institutions", "kaken_grants"],
    note: "Without CINII_APP_ID use the CiNii Research and KAKEN websites through Browser Use; do not claim API parity.",
    alternatives: ["researchmap", "official_institution_page"] },
  semantic_scholar: { label: "Semantic Scholar", anonymousApi: true, browser: true, credential: "semantic_scholar",
    roles: ["citations", "references", "related_papers", "research_neighborhood"],
    note: "citation relationship != collaboration relationship", alternatives: ["openalex", "wos"] },
  wos: { label: "Web of Science", anonymousApi: false, browser: false, credential: "wos",
    roles: ["bibliographic_backcheck", "citation_graph", "author_institution_verification", "related_works"],
    note: "WOS_API_KEY != full API entitlement; web subscription != API entitlement. Browser only with the user's own lawful web access.",
    alternatives: ["openalex", "semantic_scholar", "pubmed"] },
  google_scholar: { label: "Google Scholar", anonymousApi: false, browser: true, credential: null,
    roles: ["discovery_backcheck"], authority: "not_authoritative",
    note: "Leads must be re-verified in PubMed, DOI/publisher, ORCID, the current institution or official funding records. Stop at CAPTCHA/login.",
    alternatives: ["pubmed", "openalex"] },
};

function wosTier(probe) {
  const tier = probe?.wosTier ?? probe?.tier;
  return WOS_TIERS.includes(tier) ? tier : null;
}

// Decide the route for one provider from static facts, credential status, host
// capability discovery and optional runtime probe results. `probes` records real
// observations only (e.g. { authenticatedApi: false } after a 401/403).
export function selectRoute(providerId, { credentialStatus = "unavailable", hostTools = {}, probe = null, authorizedBrowser = false } = {}) {
  const provider = PROVIDER_REGISTRY[providerId];
  if (!provider) throw new Error(`未知 provider: ${providerId}`);
  const configured = credentialStatus === "configured" || credentialStatus === "capability-limited";
  const authenticatedApi = configured && probe?.authenticatedApi !== false;
  const anonymousApi = provider.anonymousApi && probe?.anonymousApi !== false;
  const browserAvailable = Boolean(hostTools.interactiveBrowser || hostTools.builtinWeb);
  const browser = providerId === "wos"
    ? Boolean(authorizedBrowser && browserAvailable)
    : provider.browser && browserAvailable && probe?.browser !== false;
  let selectedRoute = "alternative_sources";
  if (authenticatedApi) selectedRoute = "authenticated_api";
  else if (anonymousApi) selectedRoute = "anonymous_api";
  else if (browser) selectedRoute = "browser";
  const result = {
    label: provider.label,
    authenticated_api: authenticatedApi,
    anonymous_api: anonymousApi,
    browser,
    selected_route: selectedRoute,
    credential_status: provider.credential ? credentialStatus : "not_applicable",
    alternatives: provider.alternatives || [],
  };
  if (providerId === "wos") {
    const tier = wosTier(probe) || (configured ? "unknown_until_probed" : "unavailable");
    Object.assign(result, {
      starter_api: tier === "starter",
      researcher_api: tier === "researcher",
      expanded_api: tier === "expanded",
      capability_tier: tier,
      authorized_browser: Boolean(authorizedBrowser && browserAvailable),
      selected_route: authenticatedApi && tier !== "unavailable" ? "authenticated_api" : browser ? "browser" : "alternative_sources",
    });
    result.authenticated_api = result.selected_route === "authenticated_api";
  }
  if (providerId === "google_scholar") result.authority = "discovery_backcheck_only";
  return result;
}

export function runMode(routes) {
  const credentialed = Object.entries(routes).filter(([id]) => PROVIDER_REGISTRY[id]?.credential);
  const authenticated = credentialed.filter(([, route]) => route.selected_route === "authenticated_api").length;
  const browserOnly = credentialed.filter(([, route]) => route.selected_route === "browser").length;
  if (authenticated === credentialed.length) return "api_enriched";
  if (authenticated > 0) return "hybrid";
  if (browserOnly >= Math.ceil(credentialed.length / 2)) return "browser_fallback";
  return "public_only";
}

export function buildProviderCapabilities({ credentials, hostTools = {}, probes = {}, authorizedWosBrowser = false, now = new Date().toISOString() } = {}) {
  const statuses = credentialStatuses(credentials);
  const providers = {};
  for (const id of Object.keys(PROVIDER_REGISTRY)) {
    const credentialId = PROVIDER_REGISTRY[id].credential;
    providers[id] = selectRoute(id, {
      credentialStatus: credentialId ? statuses[credentialId] || "unavailable" : "not_applicable",
      hostTools, probe: probes[id] || null, authorizedBrowser: id === "wos" ? authorizedWosBrowser : false,
    });
  }
  return {
    generatedAt: now,
    mode: runMode(providers),
    credentialsFile: { path: credentials?.file?.path || null, status: credentials?.file?.status || "missing", source: credentials?.file?.source || "os_default" },
    hostTools: { builtinWeb: Boolean(hostTools.builtinWeb), interactiveBrowser: Boolean(hostTools.interactiveBrowser) },
    providers,
    principles: [
      "credentials are optional accelerators, not prerequisites",
      "browser fallback seeks sufficient evidence for the research question; it does not reproduce every API field",
      "not_found in a public database != the PI has no funding / no record",
      "no CAPTCHA, login or paywall bypass; Browser never manufactures paid entitlement",
    ],
  };
}

export async function writeProviderCapabilities(projectRoot, runId, capabilities) {
  const directory = resolve(projectRoot, "runs", String(runId));
  await mkdir(directory, { recursive: true });
  const path = resolve(directory, "provider-capabilities.json");
  const serialized = JSON.stringify(capabilities, null, 2);
  if (/api[_-]?key|client[_-]?secret/i.test(serialized) && /[A-Za-z0-9]{20,}/.test(serialized)) {
    throw new Error("provider capability metadata 疑似包含 secret，拒绝写入");
  }
  await writeFile(path, `${serialized}\n`, "utf8");
  return path;
}

if (isExecutedDirectly(import.meta.url)) {
  const rootIndex = process.argv.indexOf("--project-root");
  const runIndex = process.argv.indexOf("--run-id");
  const credentials = await loadCredentials();
  const capabilities = buildProviderCapabilities({ credentials, hostTools: {
    builtinWeb: process.argv.includes("--builtin-web"), interactiveBrowser: process.argv.includes("--interactive-browser"),
  }, authorizedWosBrowser: process.argv.includes("--authorized-wos-browser") });
  if (rootIndex >= 0 && runIndex >= 0) {
    const path = await writeProviderCapabilities(process.argv[rootIndex + 1], process.argv[runIndex + 1], capabilities);
    console.log(JSON.stringify({ path, mode: capabilities.mode }));
  } else {
    console.log(JSON.stringify(capabilities, null, 2));
  }
}
