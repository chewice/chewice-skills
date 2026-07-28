"""Read-only project inspection and policy audit."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

from .core import (
    ANALYSIS_SCHEMA_VERSION,
    EVENT_ID_PATTERN,
    LEGACY_MANIFEST_SCHEMAS,
    MANIFEST_SCHEMA_VERSION,
    QUESTION_ID_PATTERN,
    SENSITIVE_PATTERN,
    TASK_NAME_PATTERN,
    ensure_manifest,
    git_command,
    git_status,
    load_yaml,
    markdown_field,
    parse_markdown_section,
)
from .lifecycle import (
    explore_task_paths,
    script_contract_errors,
    unresolved_tasks,
    validate_run_receipts,
    verify_archive_snapshot,
    verify_pipeline_release,
)
from .reporting import ReportKind, validate_report


REQUIRED_CONTROL_PATHS = (
    "AGENTS.md",
    "QUESTIONS.md",
    "CURRENT_HANDOFF.md",
    "project_manifest.yaml",
)

INVENTORY_PATTERNS = {
    "code_roots": ("analysis", "notebooks", "pipeline", "scripts", "src"),
    "data_roots": ("data", "datasets", "resources"),
    "artifact_roots": ("archive", "explore", "outputs", "reports", "results"),
    "documentation_roots": ("AGENTS.md", "CURRENT_HANDOFF.md", "QUESTIONS.md", "docs"),
    "environment_files": ("pixi.toml", "pixi.lock", "pyproject.toml"),
}

SCAN_PRUNE = {
    ".git",
    "__pycache__",
    "archive",
    "data",
    "datasets",
    "explore",
    "node_modules",
    "outputs",
    "reports",
    "results",
}

TOML_TABLE_PATTERN = re.compile(
    r"^\s*\[(?!\[)\s*(?P<table>[^\]]+?)\s*\](?!\])",
    flags=re.MULTILINE,
)


def bounded_inventory(root: Path) -> dict[str, list[str]]:
    inventory = {name: [] for name in INVENTORY_PATTERNS}
    if not root.exists():
        return inventory
    for category, candidates in INVENTORY_PATTERNS.items():
        inventory[category] = sorted(
            value for value in candidates if (root / value).exists()
        )
    environment = set(inventory["environment_files"])
    for directory, names, files in os.walk(root, followlinks=False):
        base = Path(directory)
        relative = base.relative_to(root)
        if len(relative.parts) >= 5:
            names[:] = []
            continue
        names[:] = [
            name
            for name in names
            if name != ".pixi"
            and name not in SCAN_PRUNE
            and not (base / name).is_symlink()
        ]
        for filename in files:
            if filename not in {"pixi.toml", "pixi.lock", "pyproject.toml"}:
                continue
            path = base / filename
            environment.add(path.relative_to(root).as_posix())
    inventory["environment_files"] = sorted(environment)
    return inventory


def classify_pixi_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"kind": "absent", "tables": []}
    text = path.read_text(encoding="utf-8")
    tables = [
        match.group("table").strip() for match in TOML_TABLE_PATTERN.finditer(text)
    ]
    if path.name == "pixi.toml":
        if "workspace" in tables:
            kind = "workspace"
        elif "package" in tables:
            kind = "package"
        else:
            kind = "unknown"
    elif "tool.pixi.workspace" in tables:
        kind = "workspace"
    elif "tool.pixi.package" in tables:
        kind = "package"
    else:
        kind = "plain"
    return {"kind": kind, "tables": tables}


def git_tracked(root: Path, path: str) -> bool | None:
    result = git_command(root, "ls-files", "--error-unmatch", "--", path)
    if result.returncode in {0, 1}:
        return result.returncode == 0
    return None


def git_ignored(root: Path, path: str) -> bool | None:
    result = git_command(root, "check-ignore", "-q", "--", path)
    if result.returncode in {0, 1}:
        return result.returncode == 0
    return None


def inspect_pixi_policy(root: Path) -> dict[str, Any]:
    issues = []
    inventory = bounded_inventory(root)["environment_files"]
    root_workspaces = []
    uses_pixi = False
    for relative in inventory:
        path = root / relative
        if path.name not in {"pixi.toml", "pyproject.toml"}:
            continue
        classification = classify_pixi_manifest(path)
        if classification["kind"] in {"workspace", "package", "unknown"}:
            uses_pixi = True
        nested = len(Path(relative).parts) > 1
        if classification["kind"] == "workspace":
            if nested:
                issues.append(
                    {
                        "code": "nested_workspace_manifest",
                        "severity": "error",
                        "path": relative,
                        "message": "Pixi workspace must be at project root",
                    }
                )
            else:
                root_workspaces.append(relative)
        elif nested and classification["kind"] == "unknown":
            issues.append(
                {
                    "code": "nested_unknown_pixi_manifest",
                    "severity": "error",
                    "path": relative,
                    "message": "Nested Pixi manifest is not package-only",
                }
            )
    nested_locks = [
        value
        for value in inventory
        if Path(value).name == "pixi.lock" and len(Path(value).parts) > 1
    ]
    for relative in nested_locks:
        issues.append(
            {
                "code": "nested_pixi_lock",
                "severity": "error",
                "path": relative,
                "message": "Only the root Pixi lock is allowed",
            }
        )
    for directory, names, _ in os.walk(root, followlinks=False):
        base = Path(directory)
        relative = base.relative_to(root)
        names[:] = [
            name
            for name in names
            if name not in SCAN_PRUNE and not (base / name).is_symlink()
        ]
        if ".pixi" in names:
            if relative != Path("."):
                path = (relative / ".pixi").as_posix()
                issues.append(
                    {
                        "code": "nested_pixi_environment",
                        "severity": "error",
                        "path": path,
                        "message": "Nested .pixi is forbidden",
                    }
                )
            names.remove(".pixi")
    if len(root_workspaces) > 1:
        issues.append(
            {
                "code": "multiple_root_workspace_manifests",
                "severity": "error",
                "path": ".",
                "message": "Exactly one root Pixi workspace is allowed",
            }
        )
    if uses_pixi and len(root_workspaces) == 0:
        issues.append(
            {
                "code": "missing_root_workspace_manifest",
                "severity": "error",
                "path": ".",
                "message": "Pixi use requires one root workspace manifest",
            }
        )
    root_lock = root / "pixi.lock"
    if root_workspaces and not root_lock.is_file():
        issues.append(
            {
                "code": "missing_root_pixi_lock",
                "severity": "error",
                "path": "pixi.lock",
                "message": "Root Pixi workspace requires pixi.lock",
            }
        )
    if root_lock.is_file() and git_tracked(root, "pixi.lock") is False:
        issues.append(
            {
                "code": "root_pixi_lock_untracked",
                "severity": "error",
                "path": "pixi.lock",
                "message": "Root pixi.lock must be tracked",
            }
        )
    if (root / ".pixi").exists():
        result = git_command(root, "ls-files", ".pixi")
        if result.returncode == 0 and result.stdout.strip():
            issues.append(
                {
                    "code": "tracked_root_pixi_environment",
                    "severity": "error",
                    "path": ".pixi",
                    "message": "Root .pixi must not be tracked",
                }
            )
        if git_ignored(root, ".pixi") is False:
            issues.append(
                {
                    "code": "root_pixi_environment_not_ignored",
                    "severity": "warning",
                    "path": ".pixi",
                    "message": "Root .pixi should be ignored",
                }
            )
    if not uses_pixi:
        issues.append(
            {
                "code": "pixi_not_configured",
                "severity": "warning",
                "path": ".",
                "message": "No root Pixi workspace is configured",
            }
        )
    return {
        "policy": "root_workspace",
        "uses_pixi": uses_pixi,
        "root_workspace_manifests": root_workspaces,
        "root_manifest": root_workspaces[0] if len(root_workspaces) == 1 else None,
        "issues": issues,
    }


def visible_sensitive_files(root: Path) -> list[str]:
    result = git_command(root, "ls-files", "--cached", "--others", "--exclude-standard")
    if result.returncode != 0:
        return []
    return sorted(
        value for value in result.stdout.splitlines() if SENSITIVE_PATTERN.search(value)
    )


def inspect_project(root: Path) -> dict[str, Any]:
    exists = root.exists()
    entries = sorted(path.name for path in root.iterdir()) if exists else []
    governed = (root / "project_manifest.yaml").is_file()
    return {
        "project": str(root),
        "exists": exists,
        "entries": entries,
        "governed": governed,
        "recommended_mode": (
            "start" if governed else ("init" if not entries else "adopt")
        ),
        "project_inventory": bounded_inventory(root),
        "pixi_policy": inspect_pixi_policy(root),
        "control_paths": {
            path: (root / path).exists() for path in REQUIRED_CONTROL_PATHS
        },
        "git": git_status(root),
    }


def audit_questions(root: Path) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    path = root / "QUESTIONS.md"
    text = path.read_text(encoding="utf-8")
    for heading in (
        "Project purpose",
        "Input constraints",
        "Output requirements",
        "FAQ",
        "Current question",
        "Question queue",
        "Answered questions",
    ):
        if not parse_markdown_section(text, heading):
            errors.append(f"QUESTIONS.md lacks section: {heading}")
    current = parse_markdown_section(text, "Current question")
    question_id = markdown_field(current, "ID")
    if question_id and QUESTION_ID_PATTERN.fullmatch(question_id) is None:
        errors.append("QUESTIONS.md current ID must match Q-NNN")
    if "尚未填写" in current:
        warnings.append("QUESTIONS.md current question is not ready")
    return errors, warnings


def audit_lifecycle_log(root: Path) -> list[str]:
    path = root / "work/audit/lifecycle.jsonl"
    if not path.exists():
        return []
    errors = []
    seen = set()
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"Malformed lifecycle event at line {index}")
            continue
        event_id = event.get("event_id")
        if (
            not isinstance(event_id, str)
            or EVENT_ID_PATTERN.fullmatch(event_id) is None
        ):
            errors.append(f"Invalid lifecycle event ID at line {index}")
        elif event_id in seen:
            errors.append(f"Duplicate lifecycle event ID: {event_id}")
        seen.add(event_id)
    return errors


def audit_project(root: Path) -> dict[str, Any]:
    errors = []
    warnings = []
    missing = [
        relative
        for relative in REQUIRED_CONTROL_PATHS
        if not (root / relative).exists()
    ]
    errors.extend(f"Missing required control path: {value}" for value in missing)
    pixi = inspect_pixi_policy(root)
    for issue in pixi["issues"]:
        (errors if issue["severity"] == "error" else warnings).append(
            f"[{issue['code']}] {issue['path']}: {issue['message']}"
        )
    if missing:
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "pixi_policy": pixi,
        }
    manifest = ensure_manifest(root)
    version = str(manifest.get("schema_version"))
    if version in LEGACY_MANIFEST_SCHEMAS:
        warnings.append(f"Legacy manifest schema is supported read-only: {version}")
    elif version != MANIFEST_SCHEMA_VERSION:
        errors.append(f"Manifest schema must be {MANIFEST_SCHEMA_VERSION}")
    question_errors, question_warnings = audit_questions(root)
    errors.extend(question_errors)
    warnings.extend(question_warnings)
    errors.extend(audit_lifecycle_log(root))
    active = unresolved_tasks(root)
    if len(active) > 1:
        errors.append(
            "Only one explore task may remain unarchived and uncancelled: "
            + ", ".join(active)
        )
    for task_root in explore_task_paths(root):
        try:
            task = load_yaml(task_root / "task.yaml")
            if task.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
                errors.append(f"Unsupported task schema: {task_root}")
            errors.extend(script_contract_errors([task_root / "scripts"]))
            report = validate_report(
                output=task_root / "report.html",
                project_root=root,
                kind=ReportKind.EXPLORE,
                require_complete=False,
            )
            errors.extend(report["errors"])
            receipt = validate_run_receipts(root, task_root)
            if receipt["receipts"]:
                errors.extend(receipt["errors"])
        except (OSError, ValueError) as error:
            errors.append(str(error))
    archive = root / "archive"
    if archive.is_dir():
        for task_root in archive.iterdir():
            if (
                not task_root.is_dir()
                or TASK_NAME_PATTERN.fullmatch(task_root.name) is None
            ):
                errors.append(f"Invalid archive task directory: {task_root}")
                continue
            for version_root in task_root.iterdir():
                if version_root.is_dir() and re.fullmatch(r"v\d{3}", version_root.name):
                    result = verify_archive_snapshot(
                        root,
                        f"{task_root.name}@{version_root.name}",
                    )
                    errors.extend(result["errors"])
                else:
                    errors.append(f"Invalid archive version path: {version_root}")
    release = verify_pipeline_release(root)
    errors.extend(release["errors"])
    sensitive = visible_sensitive_files(root)
    errors.extend(f"Sensitive path is Git-visible: {value}" for value in sensitive)
    for legacy in (
        "reports/evidence_registry.yaml",
        "work/notion_sync",
        "docs/ai_context/status_policy.md",
    ):
        if (root / legacy).exists():
            warnings.append(f"Legacy unused path is preserved: {legacy}")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "pixi_policy": pixi,
    }
