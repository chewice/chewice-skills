"""Shared deterministic primitives for Research Project OS."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = PACKAGE_ROOT.parent
ASSET_ROOT = SKILL_ROOT / "assets"
BASE_ASSET_ROOT = ASSET_ROOT / "base"

RELEASE_VERSION = "0.7.1"
MANIFEST_SCHEMA_VERSION = "0.4.0"
LEGACY_MANIFEST_SCHEMAS = {"0.3.0"}
ANALYSIS_SCHEMA_VERSION = "2.0.0"
RUN_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = "1.0.0"

QUESTION_ID_PATTERN = re.compile(r"^Q-\d{3}$")
TASK_NAME_PATTERN = re.compile(
    r"^P(?P<order>0|[1-9]\d*)-"
    r"(?P<core>[A-Za-z][A-Za-z0-9]{0,23})-"
    r"(?P<summary>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
ARCHIVE_VERSION_PATTERN = re.compile(r"^v\d{3}$")
RUN_ID_PATTERN = re.compile(r"^RUN-\d{8}-\d{3}$")
SESSION_ID_PATTERN = re.compile(r"^SES-\d{8}-\d{3}$")
EVENT_ID_PATTERN = re.compile(r"^EVT-\d{8}-\d{3}$")

SENSITIVE_PATTERN = re.compile(
    r"(?:^|/)(?:\.env(?:\.|$)|credentials?|secrets?|tokens?|"
    r"private[_-]?keys?)(?:[._/-]|$)",
    re.IGNORECASE,
)


def project_root(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping: {path}")
    return value


def yaml_text(value: dict[str, Any]) -> str:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        width=88,
    )


def atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    binary = isinstance(content, bytes)
    mode = "wb" if binary else "w"
    kwargs: dict[str, Any] = {} if binary else {"encoding": "utf-8"}
    with tempfile.NamedTemporaryFile(
        mode,
        dir=path.parent,
        delete=False,
        **kwargs,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_text(content: str) -> str:
    return sha256_bytes(content.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def safe_project_path(
    root: Path,
    value: str | Path,
    *,
    label: str,
    must_exist: bool = False,
    allow_root: bool = False,
    allow_absolute: bool = False,
    reject_symlink: bool = False,
) -> Path:
    root = root.resolve()
    candidate = Path(value)
    if candidate.is_absolute() and not allow_absolute:
        raise ValueError(f"{label} must be a project-relative path: {value}")
    if not candidate.is_absolute() and ".." in candidate.parts:
        raise ValueError(f"{label} must be a project-relative path: {value}")
    lexical = Path(
        os.path.abspath(candidate if candidate.is_absolute() else root / candidate)
    )
    if not lexical.is_relative_to(root):
        raise ValueError(f"{label} escapes the project root: {value}")
    if reject_symlink:
        current = root
        for part in lexical.relative_to(root).parts:
            current /= part
            if current.is_symlink():
                raise ValueError(f"{label} must not use symlinks: {value}")
    resolved = lexical.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} escapes the project root: {value}")
    if not allow_root and resolved == root:
        raise ValueError(f"{label} must not be the project root")
    if must_exist and not resolved.exists():
        raise ValueError(f"{label} does not exist: {value}")
    return resolved


def relative_to_root(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def reject_symlinks(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Symlink is forbidden for audited content: {path}")
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ValueError(f"Symlink is forbidden for audited content: {child}")


def hash_path(root: Path, path: Path) -> dict[str, Any]:
    reject_symlinks(path)
    rendered = relative_to_root(root, path)
    if path.is_file():
        return {
            "path": rendered,
            "kind": "file",
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    if not path.is_dir():
        raise ValueError(f"Audited path must be a regular file or directory: {path}")
    files = [
        {
            "path": child.relative_to(path).as_posix(),
            "size": child.stat().st_size,
            "sha256": sha256_file(child),
        }
        for child in sorted(path.rglob("*"))
        if child.is_file()
    ]
    digest = sha256_text(json.dumps(files, ensure_ascii=False, sort_keys=True))
    return {
        "path": rendered,
        "kind": "directory",
        "file_count": len(files),
        "sha256": digest,
        "files": files,
    }


def file_records(root: Path, *, exclude: Iterable[str] = ()) -> list[dict[str, Any]]:
    excluded = set(exclude)
    reject_symlinks(root)
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        if SENSITIVE_PATTERN.search(relative):
            raise ValueError(f"Audited content may contain credentials: {relative}")
        records.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def git_command(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def git_commit(root: Path) -> str | None:
    result = git_command(root, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def git_status(root: Path) -> dict[str, Any]:
    result = git_command(root, "status", "--short", "--branch")
    return {
        "available": result.returncode == 0,
        "commit": git_commit(root),
        "output": result.stdout.strip(),
        "error": result.stderr.strip(),
    }


def environment_hashes(root: Path) -> dict[str, str | None]:
    return {
        name: sha256_file(root / name) if (root / name).is_file() else None
        for name in ("pixi.toml", "pixi.lock")
    }


def initialize_git(root: Path) -> dict[str, Any]:
    if (root / ".git").exists():
        return {"initialized": False, "reason": "already exists"}
    result = subprocess.run(
        ["git", "init", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "git init failed")
    return {"initialized": True}


def next_numbered_id(directory: Path, pattern: re.Pattern[str], prefix: str) -> str:
    today = utc_now().strftime("%Y%m%d")
    highest = 0
    if directory.is_dir():
        for path in directory.iterdir():
            match = pattern.fullmatch(path.stem if path.is_file() else path.name)
            if match and path.name.startswith(f"{prefix}-{today}-"):
                highest = max(highest, int(path.name.split("-")[-1].split(".")[0]))
    return f"{prefix}-{today}-{highest + 1:03d}"


def append_lifecycle_event(
    root: Path,
    *,
    action: str,
    subject: str,
    result: str,
    related_id: str | None = None,
) -> dict[str, Any]:
    path = root / "work/audit/lifecycle.jsonl"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = [line for line in existing.splitlines() if line.strip()]
    today = utc_now().strftime("%Y%m%d")
    ordinals = []
    for line in lines:
        try:
            event_id = json.loads(line).get("event_id", "")
        except json.JSONDecodeError:
            continue
        if event_id.startswith(f"EVT-{today}-"):
            ordinals.append(int(event_id.rsplit("-", 1)[1]))
    event = {
        "event_id": f"EVT-{today}-{max(ordinals, default=0) + 1:03d}",
        "timestamp": utc_text(),
        "action": action,
        "subject": subject,
        "result": result,
        "related_id": related_id,
        "git_commit": git_commit(root),
        "manifest_sha256": (
            sha256_file(root / "project_manifest.yaml")
            if (root / "project_manifest.yaml").is_file()
            else None
        ),
    }
    rendered = existing
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    rendered += json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    atomic_write(path, rendered)
    return event


def parse_markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else ""


def markdown_field(section: str, label: str) -> str | None:
    match = re.search(
        rf"^- {re.escape(label)}:\s*(.+?)\s*$",
        section,
        flags=re.MULTILINE,
    )
    return match.group(1).strip().strip("`") if match else None


def ensure_manifest(root: Path) -> dict[str, Any]:
    path = root / "project_manifest.yaml"
    if not path.is_file():
        raise ValueError("Project is not governed; run init or adopt first")
    manifest = load_yaml(path)
    version = str(manifest.get("schema_version", ""))
    if version not in {MANIFEST_SCHEMA_VERSION, *LEGACY_MANIFEST_SCHEMAS}:
        raise ValueError(f"Unsupported manifest schema: {version!r}")
    return manifest


def slug(value: str) -> str:
    rendered = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return rendered or "research-project"


def project_identifier(name: str) -> str:
    return f"PRJ-{slug(name).upper()}"


def stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def relative_link(from_directory: Path, target: Path) -> str:
    return Path(os.path.relpath(target, from_directory)).as_posix()
