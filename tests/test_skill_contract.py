"""Packaging, layering, and concise Skill contracts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "research-project-os"
VALIDATOR_PATH = ROOT / "tests/validate_skill.py"
SPEC = importlib.util.spec_from_file_location("validate_skill", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load validate_skill")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class SkillContractTests(unittest.TestCase):
    def test_skill_is_concise_and_uses_three_layers(self) -> None:
        skill = SKILL / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        self.assertLessEqual(len(content.splitlines()), 100)
        self.assertLessEqual(len(content), 8_000)
        references = SKILL / "references"
        self.assertEqual(
            {path.name for path in references.glob("*.md")},
            {"harness.md", "exploration.md", "reporting.md"},
        )
        total = len(content) + sum(
            len(path.read_text(encoding="utf-8")) for path in references.glob("*.md")
        )
        self.assertLessEqual(total, 20_000)
        for target in re.findall(r"\]\((references/[^)]+)\)", content):
            self.assertTrue((SKILL / target).is_file(), target)

    def test_removed_surfaces_are_absent(self) -> None:
        profiles = SKILL / "assets/profiles"
        notion = SKILL / "assets/base/work/notion_sync"
        self.assertFalse(
            profiles.exists() and any(path.is_file() for path in profiles.rglob("*"))
        )
        self.assertFalse(
            notion.exists() and any(path.is_file() for path in notion.rglob("*"))
        )
        self.assertFalse(
            (SKILL / "assets/base/reports/evidence_registry.yaml").exists()
        )
        help_text = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts/research_project_os.py"),
                "--help",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertNotIn("sync-export", help_text)
        self.assertNotIn("sync-audit", help_text)
        self.assertNotIn("--profile", help_text)

    def test_preserved_human_and_code_contracts(self) -> None:
        agents = (SKILL / "assets/base/AGENTS.md.tmpl").read_text(encoding="utf-8")
        questions = (SKILL / "assets/base/QUESTIONS.md").read_text(encoding="utf-8")
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        exploration = (SKILL / "references/exploration.md").read_text(encoding="utf-8")
        reporting = (SKILL / "references/reporting.md").read_text(encoding="utf-8")
        script = (SKILL / "research_project_os/lifecycle.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "You may use superpowers, but do not write any spec or plan.",
            agents,
        )
        for required_context in (
            "## Session bootstrap",
            "`AGENTS.md`：稳定规则与安全边界",
            "`QUESTIONS.md`：Project purpose",
            "`CURRENT_HANDOFF.md`：当前 objective",
            "`project_manifest.yaml`：ownership",
            "默认不加载历史 report",
            "若上下文缺失、互相冲突或 current question 未明确",
        ):
            self.assertIn(required_context, agents)
        self.assertIn("## Superpowers", agents)
        self.assertIn("不得绕过", agents)
        self.assertIn("遵循第一性原理", agents)
        self.assertIn("结束实质工作时通过 `close`", agents)
        self.assertIn("本文件完全由 human 维护", questions)
        self.assertIn("## Filling guide", questions)
        self.assertLess(
            questions.index("## Filling guide"),
            questions.index("## Project purpose"),
        )
        for heading in (
            "Project purpose",
            "Input constraints",
            "Output requirements",
            "FAQ",
            "Questions",
        ):
            self.assertIn(f"## {heading}", questions)
        for status in ("queued", "current", "answered", "deferred", "cancelled"):
            self.assertIn(f"`{status}`", questions)
        for meaning in (
            "问题已登记，但尚未批准启动",
            "当前唯一正在讨论、执行或按审核意见返工的问题",
            "human 已审核并决定关闭",
            "暂时搁置",
            "明确停止，不再尝试回答",
        ):
            self.assertIn(meaning, questions)
        for decision in (
            "pending",
            "accepted",
            "accepted_with_limitations",
            "inconclusive",
            "rework_required",
            "not_applicable",
        ):
            self.assertIn(f"`{decision}`", questions)
        self.assertIn("- Review decision: `pending`", questions)
        self.assertIn("- Reviewed on: `pending`", questions)
        self.assertIn("详细结果留在 task/archive", questions)
        self.assertIn("#### Reviewed outcome", questions)
        self.assertIn("#### Evidence", questions)
        self.assertIn("允许少量重复", exploration)
        for contract in (skill, exploration, agents):
            self.assertIn("减少函数封装和工程化代码", contract)
        self.assertIn("# %% 1. 读取输入与参数", exploration)
        self.assertIn("不得包含 HTML", agents)
        self.assertIn("markdown-it-py", reporting)
        self.assertIn("HTTPS citations", reporting)
        template = re.search(
            r'def analysis_script_text\(\).*?return """(?P<body>.*?)"""',
            script,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(template)
        generated = template.group("body").lower()
        for forbidden in ("<html", "<style", "build_report", "report-build"):
            self.assertNotIn(forbidden, generated)

    def test_reporting_api_is_public_and_cli_is_thin(self) -> None:
        package = SKILL / "research_project_os"
        self.assertTrue((package / "reporting.py").is_file())
        self.assertTrue((package / "lifecycle.py").is_file())
        self.assertTrue((package / "handoff.py").is_file())
        self.assertTrue((package / "audit.py").is_file())
        init = (package / "__init__.py").read_text(encoding="utf-8")
        for symbol in (
            "ReportBuild",
            "ReportKind",
            "build_report",
            "build_report_text",
            "validate_report",
        ):
            self.assertIn(symbol, init)
        entrypoint = (SKILL / "scripts/research_project_os.py").read_text(
            encoding="utf-8"
        )
        self.assertLessEqual(len(entrypoint.splitlines()), 25)
        self.assertIn("from research_project_os.cli import main", entrypoint)

    def test_workspace_dependency_and_release(self) -> None:
        workspace = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        self.assertEqual(workspace["workspace"]["version"], "0.7.1")
        self.assertIn("markdown-it-py", workspace["dependencies"])
        self.assertNotIn("pip", workspace["dependencies"])

    def test_eval_boundaries_cover_html_and_audited_run(self) -> None:
        evals = json.loads((SKILL / "evals/evals.json").read_text(encoding="utf-8"))
        prompts = "\n".join(value["prompt"] for value in evals["evals"])
        self.assertIn("HTML report", prompts)
        self.assertIn("full input/output provenance", prompts)
        self.assertEqual(
            {value["should_trigger"] for value in evals["evals"]},
            {True, False},
        )

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
            (skill / "research_project_os").mkdir()
            (source / "pixi.toml").write_text("[workspace]\nname='test'\n")
            (source / "pixi.lock").write_text("version: 6\n")
            (skill / "SKILL.md").write_text(
                "---\nname: research-project-os\ndescription: test\n---\n"
            )
            (skill / "scripts/research_project_os.py").write_text("print('test')\n")
            (skill / "research_project_os/__init__.py").write_text(
                "__version__ = '0.7.1'\n"
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
            self.assertEqual(codex_link.resolve(), workspace / "research-project-os")
            self.assertEqual(agents_link.resolve(), workspace / "research-project-os")


if __name__ == "__main__":
    unittest.main()
