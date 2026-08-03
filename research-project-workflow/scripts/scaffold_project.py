#!/usr/bin/env python3
"""Preview or create the minimal research project scaffold."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = SKILL_ROOT / "assets/base"
PROTECTED_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CURRENT_HANDOFF.md",
    "QUESTIONS.md",
    "README.md",
    "pixi.toml",
}
DIRECTORIES = (
    "docs/questions",
    "docs/references/papers",
    "docs/references/official",
    "docs/references/datasets",
    "docs/template",
    "docs/methods",
    "docs/runbooks",
    "explore",
    "pipeline",
    "results",
    "reports",
    "logs",
    "configs",
    "tests",
)
TARGETS = {
    "AGENTS.md": "AGENTS.md",
    "QUESTIONS.md": "QUESTIONS.md",
    "CURRENT_HANDOFF.md": "CURRENT_HANDOFF.md",
    "README.md": "README.md",
    "pixi.toml": "pixi.toml.tmpl",
    ".gitignore": "gitignore",
}


def project_slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return value or "research-project"


def render_asset(source: str, root: Path, timestamp: str) -> str:
    return (
        source.replace("{{PROJECT_NAME}}", root.name or "Research Project")
        .replace("{{PROJECT_SLUG}}", project_slug(root.name))
        .replace("{{TIMESTAMP}}", timestamp)
    )


def build_plan(root: Path, *, overwrite: bool = False) -> dict[str, Any]:
    root = root.expanduser().resolve()
    timestamp = datetime.now().astimezone().replace(microsecond=0).isoformat()
    files: list[dict[str, str]] = []
    for target_name, asset_name in TARGETS.items():
        target = root / target_name
        content = render_asset(
            (ASSET_ROOT / asset_name).read_text(encoding="utf-8"),
            root,
            timestamp,
        )
        if not target.exists():
            action = "create"
        elif not target.is_file():
            action = "conflict"
        elif target.read_text(encoding="utf-8") == content:
            action = "unchanged"
        elif overwrite and target_name not in PROTECTED_FILES:
            action = "overwrite"
        else:
            action = "preserve"
        files.append({"path": target_name, "action": action, "content": content})
    return {
        "project": str(root),
        "timestamp": timestamp,
        "directories": list(DIRECTORIES),
        "files": files,
    }


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    conflicts = [
        item["path"] for item in plan["files"] if item["action"] == "conflict"
    ]
    if conflicts:
        raise ValueError("Refusing conflicting scaffold paths: " + ", ".join(conflicts))
    root.mkdir(parents=True, exist_ok=True)
    for relative in plan["directories"]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for item in plan["files"]:
        if item["action"] not in {"create", "overwrite"}:
            continue
        target = root / item["path"]
        if item["action"] == "create" and target.exists():
            raise ValueError(f"Target appeared after planning: {target}")
        target.write_text(item["content"], encoding="utf-8")
        written.append(item["path"])
    return {"project": str(root), "written": written}


def public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        **plan,
        "files": [
            {"path": item["path"], "action": item["action"]}
            for item in plan["files"]
        ],
    }


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        plan = build_plan(args.project, overwrite=args.overwrite)
        applied = apply_plan(plan) if args.apply else None
        result = {
            "mode": "apply" if args.apply else "dry-run",
            "plan": public_plan(plan),
            "applied": applied,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"{result['mode']}: {plan['project']}")
            for item in result["plan"]["files"]:
                print(f"{item['action']}: {item['path']}")
            for directory in plan["directories"]:
                print(f"ensure-directory: {directory}/")
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
