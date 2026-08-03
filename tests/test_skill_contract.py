"""Packaging, naming, installation, and progressive-disclosure contracts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("research-project-workflow", "report-generation")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


INSTALLER = load_module("install_skill", ROOT / "scripts/install_skill.py")


class SkillContractTests(unittest.TestCase):
    def test_exactly_two_installable_skills(self) -> None:
        discovered = {
            path.parent.name
            for path in ROOT.glob("*/SKILL.md")
            if path.parent.is_dir()
        }
        self.assertEqual(discovered, set(SKILLS))
        self.assertFalse((ROOT / ("research-project-" + "os")).exists())

    def test_references_are_routed_by_concise_skill_files(self) -> None:
        expected = {
            "research-project-workflow": {
                "scaffold.md",
                "question.md",
                "explore.md",
                "handoff.md",
                "summarize-work.md",
            },
            "report-generation": {
                "html.md",
                "pdf.md",
                "templates.md",
                "validation.md",
            },
        }
        for name, references in expected.items():
            skill = ROOT / name / "SKILL.md"
            content = skill.read_text(encoding="utf-8")
            self.assertLessEqual(len(content), 6_000)
            self.assertEqual(
                {path.name for path in (ROOT / name / "references").glob("*.md")},
                references,
            )
            for reference in references:
                self.assertIn(f"references/{reference}", content)

    def test_no_nested_pixi_workspace(self) -> None:
        for name in SKILLS:
            for relative in ("pixi.toml", "pixi.lock", ".pixi"):
                self.assertFalse((ROOT / name / relative).exists())

    def test_removed_brand_and_cli_are_absent_from_deliverables(self) -> None:
        forbidden = (
            "R" + "POS",
            "r" + "pos",
            "Research Project " + "OS",
            "research_project_" + "os",
        )
        files = [ROOT / "README.md", *ROOT.glob("docs/*.md")]
        for directory in (*SKILLS, "scripts"):
            files.extend(
                path
                for path in (ROOT / directory).rglob("*")
                if path.is_file() and path.suffix in {".md", ".py", ".json", ".yaml"}
            )
        for path in files:
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text, str(path))
        help_text = subprocess.run(
            [
                sys.executable,
                str(ROOT / "research-project-workflow/scripts/scaffold_project.py"),
                "--help",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for command in (
            "archive-" + "promote",
            "pipeline-" + "create",
            "report-" + "build",
        ):
            self.assertNotIn(command, help_text)

    def test_workspace_tasks_and_version(self) -> None:
        manifest = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["workspace"]["version"], "1.0.0")
        for task in (
            "scaffold-project",
            "validate-project",
            "generate-report",
            "lint",
            "test",
            "smoke",
            "validate-skill",
        ):
            self.assertIn(task, manifest["tasks"])
        self.assertNotIn("pip", manifest["dependencies"])

    def test_eval_boundaries_have_positive_and_negative_cases(self) -> None:
        for name in SKILLS:
            values = json.loads(
                (ROOT / name / "evals/evals.json").read_text(encoding="utf-8")
            )
            self.assertEqual(values["skill_name"], name)
            self.assertEqual(
                {item["should_trigger"] for item in values["evals"]},
                {True, False},
            )

    def test_installer_validates_current_workspace(self) -> None:
        INSTALLER.validate_workspace(ROOT)

    def test_installer_creates_four_discovery_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(".git", ".pixi", "__pycache__", "*.pyc"),
            )
            subprocess.run(["git", "init", "-q", "-b", "main", source], check=True)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
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
            args = INSTALLER.parse_args(
                [
                    "--source",
                    str(source),
                    "--workspace",
                    str(workspace),
                    "--codex-skills-dir",
                    str(base / "codex"),
                    "--agents-skills-dir",
                    str(base / "agents"),
                ]
            )
            plan = INSTALLER.build_plan(args)
            self.assertEqual(len(plan["links"]), 4)
            self.assertFalse(workspace.exists())
            INSTALLER.apply_plan(plan)
            for parent in ("codex", "agents"):
                for name in SKILLS:
                    link = base / parent / name
                    self.assertTrue(link.is_symlink())
                    self.assertEqual(link.resolve(), workspace / name)


if __name__ == "__main__":
    unittest.main()
