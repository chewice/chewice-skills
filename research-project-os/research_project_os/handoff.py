"""Resumable context packs and session handoffs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import (
    SESSION_ID_PATTERN,
    append_lifecycle_event,
    atomic_write,
    ensure_manifest,
    git_status,
    load_yaml,
    markdown_field,
    parse_markdown_section,
    utc_now,
)
from .lifecycle import unresolved_tasks


HANDOFF_SECTIONS = (
    "Checkpoint",
    "Current objective",
    "Completed",
    "Confirmed decisions",
    "Outputs",
    "Blockers and interpretation boundary",
    "Next minimum action",
    "Resume commands",
)


def current_session_id(text: str) -> str:
    checkpoint = parse_markdown_section(text, "Checkpoint")
    value = markdown_field(checkpoint, "Session")
    if value is None or SESSION_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("CURRENT_HANDOFF.md has an invalid Session ID")
    return value


def next_session_id(root: Path) -> str:
    today = utc_now().strftime("%Y%m%d")
    values = []
    archive = root / "docs/handoffs/archive"
    if archive.is_dir():
        for path in archive.glob(f"SES-{today}-*.md"):
            if SESSION_ID_PATTERN.fullmatch(path.stem):
                values.append(int(path.stem.rsplit("-", 1)[1]))
    current = root / "CURRENT_HANDOFF.md"
    if current.is_file():
        session_id = current_session_id(current.read_text(encoding="utf-8"))
        if session_id.startswith(f"SES-{today}-"):
            values.append(int(session_id.rsplit("-", 1)[1]))
    return f"SES-{today}-{max(values, default=0) + 1:03d}"


def bullet_lines(values: list[str], fallback: str) -> str:
    cleaned = [value.strip() for value in values if value.strip()]
    return "\n".join(f"- {value}" for value in cleaned) or f"- {fallback}"


def build_handoff(
    *,
    session_id: str,
    summary: str,
    completed: list[str],
    outputs: list[str],
    next_step: str,
    owner: str,
) -> str:
    return f"""# Current Handoff

## Checkpoint

- Session: `{session_id}`
- Updated: {utc_now().date().isoformat()}
- Project stage: `active`
- Analysis status: `exploratory`
- Owner: {owner}

## Current objective

{summary}

## Completed

{bullet_lines(completed, "本 session 未登记完成项。")}

## Confirmed decisions

- 以 human-owned `QUESTIONS.md` 与本次明确批准为准。

## Outputs

{bullet_lines(outputs, "本 session 未登记输出。")}

## Blockers and interpretation boundary

- 尚未登记 blocker；不得把 execution 自动描述为 scientific verification。

## Next minimum action

{next_step}

## Resume commands

```bash
python /path/to/research_project_os.py start --project .
python /path/to/research_project_os.py audit --project .
```
"""


def start_context(root: Path) -> dict[str, Any]:
    manifest = ensure_manifest(root)
    files = {}
    for relative in (
        "AGENTS.md",
        "QUESTIONS.md",
        "CURRENT_HANDOFF.md",
        "project_manifest.yaml",
    ):
        path = root / relative
        if not path.is_file():
            raise ValueError(f"Missing required context file: {relative}")
        files[relative] = path.read_text(encoding="utf-8")
    active = unresolved_tasks(root)
    task_context = None
    if len(active) == 1:
        task_root = root / "explore" / active[0]
        task_context = {
            "name": active[0],
            "task": load_yaml(task_root / "task.yaml"),
            "readme": (task_root / "README.md").read_text(encoding="utf-8"),
            "report": (task_root / "report.html").relative_to(root).as_posix(),
        }
    return {
        "project": str(root),
        "schema_version": manifest.get("schema_version"),
        "context": files,
        "active_task": task_context,
        "git": git_status(root),
        "pixi": {name: (root / name).is_file() for name in ("pixi.toml", "pixi.lock")},
    }


def plan_close(
    root: Path,
    *,
    summary: str,
    completed: list[str],
    outputs: list[str],
    next_step: str,
    owner: str,
) -> dict[str, Any]:
    ensure_manifest(root)
    if not summary.strip() or not next_step.strip():
        raise ValueError("summary and next_step must not be empty")
    current_path = root / "CURRENT_HANDOFF.md"
    previous = current_path.read_text(encoding="utf-8")
    previous_session = current_session_id(previous)
    new_session = next_session_id(root)
    handoff = build_handoff(
        session_id=new_session,
        summary=summary.strip(),
        completed=completed,
        outputs=outputs,
        next_step=next_step.strip(),
        owner=owner.strip() or "unassigned",
    )
    return {
        "mode": "close",
        "project": str(root),
        "previous_session": previous_session,
        "new_session": new_session,
        "archive_path": f"docs/handoffs/archive/{previous_session}.md",
        "previous_handoff": previous,
        "handoff": handoff,
    }


def apply_close(plan: dict[str, Any], *, overwrite: bool = False) -> dict[str, Any]:
    root = Path(plan["project"])
    current = root / "CURRENT_HANDOFF.md"
    if current.read_text(encoding="utf-8") != plan["previous_handoff"]:
        raise ValueError("CURRENT_HANDOFF.md changed after close planning")
    archive = root / plan["archive_path"]
    if archive.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {archive}")
    atomic_write(archive, plan["previous_handoff"])
    atomic_write(current, plan["handoff"])
    event = append_lifecycle_event(
        root,
        action="close",
        subject="session",
        result="applied",
        related_id=plan["new_session"],
    )
    return {
        "written": True,
        "archive_path": plan["archive_path"],
        "handoff_path": "CURRENT_HANDOFF.md",
        "event": event,
    }
