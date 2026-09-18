"""Exercise lossless pagination and stale-cursor protection through the CLI."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("context_read.py")


class ContextReadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "context with spaces.md"

    def run_reader(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.path), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def read_page(self, *args):
        result = self.run_reader(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = json.loads(result.stdout)
        self.assertTrue(page["window_complete"])
        return page

    def test_full_recovery_across_unicode_long_lines_and_newline_styles(self):
        cases = [
            "",
            "最后一条：受试者而非细胞是推断单位。",
            "# 目标\r\n病例与对照\r\n\r\n限制仍有效\r\n",
            "长单行🧬e\u0301" * 1500 + "尾部反例不可丢失",
        ]
        for source in cases:
            with self.subTest(length=len(source)):
                original = source.encode("utf-8")
                self.path.write_bytes(original)
                digest = hashlib.sha256(original).hexdigest()
                start = 0
                recovered = []
                while True:
                    page = self.read_page(
                        "--chars", 997, "--start", start, "--expect-sha256", digest
                    )
                    self.assertEqual(page["sha256"], digest)
                    self.assertEqual(page["total_chars"], len(source))
                    self.assertEqual(page["start"], start)
                    self.assertLessEqual(len(page["text"]), 997)
                    self.assertEqual(page["end"], start + len(page["text"]))
                    recovered.append(page["text"])
                    if page["eof"]:
                        self.assertIsNone(page["next_start"])
                        self.assertEqual(page["end"], len(source))
                        break
                    self.assertGreater(page["next_start"], start)
                    self.assertEqual(page["next_start"], page["end"])
                    start = page["next_start"]
                self.assertEqual("".join(recovered), source)
                self.assertEqual(self.path.read_bytes(), original)

    def test_default_window_and_resume_in_a_new_process(self):
        self.path.write_text("依据" * 2000 + "未决", encoding="utf-8")
        first = self.read_page()
        self.assertEqual(len(first["text"]), 2000)
        self.assertFalse(first["eof"])
        second = self.read_page(
            "--start", first["next_start"], "--expect-sha256", first["sha256"]
        )
        self.assertEqual(second["start"], first["end"])

    def test_stale_cursor_rejects_changed_file_without_emitting_content(self):
        self.path.write_text("待核实结果" * 1000, encoding="utf-8")
        first = self.read_page()
        self.path.write_text("已改变的结果" * 1000, encoding="utf-8")
        result = self.run_reader(
            "--start", first["next_start"], "--expect-sha256", first["sha256"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("fingerprint changed", result.stderr)

    def test_invalid_offsets_and_budgets_fail_without_emitting_content(self):
        self.path.write_text("abc", encoding="utf-8")
        digest = hashlib.sha256(b"abc").hexdigest()
        cases = [
            ("--start", -1),
            ("--chars", 0),
            ("--chars", -1),
            ("--start", 1),
            ("--start", 4, "--expect-sha256", digest),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_reader(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_missing_and_non_utf8_files_fail_without_emitting_content(self):
        result = self.run_reader()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.path.write_bytes(b"\xff\xfe")
        result = self.run_reader()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
