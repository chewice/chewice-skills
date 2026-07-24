"""Run the official Skill quick validator from the local Codex installation."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    Path.home()
    / ".agents/skills/.system/skill-creator/scripts/quick_validate.py"
)


def main() -> None:
    if not VALIDATOR.is_file():
        raise SystemExit(f"Skill validator not found: {VALIDATOR}")
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(ROOT / "research-project-os")],
        check=False,
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
