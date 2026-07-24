#!/usr/bin/env python3
"""Offline integration tests for the bundled GEO/SRA acquisition helpers."""

from __future__ import annotations

import csv
import functools
import gzip
import hashlib
import http.server
import os
import re
import subprocess
import sys
import tempfile
import threading
import tomllib
from html.parser import HTMLParser
from pathlib import Path

import h5py
import numpy as np
from scipy import sparse
from scipy.io import mmwrite


HERE = Path(__file__).resolve().parent


def run(
    *args: str,
    expect: int = 0,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, text=True, capture_output=True, check=False, env=env
    )
    if result.returncode != expect:
        raise AssertionError(
            f"command return {result.returncode}, expected {expect}: {args}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def write_tsv(
    path: Path,
    fields: list[str],
    rows: list[dict[str, str]],
    crlf: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\r\n" if crlf else "\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_fastq(path: Path, count: int, length: int = 28) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as handle:
        for index in range(count):
            handle.write(
                f"@read{index}\n"
                f"{'A' * length}\n+\n"
                f"{'I' * length}\n"
            )


def digest(path: Path) -> str:
    value = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def gzip_matrix(path: Path, matrix: sparse.spmatrix) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mtx") as temp:
        mmwrite(temp.name, matrix)
        with open(temp.name, "rb") as source, gzip.open(path, "wb") as target:
            target.write(source.read())


def gzip_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as handle:
        handle.writelines(f"{line}\n" for line in lines)


def final_outputs(project: Path, gsm: str) -> None:
    matrix_dir = project / gsm / "matrix_10x"
    raw = sparse.csr_matrix(
        np.asarray([[1, 0, 2], [0, 3, 0], [4, 0, 5]], dtype=np.int32)
    )
    filtered = raw[:, :2]
    features = ["g1\tG1\tGene Expression", "g2\tG2\tGene Expression", "g3\tG3\tGene Expression"]
    raw_barcodes = ["bc1", "bc2", "bc3"]
    filtered_barcodes = raw_barcodes[:2]
    for subset, matrix, barcodes in (
        ("raw", raw, raw_barcodes),
        ("filtered", filtered, filtered_barcodes),
    ):
        directory = matrix_dir / f"{subset}_feature_bc_matrix"
        gzip_matrix(directory / "matrix.mtx.gz", matrix)
        gzip_lines(directory / "features.tsv.gz", features)
        gzip_lines(directory / "barcodes.tsv.gz", barcodes)

    velocity = project / gsm / "velocity"
    for layer in ("spliced", "unspliced", "ambiguous"):
        gzip_matrix(velocity / f"{layer}.mtx.gz", raw)
    gzip_lines(velocity / "features.tsv.gz", features)
    gzip_lines(velocity / "barcodes.tsv.gz", raw_barcodes)
    loom_path = velocity / f"{gsm}.loom"
    loom_path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(loom_path, "w") as loom:
        loom.create_dataset("matrix", data=filtered.toarray())
        layers = loom.create_group("layers")
        for layer in ("spliced", "unspliced", "ambiguous"):
            layers.create_dataset(layer, data=filtered.toarray())
        loom.create_group("row_attrs")
        loom.create_group("col_attrs")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def unified_report_test(base: Path, project: Path) -> None:
    study_fields = [
        "gse",
        "title",
        "summary",
        "overall_design",
        "organism",
        "bioproject",
        "platforms",
        "expected_samples",
        "expected_runs",
        "publication",
        "metadata_retrieved_at",
    ]
    write_tsv(
        project / "metadata/study_metadata.tsv",
        study_fields,
        [
            {
                "gse": "GSE123456",
                "title": "中文测试 <script>alert('xss')</script>",
                "summary": "单细胞 RNA sequencing 数据集",
                "overall_design": "两个 GSM，三个 run",
                "organism": "Homo sapiens",
                "bioproject": "PRJNA123456",
                "platforms": "GPL24676",
                "expected_samples": "2",
                "expected_runs": "3",
                "publication": "",
                "metadata_retrieved_at": "2026-01-01",
            }
        ],
    )
    sample_fields = [
        "gse",
        "gsm",
        "title",
        "organism",
        "tissue",
        "condition",
        "treatment",
        "chemistry",
        "instrument_model",
        "run_count",
        "lane_count",
        "read_structure",
        "selected_source",
        "final_product",
        "status",
    ]
    write_tsv(
        project / "metadata/sample_metadata.tsv",
        sample_fields,
        [
            {
                "gse": "GSE123456",
                "gsm": "GSM100001",
                "title": "样本 A",
                "organism": "Homo sapiens",
                "tissue": "PBMC",
                "condition": "control",
                "treatment": "none",
                "chemistry": "10x 3' v3",
                "instrument_model": "NovaSeq 6000",
                "run_count": "2",
                "lane_count": "2",
                "read_structure": "R1:28,R2:91",
                "selected_source": "mixed",
                "final_product": "fastq",
                "status": "complete",
            }
        ],
    )
    write_tsv(
        project / "reports/tool_versions.tsv",
        ["tool", "version"],
        [{"tool": "STAR", "version": "2.7.11b"}],
    )
    legacy = project / "reports/preflight_summary.md"
    legacy.write_text("# 旧版摘要\n\n<script>alert('legacy')</script>\n")
    multiqc = project / "reports/multiqc_data/embedded_multiqc.html"
    multiqc.parent.mkdir(parents=True, exist_ok=True)
    multiqc.write_text(
        "<!doctype html><html><body><h1>MultiQC 完整报告</h1>"
        f"<p>{project}</p></body></html>"
    )
    starsolo = (
        project
        / "reports/starsolo/GSE123456/GSM100001/GeneFull_Summary.csv"
    )
    starsolo.parent.mkdir(parents=True, exist_ok=True)
    starsolo.write_text(
        "Number of Reads,100000\n"
        "Reads With Valid Barcodes,0.98\n"
        "Sequencing Saturation,0.72\n"
        "Reads Mapped to Genome: Unique,0.88\n"
        "Reads Mapped to GeneFull: Unique GeneFull,0.55\n"
        "Estimated Number of Cells,2345\n"
        "Fraction of Unique Reads in Cells,0.80\n"
        "Median Reads per Cell,30000\n"
        "Median UMI per Cell,4000\n"
        "Median GeneFull per Cell,2100\n"
    )
    run(
        sys.executable,
        str(HERE / "summarize_starsolo.py"),
        "--root",
        str(project),
    )
    run(
        sys.executable,
        str(HERE / "build_report.py"),
        "--root",
        str(project),
        "--multiqc-html",
        str(multiqc),
        "--consume-multiqc",
    )
    report = project / "reports/report.html"
    assert report.is_file() and report.stat().st_size > 1000
    assert not multiqc.exists()
    text = report.read_text()
    assert 'lang="zh-CN"' in text
    assert "目录与层级说明" in text
    assert "作者原始上传还是数据库转换" in text
    assert "STARsolo 跨样本 Summary" in text
    assert "Estimated Number of Cells" in text
    starsolo_rows = read_tsv(project / "reports/starsolo_summary.tsv")
    assert len(starsolo_rows) == 1
    assert starsolo_rows[0]["estimated_number_of_cells"] == "2345"
    assert "GSM*/fastq/" in text
    assert "../metadata/sample_metadata.tsv" in text
    assert str(project) not in text
    assert "<script>alert('xss')</script>" not in text
    assert "&lt;script&gt;alert(&#x27;legacy&#x27;)&lt;/script&gt;" in text
    assert "<script src=" not in text and "<link rel=" not in text
    HTMLParser().feed(text)
    assert [path.name for path in (project / "reports").rglob("*.html")] == [
        "report.html"
    ]

    payload_before = re.search(
        r'id="multiqc-data">([^<]+)</script>', text
    )
    assert payload_before
    run(
        sys.executable,
        str(HERE / "build_report.py"),
        "--root",
        str(project),
    )
    refreshed = report.read_text()
    payload_after = re.search(
        r'id="multiqc-data">([^<]+)</script>', refreshed
    )
    assert payload_after and payload_after.group(1) == payload_before.group(1)

    previous = report.read_bytes()
    outside = base / "outside_multiqc.html"
    outside.write_text("<html><body>outside</body></html>")
    run(
        sys.executable,
        str(HERE / "build_report.py"),
        "--root",
        str(project),
        "--multiqc-html",
        str(outside),
        "--consume-multiqc",
        expect=1,
    )
    assert report.read_bytes() == previous
    assert outside.is_file()


def downloader_smoke_test(base: Path) -> None:
    serve = base / "serve"
    project = base / "download_project"
    serve.mkdir(parents=True)
    (project / "metadata").mkdir(parents=True)
    r1_source = serve / "SRR20000001_1.fastq.gz"
    r2_source = serve / "SRR20000001_2.fastq.gz"
    write_fastq(r1_source, 2)
    write_fastq(r2_source, 2, 91)

    handler = functools.partial(QuietHandler, directory=str(serve))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    fields = [
        "gse", "gsm", "srx", "srr", "run_alias", "lane", "library_layout",
        "read_structure", "expected_spots", "cb_length", "umi_length",
        "ngdc_status", "ngdc_run_page", "ngdc_url", "ngdc_bytes",
        "selected_source", "selected_provenance", "selected_urls",
        "selected_bytes", "selected_md5", "read_roles", "final_product",
        "fallback_reason",
    ]
    row = {
        "gse": "GSE200000",
        "gsm": "GSM200001",
        "srx": "SRX200001",
        "srr": "SRR20000001",
        "run_alias": "fixture",
        "lane": "",
        "library_layout": "PAIRED",
        "read_structure": "R1:28,R2:91",
        "expected_spots": "2",
        "cb_length": "16",
        "umi_length": "12",
        "ngdc_status": "missing",
        "ngdc_run_page": "",
        "ngdc_url": "",
        "ngdc_bytes": "",
        "selected_source": "ena_fastq",
        "selected_provenance": "ARCHIVE_GENERATED_FASTQ",
        "selected_urls": (
            f"http://127.0.0.1:{port}/{r1_source.name};"
            f"http://127.0.0.1:{port}/{r2_source.name}"
        ),
        "selected_bytes": f"{r1_source.stat().st_size};{r2_source.stat().st_size}",
        "selected_md5": f"{'0' * 32};{digest(r2_source)}",
        "read_roles": "R1;R2",
        "final_product": "fastq",
        "fallback_reason": "ngdc_missing",
    }
    manifest = project / "metadata/source_manifest.tsv"
    write_tsv(manifest, fields, [row])
    environment = os.environ.copy()
    environment.update(
        {
            "GEO_SRA_MAX_ATTEMPTS": "1",
            "GEO_SRA_CONNECTIONS": "1",
            "GEO_SRA_RUN_FASTQC": "0",
            "http_proxy": "",
            "https_proxy": "",
            "all_proxy": "",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "ALL_PROXY": "",
        }
    )
    try:
        failed = subprocess.run(
            [
                "bash",
                str(HERE / "download_run.sh"),
                str(project),
                "SRR20000001",
            ],
            text=True,
            capture_output=True,
            env=environment,
        )
        assert failed.returncode != 0, (
            f"wrong-MD5 download unexpectedly succeeded\n"
            f"stdout:\n{failed.stdout}\nstderr:\n{failed.stderr}"
        )
        assert not (
            project / "GSM200001/fastq/SRR20000001_R1.fastq.gz"
        ).exists()

        row["selected_md5"] = f"{digest(r1_source)};{digest(r2_source)}"
        write_tsv(manifest, fields, [row])
        run(
            "bash",
            str(HERE / "download_run.sh"),
            str(project),
            "SRR20000001",
            env=environment,
        )
        assert (
            project / "GSM200001/fastq/SRR20000001_R1.fastq.gz"
        ).is_file()
        run(
            sys.executable,
            str(HERE / "audit_download_evidence.py"),
            "--root",
            str(project),
            "--deep",
        )
    finally:
        server.shutdown()
        server.server_close()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="geo-sra-skill-test-") as temporary:
        base = Path(temporary)
        run(
            sys.executable,
            str(HERE / "scaffold_project.py"),
            "--gse",
            "GSE123456",
            "--output-root",
            str(base),
            "--final-product",
            "fastq",
        )
        project = base / "GEO/GSE123456"
        assert (project / "pixi.toml").is_file()
        assert (project / "scripts/run_all.sh").is_file()
        assert (project / "reports/report.html").is_file()
        assert not (project / "reports/dataset_overview.md").exists()
        run("bash", "-n", str(project / "scripts/run_all.sh"))
        with (project / "pixi.toml").open("rb") as handle:
            pixi_manifest = tomllib.load(handle)
        assert "sra-tools" in pixi_manifest["dependencies"]
        assert "check-env" in pixi_manifest["tasks"]

        expected_fields = [
            "gse",
            "gsm",
            "srx",
            "srr",
            "run_alias",
            "lane",
            "library_layout",
            "read_structure",
            "expected_spots",
            "cb_length",
            "umi_length",
            "ngdc_run_page",
            "ngdc_url",
        ]
        expected_rows = [
            {
                "gse": "GSE123456",
                "gsm": "GSM100001",
                "srx": "SRX100001",
                "srr": "SRR10000001",
                "run_alias": "sampleA_L001",
                "lane": "L001",
                "library_layout": "PAIRED",
                "read_structure": "R1:28,R2:91",
                "expected_spots": "2",
                "cb_length": "16",
                "umi_length": "12",
                "ngdc_run_page": "",
                "ngdc_url": "",
            },
            {
                "gse": "GSE123456",
                "gsm": "GSM100001",
                "srx": "SRX100001",
                "srr": "SRR10000002",
                "run_alias": "sampleA_L002",
                "lane": "L002",
                "library_layout": "PAIRED",
                "read_structure": "R1:28,R2:91",
                "expected_spots": "2",
                "cb_length": "16",
                "umi_length": "12",
                "ngdc_run_page": "",
                "ngdc_url": "",
            },
            {
                "gse": "GSE123456",
                "gsm": "GSM100002",
                "srx": "SRX100002",
                "srr": "SRR10000003",
                "run_alias": "sampleB",
                "lane": "",
                "library_layout": "PAIRED",
                "read_structure": "R1:28,R2:91",
                "expected_spots": "2",
                "cb_length": "16",
                "umi_length": "12",
                "ngdc_run_page": "",
                "ngdc_url": "",
            },
        ]
        write_tsv(
            project / "metadata/expected_runs.tsv",
            expected_fields,
            expected_rows,
            crlf=True,
        )
        fixture_fields = [
            "srr",
            "ngdc_status",
            "ngdc_url",
            "ngdc_file_type",
            "ngdc_bytes",
            "ngdc_run_page",
            "probe_message",
        ]
        fixture_rows = [
            {
                "srr": "SRR10000001",
                "ngdc_status": "available",
                "ngdc_url": "https://download2.cncb.ac.cn/INSDC/SRA/10/SRR10000/SRR10000001/SRR10000001.sra",
                "ngdc_file_type": "sra",
                "ngdc_bytes": "1000",
                "ngdc_run_page": "https://ngdc.cncb.ac.cn/gsa/browse/fixture/SRR10000001",
                "probe_message": "fixture available",
            },
            {
                "srr": "SRR10000002",
                "ngdc_status": "missing",
                "ngdc_url": "",
                "ngdc_file_type": "",
                "ngdc_bytes": "",
                "ngdc_run_page": "",
                "probe_message": "fixture missing",
            },
            {
                "srr": "SRR10000003",
                "ngdc_status": "invalid",
                "ngdc_url": "",
                "ngdc_file_type": "",
                "ngdc_bytes": "",
                "ngdc_run_page": "",
                "probe_message": "fixture endpoint has no size",
            },
        ]
        fixture = base / "ngdc_fixture.tsv"
        write_tsv(fixture, fixture_fields, fixture_rows)
        run(
            sys.executable,
            str(HERE / "probe_ngdc.py"),
            "--input",
            str(project / "metadata/expected_runs.tsv"),
            "--output",
            str(project / "reports/ngdc_coverage.tsv"),
            "--fixture",
            str(fixture),
        )

        ena_fields = [
            "run_accession",
            "submitted_ftp",
            "submitted_bytes",
            "submitted_md5",
            "fastq_ftp",
            "fastq_bytes",
            "fastq_md5",
            "fastq_file_role",
            "sra_ftp",
            "sra_bytes",
            "sra_md5",
            "read_count",
            "library_layout",
        ]
        ena_rows = [
            {
                "run_accession": "SRR10000001",
                "submitted_ftp": "",
                "submitted_bytes": "",
                "submitted_md5": "",
                "fastq_ftp": "ftp.sra.ebi.ac.uk/a_1.fastq.gz;ftp.sra.ebi.ac.uk/a_2.fastq.gz",
                "fastq_bytes": "500;500",
                "fastq_md5": f"{'a'*32};{'b'*32}",
                "fastq_file_role": "GENERATED_FILE;GENERATED_FILE",
                "sra_ftp": "",
                "sra_bytes": "",
                "sra_md5": "",
                "read_count": "2",
                "library_layout": "PAIRED",
            },
            {
                "run_accession": "SRR10000002",
                "submitted_ftp": "",
                "submitted_bytes": "",
                "submitted_md5": "",
                "fastq_ftp": "ftp.sra.ebi.ac.uk/b_1.fastq.gz;ftp.sra.ebi.ac.uk/b_2.fastq.gz",
                "fastq_bytes": "600;700",
                "fastq_md5": f"{'c'*32};{'d'*32}",
                "fastq_file_role": "GENERATED_FILE;GENERATED_FILE",
                "sra_ftp": "",
                "sra_bytes": "",
                "sra_md5": "",
                "read_count": "2",
                "library_layout": "PAIRED",
            },
            {
                "run_accession": "SRR10000003",
                "submitted_ftp": "ftp.sra.ebi.ac.uk/c_R1.fastq.gz;ftp.sra.ebi.ac.uk/c_R2.fastq.gz",
                "submitted_bytes": "800;900",
                "submitted_md5": f"{'e'*32};{'f'*32}",
                "fastq_ftp": "",
                "fastq_bytes": "",
                "fastq_md5": "",
                "fastq_file_role": "",
                "sra_ftp": "",
                "sra_bytes": "",
                "sra_md5": "",
                "read_count": "2",
                "library_layout": "PAIRED",
            },
        ]
        write_tsv(project / "metadata/ena_runs.tsv", ena_fields, ena_rows)
        run(
            sys.executable,
            str(HERE / "select_sources.py"),
            "--expected",
            str(project / "metadata/expected_runs.tsv"),
            "--ngdc",
            str(project / "reports/ngdc_coverage.tsv"),
            "--ena",
            str(project / "metadata/ena_runs.tsv"),
            "--output",
            str(project / "metadata/source_manifest.tsv"),
        )
        source_rows = {
            row["srr"]: row
            for row in read_tsv(project / "metadata/source_manifest.tsv")
        }
        assert source_rows["SRR10000001"]["selected_source"] == "ngdc_insdc"
        assert source_rows["SRR10000002"]["selected_source"] == "ena_fastq"
        assert source_rows["SRR10000002"]["fallback_reason"] == "ngdc_missing"
        assert source_rows["SRR10000003"]["selected_provenance"] == "AUTHOR_SUBMITTED"

        run(
            sys.executable,
            str(HERE / "audit_manifest.py"),
            "--root",
            str(project),
            "--manifest",
            "metadata/source_manifest.tsv",
            "--expected-samples",
            "2",
            "--expected-runs",
            "3",
        )

        good_r1 = base / "good_R1.fastq.gz"
        good_r2 = base / "good_R2.fastq.gz"
        bad_r2 = base / "bad_R2.fastq.gz"
        write_fastq(good_r1, 2)
        write_fastq(good_r2, 2, 91)
        write_fastq(bad_r2, 1, 91)
        run(
            sys.executable,
            str(HERE / "validate_fastq_pair.py"),
            "--srr",
            "SRRTEST",
            "--r1",
            str(good_r1),
            "--r2",
            str(good_r2),
            "--expected-spots",
            "2",
            "--cb-length",
            "16",
            "--umi-length",
            "12",
        )
        mismatch = subprocess.run(
            [
                sys.executable,
                str(HERE / "validate_fastq_pair.py"),
                "--srr",
                "SRRTEST",
                "--r1",
                str(good_r1),
                "--r2",
                str(bad_r2),
                "--expected-spots",
                "2",
            ],
            capture_output=True,
        )
        assert mismatch.returncode != 0

        download_fields = [
            "gse", "gsm", "srr", "source", "provenance", "final_product",
            "urls", "expected_bytes", "observed_bytes", "expected_md5",
            "observed_md5", "expected_spots", "observed_r1", "observed_r2",
            "validation", "completed_at",
        ]
        by_gsm: dict[str, list[dict[str, str]]] = {}
        for row in source_rows.values():
            gsm, srr = row["gsm"], row["srr"]
            r1 = project / gsm / "fastq" / f"{srr}_R1.fastq.gz"
            r2 = project / gsm / "fastq" / f"{srr}_R2.fastq.gz"
            write_fastq(r1, 2)
            write_fastq(r2, 2, 91)
            by_gsm.setdefault(gsm, []).append(
                {
                    "gse": row["gse"],
                    "gsm": gsm,
                    "srr": srr,
                    "source": row["selected_source"],
                    "provenance": row["selected_provenance"],
                    "final_product": "fastq",
                    "urls": row["selected_urls"],
                    "expected_bytes": row["selected_bytes"],
                    "observed_bytes": f"{r1.stat().st_size};{r2.stat().st_size}",
                    "expected_md5": row["selected_md5"],
                    "observed_md5": f"{digest(r1)};{digest(r2)}",
                    "expected_spots": "2",
                    "observed_r1": "2",
                    "observed_r2": "2",
                    "validation": "PASS",
                    "completed_at": "2026-01-01T00:00:00+00:00",
                }
            )
            marker = project / "reports/status" / f"{srr}.complete"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("validation\tPASS\n")
        for gsm, rows in by_gsm.items():
            write_tsv(project / gsm / "download_manifest.tsv", download_fields, rows)

        partial = project / "GSM100001/fastq/bad.fastq.gz.part"
        partial.write_bytes(b"partial")
        failed = subprocess.run(
            [
                sys.executable,
                str(HERE / "audit_download_evidence.py"),
                "--root",
                str(project),
                "--deep",
            ],
            capture_output=True,
        )
        assert failed.returncode != 0
        partial.unlink()
        run(
            sys.executable,
            str(HERE / "audit_download_evidence.py"),
            "--root",
            str(project),
            "--deep",
        )

        for gsm in ("GSM100001", "GSM100002"):
            final_outputs(project, gsm)
        run(
            sys.executable,
            str(HERE / "audit_final_outputs.py"),
            "--root",
            str(project),
        )
        unified_report_test(base, project)
        downloader_smoke_test(base)

    print("SELF_TEST_PASS")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


if __name__ == "__main__":
    main()
