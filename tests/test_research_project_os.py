"""Unit tests for the Research Project OS CLI."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import tomllib
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "research-project-os/scripts/research_project_os.py"
SPEC = importlib.util.spec_from_file_location("research_project_os", CLI_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load Research Project OS CLI")
RPOS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RPOS
SPEC.loader.exec_module(RPOS)


class ResearchProjectOSTests(unittest.TestCase):
    def test_inspect_recommends_init_for_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = RPOS.inspect_project(Path(temporary))
            self.assertEqual(result["recommended_mode"], "init")
            self.assertFalse(result["governed"])
            self.assertEqual(
                result["project_inventory"],
                {category: [] for category in RPOS.PROJECT_INVENTORY_PATTERNS},
            )

    def test_init_is_dry_run_and_idempotent_after_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = RPOS.plan_scaffold(root, "generic-analysis", "init", overwrite=False)
            self.assertTrue(any(action.action == "create" for action in plan["actions"]))
            self.assertFalse((root / "project_manifest.yaml").exists())

            applied = RPOS.apply_scaffold(plan, init_git=False)
            self.assertIn("project_manifest.yaml", applied["written"])
            self.assertTrue(RPOS.audit_project(root)["ok"])

            second = RPOS.plan_scaffold(root, "generic-analysis", "adopt", overwrite=False)
            changed = [
                action
                for action in second["actions"]
                if action.action in {"create", "overwrite"}
            ]
            self.assertEqual(changed, [])

    def test_generated_project_uses_chinese_explanations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = RPOS.plan_scaffold(root, "bioinformatics", "init", overwrite=False)
            RPOS.apply_scaffold(plan, init_git=False)

            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            handoff = (root / "CURRENT_HANDOFF.md").read_text(encoding="utf-8")
            manifest = (root / "project_manifest.yaml").read_text(encoding="utf-8")

            self.assertIn("项目说明默认使用中文", agents)
            self.assertIn("已采用 Research Project OS control layer", handoff)
            self.assertIn("biological replicate", manifest)
            self.assertIn("schema_version: 0.3.0", manifest)
            self.assertIn("portfolio_title:", manifest)
            self.assertIn("## Current objective", handoff)

    def test_adopt_preserves_existing_agents_and_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("existing agents\n", encoding="utf-8")
            (root / ".gitignore").write_text("existing ignore\n", encoding="utf-8")
            (root / "analysis.py").write_text("print('existing')\n", encoding="utf-8")
            plan = RPOS.plan_scaffold(root, "bioinformatics", "adopt", overwrite=True)
            RPOS.apply_scaffold(plan, init_git=False)
            self.assertEqual(
                (root / "AGENTS.md").read_text(encoding="utf-8"),
                "existing agents\n",
            )
            self.assertEqual(
                (root / ".gitignore").read_text(encoding="utf-8"),
                "existing ignore\n",
            )
            self.assertTrue(
                (root / "docs/research_project_os/AGENTS.additions.md").is_file()
            )
            self.assertTrue((root / "project_manifest.yaml").is_file())
            for path in ("analysis", "config", "data", "results", "scripts", "tests"):
                self.assertFalse((root / path).exists())

    def test_adopt_recommends_profile_directories_without_creating_them(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "existing_workflow.py").write_text("print('keep')\n", encoding="utf-8")

            plan = RPOS.plan_scaffold(root, "bioinformatics", "adopt", overwrite=False)

            self.assertNotIn("analysis", plan["directories"])
            self.assertNotIn("data/metadata", plan["directories"])
            self.assertIn("analysis", plan["profile_directory_recommendations"])
            self.assertIn("data/metadata", plan["profile_directory_recommendations"])
            self.assertNotIn("docs", plan["profile_directory_recommendations"])
            self.assertNotIn("reports", plan["profile_directory_recommendations"])

            RPOS.apply_scaffold(plan, init_git=False)
            self.assertFalse((root / "analysis").exists())
            self.assertFalse((root / "data/metadata").exists())
            structure = (root / "docs/ai_context/project_structure.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("profile 建议，`adopt` 不创建", structure)
            self.assertIn("作为 control layer parent 由 `adopt` 创建", structure)
            self.assertIn("existing_workflow.py", structure)
            self.assertEqual(
                (root / "existing_workflow.py").read_text(encoding="utf-8"),
                "print('keep')\n",
            )

    def test_profiles_create_distinct_directory_plans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bio = RPOS.plan_scaffold(root, "bioinformatics", "init", overwrite=False)
            self.assertIn("data/metadata", bio["directories"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            software = RPOS.plan_scaffold(
                root,
                "software-development",
                "init",
                overwrite=False,
            )
            self.assertIn("src", software["directories"])
            self.assertNotIn("data/metadata", software["directories"])

    def test_inspect_uses_bounded_project_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "data/deep/scripts").mkdir(parents=True)
            (root / "results").mkdir()
            (root / "docs").mkdir()
            (root / "pixi.toml").write_text("[workspace]\nname='test'\n", encoding="utf-8")
            child = root / "pixi-workspaces/analysis"
            child.mkdir(parents=True)
            (child / "pixi.toml").write_text("[workspace]\nname='child'\n", encoding="utf-8")

            inventory = RPOS.inspect_project(root)["project_inventory"]

            self.assertEqual(inventory["code_roots"], ["scripts"])
            self.assertEqual(inventory["data_roots"], ["data"])
            self.assertEqual(inventory["artifact_roots"], ["results"])
            self.assertEqual(inventory["documentation_roots"], ["docs"])
            self.assertEqual(
                inventory["environment_files"],
                ["pixi-workspaces/analysis/pixi.toml", "pixi.toml"],
            )
            self.assertNotIn("data/deep/scripts", inventory["code_roots"])

    def test_governance_templates_cover_formal_artifacts_and_literature_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = RPOS.plan_scaffold(root, "literature-review", "init", overwrite=False)
            RPOS.apply_scaffold(plan, init_git=False)

            lineage = (root / "docs/ai_context/data_lineage.md").read_text(encoding="utf-8")
            manifest = (root / "project_manifest.yaml").read_text(encoding="utf-8")
            self.assertIn("produced_by", lineage)
            self.assertIn("environment_manifest", lineage)
            self.assertIn("environment_lock", lineage)
            self.assertIn("evidence_ids", lineage)
            self.assertIn("source query", manifest)
            self.assertIn("abstract-only evidence", manifest)

    def test_release_is_decoupled_from_stable_schemas_and_evals_cover_boundaries(self) -> None:
        workspace = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        evals = json.loads(
            (ROOT / "research-project-os/evals/evals.json").read_text(encoding="utf-8")
        )

        self.assertEqual(workspace["workspace"]["version"], "0.3.1")
        self.assertEqual(RPOS.RELEASE_VERSION, "0.3.1")
        self.assertEqual(RPOS.MANIFEST_SCHEMA_VERSION, "0.3.0")
        self.assertEqual(RPOS.SYNC_PAYLOAD_SCHEMA_VERSION, "0.3.0")
        trigger_values = {case["should_trigger"] for case in evals["evals"]}
        self.assertEqual(trigger_values, {True, False})
        prompts = "\n".join(case["prompt"] for case in evals["evals"])
        for term in ("Pixi", "QC", "STARsolo", "UMAP", "PubMed"):
            self.assertIn(term, prompts)

    def test_close_is_dry_run_then_archives_on_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = RPOS.plan_scaffold(root, "generic-analysis", "init", overwrite=False)
            RPOS.apply_scaffold(plan, init_git=False)
            args = SimpleNamespace(
                session_id="SES-20260716-002",
                summary="完成测试 session。",
                completed=["已验证 scaffold。"],
                evidence=["audit 已通过"],
                next_step="继续下一项最小任务。",
                owner="test",
                apply=False,
                overwrite=False,
            )
            dry_run = RPOS.close_session(root, args)
            self.assertFalse(dry_run["written"])
            self.assertFalse((root / dry_run["archive_path"]).exists())

            args.apply = True
            written = RPOS.close_session(root, args)
            self.assertTrue(written["written"])
            self.assertTrue((root / written["archive_path"]).is_file())
            self.assertTrue((root / written["payload_path"]).is_file())
            self.assertTrue(RPOS.audit_project(root)["ok"])

            payload = written["payload"]
            self.assertEqual(payload["schema_version"], "0.3.0")
            self.assertEqual(payload["payload_kind"], "session-close")
            self.assertEqual(
                payload["notion_target"]["allocation_policy"]["strategy"],
                "append_only_max_plus_one",
            )

    def test_numbering_is_append_only_and_expands_past_99(self) -> None:
        pages = [
            {"title": "01｜baseline", "stable_id": "OUT-1", "page_id": "page-1"},
            {"title": "09｜checkpoint", "stable_id": "OUT-9", "page_id": "page-9"},
        ]
        allocated = RPOS.allocate_numbered_page(
            pages,
            stable_id="OUT-10",
            title="next",
        )
        self.assertEqual(allocated["ordinal"], 10)
        self.assertEqual(allocated["numbered_title"], "10｜next")

        reused = RPOS.allocate_numbered_page(
            pages,
            stable_id="OUT-9",
            title="ignored",
        )
        self.assertEqual(reused["action"], "reuse")
        self.assertEqual(reused["ordinal"], 9)

        after_99 = RPOS.allocate_numbered_page(
            [{"title": "99｜latest", "stable_id": "OUT-99"}],
            stable_id="OUT-100",
            title="next",
        )
        self.assertEqual(after_99["numbered_title"], "100｜next")

    def test_numbering_conflicts_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            RPOS.allocate_numbered_page(
                [{"title": "not-numbered", "stable_id": "OUT-1"}],
                stable_id="OUT-2",
                title="next",
            )
        with self.assertRaises(ValueError):
            RPOS.allocate_numbered_page(
                [
                    {"title": "01｜one", "stable_id": "OUT-1"},
                    {"title": "01｜duplicate", "stable_id": "OUT-2"},
                ],
                stable_id="OUT-3",
                title="next",
            )

    def test_manifest_migration_preserves_ids(self) -> None:
        legacy = {
            "schema_version": "0.2.0",
            "project": {"id": "PRJ-TEST", "name": "test", "repository_root": "."},
            "notion": {
                "project_page_id": "old-page",
                "databases": {"projects": "collection://projects"},
            },
        }
        migrated = RPOS.migrate_manifest_schema(legacy)
        self.assertEqual(migrated["schema_version"], "0.3.0")
        self.assertEqual(migrated["notion"]["project_page_id"], "old-page")
        self.assertEqual(
            migrated["notion"]["databases"]["projects"],
            "collection://projects",
        )
        self.assertIsNone(migrated["notion"]["portfolio_page_id"])
        self.assertEqual(legacy["schema_version"], "0.2.0")

    def test_application_receipt_requires_complete_read_back(self) -> None:
        payload = {"payload_id": "SYNC-TEST"}
        receipt = RPOS.build_application_receipt(
            payload,
            page_ids={
                "portfolio": "portfolio-page",
                "control": "control-page",
                "project": "project-page",
                "output": "output-page",
            },
            assigned_ordinals={"project": 1, "output": 1},
            read_back={"verified": True},
            applied_at=datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(receipt["assigned_ordinals"]["output"], 1)
        self.assertTrue(receipt["read_back"]["verified"])

    def test_finalize_application_preserves_pending_payload_and_adds_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work/notion_sync/pending").mkdir(parents=True)
            (root / "work/notion_sync/applied").mkdir(parents=True)
            payload = {
                "schema_version": "0.3.0",
                "payload_id": "SYNC-TEST",
                "base": {"source_hashes": {}},
            }
            pending = root / "work/notion_sync/pending/SYNC-TEST.json"
            pending.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            result = RPOS.finalize_application(
                root,
                "SYNC-TEST",
                page_ids={
                    "portfolio": "portfolio-page",
                    "control": "control-page",
                    "project": "project-page",
                    "output": "output-page",
                },
                assigned_ordinals={"project": 1, "output": 1},
                read_back={"verified": True},
                applied_at=datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc),
            )
            self.assertFalse(pending.exists())
            applied = Path(result["applied"])
            self.assertTrue(applied.is_file())
            applied_payload = json.loads(applied.read_text(encoding="utf-8"))
            self.assertEqual(applied_payload["payload_id"], "SYNC-TEST")
            self.assertTrue(applied_payload["application"]["read_back"]["verified"])

    def test_init_rejects_non_empty_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "existing.txt").write_text("content\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                RPOS.plan_scaffold(root, "generic-analysis", "init", overwrite=False)


if __name__ == "__main__":
    unittest.main()
