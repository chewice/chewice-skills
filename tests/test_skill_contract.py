"""Skill packaging and concise-document contracts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tests/validate_skill.py"
SPEC = importlib.util.spec_from_file_location("validate_skill", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load validate_skill")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class SkillContractTests(unittest.TestCase):
    def test_skill_is_concise_and_references_are_bounded(self) -> None:
        skill = ROOT / "research-project-os/SKILL.md"
        references = ROOT / "research-project-os/references"
        words = skill.read_text(encoding="utf-8").split()
        self.assertGreaterEqual(len(words), 400)
        self.assertLessEqual(len(words), 500)
        self.assertEqual(
            {path.name for path in references.glob("*.md")},
            {
                "analysis_lifecycle.md",
                "evidence.md",
                "governance.md",
                "migration_policy.md",
                "notion_git_contract.md",
            },
        )
        total_words = len(words) + sum(
            len(path.read_text(encoding="utf-8").split())
            for path in references.glob("*.md")
        )
        self.assertLessEqual(total_words, 1_600)
        for target in re.findall(r"\]\((references/[^)]+)\)", skill.read_text()):
            self.assertTrue((ROOT / "research-project-os" / target).is_file(), target)

    def test_explore_style_defers_abstraction_to_pipeline(self) -> None:
        skill = (ROOT / "research-project-os/SKILL.md").read_text(encoding="utf-8")
        lifecycle = (
            ROOT / "research-project-os/references/analysis_lifecycle.md"
        ).read_text(encoding="utf-8")
        agents = (ROOT / "research-project-os/assets/base/AGENTS.md.tmpl").read_text(
            encoding="utf-8"
        )

        self.assertIn("executable lab notebook", skill)
        self.assertIn("Keep one-off logic inline", skill)
        self.assertIn("允许少量重复", lifecycle)
        self.assertIn("Chinese outline", skill)
        self.assertIn("Chinese outline contract", lifecycle)
        self.assertIn("# %% 1. 读取输入与参数", lifecycle)
        self.assertIn("跨文件 abstractions", agents)
        self.assertIn("编号中文", agents)
        self.assertIn("模块化、参数化、复用接口", agents)

    def test_validator_candidate_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            configured = home / "custom"
            candidates = VALIDATOR.validator_candidates(
                codex_home=str(configured),
                home=home,
            )
            self.assertEqual(
                candidates,
                [
                    configured / VALIDATOR.VALIDATOR_RELATIVE,
                    home / ".codex" / VALIDATOR.VALIDATOR_RELATIVE,
                    home / ".agents" / VALIDATOR.VALIDATOR_RELATIVE,
                ],
            )

    def test_installer_uses_full_root_workspace_and_symlinks(self) -> None:
        installer = ROOT / "scripts/install_skill.py"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            skill = source / "research-project-os"
            (skill / "scripts").mkdir(parents=True)
            (source / "pixi.toml").write_text("[workspace]\nname='test'\n")
            (source / "pixi.lock").write_text("version: 6\n")
            (skill / "SKILL.md").write_text(
                "---\nname: research-project-os\ndescription: test\n---\n"
            )
            (skill / "scripts/research_project_os.py").write_text("print('test')\n")
            subprocess.run(["git", "init", "-q", "-b", "main", source], check=True)
            subprocess.run(
                ["git", "-C", str(source), "add", "."],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(source),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "fixture",
                ],
                check=True,
            )
            workspace = base / "installed"
            codex_link = base / "codex/research-project-os"
            agents_link = base / "agents/research-project-os"
            command = [
                sys.executable,
                str(installer),
                "--source",
                str(source),
                "--workspace",
                str(workspace),
                "--codex-link",
                str(codex_link),
                "--agents-link",
                str(agents_link),
            ]
            dry_run = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("DRY-RUN", dry_run.stdout)
            self.assertFalse(workspace.exists())

            subprocess.run([*command, "--apply"], check=True)
            self.assertTrue((workspace / "pixi.toml").is_file())
            self.assertTrue((workspace / "pixi.lock").is_file())
            self.assertFalse((workspace / "research-project-os/pixi.toml").exists())
            self.assertEqual(
                codex_link.resolve(),
                workspace / "research-project-os",
            )
            self.assertEqual(
                agents_link.resolve(),
                workspace / "research-project-os",
            )


if __name__ == "__main__":
    unittest.main()
