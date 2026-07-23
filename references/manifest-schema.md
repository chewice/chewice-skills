# Manifest and project schema

## Dataset directory

Use `<output-root>/GEO/<GSE>/`. If no output root is given, use
`<current-directory>/GEO/<GSE>/`.

```text
GEO/GSE123456/
├── metadata/
│   ├── study_metadata.tsv
│   ├── sample_metadata.tsv
│   ├── sample_characteristics.tsv
│   ├── srr_gsm_mapping.tsv
│   ├── expected_runs.tsv
│   ├── ena_runs.tsv
│   └── source_manifest.tsv
├── GSM000001/
│   ├── fastq/
│   ├── sra/
│   ├── work/
│   ├── matrix_10x/
│   ├── velocity/
│   └── download_manifest.tsv
├── reports/
│   ├── logs/
│   ├── status/
│   ├── dataset_overview.md
│   ├── preflight_audit.tsv
│   ├── ngdc_coverage.tsv
│   └── download_integrity_audit.tsv
├── scripts/
├── pixi.toml
└── pixi.lock
```

Create only terminal-product directories that are needed. Operational logs are
not expression `logcounts` and must be retained.

## `expected_runs.tsv`

One row per expected run:

| Column | Requirement |
|---|---|
| `gse` | `GSE` accession |
| `gsm` | Parent `GSM` accession |
| `srx` | Experiment accession, if available |
| `srr` | Unique `SRR`/`ERR`/`DRR`/`CRR` run accession |
| `run_alias` | Original run alias |
| `lane` | Lane parsed from metadata/filename, or empty |
| `library_layout` | `PAIRED` or `SINGLE` |
| `read_structure` | Known structure such as `R1:28,R2:91`; do not guess |
| `expected_spots` | Expected records per logical mate |
| `cb_length` | Barcode length for single-cell data, or empty |
| `umi_length` | UMI length, or empty |

Normalize line endings to LF. Numeric fields must contain digits only or be
empty. Preserve the complete expected run set even when a provider is missing a
run.

## `ena_runs.tsv`

Retain the original ENA report fields when available. Source selection needs at
least:

```text
run_accession
submitted_ftp
submitted_bytes
submitted_md5
fastq_ftp
fastq_bytes
fastq_md5
fastq_file_role
sra_ftp
sra_bytes
sra_md5
read_count
library_layout
```

Semicolon-separated URL/byte/MD5/role arrays must have matching lengths.
Convert bare FTP host paths to `https://` only when the same endpoint supports
HTTPS.

## `ngdc_coverage.tsv`

One row per expected run:

```text
gse
gsm
srx
srr
ngdc_browse_url
ngdc_run_page
ngdc_status
ngdc_url
ngdc_file_type
ngdc_bytes
expected_spots
probe_attempts
probe_message
```

Allowed `ngdc_status` values:

- `available`: endpoint returned a positive, stable Content-Length.
- `missing`: all resolved/candidate endpoints returned not found.
- `invalid`: endpoint exists but metadata/size is invalid.
- `unreachable`: network/TLS/server failure prevented a decision.
- `not_probed`: no network probe has been performed.

## `source_manifest.tsv`

One row per run:

```text
gse
gsm
srx
srr
run_alias
lane
library_layout
read_structure
expected_spots
cb_length
umi_length
ngdc_status
ngdc_run_page
ngdc_url
ngdc_bytes
selected_source
selected_provenance
selected_urls
selected_bytes
selected_md5
read_roles
final_product
fallback_reason
```

Allowed `selected_source`:

- `ngdc_gsa`
- `ngdc_insdc`
- `ena_submitted`
- `ena_fastq`
- `ncbi_sra`

Allowed `selected_provenance`:

- `AUTHOR_SUBMITTED`
- `GSA_AUTHOR_SUBMITTED`
- `NGDC_MIRROR_SRA`
- `ARCHIVE_NORMALIZED_SRA`
- `ARCHIVE_GENERATED_FASTQ`
- `AUTHOR_SUBMITTED_BAM`
- `GEO_PROCESSED`

Allowed `final_product`: `fastq`, `sra`, `matrix_velocity`.

`selected_urls`, `selected_bytes`, `selected_md5`, and `read_roles` use
semicolon-separated arrays. Roles are `SRA`, `R1`, `R2`, `I1`, `I2`, `BAM`, or
`OTHER`. Every non-NGDC selection requires `fallback_reason`.

## `sample_metadata.tsv`

Use one row per GSM and retain at least:

```text
gse
gsm
title
organism
tissue
condition
treatment
donor_subject
sex
age
batch
library_strategy
library_source
library_selection
platform
instrument_model
chemistry
srx_list
srr_list
run_count
lane_count
read_structure
ngdc_coverage
provenance
selected_source
final_product
expected_bytes
status
notes
```

Do not flatten arbitrary GEO characteristics into lossy columns. Store them in
`sample_characteristics.tsv` with `gse`, `gsm`, `key`, `value`, and
`source_order`.

## Per-GSM `download_manifest.tsv`

Append one row only after a run reaches a validated terminal state:

```text
gse
gsm
srr
source
provenance
final_product
urls
expected_bytes
observed_bytes
expected_md5
observed_md5
expected_spots
observed_r1
observed_r2
validation
completed_at
```

Write through a temporary file and atomically rename. Never use a completion row
as a substitute for checking the referenced files.
