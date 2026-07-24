#!/usr/bin/env python3
"""Install the full skill workspace and create discovery symlinks."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "research-project-os"


def parse_args() -> argparse.Namespace:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(REPOSITORY_ROOT))
    parser.add_argument("--ref", default="main")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=codex_home / "skill-workspaces/research-project-os-skill",
    )
    parser.add_argument(
        "--codex-link",
        type=Path,
        default=codex_home / f"skills/{SKILL_NAME}",
    )
    parser.add_argument(
        "--agents-link",
        type=Path,
        default=Path.home() / f".agents/skills/{SKILL_NAME}",
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def validate_workspace(root: Path) -> None:
    required = (
        root / "pixi.toml",
        root / "pixi.lock",
        root / SKILL_NAME / "SKILL.md",
        root / SKILL_NAME / "scripts/research_project_os.py",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Missing workspace files: " + ", ".join(missing))
    forbidden = (
        root / SKILL_NAME / "pixi.toml",
        root / SKILL_NAME / "pixi.lock",
        root / SKILL_NAME / ".pixi",
    )
    nested = [str(path) for path in forbidden if path.exists()]
    if nested:
        raise ValueError("Nested Pixi state is forbidden: " + ", ".join(nested))


def link_state(link: Path, target: Path) -> str:
    if not link.is_symlink() and not link.exists():
        return "create"
    if link.is_symlink() and link.resolve(strict=False) == target:
        return "unchanged"
    return "conflict"


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    workspace = args.workspace.expanduser().resolve()
    skill_target = workspace / SKILL_NAME
    links = [
        args.codex_link.expanduser().absolute(),
        args.agents_link.expanduser().absolute(),
    ]
    if workspace.exists():
        raise FileExistsError(
            f"Workspace already exists: {workspace}. Move it to a recoverable "
            "backup before installing."
        )
    link_actions = [
        {"path": link, "target": skill_target, "action": link_state(link, skill_target)}
        for link in links
    ]
    conflicts = [item["path"] for item in link_actions if item["action"] == "conflict"]
    if conflicts:
        raise FileExistsError(
            "Refusing to replace discovery paths: "
            + ", ".join(str(path) for path in conflicts)
        )
    return {
        "source": str(args.source),
        "ref": str(args.ref),
        "workspace": workspace,
        "skill_target": skill_target,
        "links": link_actions,
    }


def apply_plan(plan: dict[str, Any]) -> None:
    workspace = plan["workspace"]
    workspace.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{workspace.name}.install-",
            dir=workspace.parent,
        )
    )
    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-hardlinks",
                "--single-branch",
                "--branch",
                plan["ref"],
                plan["source"],
                str(staging),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise OSError(result.stderr.strip() or "git clone failed")
        validate_workspace(staging)
        staging.replace(workspace)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    for item in plan["links"]:
        if item["action"] == "unchanged":
            continue
        link = item["path"]
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(item["target"], target_is_directory=True)


def print_plan(plan: dict[str, Any], *, applied: bool) -> None:
    mode = "APPLIED" if applied else "DRY-RUN"
    print(f"{mode} install {plan['source']}@{plan['ref']}")
    print(f"workspace: {plan['workspace']}")
    for item in plan["links"]:
        print(f"{item['action']}: {item['path']} -> {item['target']}")
    if not applied:
        print("Pass --apply to install.")


def main() -> None:
    args = parse_args()
    try:
        plan = build_plan(args)
        if args.apply:
            apply_plan(plan)
        print_plan(plan, applied=args.apply)
    except (FileExistsError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
