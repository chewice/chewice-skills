#!/usr/bin/env python3
"""Collect read-only Pixi diagnostics while redacting sensitive values."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any


SENSITIVE_KEY = re.compile(
    r"(authorization|credential|password|passwd|proxy|secret|token|username)",
    re.IGNORECASE,
)
SENSITIVE_ENV = re.compile(
    r"^(HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|PIP_INDEX_URL|"
    r"PIP_EXTRA_INDEX_URL|UV_INDEX_URL|PIXI_AUTH_FILE)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect non-mutating Pixi workspace diagnostics."
    )
    parser.add_argument(
        "--manifest-path",
        type=pathlib.Path,
        default=pathlib.Path("."),
        help="pixi.toml, pyproject.toml, or workspace directory",
    )
    parser.add_argument("--environment", help="named environment to inspect")
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def redact(value: Any, key: str | None = None) -> Any:
    if key and SENSITIVE_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {item_key: redact(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    result: dict[str, Any] = {
        "command": command,
        "returncode": completed.returncode,
    }
    if completed.stdout.strip():
        try:
            result["data"] = redact(json.loads(completed.stdout))
        except json.JSONDecodeError:
            result["stdout"] = completed.stdout.strip()
    if completed.stderr.strip():
        result["stderr"] = completed.stderr.strip()
    return result


def run_text(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def sensitive_environment() -> dict[str, bool]:
    return {
        name: True
        for name in sorted(os.environ)
        if SENSITIVE_ENV.match(name) or SENSITIVE_KEY.search(name)
    }


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    pixi = shutil.which("pixi")
    if pixi is None:
        return {
            "ok": False,
            "error": "pixi executable was not found on PATH",
            "sensitive_environment_present": sensitive_environment(),
        }, 2

    manifest_path = args.manifest_path.expanduser().resolve()
    common_options = ["--manifest-path", str(manifest_path), "--no-progress"]
    info_command = [pixi, "info", *common_options]
    if args.extended:
        info_command.append("--extended")
    info_command.append("--json")

    report: dict[str, Any] = {
        "ok": True,
        "manifest_path": str(manifest_path),
        "pixi_version": run_text([pixi, "--version"]),
        "workspace_info": run_json(info_command),
        "config": {
            "effective": run_json(
                [pixi, "config", "list", *common_options, "--json"]
            ),
            "local": run_json(
                [pixi, "config", "list", *common_options, "--local", "--json"]
            ),
            "global": run_json(
                [pixi, "config", "list", *common_options, "--global", "--json"]
            ),
        },
        "environments": run_text(
            [
                pixi,
                "workspace",
                "--manifest-path",
                str(manifest_path),
                "--no-progress",
                "environment",
                "list",
            ]
        ),
        "sensitive_environment_present": sensitive_environment(),
    }

    if args.environment:
        report["selected_environment"] = args.environment
        report["packages"] = run_json(
            [
                pixi,
                "list",
                *common_options,
                "--environment",
                args.environment,
                "--json",
                "--frozen",
                "--no-install",
            ]
        )

    failures = []
    for section in ("workspace_info", "environments"):
        if report[section]["returncode"] != 0:
            failures.append(section)
    report["ok"] = not failures
    report["failed_sections"] = failures
    return report, 0 if report["ok"] else 1


def print_human(report: dict[str, Any]) -> None:
    print(f"Pixi diagnostics: {'OK' if report.get('ok') else 'INCOMPLETE'}")
    if "error" in report:
        print(f"Error: {report['error']}")
        return
    print(f"Manifest path: {report['manifest_path']}")
    print(f"Version: {report['pixi_version'].get('stdout', 'unknown')}")
    print(
        "Sensitive environment variables present: "
        f"{len(report['sensitive_environment_present'])}"
    )
    for name in ("workspace_info", "environments"):
        section = report[name]
        print(f"{name}: return code {section['returncode']}")
        if section.get("stderr"):
            print(f"  {section['stderr']}")
    if "packages" in report:
        print(f"packages ({report['selected_environment']}): return code {report['packages']['returncode']}")
        if report["packages"].get("stderr"):
            print(f"  {report['packages']['stderr']}")


def main() -> int:
    args = parse_args()
    report, exit_code = build_report(args)
    if args.as_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print_human(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
