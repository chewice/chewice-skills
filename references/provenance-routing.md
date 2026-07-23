# Provenance and provider routing

## Provenance decision

Classify the bytes actually downloaded, not the biological content they
represent.

| Evidence | Classification | Meaning |
|---|---|---|
| ENA `submitted_*` and `SUBMITTED_FILE` | `AUTHOR_SUBMITTED` | File submitted by the depositor |
| Native GSA/CRA file | `GSA_AUTHOR_SUBMITTED` | File submitted to NGDC GSA |
| NGDC INSDC mirror `.sra` | `NGDC_MIRROR_SRA` | Mirrored archive representation, not original FASTQ bytes |
| NCBI/ENA `.sra` | `ARCHIVE_NORMALIZED_SRA` | Archive-normalized SRA |
| ENA `GENERATED_FILE` or `fasterq-dump` output | `ARCHIVE_GENERATED_FASTQ` | FASTQ generated from archive content |
| Submitted BAM | `AUTHOR_SUBMITTED_BAM` | Author alignment, reference-dependent |
| GEO count/logcount/normalized matrix | `GEO_PROCESSED` | Processed data; exclude by default |

Do not infer `AUTHOR_SUBMITTED` merely from a filename that resembles the
author's filename. A Run alias displayed by an archive can preserve an original
name while the downloadable object is still normalized SRA.

## Fixed source priority

Apply priority independently to each run:

1. Native NGDC GSA file for CRA/CRR data.
2. Available and valid NGDC INSDC mirror SRA.
3. Usable ENA submitted FASTQ, then ENA generated FASTQ.
4. NCBI SRA Toolkit.

Do not let a project-level NGDC hit imply complete coverage. Compare the exact
expected run set with the exact available run set.

Do not choose ENA over a valid NGDC run solely because ENA benchmarks faster.
Direct/proxy tests may diagnose reachability, but they do not change priority.

## Valid fallback reasons

Use one of:

- `ngdc_missing`
- `ngdc_no_file_endpoint`
- `ngdc_unreachable_after_3_attempts`
- `ngdc_size_invalid`
- `ngdc_vdb_validate_failed`
- `ngdc_read_count_failed`
- `ngdc_metadata_conflict`
- `native_gsa_not_applicable`

Add a concise detail after a colon if needed. Never leave the reason empty for
an ENA/NCBI selection.

## Product choice

- Default: analysis-ready FASTQ.
- STARsolo, re-alignment, and velocity: FASTQ.
- Archive/reconversion: SRA or author-submitted source.
- Reuse of author alignments: BAM only after reference/aligner compatibility
  review.
- Native author FASTQ is preferable when it remains compatible with the
  intended analysis, but a valid NGDC mirror still takes source priority when
  the user requested NGDC-first routing.

When the terminal product is FASTQ and NGDC provides SRA, describe both stages:
downloaded object = `NGDC_MIRROR_SRA`; retained FASTQ =
`ARCHIVE_GENERATED_FASTQ`.
