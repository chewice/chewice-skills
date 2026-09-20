#!/usr/bin/env python3
"""Offline CLI regressions for source eligibility and read-file identity."""

import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SELECTOR = Path(__file__).resolve().parents[1] / "scripts/select_sources.py"
MD5_A = "a" * 32
MD5_B = "b" * 32


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="geo-source-selection-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "selected.tsv"

    def write_tsv(self, filename, rows, empty_fields):
        path = self.root / filename
        fields = list(dict.fromkeys(key for row in rows for key in row)) or empty_fields
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def select(self, *, ena=None, ngdc=None, layout="PAIRED", preference="auto", product="fastq"):
        expected = self.write_tsv(
            "expected.tsv",
            [{"gse": "GSE1", "gsm": "GSM1", "srr": "SRR1", "library_layout": layout}],
            [],
        )
        ena_path = self.write_tsv("ena.tsv", [ena] if ena else [], ["run_accession"])
        ngdc_path = self.write_tsv("ngdc.tsv", [ngdc] if ngdc else [], ["srr"])
        return subprocess.run(
            [
                sys.executable, str(SELECTOR),
                "--expected", str(expected),
                "--ena", str(ena_path),
                "--ngdc", str(ngdc_path),
                "--root", str(self.root),
                "--output", str(self.output),
                "--source-preference", preference,
                "--final-product", product,
            ],
            cwd=SELECTOR.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def selected_row(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.output.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 1)
        return rows[0]

    def assert_rejection(self, row, source, field):
        reason = row["selection_reason"].lower()
        self.assertIn(source.lower(), reason)
        self.assertIn(field.lower(), reason)

    def generated_pair(self):
        return {
            "run_accession": "SRR1",
            "fastq_ftp": "ftp.sra.ebi.ac.uk/SRR1_1.fastq.gz;ftp.sra.ebi.ac.uk/SRR1_2.fastq.gz",
            "fastq_bytes": "100;200",
            "fastq_md5": f"{MD5_A};{MD5_B}",
        }

    def submitted_pair(self):
        return {
            "run_accession": "SRR1",
            "submitted_ftp": "ftp.sra.ebi.ac.uk/sample_R1.fastq.gz;ftp.sra.ebi.ac.uk/sample_R2.fastq.gz",
            "submitted_bytes": "110;210",
            "submitted_md5": f"{MD5_A};{MD5_B}",
        }

    def test_sra_product_selects_archive_instead_of_fastq(self):
        ena = {**self.generated_pair(), **self.submitted_pair()}
        row = self.selected_row(self.select(ena=ena, product="sra"))
        self.assertEqual(row["selected_source"], "ncbi_sra")
        self.assertEqual(row["object_class"], "FULL_QUALITY_ARCHIVE")
        self.assertEqual(row["read_roles"], "SRA")
        self.assert_rejection(row, "ena_submitted", "final_product")

    def test_invalid_submitted_metadata_falls_back_to_valid_generated_files(self):
        invalid_values = {
            "submitted_md5": ["", "invalid;invalid", f"{MD5_A};", f"{MD5_A};{'z' * 32}"],
            "submitted_bytes": ["", "110;", "110;not-a-number", "110;0", "110;-1", "110;1.5"],
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    ena = {**self.generated_pair(), **self.submitted_pair(), field: value}
                    row = self.selected_row(self.select(ena=ena))
                    self.assertEqual(row["selected_source"], "ena_fastq")
                    self.assertEqual(row["selected_urls"].split(";"), [
                        "https://ftp.sra.ebi.ac.uk/SRR1_1.fastq.gz",
                        "https://ftp.sra.ebi.ac.uk/SRR1_2.fastq.gz",
                    ])
                    self.assert_rejection(row, "ena_submitted", field.removeprefix("submitted_"))

    def test_explicit_ena_cannot_fall_back_to_ncbi_or_replace_old_manifest(self):
        ena = {**self.submitted_pair(), "submitted_md5": ""}
        original = "previous manifest must survive\n"
        self.output.write_text(original)
        result = self.select(ena=ena, preference="ena")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), original)
        self.assertIn("ena_submitted", result.stderr.lower())
        self.assertIn("md5", result.stderr.lower())

    def test_same_submitted_urls_can_use_complete_fastq_metadata(self):
        ena = self.submitted_pair()
        ena.update({
            "submitted_md5": "",
            "fastq_ftp": ena["submitted_ftp"],
            "fastq_file_role": "SUBMITTED_FILE;SUBMITTED_FILE",
            "fastq_bytes": "100;200",
            "fastq_md5": f"{MD5_A};{MD5_B}",
        })
        row = self.selected_row(self.select(ena=ena, preference="ena"))
        self.assertEqual(row["selected_source"], "ena_submitted")
        self.assertEqual(row["selected_provenance"], "AUTHOR_SUBMITTED")
        self.assertEqual(row["selected_md5"], ena["fastq_md5"])
        self.assertEqual(row["selected_bytes"], ena["fastq_bytes"])
        self.assertEqual(row["selected_urls"], ";".join(
            "https://" + url for url in ena["fastq_ftp"].split(";")
        ))
        self.assert_rejection(row, "ena_submitted", "md5")

    def test_sra_product_with_explicit_ena_fails_without_writing_manifest(self):
        result = self.select(ena=self.generated_pair(), preference="ena", product="sra")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_ambiguous_submitted_pair_is_not_assigned_roles_by_array_order(self):
        ena = {
            **self.submitted_pair(),
            "submitted_ftp": "ftp.sra.ebi.ac.uk/a.fastq.gz;ftp.sra.ebi.ac.uk/b.fastq.gz",
        }
        result = self.select(ena=ena, preference="ena")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_ambiguous_submitted_pair_can_fall_back_to_named_generated_pair(self):
        ena = {
            **self.generated_pair(), **self.submitted_pair(),
            "submitted_ftp": "ftp.sra.ebi.ac.uk/a.fastq.gz;ftp.sra.ebi.ac.uk/b.fastq.gz",
        }
        row = self.selected_row(self.select(ena=ena, preference="ena"))
        self.assertEqual(row["selected_source"], "ena_fastq")
        self.assertEqual(row["read_roles"], "R1;R2")
        self.assert_rejection(row, "ena_submitted", "role")

    def test_duplicate_lane_roles_fall_back_or_fail_when_no_alternative_exists(self):
        submitted = {
            "run_accession": "SRR1",
            "submitted_ftp": ";".join(
                f"ftp.sra.ebi.ac.uk/sample_L00{lane}_R{read}.fastq.gz"
                for lane in (1, 2) for read in (1, 2)
            ),
            "submitted_bytes": "100;100;100;100",
            "submitted_md5": ";".join([MD5_A] * 4),
        }
        row = self.selected_row(self.select(ena={**self.generated_pair(), **submitted}, preference="ena"))
        self.assertEqual(row["selected_source"], "ena_fastq")
        self.assert_rejection(row, "ena_submitted", "role")
        previous = self.output.read_text()
        result = self.select(ena=submitted, preference="ena")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), previous)

    def test_normal_single_submitted_file_remains_usable(self):
        ena = {
            "run_accession": "SRR1", "submitted_ftp": "ftp.sra.ebi.ac.uk/sample.fastq.gz",
            "submitted_bytes": "100", "submitted_md5": MD5_A,
        }
        row = self.selected_row(self.select(ena=ena, layout="SINGLE"))
        self.assertEqual(row["selected_source"], "ena_submitted")
        self.assertEqual(row["read_roles"], "R1")

    def test_normal_submitted_pair_remains_preferred_over_generated_pair(self):
        row = self.selected_row(self.select(ena={**self.generated_pair(), **self.submitted_pair()}))
        self.assertEqual(row["selected_source"], "ena_submitted")
        self.assertEqual(row["read_roles"], "R1;R2")

    def test_index_reads_keep_roles_and_order(self):
        ena = {
            "run_accession": "SRR1",
            "submitted_ftp": ";".join(
                f"ftp.sra.ebi.ac.uk/sample_{role}.fastq.gz" for role in ("I2", "R2", "I1", "R1")
            ),
            "submitted_bytes": "40;200;30;100",
            "submitted_md5": ";".join([MD5_A] * 4),
        }
        row = self.selected_row(self.select(ena=ena))
        self.assertEqual(row["selected_source"], "ena_submitted")
        self.assertEqual(row["read_roles"], "I2;R2;I1;R1")
        self.assertEqual(row["selected_bytes"], "40;200;30;100")

    def test_ngdc_full_archive_with_content_length_remains_usable(self):
        ngdc = {
            "srr": "SRR1", "ngdc_status": "available", "ngdc_file_type": "sra",
            "ngdc_url": "https://example.invalid/SRR1.sra", "ngdc_bytes": "500",
        }
        for product in ("sra", "fastq"):
            with self.subTest(product=product):
                row = self.selected_row(self.select(ngdc=ngdc, product=product))
                self.assertEqual(row["selected_source"], "ngdc_insdc")
                self.assertEqual(row["object_class"], "FULL_QUALITY_ARCHIVE")
                self.assertEqual(row["read_roles"], "SRA")


if __name__ == "__main__":
    unittest.main()
