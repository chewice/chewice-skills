#!/usr/bin/env python3
"""Install the shared workspace and create discovery links for both Skills."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAMES = ("research-project-workflow", "report-generation")


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(REPOSITORY_ROOT))
    parser.add_argument("--ref", default="main")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=codex_home / "skill-workspaces/research-project-workflow-skills",
    )
    parser.add_argument(
        "--codex-skills-dir",
        type=Path,
        default=codex_home / "skills",
    )
    parser.add_argument(
        "--agents-skills-dir",
        type=Path,
        default=Path.home() / ".agents/skills",
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(arguments)


def validate_workspace(root: Path) -> None:
    required = [root / "pixi.toml", root / "pixi.lock"]
    for name in SKILL_NAMES:
        required.extend(
            [
                root / name / "SKILL.md",
                root / name / "agents/openai.yaml",
            ]
        )
    required.extend(
        [
            root / "research-project-workflow/scripts/scaffold_project.py",
            root / "research-project-workflow/scripts/validate_project.py",
            root / "report-generation/scripts/generate_report.py",
        ]
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Missing workspace files: " + ", ".join(missing))
    nested = [
        str(path)
        for name in SKILL_NAMES
        for path in (
            root / name / "pixi.toml",
            root / name / "pixi.lock",
            root / name / ".pixi",
        )
        if path.exists()
    ]
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
    if workspace.exists():
        raise FileExistsError(
            f"Workspace already exists: {workspace}. Move it to a recoverable backup."
        )
    links = []
    for parent in (args.codex_skills_dir, args.agents_skills_dir):
        parent = parent.expanduser().absolute()
        for name in SKILL_NAMES:
            link = parent / name
            target = workspace / name
            links.append(
                {
                    "path": link,
                    "target": target,
                    "action": link_state(link, target),
                }
            )
    conflicts = [item["path"] for item in links if item["action"] == "conflict"]
    if conflicts:
        raise FileExistsError(
            "Refusing to replace discovery paths: "
            + ", ".join(str(path) for path in conflicts)
        )
    return {
        "source": str(args.source),
        "ref": str(args.ref),
        "workspace": workspace,
        "links": links,
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
        shutil.rmtree(staging, ignore_errors=True)
        raise
    for item in plan["links"]:
        if item["action"] == "unchanged":
            continue
        link = item["path"]
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(item["target"], target_is_directory=True)


def print_plan(plan: dict[str, Any], *, applied: bool) -> None:
    print(f"{'APPLIED' if applied else 'DRY-RUN'} install")
    print(f"source: {plan['source']}@{plan['ref']}")
    print(f"workspace: {plan['workspace']}")
    for item in plan["links"]:
        print(f"{item['action']}: {item['path']} -> {item['target']}")
    if not applied:
        print("Pass --apply to install.")


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        plan = build_plan(args)
        if args.apply:
            apply_plan(plan)
        print_plan(plan, applied=args.apply)
        return 0
    except (FileExistsError, OSError, ValueError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
