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
SKILLS = ("research-context",)


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
    def test_repository_agents_protected_contract(self) -> None:
        content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        language = (
            "## Language\n\n"
            "项目说明默认使用中文。稳定的 engineering terms、machine-readable contract 和\n"
            "文件名保持英文。"
        )
        environment = (
            "## Environment\n\n"
            "- 使用 Pixi 管理 dependencies 和 tasks。\n"
            "- 仓库只允许根级 Pixi workspace；不得跟踪 `.pixi/`。\n"
            "- 不得手动编辑 `pixi.lock`。\n"
            "- pixi环境构建调用 `pixi-environment-builder` skill。"
        )
        principles = "## 总原则\n\n- 遵循第一性原理、奥卡姆剃刀原理"
        self.assertIn(language, content)
        self.assertIn(environment, content)
        self.assertIn(principles, content)

    def test_exactly_one_installable_skill(self) -> None:
        discovered = {
            path.parent.name
            for path in ROOT.glob("*/SKILL.md")
            if path.parent.is_dir()
        }
        self.assertEqual(discovered, set(SKILLS))
        self.assertFalse((ROOT / "report-generation").exists())
        self.assertFalse((ROOT / ("research-project-" + "os")).exists())

    def test_references_are_routed_by_concise_skill_files(self) -> None:
        expected = {
            "context.md",
            "delegation.md",
            "decisions.md",
        }
        skill = ROOT / "research-context/SKILL.md"
        content = skill.read_text(encoding="utf-8")
        self.assertLessEqual(len(content), 6_000)
        self.assertEqual(
            {path.name for path in (ROOT / "research-context/references").glob("*.md")},
            expected,
        )
        for reference in expected:
            self.assertIn(f"references/{reference}", content)

    def test_no_nested_pixi_workspace(self) -> None:
        for name in SKILLS:
            for relative in ("pixi.toml", "pixi.lock", ".pixi"):
                self.assertFalse((ROOT / name / relative).exists())

    def test_skill_keeps_first_principles_and_single_context(self) -> None:
        content = (ROOT / "research-context/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("第一性原理", content)
        self.assertIn("Occam's razor", content)
        self.assertIn("context.md", content)
        self.assertIn("doc/context.md", content)
        self.assertNotIn("BRIEF.md", content)
        self.assertNotIn("CURRENT_HANDOFF.md", content)
        self.assertNotIn("report-generation", content)

    def test_removed_brand_and_legacy_tools_are_absent(self) -> None:
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
        self.assertFalse(
            (ROOT / "research-context/scripts/scaffold_project.py").exists()
        )
        self.assertFalse((ROOT / "report-generation/scripts/generate_report.py").exists())

    def test_workspace_tasks_and_version(self) -> None:
        manifest = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["workspace"]["version"], "1.0.0")
        for task in ("lint", "test", "smoke", "validate-skill"):
            self.assertIn(task, manifest["tasks"])
        for removed in (
            "scaffold-project",
            "record-project",
            "validate-project",
            "generate-report",
        ):
            self.assertNotIn(removed, manifest["tasks"])
        self.assertNotIn("pip", manifest["dependencies"])
        self.assertNotIn("markdown-it-py", manifest["dependencies"])

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

    def test_openai_metadata_matches_skill_names(self) -> None:
        for name in SKILLS:
            content = (ROOT / name / "agents/openai.yaml").read_text(encoding="utf-8")
            self.assertIn(f"${name}", content)
            self.assertIn("default_prompt:", content)

    def test_installer_validates_current_workspace(self) -> None:
        INSTALLER.validate_workspace(ROOT)

    def test_installer_creates_two_discovery_links(self) -> None:
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
            self.assertEqual(len(plan["links"]), 2)
            self.assertFalse(workspace.exists())
            INSTALLER.apply_plan(plan)
            for parent in ("codex", "agents"):
                link = base / parent / "research-context"
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.resolve(), workspace / "research-context")


if __name__ == "__main__":
    unittest.main()
