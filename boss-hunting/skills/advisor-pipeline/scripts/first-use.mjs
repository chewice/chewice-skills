#!/usr/bin/env node
// Read-only environment check plus one-time creation of the ignored shared
// credentials template. Never installs packages or prints credential values.
import { existsSync } from "node:fs";
import { mkdir, open, readFile, stat, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { findRepositoryRoot, loadCredentials, registeredRepositoryRoot, repositoryPointerPath, SKILL_CREDENTIALS_RELATIVE_PATH } from "./credentials.mjs";
import { isExecutedDirectly } from "./direct-execution.mjs";

const SKILL_NAMES = [
  "boss-hunting", "advisor-pipeline", "advisor-finder", "advisor-detective",
  "advisor-evaluator", "advisor-research-proposal", "advisor-outreach",
];

function pixiExecutable() {
  const candidates = [process.env.PIXI_EXE, "pixi", resolve(homedir(), ".pixi", "bin", process.platform === "win32" ? "pixi.exe" : "pixi")].filter(Boolean);
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["--version"], { encoding: "utf8", timeout: 5000 });
    if (result.status === 0) return { command: candidate, version: String(result.stdout || "").trim() };
  }
  return null;
}

export async function createTemplate(repoRoot, { pointer = repositoryPointerPath() } = {}) {
  const path = resolve(repoRoot, SKILL_CREDENTIALS_RELATIVE_PATH);
  const template = resolve(repoRoot, "config", "credentials.example.env");
  const content = await readFile(template, "utf8");
  let created = false;
  try {
    const handle = await open(path, "wx", 0o600);
    try { await handle.writeFile(content); } finally { await handle.close(); }
    created = true;
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  await mkdir(dirname(pointer), { recursive: true });
  await writeFile(pointer, repoRoot + "\n", { mode: 0o600 });
  return { path, created };
}

export async function firstUseCheck({ repositoryRoot, createFile = true, pointer } = {}) {
  repositoryRoot = repositoryRoot === undefined ? findRepositoryRoot() || await registeredRepositoryRoot() : repositoryRoot;
  const supportedPlatform = process.platform === "linux" && process.arch === "x64";
  const pixi = pixiExecutable();
  const skills = repositoryRoot ? Object.fromEntries(SKILL_NAMES.map((name) => [name, existsSync(resolve(repositoryRoot, "skills", name, "SKILL.md"))])) : {};
  let runtime = { ready: false, detail: "未检查：未找到 Pixi 或仓库" };
  if (pixi && repositoryRoot && supportedPlatform) {
    const check = spawnSync(pixi.command, ["run", "--as-is", "--manifest-path", resolve(repositoryRoot, "pixi.toml"), "check-runtime"], {
      cwd: repositoryRoot, encoding: "utf8", timeout: 20000,
    });
    runtime = {
      ready: check.status === 0,
      detail: check.status === 0 ? String(check.stdout || "").trim().replace(/\s+/g, " ") : "锁定环境尚未就绪；可在仓库运行 pixi install",
    };
  }
  const template = repositoryRoot && createFile ? await createTemplate(repositoryRoot, { pointer }) : null;
  const credentials = await loadCredentials({ repositoryRoot });
  let sharedFileMode = null;
  if (repositoryRoot) {
    try { sharedFileMode = (await stat(resolve(repositoryRoot, SKILL_CREDENTIALS_RELATIVE_PATH))).mode & 0o777; }
    catch { /* shared file has not been created */ }
  }
  return {
    repositoryRoot,
    environment: {
      platform: process.platform + "-" + (process.arch === "x64" ? "64" : process.arch),
      supportedPlatform,
      pixi: pixi?.version || "missing",
      runtime,
      skills,
      webDependencies: repositoryRoot && existsSync(resolve(repositoryRoot, "web", "node_modules")) ? "installed_optional" : "missing_optional",
    },
    credentials: {
      file: credentials.file,
      sharedPath: repositoryRoot ? resolve(repositoryRoot, SKILL_CREDENTIALS_RELATIVE_PATH) : null,
      sharedFileMode,
      created: template?.created || false,
      providers: Object.fromEntries(Object.entries(credentials.providers).map(([id, item]) => [id, item.status])),
    },
  };
}

export function renderFirstUse(result) {
  const { environment, credentials } = result;
  const skillReady = Object.keys(environment.skills).length === SKILL_NAMES.length && Object.values(environment.skills).every(Boolean);
  const ready = environment.supportedPlatform && environment.pixi !== "missing" && environment.runtime.ready && skillReady;
  const lines = [
    "Boss Hunting 首次使用检查",
    "",
    "1. 依赖环境",
    "平台：" + environment.platform + "（" + (environment.supportedPlatform ? "符合 linux-64" : "当前 Pixi manifest 未覆盖") + "）",
    "Pixi：" + environment.pixi,
    "锁定运行环境：" + (environment.runtime.ready ? "就绪；" + environment.runtime.detail : "缺失或未验证"),
    "Skills：" + Object.values(environment.skills).filter(Boolean).length + "/" + SKILL_NAMES.length,
    "Web 前端依赖：" + (environment.webDependencies === "installed_optional" ? "已安装（可选）" : "未安装（直接使用 Skill 不需要）"),
  ];
  if (!result.repositoryRoot) lines.push("未找到 Boss Hunting 源仓库：请先在克隆后的源仓库运行本检查，再从其他项目复用该安装。");
  else if (!ready) lines.push("请先修复缺失项；Pixi 环境安装命令：在 Boss Hunting 仓库运行 pixi install（本检查不会安装）。");
  lines.push(
    "",
    "2. 可选 API 凭据",
    "请手动填写：" + (credentials.sharedPath || (result.repositoryRoot ? resolve(result.repositoryRoot, SKILL_CREDENTIALS_RELATIVE_PATH) : "源仓库 skills/boss-hunting/credentials.env（当前未定位源仓库）")),
    "文件：" + (credentials.created ? "首次创建空值模板" : result.repositoryRoot ? "已存在，未覆盖" : "未创建"),
    "OpenAlex=" + credentials.providers.openalex + "；NCBI=" + credentials.providers.ncbi + "；ORCID=" + credentials.providers.orcid,
    "CiNii/KAKEN=" + credentials.providers.cinii + "；Semantic Scholar=" + credentials.providers.semantic_scholar + "；WoS=" + credentials.providers.wos,
    "推荐 OpenAlex（OPENALEX_API_KEY）：注册或登录，打开 API 设置复制 Key：https://openalex.org/settings/api",
    "推荐 NCBI（NCBI_API_KEY）：登录 My NCBI，在 Account Settings 的 API Key Management 创建 Key：https://www.ncbi.nlm.nih.gov/account/settings/",
    "身份消歧按需 ORCID（ORCID_CLIENT_ID＋ORCID_CLIENT_SECRET）：登录，在 Developer Tools 注册 Public API client：https://info.orcid.org/documentation/integration-guide/registering-a-public-api-client/",
    "日本方向按需 CiNii/KAKEN（CINII_APP_ID）：填写 Web API Developer Registration 表单取得 Application ID：https://support.nii.ac.jp/en/cinii/api/developer",
    "引文补充按需 Semantic Scholar（SEMANTIC_SCHOLAR_API_KEY）：提交 Request an API Key 表单，查收邮件：https://www.semanticscholar.org/product/api#api-key-form",
    "有机构权限时按需 WoS（WOS_API_KEY）：注册门户和应用，订阅获准的 API 计划：https://developer.clarivate.com/",
    "每行填写 VARIABLE=实际值；不要把 Key 发到聊天。Key 缺失不阻止公开检索。",
  );
  if (environment.platform.startsWith("win32") && credentials.sharedFileMode !== null && credentials.sharedFileMode !== undefined) {
    lines.push("Windows 文件权限需在文件属性中核对；Node.js 的 mode 数值不能证明凭据文件仅本人可读。填写真实 Key 前请核对访问权限。");
  } else if (credentials.sharedFileMode !== null && credentials.sharedFileMode !== undefined && (credentials.sharedFileMode & 0o077)) {
    lines.push("文件系统报告凭据文件权限为 0" + credentials.sharedFileMode.toString(8) + "；填写真实 Key 前请核对宿主系统的文件访问权限。");
  }
  if (credentials.file.source === "override") lines.push("当前设置了 BOSS_HUNTING_CREDENTIALS_FILE，状态检测优先读取该覆盖文件。");
  if (ready) lines.push(
    "",
    "3. 首次使用 prompt 示例",
    "$boss-hunting 探索肿瘤免疫治疗反应的博士导师。领域：肿瘤学；科学问题：肿瘤微环境如何影响免疫治疗反应；目标地区：香港和美国。先做无 CV 的方向探索，按公开证据生成 HTML 报告。",
  );
  else lines.push("", "3. 环境就绪后，再提供医学领域、科学问题和目标地区以开始调查。");
  return lines.join("\n");
}

if (isExecutedDirectly(import.meta.url)) {
  const report = await firstUseCheck();
  console.log(process.argv.includes("--json") ? JSON.stringify(report, null, 2) : renderFirstUse(report));
}
