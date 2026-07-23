# Interrupted-transfer and recovery playbook

## Transfer invariants

A final filename means all applicable invariants passed:

1. Published byte count matches.
2. Published MD5/checksum matches.
3. `gzip -t` succeeds for FASTQ or `vdb-validate` succeeds for SRA.
4. Conversion completed atomically.
5. Paired records and expected spots match.

Write active transfers to `.part`. For aria2, retain `.part.aria2` so completed
pieces can be trusted. A partial file without piece metadata is not safely
resumable.

## Common failures

### TLS/network interruption

- Keep `.part` and `.part.aria2`.
- Retry only the affected pieces.
- Do not append a fresh stream to an untracked partial.
- After three identical failures, stop and record the route as unreachable.

### Expected size but wrong checksum

- Treat the file as corrupt.
- Delete `.part` and its control file.
- Restart from byte zero.
- Never promote by size alone.

### SRA endpoint has no checksum

- Require stable positive Content-Length.
- Download atomically.
- Require `vdb-validate` internal MD5/consistency checks.
- Require converted read counts to match provider `expected_spots`.

### False read-count mismatch

- Normalize CRLF before parsing TSV.
- Do not use whitespace-collapsing shell parsing for empty tab fields.
- Validate numeric fields before running a sample.
- Compare expected, R1, and R2 as normalized integers.

### R1/R2/I1/I2 ambiguity

- Inspect submitted filenames, run metadata, read lengths, and chemistry.
- Do not assume `_1` is barcode or biological read across all platforms.
- Keep technical reads separate.
- Fail preflight when roles remain ambiguous.

### Multi-run or multi-lane sample

- Validate each run independently.
- Keep files separate during acquisition.
- Group runs by GSM only at the analysis invocation.
- Preserve the contributing SRR list in final provenance.

### Live script changed during execution

- Stop the affected job cleanly.
- Run `bash -n` or the relevant syntax checker.
- Restart from validated checkpoints.
- Do not hot-edit a shell script a live Bash process may read later.

## Cleanup gate

Delete sources only when:

- every expected run has a validated download-manifest row;
- the requested terminal artifact exists and passes its direct audit;
- no `.part`, `.aria2`, or `.tmp` is being used by a live process;
- cleanup behavior matches the requested terminal product.
