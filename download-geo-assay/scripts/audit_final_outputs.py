#!/usr/bin/env python3
"""Deprecated alias for audit_processed_outputs.py."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from audit_processed_outputs import main

if __name__ == "__main__":
    raise SystemExit(main())
