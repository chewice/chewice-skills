"""Smoke test for skill structure and installer dry-run planning."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install_skill.py"
SKILL_DIR = ROOT / "research-context"


def main() -> None:
    skill = SKILL_DIR / "SKILL.md"
    assert skill.is_file()
    content = skill.read_text(encoding="utf-8")
    assert "name: research-context" in content
    assert "第一性原理" in content
    assert "Occam's razor" in content
    for name in ("context.md", "delegation.md", "decisions.md"):
        path = SKILL_DIR / "references" / name
        assert path.is_file(), path
        assert f"references/{name}" in content
    assert not (SKILL_DIR / "scripts").exists()
    assert not (ROOT / "report-generation").exists()

    with tempfile.TemporaryDirectory() as temporary:
        result = subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "--source",
                str(ROOT),
                "--workspace",
                str(Path(temporary) / "workspace"),
                "--codex-skills-dir",
                str(Path(temporary) / "codex"),
                "--agents-skills-dir",
                str(Path(temporary) / "agents"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(
                "Installer dry-run failed\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        assert "DRY-RUN install" in result.stdout
        assert "research-context" in result.stdout
        assert not (Path(temporary) / "workspace").exists()
    print("Smoke test passed")


if __name__ == "__main__":
    main()
