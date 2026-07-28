"""Non-destructive project scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any

from .core import (
    BASE_ASSET_ROOT,
    MANIFEST_SCHEMA_VERSION,
    append_lifecycle_event,
    atomic_write,
    initialize_git,
    project_identifier,
    sha256_file,
    slug,
)


PROTECTED_ADOPTION_PATHS = {
    ".gitignore",
    "AGENTS.md",
    "CURRENT_HANDOFF.md",
    "QUESTIONS.md",
    "README.md",
    "project_manifest.yaml",
}

INIT_DIRECTORIES = (
    "archive",
    "docs/handoffs/archive",
    "explore",
    "pipeline",
    "reports",
    "work/audit",
)

ADOPT_DIRECTORIES = (
    "docs/handoffs/archive",
    "work/audit",
)


@dataclass(frozen=True)
class FileAction:
    path: str
    action: str
    content: str | None = None
    reason: str | None = None
    expected_sha256: str | None = None


def render_template(content: str, replacements: dict[str, str]) -> str:
    rendered = content
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    unresolved = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", rendered)))
    if unresolved:
        raise ValueError(f"Unresolved template variables: {', '.join(unresolved)}")
    return rendered


def template_target(path: Path) -> str:
    rendered = path.as_posix()
    if rendered == "gitignore.tmpl":
        return ".gitignore"
    if rendered.endswith(".tmpl"):
        return rendered[: -len(".tmpl")]
    return rendered


def template_replacements(root: Path) -> dict[str, str]:
    today = date.today()
    return {
        "PROJECT_ID": project_identifier(root.name),
        "PROJECT_NAME": slug(root.name).replace("-", "_"),
        "DATE": today.isoformat(),
        "DATE_COMPACT": today.strftime("%Y%m%d"),
        "MANIFEST_SCHEMA": MANIFEST_SCHEMA_VERSION,
    }


def asset_files(root: Path) -> dict[str, str]:
    replacements = template_replacements(root)
    files = {}
    for source in sorted(path for path in BASE_ASSET_ROOT.rglob("*") if path.is_file()):
        relative = source.relative_to(BASE_ASSET_ROOT)
        target = template_target(relative)
        files[target] = render_template(
            source.read_text(encoding="utf-8"),
            replacements,
        )
    return files


def directory_is_empty_for_init(root: Path) -> bool:
    if not root.exists():
        return True
    return not any(path.name != ".git" for path in root.iterdir())


def plan_scaffold(
    root: Path,
    mode: str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    if mode not in {"init", "adopt"}:
        raise ValueError("mode must be init or adopt")
    if mode == "init" and not directory_is_empty_for_init(root):
        raise ValueError(
            "init requires an empty directory; use adopt for an existing project"
        )
    if mode == "adopt" and not root.exists():
        raise ValueError(
            "adopt requires an existing project directory; use init instead"
        )
    actions = []
    for relative, content in sorted(asset_files(root).items()):
        target = root / relative
        if not target.exists():
            actions.append(FileAction(relative, "create", content))
        elif target.is_file() and target.read_text(encoding="utf-8") == content:
            actions.append(FileAction(relative, "unchanged", reason="content matches"))
        elif mode == "adopt" and relative in PROTECTED_ADOPTION_PATHS:
            actions.append(
                FileAction(relative, "skip", reason="protected during adopt")
            )
        elif overwrite:
            actions.append(
                FileAction(
                    relative,
                    "overwrite",
                    content,
                    expected_sha256=sha256_file(target),
                )
            )
        else:
            actions.append(
                FileAction(relative, "skip", reason="existing content differs")
            )
    directories = list(INIT_DIRECTORIES if mode == "init" else ADOPT_DIRECTORIES)
    return {
        "mode": mode,
        "project": str(root),
        "directories": directories,
        "actions": actions,
    }


def apply_scaffold(plan: dict[str, Any], *, init_git: bool = False) -> dict[str, Any]:
    root = Path(plan["project"])
    root.mkdir(parents=True, exist_ok=True)
    for relative in plan["directories"]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    written = []
    for action in plan["actions"]:
        if action.action not in {"create", "overwrite"}:
            continue
        if action.content is None:
            raise AssertionError(f"Missing planned content for {action.path}")
        target = root / action.path
        if action.action == "create" and target.exists():
            raise ValueError(f"Scaffold target appeared after planning: {target}")
        if action.action == "overwrite" and (
            not target.is_file() or sha256_file(target) != action.expected_sha256
        ):
            raise ValueError(f"Scaffold target changed after planning: {target}")
        atomic_write(target, action.content)
        written.append(action.path)
    git = initialize_git(root) if init_git else {"initialized": False}
    event = append_lifecycle_event(
        root,
        action=plan["mode"],
        subject="project",
        result="applied",
    )
    return {"written": written, "git": git, "event": event}


def plan_to_dict(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        **plan,
        "actions": [
            {
                "path": action.path,
                "action": action.action,
                "reason": action.reason,
                "expected_sha256": action.expected_sha256,
            }
            for action in plan["actions"]
        ],
    }
