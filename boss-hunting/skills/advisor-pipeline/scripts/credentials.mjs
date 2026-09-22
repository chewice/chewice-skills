#!/usr/bin/env node
// Optional API credential loader for Boss Hunting.
//
// Credentials are accelerators, not prerequisites. The loader resolves them in
// a fixed order (process environment -> BOSS_HUNTING_CREDENTIALS_FILE -> the
// OS user config file) and never scans the disk for .env files. Callers only
// receive capability status words; secret values stay inside this module's
// return object and must not be copied into prompts, subagent output, evidence,
// run logs, HTML or Markdown.
import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { resolve } from "node:path";
import { isExecutedDirectly } from "./direct-execution.mjs";

export const CREDENTIAL_FILE_OVERRIDE = "BOSS_HUNTING_CREDENTIALS_FILE";

export const CREDENTIAL_PROVIDERS = [
  { id: "openalex", label: "OpenAlex", variables: ["OPENALEX_API_KEY"] },
  { id: "ncbi", label: "NCBI E-utilities", variables: ["NCBI_API_KEY"] },
  { id: "orcid", label: "ORCID", variables: ["ORCID_CLIENT_ID", "ORCID_CLIENT_SECRET"] },
  { id: "cinii", label: "CiNii/KAKEN", variables: ["CINII_APP_ID"] },
  { id: "semantic_scholar", label: "Semantic Scholar", variables: ["SEMANTIC_SCHOLAR_API_KEY"] },
  { id: "wos", label: "Web of Science", variables: ["WOS_API_KEY"] },
];

export const CREDENTIAL_VARIABLES = CREDENTIAL_PROVIDERS.flatMap((provider) => provider.variables);

export const CREDENTIAL_STATUSES = ["configured", "unavailable", "invalid", "capability-limited"];

export function defaultCredentialsPath({ platform = process.platform, env = process.env } = {}) {
  if (platform === "win32") {
    const appData = env.APPDATA || resolve(env.USERPROFILE || homedir(), "AppData", "Roaming");
    return resolve(appData, "boss-hunting", "credentials.env");
  }
  const configHome = env.XDG_CONFIG_HOME || resolve(env.HOME || homedir(), ".config");
  return resolve(configHome, "boss-hunting", "credentials.env");
}

export function resolveCredentialsPath({ platform = process.platform, env = process.env } = {}) {
  const override = String(env[CREDENTIAL_FILE_OVERRIDE] || "").trim();
  if (override) return { path: resolve(override), source: "override" };
  return { path: defaultCredentialsPath({ platform, env }), source: "os_default" };
}

export function parseDotenv(content) {
  const values = {};
  for (const rawLine of String(content || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values[match[1]] = value;
  }
  return values;
}

function looksInvalid(value) {
  const trimmed = String(value).trim();
  return !trimmed || /\s/.test(trimmed) || /^(your[-_ ]?key|changeme|xxx+|todo|placeholder|<.*>)$/i.test(trimmed);
}

function providerStatus(provider, values) {
  const present = provider.variables.map((name) => values[name]).filter((value) => value !== undefined && String(value).trim() !== "");
  if (!present.length) return "unavailable";
  if (present.length < provider.variables.length) return "invalid";
  if (present.some(looksInvalid)) return "invalid";
  return "configured";
}

export async function loadCredentials({ env = process.env, platform = process.platform, readFileImpl = readFile } = {}) {
  const location = resolveCredentialsPath({ platform, env });
  const fromEnvironment = {};
  for (const name of CREDENTIAL_VARIABLES) {
    if (env[name] !== undefined && String(env[name]).trim() !== "") fromEnvironment[name] = String(env[name]);
  }
  let fromFile = {};
  let fileStatus = "missing";
  try {
    fromFile = parseDotenv(await readFileImpl(location.path, "utf8"));
    fileStatus = "loaded";
  } catch (error) {
    fileStatus = error?.code === "ENOENT" ? "missing" : "unreadable";
  }
  const values = {};
  const origins = {};
  for (const name of CREDENTIAL_VARIABLES) {
    if (fromEnvironment[name] !== undefined) { values[name] = fromEnvironment[name]; origins[name] = "process_env"; }
    else if (fromFile[name] !== undefined && String(fromFile[name]).trim() !== "") {
      values[name] = String(fromFile[name]);
      origins[name] = location.source === "override" ? "override_file" : "os_default_file";
    }
  }
  const providers = Object.fromEntries(CREDENTIAL_PROVIDERS.map((provider) => [provider.id, {
    label: provider.label,
    status: providerStatus(provider, values),
    variables: provider.variables,
    origin: provider.variables.map((name) => origins[name]).find(Boolean) || null,
  }]));
  return {
    file: { ...location, status: fileStatus },
    providers,
    // Secret values are exposed only here for the retrieval layer.
    secrets: values,
  };
}

export function credentialStatuses(credentials) {
  return Object.fromEntries(Object.entries(credentials?.providers || {}).map(([id, provider]) => [id, provider.status]));
}

// Remove every known secret value from a text before it can reach prompts,
// subagent outputs, evidence rows, logs or reports.
export function redactSecrets(text, credentials) {
  let output = String(text ?? "");
  const secrets = Object.values(credentials?.secrets || {}).filter((value) => String(value).length >= 4);
  for (const secret of secrets.sort((left, right) => right.length - left.length)) {
    output = output.split(secret).join("[REDACTED]");
  }
  return output;
}

export function containsSecret(value, credentials) {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return Object.values(credentials?.secrets || {}).some((secret) => String(secret).length >= 4 && text.includes(secret));
}

export function renderCredentialStatus(credentials) {
  const lines = ["Boss Hunting credentials", ""];
  for (const provider of CREDENTIAL_PROVIDERS) {
    const status = credentials?.providers?.[provider.id]?.status || "unavailable";
    lines.push(`${provider.label.padEnd(20)} ${status}`);
  }
  lines.push("", `Credentials file:`, credentials?.file?.path || defaultCredentialsPath(),
    `(${credentials?.file?.status || "missing"}; source: ${credentials?.file?.source || "os_default"})`, "",
    "可继续运行；缺失 credential 将使用匿名 API、Browser Use 或其他公开来源降级。",
    "Do not paste keys into the chat. Put them in the credentials file or the process environment.");
  return lines.join("\n");
}

if (isExecutedDirectly(import.meta.url)) {
  const credentials = await loadCredentials();
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify({ file: credentials.file, providers: credentialStatuses(credentials) }, null, 2));
  } else {
    console.log(renderCredentialStatus(credentials));
  }
}
