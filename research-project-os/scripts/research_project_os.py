#!/usr/bin/env python3
"""Thin entrypoint for the Research Project OS package."""

from __future__ import annotations

from pathlib import Path
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from research_project_os.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
