#!/usr/bin/env python3
"""Detect GEO assay type and route each GSM to an acquisition workflow."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capabilities import CapabilityError, assay_capability  # noqa: E402
from project_layout import write_tsv_atomic  # noqa: E402

FIELDS = [
    "gse",
    "gsm",
    "gpl",
    "assay_type",
    "modality",
    "raw_file_type",
    "workflow",
    "capability_reference",
    "evidence",
]
AFFYMETRIX_GPL = {
    "GPL570",
    "GPL96",
    "GPL97",
    "GPL571",
    "GPL6244",
    "GPL1261",
    "GPL8321",
    "GPL81",
    "GPL339",
    "GPL340",
    "GPL341",
    "GPL85",
    "GPL91",
    "GPL92",
    "GPL93",
    "GPL94",
    "GPL95",
    "GPL13158",
    "GPL17586",
}
METHYLATION_GPL = {
    "GPL13534",
    "GPL21145",
    "GPL23976",
    "GPL8490",
    "GPL33022",
}
ILLUMINA_EXPRESSION_GPL = {
    "GPL10558",
    "GPL6947",
    "GPL6884",
    "GPL6102",
    "GPL6883",
    "GPL4133",
}
SEQUENCING = re.compile(
    r"rna[- ]?seq|single[- ]cell|ncrna[- ]seq|mirna[- ]seq|chip[- ]seq|"
    r"atac[- ]seq|high-throughput sequencing|illumina hiseq|nextseq|"
    r"novaseq|miseq|10x genomics",
    re.I,
)
AFFY_TEXT = re.compile(r"affymetrix|genechip|u133|hugene|hta[- ]2", re.I)
METHYL_TEXT = re.compile(r"methylat|450k|epic|infinium.*cpg", re.I)
ILLUMINA_BEAD = re.compile(r"beadchip|humanht-12|humanref-8|illumina.*expression", re.I)
RNASEQ_LIB = re.compile(r"rna[- ]?seq|ncrna[- ]?seq|transcriptome", re.I)
ATAC_LIB = re.compile(r"atac[- ]?seq", re.I)
CHIP_LIB = re.compile(r"chip[- ]?seq", re.I)
MIRNA_LIB = re.compile(r"mirna[- ]?seq", re.I)
RNA_TEXT = re.compile(r"rna[- ]?seq|single[- ]cell|transcriptome|10x genomics", re.I)
SCRNA_TEXT = re.compile(r"single[- ]cell|scrna|10x genomics|droplet", re.I)
SNRNA_TEXT = re.compile(r"single[- ]nucle|snrna|sn[- ]rna", re.I)


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def has_run(row: dict[str, str]) -> bool:
    for key in ("srr_list", "srr", "run_accession"):
        value = row.get(key, "").strip()
        if value and value.upper() not in {"NA", "NONE"}:
            return True
    return False


def classify(row: dict[str, str]) -> dict[str, str]:
    gpl = (row.get("gpl") or row.get("platform") or "").strip().upper()
    if "," in gpl:
        gpl = gpl.split(",")[0].strip()
    title = " ".join(
        row.get(key, "")
        for key in ("platform_title", "title", "instrument_model", "chemistry")
    )
    technology = row.get("technology", "")
    library = " ".join(
        row.get(key, "")
        for key in ("library_strategy", "library_source", "library_selection")
    )
    blob = " ".join([gpl, title, technology, library])
    evidence: list[str] = []
    if has_run(row) or RNASEQ_LIB.search(library) or SEQUENCING.search(blob):
        if has_run(row):
            evidence.append("SRR/run accession")
        if RNASEQ_LIB.search(library) or ATAC_LIB.search(library) or CHIP_LIB.search(library) or MIRNA_LIB.search(library):
            evidence.append(f"library_strategy={row.get('library_strategy', '')}")
        if SEQUENCING.search(blob):
            evidence.append("sequencing platform/technology")
        assay_type = "sequencing"
        modality = "sequencing"
        if RNASEQ_LIB.search(library) or RNA_TEXT.search(blob):
            assay_type = "RNA-seq"
            modality = "bulk_rnaseq"
            if SNRNA_TEXT.search(blob) or SNRNA_TEXT.search(library):
                modality = "snRNAseq"
            elif SCRNA_TEXT.search(blob) or SCRNA_TEXT.search(library):
                modality = "scRNAseq"
        if MIRNA_LIB.search(library) or MIRNA_LIB.search(blob):
            assay_type = "miRNA-seq"
            modality = "mirna"
        if ATAC_LIB.search(library) or ATAC_LIB.search(blob):
            assay_type = "ATAC-seq"
            modality = "atac"
        if CHIP_LIB.search(library) or CHIP_LIB.search(blob):
            assay_type = "ChIP-seq"
            modality = "chip"
        return {
            "gpl": gpl,
            "assay_type": assay_type,
            "modality": modality,
            "raw_file_type": "FASTQ",
            "workflow": "sra",
            "evidence": ";".join(evidence) or "sequencing",
        }
    if gpl in AFFYMETRIX_GPL or AFFY_TEXT.search(blob):
        evidence.append(f"gpl={gpl}" if gpl in AFFYMETRIX_GPL else "Affymetrix text")
        return {
            "gpl": gpl,
            "assay_type": "microarray",
            "modality": "microarray",
            "raw_file_type": "CEL",
            "workflow": "affymetrix",
            "evidence": ";".join(evidence),
        }
    if gpl in METHYLATION_GPL or METHYL_TEXT.search(blob):
        evidence.append(f"gpl={gpl}" if gpl in METHYLATION_GPL else "methylation text")
        return {
            "gpl": gpl,
            "assay_type": "methylation",
            "modality": "methylation",
            "raw_file_type": "IDAT",
            "workflow": "methylation",
            "evidence": ";".join(evidence),
        }
    if gpl in ILLUMINA_EXPRESSION_GPL or ILLUMINA_BEAD.search(blob):
        evidence.append(f"gpl={gpl}" if gpl in ILLUMINA_EXPRESSION_GPL else "Illumina BeadChip")
        return {
            "gpl": gpl,
            "assay_type": "microarray",
            "modality": "microarray",
            "raw_file_type": "IDAT",
            "workflow": "illumina",
            "evidence": ";".join(evidence),
        }
    raise SystemExit(
        f"无法判定 assay：gsm={row.get('gsm', '')} gpl={gpl or 'missing'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Route GEO samples to assay workflows")
    parser.add_argument("--samples", type=Path, help="sample_metadata.tsv")
    parser.add_argument("--platforms", type=Path, help="platform_metadata.tsv")
    parser.add_argument("--expected-runs", type=Path)
    parser.add_argument("--root", type=Path, help="GSE project root")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-mixed",
        action="store_true",
        help="兼容旧参数；混合 assay 现在默认写入分流表并按 assay 分别记录存储策略",
    )
    parser.add_argument(
        "--reject-mixed",
        action="store_true",
        help="遇到混合 workflow 时退出，不写分流表",
    )
    args = parser.parse_args()
    root = args.root.resolve() if args.root else None
    samples_path = args.samples
    if samples_path is None and root is not None:
        samples_path = root / "metadata/sample_metadata.tsv"
    if samples_path is None:
        raise SystemExit("需要 --samples 或 --root")
    rows = read_tsv(samples_path)
    if not rows:
        raise SystemExit(f"empty {samples_path}")
    platform_path = args.platforms
    if platform_path is None and root is not None:
        platform_path = root / "metadata/platform_metadata.tsv"
    platforms = {
        row.get("gpl", "").upper(): row
        for row in (read_tsv(platform_path) if platform_path else [])
        if row.get("gpl")
    }
    runs_by_gsm: dict[str, list[str]] = {}
    expected_path = args.expected_runs
    if expected_path is None and root is not None:
        expected_path = root / "metadata/expected_runs.tsv"
    for run in read_tsv(expected_path) if expected_path else []:
        runs_by_gsm.setdefault(run.get("gsm", ""), []).append(run.get("srr", ""))

    output_rows: list[dict[str, str]] = []
    for row in rows:
        gsm = row.get("gsm", "")
        merged = dict(row)
        if gsm in runs_by_gsm and runs_by_gsm[gsm]:
            merged["srr_list"] = ";".join(runs_by_gsm[gsm])
        gpl = (merged.get("platform") or merged.get("gpl") or "").split(",")[0].strip().upper()
        if gpl in platforms:
            platform = platforms[gpl]
            merged.setdefault("gpl", gpl)
            merged.setdefault("platform_title", platform.get("title", ""))
            merged.setdefault("technology", platform.get("technology", ""))
        classified = classify(merged)
        try:
            _, capability = assay_capability(classified["modality"], root)
        except CapabilityError as exc:
            raise SystemExit(str(exc)) from exc
        classified["workflow"] = str(capability.get("workflow", ""))
        classified["capability_reference"] = str(capability.get("reference", ""))
        output_rows.append(
            {
                "gse": row.get("gse", ""),
                "gsm": gsm,
                "gpl": classified["gpl"] or gpl,
                **classified,
            }
        )

    workflows = {row["workflow"] for row in output_rows}
    modalities = {row["modality"] for row in output_rows}
    if (len(workflows) > 1 or len(modalities) > 1) and args.reject_mixed:
        counts = dict(Counter(row["workflow"] for row in output_rows))
        raise SystemExit(f"同一 GSE 混合 assay workflow，暂停下载：{counts}")

    output = args.output
    if output is None:
        if root is None:
            raise SystemExit("需要 --output 或 --root")
        output = root / "metadata/assay_routing.tsv"
    write_tsv_atomic(output, FIELDS, output_rows)
    summary = Counter(
        (row["assay_type"], row["modality"], row["raw_file_type"], row["workflow"])
        for row in output_rows
    )
    mixed = " MIXED" if len({row["workflow"] for row in output_rows}) > 1 else ""
    print(
        "ASSAY_ROUTE "
        + " ".join(
            f"{assay}/{modality}/{raw}/{workflow}={count}"
            for (assay, modality, raw, workflow), count in sorted(summary.items())
        )
        + f" output={output}{mixed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
