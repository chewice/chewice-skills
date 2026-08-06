"""Run the official Skill quick validator for both installable Skills."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("research-project-workflow", "report-generation")
VALIDATOR_RELATIVE = Path("skills/.system/skill-creator/scripts/quick_validate.py")


def validator_candidates(
    *,
    codex_home: str | None = None,
    home: Path | None = None,
) -> list[Path]:
    home = home or Path.home()
    configured = codex_home if codex_home is not None else os.environ.get("CODEX_HOME")
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser() / VALIDATOR_RELATIVE)
    candidates.extend(
        [
            home / ".codex" / VALIDATOR_RELATIVE,
            home / ".agents" / VALIDATOR_RELATIVE,
        ]
    )
    return list(dict.fromkeys(candidates))


def find_validator() -> Path:
    for candidate in validator_candidates():
        if candidate.is_file():
            return candidate
    rendered = "\n".join(f"- {path}" for path in validator_candidates())
    raise FileNotFoundError(f"Skill validator not found. Checked:\n{rendered}")


def main() -> int:
    try:
        validator = find_validator()
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1
    failed = []
    for name in SKILLS:
        result = subprocess.run(
            [sys.executable, str(validator), str(ROOT / name)],
            check=False,
        )
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print("Skill validation failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
