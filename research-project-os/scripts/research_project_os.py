"""Create and maintain a reusable Research Project OS control layer.

This CLI is intentionally conservative:

- inspect, start, audit, and sync-audit are read-only;
- init, adopt, close, and sync-export are dry-run unless --apply is explicit;
- existing files are preserved unless --overwrite is explicit;
- adopt never replaces AGENTS.md, README.md, or .gitignore;
- no command stages, commits, pushes, or writes to Notion.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = SKILL_ROOT / "assets"
BASE_ASSET_ROOT = ASSET_ROOT / "base"
PROFILE_ROOT = ASSET_ROOT / "profiles"
PROFILE_NAMES = (
    "generic-analysis",
    "bioinformatics",
    "literature-review",
    "software-development",
)
RELEASE_VERSION = "0.3.2"
MANIFEST_SCHEMA_VERSION = "0.3.0"
SYNC_PAYLOAD_SCHEMA_VERSION = "0.3.0"
SUPPORTED_MANIFEST_SCHEMAS = {"0.1.0", "0.2.0", MANIFEST_SCHEMA_VERSION}
SYNC_EXPORT_KINDS = ("project-adopt", "milestone", "full-state")
OUTPUT_KINDS = (*SYNC_EXPORT_KINDS, "session-close")
PROTECTED_ADOPTION_PATHS = {"AGENTS.md", "README.md", ".gitignore"}
REQUIRED_CONTROL_PATHS = (
    "AGENTS.md",
    "project_manifest.yaml",
    "CURRENT_HANDOFF.md",
    "docs/ai_context/status_policy.md",
    "docs/ai_context/tasks.md",
    "docs/ai_context/open_questions.md",
    "docs/ai_context/decisions.md",
    "docs/handoffs/archive",
    "reports/evidence_registry.yaml",
    "work/notion_sync/pending",
    "work/notion_sync/applied",
    "work/notion_sync/conflicts",
    "work/notion_sync/superseded",
)
HANDOFF_SECTIONS = (
    "Checkpoint",
    "Current objective",
    "Completed",
    "Confirmed decisions",
    "Evidence and outputs",
    "Open questions",
    "Blockers and interpretation boundary",
    "Next minimum action",
    "Resume commands",
)
SENSITIVE_PATTERNS = (
    re.compile(r"\.(?:fastq|fq)(?:\.gz)?$", re.IGNORECASE),
    re.compile(r"\.(?:h5ad|loom|mtx|mtx\.gz)$", re.IGNORECASE),
    re.compile(r"\.zarr(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)\.env(?:\.|$)", re.IGNORECASE),
    re.compile(
        r"(?:^|/)(?:credentials?|secrets?|tokens?|private[_-]?keys?)(?:[._/-]|$)",
        re.IGNORECASE,
    ),
)
SESSION_PATTERN = re.compile(r"^SES-\d{8}-\d{3}$")
NUMBERED_TITLE_PATTERN = re.compile(r"^(?P<ordinal>\d{2,})｜(?P<title>\S(?:.*\S)?)$")
TOML_TABLE_PATTERN = re.compile(
    r"^\s*\[(?!\[)\s*(?P<table>[^\]]+?)\s*\](?!\])(?:\s*#.*)?$",
    flags=re.MULTILINE,
)
DEFAULT_PIXI_POLICY = {
    "policy": "root_workspace",
    "allow_nested_package_manifests": True,
}
PIXI_SCAN_MAX_DEPTH = 6
PIXI_SCAN_MAX_ENTRIES = 10_000
PIXI_SCAN_PRUNE_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "data",
    "datasets",
    "figure",
    "figures",
    "node_modules",
    "output",
    "outputs",
    "reports",
    "resources",
    "result",
    "results",
    "runs",
}
PROJECT_INVENTORY_PATTERNS = {
    "code_roots": (
        "*.R",
        "*.ipynb",
        "*.py",
        "*.sh",
        "analysis",
        "analyses",
        "notebooks",
        "R",
        "scripts",
        "src",
        "utils",
        "workflow",
        "workflows",
    ),
    "environment_files": (
        ".pixi/config.toml",
        "DESCRIPTION",
        "environment.yml",
        "environment.yaml",
        "pixi.lock",
        "pixi.toml",
        "pyproject.toml",
        "renv.lock",
        "requirements.txt",
        "environments/*/pixi.lock",
        "environments/*/pixi.toml",
        "pixi-workspaces/*/pixi.lock",
        "pixi-workspaces/*/pixi.toml",
    ),
    "data_roots": ("data", "datasets", "resources"),
    "artifact_roots": (
        "figure",
        "figures",
        "output",
        "outputs",
        "reports",
        "result",
        "results",
        "runs",
    ),
    "documentation_roots": ("AGENTS.md", "README.md", "docs"),
}


@dataclass(frozen=True)
class FileAction:
    path: str
    action: str
    content: str | None = None
    reason: str | None = None


def configure_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return logging.getLogger("research_project_os")


def add_project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("."),
        help="Target project directory.",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=RELEASE_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("inspect", "start", "audit", "sync-audit"):
        command_parser = subparsers.add_parser(command)
        add_project_argument(command_parser)
        command_parser.add_argument("--json", action="store_true")

    for command in ("init", "adopt"):
        command_parser = subparsers.add_parser(command)
        add_project_argument(command_parser)
        command_parser.add_argument(
            "--profile", choices=PROFILE_NAMES, default="generic-analysis"
        )
        command_parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the displayed scaffold plan.",
        )
        command_parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace conflicting control files, excluding protected adoption files.",
        )
        command_parser.add_argument(
            "--init-git",
            action="store_true",
            help="Initialize Git if the project is not already a repository.",
        )
        command_parser.add_argument("--json", action="store_true")

    close_parser = subparsers.add_parser("close")
    add_project_argument(close_parser)
    close_parser.add_argument("--summary", required=True)
    close_parser.add_argument("--completed", action="append", default=[])
    close_parser.add_argument("--evidence", action="append", default=[])
    close_parser.add_argument("--next-step", required=True)
    close_parser.add_argument("--owner", default="unassigned")
    close_parser.add_argument("--session-id")
    close_parser.add_argument("--apply", action="store_true")
    close_parser.add_argument("--overwrite", action="store_true")
    close_parser.add_argument("--json", action="store_true")

    sync_export_parser = subparsers.add_parser("sync-export")
    add_project_argument(sync_export_parser)
    sync_export_parser.add_argument("--kind", choices=SYNC_EXPORT_KINDS, required=True)
    sync_export_parser.add_argument("--title")
    sync_export_parser.add_argument("--summary")
    sync_export_parser.add_argument("--session-id")
    sync_export_parser.add_argument("--apply", action="store_true")
    sync_export_parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def project_root(path: Path) -> Path:
    return path.expanduser().resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping: {path}")
    return value


def load_profile(name: str) -> dict[str, Any]:
    profile = load_yaml(PROFILE_ROOT / name / "profile.yaml")
    if profile.get("name") != name:
        raise ValueError(f"Profile name mismatch: {name}")
    return profile


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return normalized.lower() or "research-project"


def project_identifier(name: str) -> str:
    return f"PRJ-{slug(name).upper()}"


def format_ordinal(value: int) -> str:
    if value < 0:
        raise ValueError("Ordinal must be non-negative")
    return f"{value:02d}"


def parse_numbered_title(title: str) -> tuple[int, str]:
    match = NUMBERED_TITLE_PATTERN.fullmatch(title)
    if match is None:
        raise ValueError(f"Malformed numbered Notion title: {title!r}")
    return int(match.group("ordinal")), match.group("title")


def allocate_numbered_page(
    existing_pages: list[dict[str, Any]],
    *,
    stable_id: str,
    title: str,
    minimum_ordinal: int = 1,
) -> dict[str, Any]:
    """Resolve an existing stable page or allocate an append-only ordinal.

    The Notion MCP layer supplies current direct children as mappings containing
    ``title``, ``stable_id`` and, when available, ``page_id``. Any malformed
    title, duplicate ordinal or duplicate stable ID is a hard conflict.
    """

    if minimum_ordinal < 0:
        raise ValueError("minimum_ordinal must be non-negative")
    seen_ordinals: dict[int, str] = {}
    stable_matches: list[dict[str, Any]] = []
    parsed: list[tuple[int, dict[str, Any]]] = []
    for page in existing_pages:
        page_title = page.get("title")
        if not isinstance(page_title, str):
            raise ValueError("Every Notion child must have a string title")
        ordinal, _ = parse_numbered_title(page_title)
        if ordinal in seen_ordinals:
            raise ValueError(
                f"Duplicate Notion ordinal {format_ordinal(ordinal)}: "
                f"{seen_ordinals[ordinal]!r} and {page_title!r}"
            )
        seen_ordinals[ordinal] = page_title
        parsed.append((ordinal, page))
        if page.get("stable_id") == stable_id:
            stable_matches.append(page)

    if len(stable_matches) > 1:
        raise ValueError(f"Duplicate Notion stable ID: {stable_id}")
    if stable_matches:
        ordinal, current_title = parse_numbered_title(stable_matches[0]["title"])
        return {
            "action": "reuse",
            "ordinal": ordinal,
            "numbered_title": current_title,
            "page_id": stable_matches[0].get("page_id"),
            "stable_id": stable_id,
        }

    next_ordinal = (
        max(
            [minimum_ordinal - 1, *(ordinal for ordinal, _ in parsed)],
        )
        + 1
    )
    return {
        "action": "create",
        "ordinal": next_ordinal,
        "numbered_title": f"{format_ordinal(next_ordinal)}｜{title}",
        "page_id": None,
        "stable_id": stable_id,
    }


def migrate_manifest_schema(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a non-mutating 0.3.0 view of a supported manifest."""

    version = str(manifest.get("schema_version", "0.1.0"))
    if version not in SUPPORTED_MANIFEST_SCHEMAS:
        raise ValueError(f"Unsupported manifest schema: {version}")
    migrated = json.loads(json.dumps(manifest))
    migrated["schema_version"] = MANIFEST_SCHEMA_VERSION
    notion = migrated.setdefault("notion", {})
    if not isinstance(notion, dict):
        raise ValueError("Manifest notion field must be a mapping")
    project = migrated.get("project", {})
    repository_root = Path(str(project.get("repository_root", ".")))
    default_year = date.today().year
    notion.setdefault("portfolio_year", default_year)
    notion.setdefault("portfolio_title", f"Project{notion['portfolio_year']}")
    notion.setdefault("portfolio_page_id", None)
    notion.setdefault("control_page_id", None)
    notion.setdefault("project_page_id", None)
    notion.setdefault("project_ordinal", None)
    notion.setdefault("databases", {})
    project["repository_root"] = repository_root.as_posix()
    return migrated


def render_template(content: str, replacements: dict[str, str]) -> str:
    rendered = content
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    unresolved = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", rendered)))
    if unresolved:
        raise ValueError(f"Unresolved template variables: {', '.join(unresolved)}")
    return rendered


def template_target(relative_path: Path) -> str:
    rendered = relative_path.as_posix()
    if rendered == "gitignore.tmpl":
        return ".gitignore"
    if rendered.endswith(".tmpl"):
        return rendered[: -len(".tmpl")]
    return rendered


def base_control_directories() -> set[str]:
    directories = set()
    for asset_path in BASE_ASSET_ROOT.rglob("*"):
        if not asset_path.is_file():
            continue
        target = template_target(asset_path.relative_to(BASE_ASSET_ROOT))
        parent = str(Path(target).parent)
        if parent not in {"", "."}:
            directories.add(parent)
    return directories


def directory_created_by_plan(path: str, directories: set[str]) -> bool:
    candidate = Path(path)
    return any(
        candidate == planned or candidate in planned.parents
        for planned in (Path(value) for value in directories)
    )


def bounded_project_inventory(root: Path) -> dict[str, list[str]]:
    """Return a shallow inventory without traversing data or artifact trees."""

    inventory = {category: [] for category in PROJECT_INVENTORY_PATTERNS}
    if not root.exists():
        return inventory
    for category, patterns in PROJECT_INVENTORY_PATTERNS.items():
        matches: set[str] = set()
        for pattern in patterns:
            matches.update(
                path.relative_to(root).as_posix()
                for path in root.glob(pattern)
                if path.exists()
            )
        inventory[category] = sorted(matches)
    return inventory


def inventory_markdown(inventory: dict[str, list[str]]) -> str:
    lines = []
    for category in PROJECT_INVENTORY_PATTERNS:
        paths = inventory.get(category, [])
        if paths:
            rendered = ", ".join(f"`{path}`" for path in paths)
            lines.append(f"- `{category}`: {rendered}")
    return "\n".join(lines) or "- 尚未检测到现有 project path。"


def profile_layout_markdown(root: Path, profile: dict[str, Any], mode: str) -> str:
    lines = []
    control_directories = base_control_directories()
    for path in sorted(str(value) for value in profile.get("directories", [])):
        if mode == "init":
            note = "由 `init` 创建"
        elif (root / path).exists():
            note = "现有路径，`adopt` 保留"
        elif directory_created_by_plan(path, control_directories):
            note = "作为 control layer parent 由 `adopt` 创建"
        else:
            note = "profile 建议，`adopt` 不创建"
        lines.append(f"- `{path}/`：{note}")
    return "\n".join(lines) or "- 此 profile 未声明 directory。"


def template_replacements(
    root: Path,
    profile: dict[str, Any],
    mode: str,
) -> dict[str, str]:
    project_name = root.name or "research-project"
    required_context = profile.get("required_context", [])
    required_lines = ["    - AGENTS.md", "    - CURRENT_HANDOFF.md"]
    required_lines.extend(f"    - {path}" for path in required_context)
    today = date.today()
    return {
        "PROJECT_ID": project_identifier(project_name),
        "PROJECT_NAME": slug(project_name).replace("-", "_"),
        "PROFILE": str(profile["name"]),
        "DATE": today.isoformat(),
        "DATE_COMPACT": today.strftime("%Y%m%d"),
        "PORTFOLIO_YEAR": str(today.year),
        "PORTFOLIO_TITLE": f"Project{today.year}",
        "REQUIRED_CONTEXT": "\n".join(required_lines),
        "PROJECT_INVENTORY": inventory_markdown(bounded_project_inventory(root)),
        "PROFILE_LAYOUT": profile_layout_markdown(root, profile, mode),
        "INTERPRETATION_BOUNDARY": str(profile["interpretation_boundary"]),
    }


def read_asset_files(
    root: Path,
    profile: dict[str, Any],
    mode: str,
) -> dict[str, str]:
    replacements = template_replacements(root, profile, mode)
    files: dict[str, str] = {}
    for asset_path in sorted(
        path for path in BASE_ASSET_ROOT.rglob("*") if path.is_file()
    ):
        relative = asset_path.relative_to(BASE_ASSET_ROOT)
        target = template_target(relative)
        if mode == "adopt" and target == "AGENTS.md" and (root / "AGENTS.md").exists():
            continue
        if (
            mode == "adopt"
            and target == ".gitignore"
            and (root / ".gitignore").exists()
        ):
            continue
        content = asset_path.read_text(encoding="utf-8")
        files[target] = render_template(content, replacements)
    return files


def directory_is_empty_for_init(root: Path) -> bool:
    if not root.exists():
        return True
    return not any(path.name != ".git" for path in root.iterdir())


def plan_scaffold(
    root: Path,
    profile_name: str,
    mode: str,
    overwrite: bool,
) -> dict[str, Any]:
    if mode == "init" and not directory_is_empty_for_init(root):
        raise ValueError(
            "init requires an empty directory; use adopt for an existing project"
        )
    if mode == "adopt" and not root.exists():
        raise ValueError(
            "adopt requires an existing project directory; use init instead"
        )

    profile = load_profile(profile_name)
    files = read_asset_files(root, profile, mode)
    actions: list[FileAction] = []
    profile_directories = sorted(str(path) for path in profile.get("directories", []))
    control_directories = {
        str(Path(path).parent)
        for path in files
        if str(Path(path).parent) not in {"", "."}
    }
    directories = sorted(
        control_directories | (set(profile_directories) if mode == "init" else set())
    )
    profile_directory_recommendations = (
        [
            path
            for path in profile_directories
            if not (root / path).exists()
            and not directory_created_by_plan(path, control_directories)
        ]
        if mode == "adopt"
        else []
    )
    for relative_path, content in sorted(files.items()):
        target = root / relative_path
        if not target.exists():
            actions.append(FileAction(relative_path, "create", content))
            continue
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            actions.append(
                FileAction(relative_path, "unchanged", reason="content matches")
            )
            continue
        if mode == "adopt" and relative_path in PROTECTED_ADOPTION_PATHS:
            actions.append(
                FileAction(relative_path, "skip", reason="protected during adopt")
            )
            continue
        if overwrite:
            actions.append(FileAction(relative_path, "overwrite", content))
        else:
            actions.append(
                FileAction(relative_path, "skip", reason="existing content differs")
            )

    return {
        "mode": mode,
        "project": str(root),
        "profile": profile_name,
        "directories": directories,
        "profile_directories": profile_directories,
        "profile_directory_recommendations": profile_directory_recommendations,
        "actions": actions,
    }


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def git_command(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def initialize_git(root: Path) -> dict[str, Any]:
    if (root / ".git").exists():
        return {"initialized": False, "reason": "already a Git repository"}
    result = subprocess.run(
        ["git", "init", "-b", "chore/adopt-research-project-os", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "git init failed")
    return {"initialized": True, "output": result.stdout.strip()}


def apply_scaffold(plan: dict[str, Any], init_git: bool) -> dict[str, Any]:
    root = Path(plan["project"])
    root.mkdir(parents=True, exist_ok=True)
    for relative in plan["directories"]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for action in plan["actions"]:
        if action.action not in {"create", "overwrite"}:
            continue
        if action.content is None:
            raise ValueError(f"Missing content for {action.path}")
        atomic_write(root / action.path, action.content)
        written.append(action.path)
    git_result = (
        initialize_git(root)
        if init_git
        else {"initialized": False, "reason": "not requested"}
    )
    return {"written": written, "git": git_result}


def git_status(root: Path) -> dict[str, Any]:
    result = git_command(root, "status", "--short", "--branch")
    return {
        "available": result.returncode == 0,
        "output": result.stdout.strip(),
        "error": result.stderr.strip(),
    }


def visible_git_files(root: Path) -> list[str]:
    result = git_command(
        root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    )
    if result.returncode != 0:
        return []
    return sorted(path for path in result.stdout.split("\0") if path)


def toml_tables(path: Path) -> list[dict[str, Any]]:
    """Return table headers without requiring a TOML 1.1 parser."""

    content = path.read_text(encoding="utf-8")
    tables = []
    for match in TOML_TABLE_PATTERN.finditer(content):
        tables.append(
            {
                "name": match.group("table").strip(),
                "line": content.count("\n", 0, match.start()) + 1,
            }
        )
    return tables


def classify_pixi_manifest(path: Path) -> dict[str, Any]:
    """Classify workspace, package-only, non-Pixi, or unknown manifests."""

    tables = toml_tables(path)
    names = [table["name"] for table in tables]
    workspace_names = {"workspace", "tool.pixi.workspace"}
    workspace = [table for table in tables if table["name"] in workspace_names]
    package = [
        table
        for table in tables
        if table["name"] == "package"
        or table["name"].startswith("package.")
        or table["name"] == "tool.pixi.package"
        or table["name"].startswith("tool.pixi.package.")
    ]
    pixi_tables = [
        table
        for table in tables
        if table["name"] == "tool.pixi" or table["name"].startswith("tool.pixi.")
    ]
    if workspace:
        kind = "workspace"
        evidence = workspace
    elif package:
        kind = "package"
        evidence = package
    elif path.name == "pyproject.toml" and not pixi_tables:
        kind = "non-pixi"
        evidence = []
    else:
        kind = "unknown"
        evidence = tables
    return {
        "path": path,
        "kind": kind,
        "tables": names,
        "evidence": evidence,
    }


def effective_pixi_policy(manifest: dict[str, Any] | None) -> dict[str, Any]:
    policy = dict(DEFAULT_PIXI_POLICY)
    source = "default"
    issues: list[dict[str, str]] = []
    if manifest is None:
        return {**policy, "source": source, "issues": issues}
    governance = manifest.get("governance")
    pixi = governance.get("pixi") if isinstance(governance, dict) else None
    if pixi is None:
        return {**policy, "source": source, "issues": issues}
    source = "project_manifest.yaml"
    if not isinstance(pixi, dict):
        issues.append(
            pixi_issue(
                "invalid_pixi_policy",
                "project_manifest.yaml",
                "governance.pixi must be a mapping",
                "Use policy: root_workspace and a boolean allow_nested_package_manifests.",
            )
        )
        return {**policy, "source": source, "issues": issues}
    configured_policy = pixi.get("policy", policy["policy"])
    if configured_policy != "root_workspace":
        issues.append(
            pixi_issue(
                "invalid_pixi_policy",
                "project_manifest.yaml",
                f"unsupported governance.pixi.policy={configured_policy!r}",
                "Set governance.pixi.policy to root_workspace.",
            )
        )
    else:
        policy["policy"] = configured_policy
    allow_packages = pixi.get(
        "allow_nested_package_manifests",
        policy["allow_nested_package_manifests"],
    )
    if not isinstance(allow_packages, bool):
        issues.append(
            pixi_issue(
                "invalid_pixi_policy",
                "project_manifest.yaml",
                "governance.pixi.allow_nested_package_manifests must be boolean",
                "Set the value to true or false.",
            )
        )
    else:
        policy["allow_nested_package_manifests"] = allow_packages
    return {**policy, "source": source, "issues": issues}


def pixi_issue(
    code: str,
    path: str,
    evidence: str,
    recommendation: str,
    *,
    severity: str = "error",
) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def bounded_pixi_candidates(root: Path) -> dict[str, Any]:
    """Find Pixi paths without following links or walking artifact trees."""

    paths: set[str] = set()
    entries_seen = 0
    truncated = False
    if root.exists():
        stack = [(root, 0)]
        while stack and not truncated:
            directory, depth = stack.pop()
            try:
                children = sorted(directory.iterdir(), key=lambda path: path.name)
            except OSError:
                continue
            for child in children:
                entries_seen += 1
                if entries_seen > PIXI_SCAN_MAX_ENTRIES:
                    truncated = True
                    break
                relative = child.relative_to(root).as_posix()
                if child.is_symlink():
                    continue
                if child.is_dir():
                    if child.name == ".pixi":
                        paths.add(relative)
                        continue
                    if (
                        child.name in PIXI_SCAN_PRUNE_NAMES
                        or depth >= PIXI_SCAN_MAX_DEPTH
                    ):
                        continue
                    stack.append((child, depth + 1))
                elif child.name in {"pixi.toml", "pixi.lock", "pyproject.toml"}:
                    paths.add(relative)

    for relative in visible_git_files(root):
        path = Path(relative)
        if path.name in {"pixi.toml", "pixi.lock", "pyproject.toml"}:
            paths.add(path.as_posix())
        if ".pixi" in path.parts:
            index = path.parts.index(".pixi")
            paths.add(Path(*path.parts[: index + 1]).as_posix())
    return {
        "paths": sorted(paths),
        "truncated": truncated,
        "max_depth": PIXI_SCAN_MAX_DEPTH,
        "max_entries": PIXI_SCAN_MAX_ENTRIES,
    }


def git_path_tracked(root: Path, relative: str) -> bool | None:
    result = git_command(root, "rev-parse", "--is-inside-work-tree")
    if result.returncode != 0:
        return None
    tracked = git_command(root, "ls-files", "--error-unmatch", "--", relative)
    return tracked.returncode == 0


def git_path_ignored(root: Path, relative: str) -> bool | None:
    result = git_command(root, "rev-parse", "--is-inside-work-tree")
    if result.returncode != 0:
        return None
    ignored = git_command(root, "check-ignore", "--quiet", "--", relative)
    return ignored.returncode == 0


def tracked_under(root: Path, relative: str) -> list[str] | None:
    result = git_command(root, "rev-parse", "--is-inside-work-tree")
    if result.returncode != 0:
        return None
    tracked = git_command(root, "ls-files", "-z", "--", relative)
    if tracked.returncode != 0:
        return []
    return sorted(path for path in tracked.stdout.split("\0") if path)


def format_manifest_evidence(classification: dict[str, Any]) -> str:
    matches = classification["evidence"]
    if not matches:
        return "no Pixi workspace or package table found"
    return ", ".join(f"[{item['name']}] at line {item['line']}" for item in matches)


def inspect_pixi_policy(
    root: Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect root_workspace policy without changing or solving environments."""

    configured = effective_pixi_policy(manifest)
    issues = list(configured.pop("issues"))
    scan = bounded_pixi_candidates(root)
    root_classifications: list[dict[str, Any]] = []
    nested_classifications: list[dict[str, Any]] = []
    nested_locks: list[str] = []
    nested_environments: list[str] = []

    for relative in scan["paths"]:
        path = root / relative
        if relative == ".pixi":
            continue
        if path.name == "pixi.lock":
            if path.parent != root:
                nested_locks.append(relative)
            continue
        if path.name not in {"pixi.toml", "pyproject.toml"} or not path.is_file():
            if path.name == ".pixi" and path.parent != root:
                nested_environments.append(relative)
            continue
        try:
            classification = classify_pixi_manifest(path)
        except (OSError, UnicodeError) as error:
            if path.name == "pixi.toml":
                issues.append(
                    pixi_issue(
                        "unreadable_pixi_manifest",
                        relative,
                        str(error),
                        "Make the manifest readable, then rerun inspect.",
                    )
                )
            continue
        classification["relative_path"] = relative
        if classification["kind"] == "non-pixi":
            continue
        if path.parent == root:
            root_classifications.append(classification)
        else:
            nested_classifications.append(classification)

    for relative in scan["paths"]:
        path = root / relative
        if path.name == ".pixi" and path.parent != root:
            nested_environments.append(relative)

    root_workspaces = [
        item for item in root_classifications if item["kind"] == "workspace"
    ]
    if len(root_workspaces) > 1:
        issues.append(
            pixi_issue(
                "multiple_root_workspace_manifests",
                ".",
                "workspace manifests: "
                + ", ".join(item["relative_path"] for item in root_workspaces),
                "Keep exactly one root pixi.toml or Pixi-enabled pyproject.toml.",
            )
        )
    for item in root_classifications:
        if item["kind"] != "workspace":
            issues.append(
                pixi_issue(
                    "root_manifest_not_workspace",
                    item["relative_path"],
                    format_manifest_evidence(item),
                    "Define the single root workspace here or remove the Pixi manifest.",
                )
            )

    uses_pixi = bool(
        root_classifications
        or nested_classifications
        or nested_locks
        or nested_environments
        or (root / "pixi.lock").exists()
        or (root / ".pixi").exists()
    )
    if uses_pixi and not root_workspaces and not root_classifications:
        issues.append(
            pixi_issue(
                "missing_root_workspace_manifest",
                ".",
                "Pixi artifacts exist but no root workspace manifest was found",
                "Create one root pixi.toml or a pyproject.toml with [tool.pixi.workspace].",
            )
        )

    migration = (
        "Consolidate dependencies by compatibility and reproducibility boundary into root "
        "features/environments; use <component>:<task> and task.cwd; regenerate pixi.lock "
        "at the root; validate before manually removing nested environment files."
    )
    for item in nested_classifications:
        relative = item["relative_path"]
        if item["kind"] == "workspace":
            issues.append(
                pixi_issue(
                    "nested_workspace_manifest",
                    relative,
                    format_manifest_evidence(item),
                    migration,
                )
            )
        elif item["kind"] == "package":
            if not configured["allow_nested_package_manifests"]:
                issues.append(
                    pixi_issue(
                        "nested_package_manifest_disallowed",
                        relative,
                        format_manifest_evidence(item),
                        "Enable allow_nested_package_manifests or move package metadata "
                        "into the root workspace.",
                    )
                )
        else:
            issues.append(
                pixi_issue(
                    "unknown_nested_pixi_manifest",
                    relative,
                    format_manifest_evidence(item),
                    migration,
                )
            )
    for relative in sorted(set(nested_locks)):
        issues.append(
            pixi_issue(
                "nested_pixi_lock",
                relative,
                "pixi.lock is outside the project root",
                migration,
            )
        )
    for relative in sorted(set(nested_environments)):
        issues.append(
            pixi_issue(
                "nested_pixi_environment",
                relative,
                ".pixi directory is outside the project root",
                migration,
            )
        )

    root_lock = root / "pixi.lock"
    root_lock_tracked = (
        git_path_tracked(root, "pixi.lock") if root_lock.exists() else False
    )
    root_lock_ignored = (
        git_path_ignored(root, "pixi.lock") if root_lock.exists() else False
    )
    if root_workspaces:
        if not root_lock.exists():
            issues.append(
                pixi_issue(
                    "missing_root_pixi_lock",
                    "pixi.lock",
                    "root workspace has no pixi.lock",
                    "Run pixi lock at the root and commit pixi.lock.",
                )
            )
        elif root_lock_tracked is not True or root_lock_ignored is True:
            state = (
                "Git unavailable"
                if root_lock_tracked is None
                else f"tracked={root_lock_tracked}, ignored={root_lock_ignored}"
            )
            issues.append(
                pixi_issue(
                    "root_pixi_lock_untracked",
                    "pixi.lock",
                    state,
                    "Remove ignore rules, add pixi.lock to Git, and commit it.",
                )
            )

    root_environment = root / ".pixi"
    root_environment_ignored = (
        git_path_ignored(root, ".pixi") if root_environment.exists() else None
    )
    root_environment_tracked = (
        tracked_under(root, ".pixi") if root_environment.exists() else []
    )
    if root_environment.exists():
        if root_environment_ignored is not True:
            issues.append(
                pixi_issue(
                    "root_pixi_environment_not_ignored",
                    ".pixi",
                    (
                        "Git unavailable"
                        if root_environment_ignored is None
                        else "root .pixi is not ignored"
                    ),
                    "Add /.pixi/ to the root .gitignore.",
                )
            )
        if root_environment_tracked:
            issues.append(
                pixi_issue(
                    "tracked_root_pixi_environment",
                    ".pixi",
                    "tracked files: " + ", ".join(root_environment_tracked),
                    "Remove .pixi contents from Git while preserving the local environment.",
                )
            )

    if scan["truncated"]:
        issues.append(
            pixi_issue(
                "pixi_scan_truncated",
                ".",
                f"scan exceeded {scan['max_entries']} entries",
                "Review pruned paths manually or reduce the project scan surface.",
                severity="warning",
            )
        )

    return {
        **configured,
        "uses_pixi": uses_pixi,
        "root_manifest": (
            root_workspaces[0]["relative_path"] if len(root_workspaces) == 1 else None
        ),
        "root_workspace_manifests": [item["relative_path"] for item in root_workspaces],
        "root_lock": {
            "present": root_lock.exists(),
            "tracked": root_lock_tracked,
            "ignored": root_lock_ignored,
        },
        "root_environment": {
            "present": root_environment.exists(),
            "ignored": root_environment_ignored,
            "tracked_files": root_environment_tracked,
        },
        "scan": {
            "truncated": scan["truncated"],
            "max_depth": scan["max_depth"],
            "max_entries": scan["max_entries"],
        },
        "issues": issues,
    }


def inspect_project(root: Path) -> dict[str, Any]:
    exists = root.exists()
    entries = [] if not exists else sorted(path.name for path in root.iterdir())
    manifest_path = root / "project_manifest.yaml"
    manifest = load_yaml(manifest_path) if manifest_path.is_file() else None
    recommendation = "init" if directory_is_empty_for_init(root) else "adopt"
    if manifest is not None:
        recommendation = "start"
    return {
        "project": str(root),
        "exists": exists,
        "entries": entries,
        "recommended_mode": recommendation,
        "governed": manifest is not None and (root / "CURRENT_HANDOFF.md").is_file(),
        "profile": manifest.get("project", {}).get("profile") if manifest else None,
        "project_inventory": bounded_project_inventory(root),
        "pixi_policy": inspect_pixi_policy(root, manifest),
        "control_paths": {
            path: (root / path).exists() for path in REQUIRED_CONTROL_PATHS
        },
        "git": git_status(root),
    }


def markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body").strip() if match else ""


def checkpoint_value(text: str, label: str) -> str | None:
    checkpoint = markdown_section(text, "Checkpoint")
    match = re.search(
        rf"^- {re.escape(label)}:\s*(.+?)\s*$", checkpoint, flags=re.MULTILINE
    )
    return match.group(1).strip().strip("`") if match else None


def audit_project(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = root / "project_manifest.yaml"
    manifest = load_yaml(manifest_path) if manifest_path.is_file() else None
    pixi_policy = inspect_pixi_policy(root, manifest)
    for issue in pixi_policy["issues"]:
        message = (
            f"[{issue['code']}] {issue['path']}: {issue['evidence']} "
            f"Recommendation: {issue['recommendation']}"
        )
        (errors if issue["severity"] == "error" else warnings).append(message)
    missing_controls = []
    for relative in REQUIRED_CONTROL_PATHS:
        if not (root / relative).exists():
            missing_controls.append(f"Missing required control path: {relative}")
    errors.extend(missing_controls)
    if missing_controls:
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "pixi_policy": pixi_policy,
        }

    if manifest is None:
        raise AssertionError("Required manifest disappeared during audit")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"Manifest schema must be {MANIFEST_SCHEMA_VERSION}; found "
            f"{manifest.get('schema_version')!r}"
        )
    project = manifest.get("project")
    if not isinstance(project, dict):
        errors.append("Manifest must contain a project mapping")
    elif project.get("profile") not in PROFILE_NAMES:
        errors.append(f"Unknown project profile: {project.get('profile')!r}")

    notion = manifest.get("notion")
    if not isinstance(notion, dict):
        errors.append("Manifest must contain a notion mapping")
    else:
        year = notion.get("portfolio_year")
        if not isinstance(year, int):
            errors.append("notion.portfolio_year must be an integer")
        elif notion.get("portfolio_title") != f"Project{year}":
            errors.append("notion.portfolio_title must equal Project{portfolio_year}")
        ordinal = notion.get("project_ordinal")
        if ordinal is not None and (not isinstance(ordinal, int) or ordinal < 1):
            errors.append("notion.project_ordinal must be null or an integer >= 1")

    handoff = (root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8")
    for section in HANDOFF_SECTIONS:
        if not markdown_section(handoff, section):
            errors.append(f"Missing or empty handoff section: {section}")
    session_id = checkpoint_value(handoff, "Session")
    if session_id is None or not SESSION_PATTERN.fullmatch(session_id):
        errors.append(f"Invalid session ID: {session_id!r}")

    evidence = load_yaml(root / "reports/evidence_registry.yaml").get("evidence")
    if not isinstance(evidence, list):
        errors.append("Evidence registry must contain an evidence list")

    visible_sensitive = [
        path
        for path in visible_git_files(root)
        if any(pattern.search(path) for pattern in SENSITIVE_PATTERNS)
    ]
    errors.extend(
        f"Sensitive or large file is visible to Git: {path}"
        for path in visible_sensitive
    )

    git = git_status(root)
    if not git["available"]:
        warnings.append(
            "Git is unavailable; initialize it before creating an evidence baseline"
        )
    elif "No commits yet" in git["output"]:
        warnings.append("Git has no baseline commit")

    sync_audit = audit_sync_queue(root)
    errors.extend(sync_audit["errors"])
    pending = sync_audit["counts"]["pending"]
    if pending:
        warnings.append(f"{pending} Notion payload(s) await human review")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "profile": project.get("profile") if isinstance(project, dict) else None,
        "pending_sync": pending,
        "pixi_policy": pixi_policy,
    }


def next_session_id(root: Path, current: str) -> str:
    prefix = f"SES-{date.today():%Y%m%d}-"
    values: list[int] = []
    if current.startswith(prefix):
        values.append(int(current.rsplit("-", maxsplit=1)[1]))
    for path in (root / "docs/handoffs/archive").glob(f"{prefix}*.md"):
        if SESSION_PATTERN.fullmatch(path.stem):
            values.append(int(path.stem.rsplit("-", maxsplit=1)[1]))
    return f"{prefix}{max(values, default=0) + 1:03d}"


def bullet_lines(values: list[str], fallback: str) -> str:
    cleaned = [value.strip() for value in values if value.strip()]
    return "\n".join(f"- {value}" for value in cleaned) if cleaned else f"- {fallback}"


def build_handoff(
    manifest: dict[str, Any],
    previous: str,
    session_id: str,
    summary: str,
    completed: list[str],
    evidence: list[str],
    next_step: str,
    owner: str,
) -> str:
    stage = manifest.get("project", {}).get("current_stage", "unknown")
    analysis_status = manifest.get("analysis", {}).get("status", "exploratory")
    decisions = (
        markdown_section(previous, "Confirmed decisions") or "- 尚未记录 decision。"
    )
    questions = (
        markdown_section(previous, "Open questions") or "- 尚未记录 open question。"
    )
    boundary = (
        markdown_section(previous, "Blockers and interpretation boundary")
        or "- 尚未记录 blocker 或 interpretation boundary。"
    )
    return f"""# Current Handoff

## Checkpoint

- Session: `{session_id}`
- Updated: {date.today().isoformat()}
- Project stage: `{stage}`
- Analysis status: `{analysis_status}`
- Owner: {owner}

## Current objective

{summary}

## Completed

{bullet_lines(completed, summary)}

## Confirmed decisions

{decisions}

## Evidence and outputs

{bullet_lines(evidence, "本次 session 未登记新的 evidence。")}

## Open questions

{questions}

## Blockers and interpretation boundary

{boundary}

## Next minimum action

{next_step}

## Resume commands

```bash
python /path/to/research_project_os.py start --project .
python /path/to/research_project_os.py audit --project .
```
"""


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def git_commit(root: Path) -> str | None:
    result = git_command(root, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def source_hashes(
    root: Path,
    *,
    handoff_override: str | None = None,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for relative in ("project_manifest.yaml", "CURRENT_HANDOFF.md"):
        path = root / relative
        if relative == "CURRENT_HANDOFF.md" and handoff_override is not None:
            values[relative] = sha256_text(handoff_override)
        elif path.is_file():
            values[relative] = sha256_text(path.read_text(encoding="utf-8"))
    return values


def state_fingerprint(hashes: dict[str, str]) -> str:
    canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def compact_title(value: str, limit: int = 88) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        raise ValueError("Notion output title must not be empty")
    return (
        normalized
        if len(normalized) <= limit
        else normalized[: limit - 1].rstrip() + "…"
    )


def build_sync_payload(
    root: Path,
    manifest: dict[str, Any],
    *,
    output_kind: str,
    title: str | None,
    summary: str,
    session_id: str | None,
    generated_at: datetime | None = None,
    handoff_override: str | None = None,
) -> dict[str, Any]:
    if output_kind not in OUTPUT_KINDS:
        raise ValueError(f"Unsupported output kind: {output_kind}")
    normalized = migrate_manifest_schema(manifest)
    project = normalized.get("project", {})
    notion = normalized["notion"]
    project_id = project.get("id")
    project_name = project.get("name")
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("Manifest project.id must be a non-empty string")
    if not isinstance(project_name, str) or not project_name:
        raise ValueError("Manifest project.name must be a non-empty string")
    if session_id is not None and not SESSION_PATTERN.fullmatch(session_id):
        raise ValueError("Session ID must match SES-YYYYMMDD-NNN")

    hashes = source_hashes(root, handoff_override=handoff_override)
    fingerprint = state_fingerprint(hashes)
    if output_kind == "project-adopt":
        output_title = compact_title(title or "项目纳入与治理基线")
        output_id = f"ADOPT-{project_id}"
    elif output_kind == "session-close":
        if session_id is None:
            raise ValueError("session-close requires a session ID")
        output_title = compact_title(title or f"{session_id}：{summary}")
        output_id = session_id
    elif output_kind == "milestone":
        if title is None:
            raise ValueError("milestone requires --title")
        output_title = compact_title(title)
        output_id = f"REPORT-{slug(output_title).upper()}-{fingerprint[:12].upper()}"
    else:
        output_title = compact_title(title or "项目完整治理状态")
        output_id = f"FULL-{project_id}-{session_id or fingerprint[:12].upper()}"

    portfolio_year = int(notion["portfolio_year"])
    portfolio_title = str(notion.get("portfolio_title") or f"Project{portfolio_year}")
    project_ordinal = notion.get("project_ordinal")
    if project_ordinal is not None:
        project_ordinal = int(project_ordinal)
        if project_ordinal < 1:
            raise ValueError("notion.project_ordinal must be at least 1")
    project_title = (
        f"{format_ordinal(project_ordinal)}｜{project_name}"
        if project_ordinal is not None
        else project_name
    )
    timestamp = generated_at or datetime.now(timezone.utc)
    payload_id = f"SYNC-{output_id}-{output_kind}-{fingerprint[:12]}"
    stable_metadata = {
        "portfolio_id": f"PORTFOLIO-{portfolio_year}",
        "project_id": project_id,
        "output_id": output_id,
        "output_kind": output_kind,
        "session_id": session_id,
        "git_commit": git_commit(root),
        "source_fingerprint": fingerprint,
    }
    notion_target = {
        "portfolio": {
            "stable_id": f"PORTFOLIO-{portfolio_year}",
            "year": portfolio_year,
            "title": portfolio_title,
            "page_id": notion.get("portfolio_page_id"),
        },
        "control": {
            "stable_id": f"CONTROL-{portfolio_year}",
            "title": "00｜Research OS Control",
            "page_id": notion.get("control_page_id"),
        },
        "project": {
            "stable_id": project_id,
            "title": project_title,
            "unprefixed_title": project_name,
            "page_id": notion.get("project_page_id"),
            "ordinal": project_ordinal,
        },
        "output": {
            "stable_id": output_id,
            "kind": output_kind,
            "title": output_title,
            "page_id": None,
            "ordinal": None,
            "metadata": stable_metadata,
        },
        "allocation_policy": {
            "strategy": "append_only_max_plus_one",
            "minimum_width": 2,
            "reserved_project_ordinals": [0],
            "reuse_deleted_ordinals": False,
            "renumber_existing_pages": False,
            "conflict_policy": "stop_for_human_review",
        },
    }
    return {
        "schema_version": SYNC_PAYLOAD_SCHEMA_VERSION,
        "payload_id": payload_id,
        "payload_kind": output_kind,
        "generated_at_utc": timestamp.isoformat(),
        "mode": "review_before_apply",
        "base": {
            "git_commit": stable_metadata["git_commit"],
            "source_hashes": hashes,
            "working_state_sha256": fingerprint,
        },
        "project": {
            "id": project_id,
            "name": project_name,
            "status": project.get("status"),
            "stage": project.get("current_stage"),
        },
        "session": {
            "id": session_id,
            "summary": summary,
        },
        "notion_target": notion_target,
        "operations": [
            {
                "operation": "ensure_page",
                "object_type": "portfolio",
                **notion_target["portfolio"],
            },
            {
                "operation": "ensure_page",
                "object_type": "control",
                **notion_target["control"],
            },
            {
                "operation": "ensure_numbered_page",
                "object_type": "project",
                **notion_target["project"],
            },
            {
                "operation": "ensure_numbered_page",
                "object_type": "output",
                **notion_target["output"],
            },
        ],
        "authority": {
            "git": "完整 handoff、code、environment、reports 和 evidence details",
            "notion": "cross-project navigation、task priority 与 human approval",
        },
        "conflict_policy": "stop_and_move_to_conflicts",
    }


def pending_payload_path(root: Path, payload: dict[str, Any]) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(payload["payload_id"]))
    return root / "work/notion_sync/pending" / f"{safe_id}.json"


def write_pending_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path = pending_payload_path(root, payload)
    content = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"Refusing to replace immutable payload: {path}")
        return {
            "written": False,
            "reason": "identical payload already pending",
            "path": str(path),
        }
    atomic_write(path, content)
    return {"written": True, "path": str(path)}


def build_application_receipt(
    payload: dict[str, Any],
    *,
    page_ids: dict[str, str],
    assigned_ordinals: dict[str, int],
    read_back: dict[str, Any],
    applied_at: datetime | None = None,
) -> dict[str, Any]:
    required_pages = {"portfolio", "control", "project", "output"}
    if set(page_ids) != required_pages:
        raise ValueError("Application receipt must contain all page IDs")
    if set(assigned_ordinals) != {"project", "output"}:
        raise ValueError("Application receipt must contain project and output ordinals")
    if any(not value for value in page_ids.values()):
        raise ValueError("Application receipt page IDs must be non-empty")
    timestamp = applied_at or datetime.now(timezone.utc)
    return {
        "payload_id": payload.get("payload_id"),
        "applied_at_utc": timestamp.isoformat(),
        "page_ids": page_ids,
        "assigned_ordinals": assigned_ordinals,
        "read_back": read_back,
    }


def finalize_application(
    root: Path,
    payload_id: str,
    *,
    page_ids: dict[str, str],
    assigned_ordinals: dict[str, int],
    read_back: dict[str, Any],
    applied_at: datetime | None = None,
) -> dict[str, Any]:
    """Move an immutable pending payload to applied with a read-back receipt."""

    pending = root / "work/notion_sync/pending" / f"{payload_id}.json"
    applied = root / "work/notion_sync/applied" / f"{payload_id}.json"
    if not pending.is_file():
        raise FileNotFoundError(f"Pending payload not found: {pending}")
    if applied.exists():
        raise FileExistsError(f"Applied payload already exists: {applied}")
    payload = json.loads(pending.read_text(encoding="utf-8"))
    receipt = build_application_receipt(
        payload,
        page_ids=page_ids,
        assigned_ordinals=assigned_ordinals,
        read_back=read_back,
        applied_at=applied_at,
    )
    applied_payload = {**payload, "application": receipt}
    atomic_write(
        applied,
        json.dumps(applied_payload, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
    )
    pending.unlink()
    return {"pending": str(pending), "applied": str(applied), "receipt": receipt}


def audit_sync_queue(root: Path) -> dict[str, Any]:
    queue = root / "work/notion_sync"
    errors: list[str] = []
    stale: list[str] = []
    counts: dict[str, int] = {}
    for state in ("pending", "applied", "conflicts", "superseded"):
        paths = sorted((queue / state).glob("*.json"))
        counts[state] = len(paths)
        for path in paths:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as error:
                errors.append(f"{path}: invalid JSON: {error}")
                continue
            if payload.get(
                "schema_version"
            ) != SYNC_PAYLOAD_SCHEMA_VERSION and state in {"pending", "applied"}:
                errors.append(f"{path}: unsupported active payload schema")
                continue
            if state == "pending":
                expected = payload.get("base", {}).get("source_hashes")
                if not isinstance(expected, dict):
                    errors.append(f"{path}: missing source hashes")
                    continue
                current = source_hashes(root)
                comparable = {key: current.get(key) for key in expected}
                if comparable != expected:
                    stale.append(str(payload.get("payload_id") or path.stem))
            if state == "applied":
                receipt = payload.get("application")
                if not isinstance(receipt, dict) or not receipt.get("read_back"):
                    errors.append(f"{path}: applied payload lacks read-back receipt")
    errors.extend(f"Stale pending payload: {payload_id}" for payload_id in stale)
    return {
        "ok": not errors,
        "errors": errors,
        "stale_payloads": stale,
        "counts": counts,
    }


def export_sync_payload(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_yaml(root / "project_manifest.yaml")
    handoff = (root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8")
    session_id = args.session_id or checkpoint_value(handoff, "Session")
    summary = args.summary or markdown_section(handoff, "Current objective")
    payload = build_sync_payload(
        root,
        manifest,
        output_kind=args.kind,
        title=args.title,
        summary=summary,
        session_id=session_id,
    )
    result = {
        "written": False,
        "payload_path": str(pending_payload_path(root, payload).relative_to(root)),
        "payload": payload,
    }
    if args.apply:
        write_result = write_pending_payload(root, payload)
        result["written"] = write_result["written"]
        result["write_result"] = write_result
    return result


def close_session(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_yaml(root / "project_manifest.yaml")
    previous = (root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8")
    previous_session = checkpoint_value(previous, "Session")
    if previous_session is None or not SESSION_PATTERN.fullmatch(previous_session):
        raise ValueError("CURRENT_HANDOFF.md has an invalid session ID")
    session_id = args.session_id or next_session_id(root, previous_session)
    if not SESSION_PATTERN.fullmatch(session_id):
        raise ValueError("Session ID must match SES-YYYYMMDD-NNN")

    handoff = build_handoff(
        manifest,
        previous,
        session_id,
        args.summary,
        args.completed,
        args.evidence,
        args.next_step,
        args.owner,
    )
    payload = build_sync_payload(
        root,
        manifest,
        output_kind="session-close",
        title=None,
        summary=args.summary,
        session_id=session_id,
        handoff_override=handoff,
    )
    payload["session"].update(
        {
            "completed": args.completed,
            "evidence": args.evidence,
            "next_step": args.next_step,
        }
    )
    archive_path = root / f"docs/handoffs/archive/{previous_session}.md"
    payload_path = pending_payload_path(root, payload)
    result = {
        "written": False,
        "previous_session": previous_session,
        "new_session": session_id,
        "archive_path": str(archive_path.relative_to(root)),
        "handoff_path": "CURRENT_HANDOFF.md",
        "payload_path": str(payload_path.relative_to(root)),
        "handoff_preview": handoff,
        "payload": payload,
    }
    if not args.apply:
        return result
    if archive_path.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {archive_path}; pass --overwrite")
    atomic_write(archive_path, previous)
    atomic_write(root / "CURRENT_HANDOFF.md", handoff)
    write_pending_payload(root, payload)
    result["written"] = True
    return result


def plan_to_dict(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: value for key, value in plan.items() if key != "actions"},
        "actions": [
            {
                "path": action.path,
                "action": action.action,
                "reason": action.reason,
            }
            for action in plan["actions"]
        ],
    }


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def print_plan(plan: dict[str, Any], applied: dict[str, Any] | None = None) -> None:
    print(f"{plan['mode']} project={plan['project']} profile={plan['profile']}")
    for action in plan["actions"]:
        suffix = f" ({action.reason})" if action.reason else ""
        print(f"  {action.action:9} {action.path}{suffix}")
    recommendations = plan["profile_directory_recommendations"]
    if recommendations:
        print("Profile directory recommendations (not created by adopt):")
        for path in recommendations:
            print(f"  recommend {path}/")
    if applied is None:
        print("Dry-run only; pass --apply to write.")
    else:
        print(f"Written files: {len(applied['written'])}")
        print(f"Git initialized: {applied['git']['initialized']}")


def print_inspection(value: dict[str, Any]) -> None:
    print(f"Project: {value['project']}")
    print(f"Recommended mode: {value['recommended_mode']}")
    print(f"Governed: {value['governed']}")
    print(f"Profile: {value['profile']}")
    print("Project inventory (bounded):")
    populated = False
    for category, paths in value["project_inventory"].items():
        if paths:
            populated = True
            print(f"  {category}: {', '.join(paths)}")
    if not populated:
        print("  none")
    pixi = value["pixi_policy"]
    print(
        "Pixi policy: "
        f"{pixi['policy']} ({pixi['source']}), "
        f"root={pixi['root_manifest'] or 'none'}"
    )
    for issue in pixi["issues"]:
        print(
            f"  {issue['severity'].upper()} [{issue['code']}] "
            f"{issue['path']}: {issue['evidence']}"
        )
    print("Control paths:")
    for path, present in value["control_paths"].items():
        print(f"  [{'ok' if present else 'missing'}] {path}")
    print("Git:")
    print(value["git"]["output"] or value["git"]["error"] or "unavailable")


def print_audit(value: dict[str, Any]) -> None:
    print(f"Research Project OS audit: {'PASS' if value['ok'] else 'FAIL'}")
    for warning in value["warnings"]:
        print(f"WARNING {warning}")
    for error in value["errors"]:
        print(f"ERROR {error}")


def print_start(root: Path, inspection: dict[str, Any]) -> None:
    print_inspection(inspection)
    print("\nCurrent handoff:\n")
    print((root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8").rstrip())


def print_close(value: dict[str, Any]) -> None:
    mode = "wrote" if value["written"] else "dry-run"
    print(f"Session close {mode}: {value['previous_session']} → {value['new_session']}")
    print(f"Archive: {value['archive_path']}")
    print(f"Handoff: {value['handoff_path']}")
    print(f"Notion payload: {value['payload_path']}")
    if not value["written"]:
        print("\nHandoff preview:\n")
        print(value["handoff_preview"].rstrip())


def print_sync_export(value: dict[str, Any]) -> None:
    mode = "wrote" if value["written"] else "dry-run"
    target = value["payload"]["notion_target"]
    print(f"Notion sync export {mode}: {value['payload']['payload_kind']}")
    print(f"Portfolio: {target['portfolio']['title']}")
    print(f"Project: {target['project']['title']}")
    print(f"Output: {target['output']['title']}")
    print(f"Payload: {value['payload_path']}")


def print_sync_audit(value: dict[str, Any]) -> None:
    print(f"Notion sync audit: {'PASS' if value['ok'] else 'FAIL'}")
    for state, count in value["counts"].items():
        print(f"  {state}: {count}")
    for error in value["errors"]:
        print(f"ERROR {error}")


def main() -> None:
    args = parse_args()
    logger = configure_logging()
    root = project_root(args.project)
    try:
        if args.command == "inspect":
            value = inspect_project(root)
            print_json(value) if args.json else print_inspection(value)
            return
        if args.command in {"init", "adopt"}:
            plan = plan_scaffold(root, args.profile, args.command, args.overwrite)
            applied = apply_scaffold(plan, args.init_git) if args.apply else None
            if args.json:
                print_json({"plan": plan_to_dict(plan), "applied": applied})
            else:
                print_plan(plan, applied)
            return
        if args.command == "audit":
            value = audit_project(root)
            print_json(value) if args.json else print_audit(value)
            if not value["ok"]:
                raise SystemExit(1)
            return
        if args.command == "sync-audit":
            value = audit_sync_queue(root)
            print_json(value) if args.json else print_sync_audit(value)
            if not value["ok"]:
                raise SystemExit(1)
            return
        if args.command == "start":
            value = inspect_project(root)
            if not value["governed"]:
                raise ValueError("Project is not governed; run init or adopt first")
            print_json(value) if args.json else print_start(root, value)
            return
        if args.command == "close":
            value = close_session(root, args)
            print_json(value) if args.json else print_close(value)
            return
        if args.command == "sync-export":
            value = export_sync_payload(root, args)
            print_json(value) if args.json else print_sync_export(value)
            return
        raise AssertionError(f"Unhandled command: {args.command}")
    except (
        FileExistsError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as error:
        logger.error("%s", error)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
