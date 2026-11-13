import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pixi_diagnose.py"
spec = importlib.util.spec_from_file_location("pixi_diagnose", SCRIPT)
diagnose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnose)


class DiagnosticTests(unittest.TestCase):
    def test_arbitrary_output_is_not_disclosed(self):
        secret = "example-secret-123"
        samples = [
            json.dumps({"url": "https://user:" + secret + "@host", secret: secret}),
            "not json " + secret,
        ]
        for stdout in samples:
            with self.subTest(stdout=stdout), patch.object(
                diagnose.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, stdout, secret)
            ):
                result = diagnose.run_json(["pixi", "config"])
                self.assertNotIn(secret, json.dumps(result))
                self.assertTrue(result["stderr_present"])

    def test_failures_include_config_packages_and_invalid_json(self):
        args = argparse.Namespace(manifest_path=Path("."), extended=False, environment="gpu")

        def fake_run(command, **kwargs):
            output = "pixi 1.2.3" if "--version" in command else "{}"
            code = 0
            if "--local" in command:
                code = 1
            if "--frozen" in command:
                output = "invalid"
            return subprocess.CompletedProcess(command, code, output, "")

        with patch.object(diagnose.shutil, "which", return_value="pixi"), patch.object(
            diagnose.subprocess, "run", side_effect=fake_run
        ):
            report, status = diagnose.build_report(args)
        self.assertEqual(status, 1)
        self.assertEqual(set(report["failed_sections"]), {"config.local", "packages"})
        self.assertEqual(report["pixi_version"]["version"], "1.2.3")

    def test_missing_executable_and_command_start_failure(self):
        args = argparse.Namespace(manifest_path=Path("."), extended=False, environment=None)
        with patch.object(diagnose.shutil, "which", return_value=None):
            report, status = diagnose.build_report(args)
        self.assertEqual(status, 2)
        self.assertFalse(report["ok"])
        with patch.object(diagnose.subprocess, "run", side_effect=OSError("secret")):
            self.assertNotIn("secret", json.dumps(diagnose.run_text(["pixi"])))


if __name__ == "__main__":
    unittest.main()
