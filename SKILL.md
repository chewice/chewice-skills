---
name: download-geo-sra-safely
description: Safely inspect, plan, download, resume, validate, and document public GEO/GSE/GSM, SRA/SRR/SRX/PRJNA, ENA, and CNCB-NGDC GSA/INSDC sequencing data. Use whenever Codex is asked to download or verify GSE/SRA data, recover an interrupted transfer, decide between author-submitted files and archive-generated FASTQ/SRA/BAM, inspect R1/R2/I1/I2 or multi-run/lane structure, organize one folder per GSM, or produce STARsolo/RNA-velocity inputs from public raw reads. Prefer an available and valid NGDC mirror run before ENA or NCBI, use pixi and detached tmux for long jobs, and retain auditable integrity evidence.
---

# Download GEO/SRA Safely

## Operating contract

Treat metadata discovery, transfer, conversion, and analysis as separate gates.
Never begin a large transfer until the accession set and terminal data product
are explicit. Default the terminal product to analysis-ready FASTQ. Do not
download GEO logcounts or normalized expression matrices unless explicitly
requested.

Use pixi for the environment. Pin the resolved tools in `pixi.lock`. Run long
downloads and processing in a detached tmux session. Default monitoring to 1800
seconds and report progress by samples/runs, phase, errors, bytes, and free
space.

Set the helper location before using bundled commands:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/download-geo-sra-safely"
```

Use `scripts/scaffold_project.py` to create the dataset-local layout. Read
`references/manifest-schema.md` before creating metadata tables.

## 1. Introduce and resolve the dataset

Before downloading:

1. Resolve GSE -> GSM -> SRX -> SRR and BioProject relationships from official
   GEO, SRA, and ENA metadata.
2. Explain the study title, purpose, organism, tissue/disease, design, groups,
   assay, platform, library strategy, and chemistry when available.
3. Count expected GSMs and SRRs. Identify GSMs split across runs or lanes.
4. Inspect submitted and generated filenames for R1/R2/I1/I2 and technical
   read patterns. Use read lengths and experiment metadata; filenames alone are
   not sufficient.
5. Decide whether the requested downstream work needs FASTQ, BAM, SRA, or
   author-submitted bytes. STARsolo, re-alignment, and RNA velocity normally
   require FASTQ.
6. Save the explanation in `reports/dataset_overview.md`, normalized sample
   metadata in `metadata/sample_metadata.tsv`, multi-valued characteristics in
   `metadata/sample_characteristics.tsv`, and the complete expected run set in
   `metadata/expected_runs.tsv`.

Do not silently continue when GEO, ENA, and SRA disagree on the expected run
set. Write the difference to the preflight report and pause for resolution.

## 2. Classify provenance and prefer NGDC

Read `references/provenance-routing.md` before selecting files.

For every expected run, inspect
`https://ngdc.cncb.ac.cn/gsa/browse/` and the corresponding GSA or INSDC run
record. Probe the actual `download*.cncb.ac.cn` file endpoint, not merely the
browse page. Run:

```bash
pixi run --locked python "$SKILL_DIR/scripts/probe_ngdc.py" \
  --input metadata/expected_runs.tsv \
  --output reports/ngdc_coverage.tsv
```

Apply this run-level priority:

1. NGDC-native GSA author files for CRA/CRR accessions.
2. Valid NGDC INSDC mirror SRA for SRR accessions.
3. ENA author-submitted FASTQ when usable; otherwise ENA generated FASTQ.
4. NCBI SRA Toolkit as the final fallback.

Do not replace an available, valid NGDC run merely because another route is
faster. Fallback only when the run is missing, has no file endpoint, is
unreachable for three attempts, or fails size/integrity/read-count validation.
Record a fallback reason for every non-NGDC selection.

Generate `metadata/source_manifest.tsv` with
`scripts/select_sources.py`, then validate it:

```bash
pixi run --locked python "$SKILL_DIR/scripts/select_sources.py" \
  --expected metadata/expected_runs.tsv \
  --ngdc reports/ngdc_coverage.tsv \
  --ena metadata/ena_runs.tsv \
  --output metadata/source_manifest.tsv

pixi run --locked python "$SKILL_DIR/scripts/audit_manifest.py" \
  --root . --manifest metadata/source_manifest.tsv
```

Always answer: “Are these author-uploaded bytes or an archive-converted
version?” Use only the provenance values defined in the schema. In particular,
NGDC INSDC `.sra` is `NGDC_MIRROR_SRA`; FASTQ produced by `fasterq-dump` is
`ARCHIVE_GENERATED_FASTQ`.

## 3. Download and validate atomically

Use one GSM directory and separate files for every run/lane. Do not concatenate
runs during acquisition.

Use `scripts/download_run.sh <project-root> <SRR>` for each source-manifest
row. Start the sample loop in detached tmux. The downloader must:

- write only to `.part` plus aria2 control state;
- require expected byte count when published;
- require provider MD5 for ENA files;
- run `gzip -t` on FASTQ and `vdb-validate` on SRA;
- atomically rename only after validation;
- run `fasterq-dump --split-files` for an SRA-to-FASTQ terminal product;
- atomically compress converted FASTQ;
- validate paired record counts, expected spots, and barcode-read minimum
  length when CB/UMI geometry is known;
- append an auditable row to `GSM*/download_manifest.tsv`;
- retain failed partials only when a valid aria2 piece map exists.

Use `scripts/validate_fastq_pair.py` directly when validating existing FASTQ.
Never accept “HTTP succeeded” or “size matches” as sufficient proof.

## 4. Monitor and recover

Run `scripts/watchdog.sh <project-root> [interval-seconds]` in its own detached
tmux session. Read `references/recovery-playbook.md` before modifying a failed
job.

Recover a repeatable network or integrity error at most three times. Stop and
report after the third identical failure. Never edit a shell script that a live
sample process is currently reading; stop it, validate syntax, then restart.
Normalize CRLF and validate numeric TSV fields so formatting errors cannot
masquerade as read-count failures.

## 5. Optional STARsolo and velocity branch

Enter this branch only when the user requests matrices, re-alignment, or RNA
velocity. Read `references/starsolo-read-geometry.md`.

- Keep the reference organism/version explicit.
- Build and run a STAR index with the same locked STAR version.
- Preserve the experiment's chemistry, CB/UMI geometry, and whitelist; never
  “upgrade” all datasets to one chemistry.
- Verify actual barcode/cDNA roles before assigning STARsolo input order.
- Group validated runs by GSM without losing run provenance.
- For velocity request `Gene`, `GeneFull`, and `Velocyto` as separately passed
  STAR arguments and validate raw/filtered 10x matrices plus spliced,
  unspliced, ambiguous, and loom outputs.

Run `scripts/audit_final_outputs.py --root <GSE-dir>` before cleanup.

## 6. Cleanup and handoff

Run `scripts/audit_download_evidence.py --root <GSE-dir>` first.

- FASTQ terminal product: keep FASTQ; remove SRA, `.part`, `.aria2`, and work.
- SRA terminal product: keep validated SRA.
- Matrix/velocity terminal product: remove SRA, FASTQ, and work only after both
  download-evidence and final-output audits pass.
- Never clean an incomplete or unaudited sample.

Report:

- expected/observed GSM and SRR counts;
- NGDC available/missing/invalid and fallback counts;
- author-submitted versus archive-generated products;
- multi-run/lane and read-role findings;
- retained product paths, total size, integrity status, and cleanup performed.
