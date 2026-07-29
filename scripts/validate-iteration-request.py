#!/usr/bin/env python3
"""Validate a scripting-style iteration request without writing any files."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a scripting-style Phase 1 or Phase 2 JSON request."
    )
    parser.add_argument(
        "request",
        help="JSON request path, or '-' to read JSON from stdin",
    )
    args = parser.parse_args()

    try:
        if args.request == "-":
            request = json.loads(sys.stdin.read())
        else:
            request_path = Path(args.request).expanduser().resolve()
            if not request_path.is_file():
                raise SystemExit(f"Request does not exist: {request_path}")
            request = json.loads(request_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON request: {exc}") from exc

    if not isinstance(request, dict):
        raise SystemExit("Request must be a JSON object.")
    if request.get("schema_version") != "1.0":
        raise SystemExit("schema_version must be '1.0'.")

    iteration_id = request.get("iteration_id")
    if not isinstance(iteration_id, str) or not iteration_id.strip():
        raise SystemExit("iteration_id must be a non-empty string.")
    if not all(char.isalnum() or char in "-_" for char in iteration_id):
        raise SystemExit("iteration_id may contain only letters, digits, '-' and '_'.")

    phase = request.get("phase")
    if phase not in {"phase1", "phase2"}:
        raise SystemExit("phase must be 'phase1' or 'phase2'.")

    target_skill_value = request.get("target_skill")
    if not isinstance(target_skill_value, str) or not target_skill_value:
        raise SystemExit("target_skill must be a non-empty path.")
    target_skill = Path(target_skill_value).expanduser().resolve()
    if not (target_skill / "SKILL.md").is_file():
        raise SystemExit(f"target_skill does not contain SKILL.md: {target_skill}")

    approval = request.get("approval")
    if not isinstance(approval, dict):
        raise SystemExit("approval must be a mapping.")
    confirmed = approval.get("confirmed")
    if phase == "phase1" and confirmed is not False:
        raise SystemExit("Phase 1 requires approval.confirmed: false.")
    if phase == "phase2":
        if confirmed is not True:
            raise SystemExit("Phase 2 requires approval.confirmed: true.")
        decisions = approval.get("accepted_decisions")
        if not isinstance(decisions, list) or not decisions:
            raise SystemExit("Phase 2 requires non-empty approval.accepted_decisions.")
        review_value = request.get("phase1_review_dir")
        if not isinstance(review_value, str) or not review_value:
            raise SystemExit("Phase 2 requires phase1_review_dir.")
        review_dir = Path(review_value).expanduser().resolve()
        if not review_dir.is_dir():
            raise SystemExit(f"phase1_review_dir does not exist: {review_dir}")

    example_entries = request.get("new_examples")
    if not isinstance(example_entries, list) or not example_entries:
        raise SystemExit("new_examples must be a non-empty list.")

    allowed_suffixes = {".R": "R", ".py": "Python", ".sh": "Bash"}
    excluded_dirs = {
        ".git",
        ".pixi",
        "__pycache__",
        "data",
        "R",
        "resources",
        "softwares",
        "参考文献",
    }
    excluded_files = {"setup-vscode.sh"}
    discovered = {}

    for entry in example_entries:
        if isinstance(entry, str):
            example_value = entry
            stage_hint = None
            role_hint = None
        elif isinstance(entry, dict):
            example_value = entry.get("path")
            stage_hint = entry.get("stage_hint")
            role_hint = entry.get("role_hint")
        else:
            raise SystemExit("Each new_examples entry must be a path string or mapping.")

        if not isinstance(example_value, str) or not example_value:
            raise SystemExit("Each new_examples entry requires a non-empty path.")
        example_path = Path(example_value).expanduser().resolve()
        if not example_path.exists():
            raise SystemExit(f"Example path does not exist: {example_path}")
        if any(part in excluded_dirs for part in example_path.parts):
            raise SystemExit(f"Example path is inside an excluded directory: {example_path}")

        candidates = []
        if example_path.is_file():
            if example_path.name in excluded_files:
                raise SystemExit(f"Example is an excluded scaffold file: {example_path}")
            candidates.append(example_path)
        elif example_path.is_dir():
            script_roots = []
            for current_root, dirnames, _ in os.walk(example_path):
                dirnames[:] = [
                    name
                    for name in dirnames
                    if name not in excluded_dirs and not name.startswith(".")
                ]
                current_path = Path(current_root)
                if current_path.name == "scripts":
                    script_roots.append(current_path)
                    dirnames[:] = []

            search_roots = script_roots or [example_path]
            for search_root in search_roots:
                for current_root, dirnames, filenames in os.walk(search_root):
                    dirnames[:] = [
                        name
                        for name in dirnames
                        if name not in excluded_dirs and not name.startswith(".")
                    ]
                    current_path = Path(current_root)
                    for filename in sorted(filenames):
                        if filename in excluded_files:
                            continue
                        candidate = current_path / filename
                        if candidate.suffix in allowed_suffixes:
                            candidates.append(candidate.resolve())
        else:
            raise SystemExit(f"Example path is not a regular file or directory: {example_path}")

        for candidate in candidates:
            if candidate.suffix not in allowed_suffixes:
                raise SystemExit(
                    f"Unsupported example extension: {candidate}. "
                    "Allowed: .R, .py, .sh"
                )
            content = candidate.read_bytes()
            line_count = content.count(b"\n")
            if content and not content.endswith(b"\n"):
                line_count += 1
            discovered[str(candidate)] = {
                "path": str(candidate),
                "language": allowed_suffixes[candidate.suffix],
                "line_count": line_count,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "stage_hint": stage_hint,
                "role_hint": role_hint,
            }

    if not discovered:
        raise SystemExit("No .R, .py or .sh examples were discovered.")

    context_readmes = request.get("context_readmes", [])
    if not isinstance(context_readmes, list):
        raise SystemExit("context_readmes must be a list.")
    validated_readmes = []
    for readme_value in context_readmes:
        if not isinstance(readme_value, str) or not readme_value:
            raise SystemExit("Each context_readmes entry must be a non-empty path.")
        readme = Path(readme_value).expanduser().resolve()
        if not readme.is_file() or readme.name != "README.md":
            raise SystemExit(f"Context file must be an existing README.md: {readme}")
        if any(part in excluded_dirs for part in readme.parts):
            raise SystemExit(f"README is inside an excluded directory: {readme}")
        validated_readmes.append(str(readme))

    manifest = {
        "status": "valid",
        "schema_version": "1.0",
        "iteration_id": iteration_id,
        "phase": phase,
        "target_skill": str(target_skill),
        "examples": [discovered[path] for path in sorted(discovered)],
        "context_readmes": sorted(set(validated_readmes)),
        "source_examples_read_only": True,
        "skill_rule_write_allowed": False,
        "phase1_review_write_allowed": phase == "phase1",
        "phase2_request_complete": phase == "phase2",
        "validator_grants_write_authority": False,
        "requires_current_conversation_confirmation": phase == "phase2",
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
