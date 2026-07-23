# STARsolo read geometry

## Determine roles, never assume them

For standard 10x 3' libraries, STARsolo usually receives cDNA reads first and
barcode/UMI reads second, even though files are commonly named R2 and R1.
Confirm this from the experiment rather than applying it globally.

Review:

- kit/chemistry version;
- R1/R2/I1/I2 lengths;
- submitted filenames and run aliases;
- barcode and UMI positions;
- whitelist used by the original kit;
- whether SRA conversion exposed technical reads.

Technical reads created by `fasterq-dump --include-technical` must not
automatically enter STARsolo. Some archives can expose more than two reads; map
their roles explicitly.

## Common 10x defaults

These are hints, not replacements for dataset evidence:

| Chemistry | CB | UMI | Common whitelist |
|---|---:|---:|---|
| 10x 3' v2 | 16 | 10 | `737K-august-2016.txt` |
| 10x 3' v3 | 16 | 12 | `3M-february-2018.txt` |

Some v3 datasets expose a 10-base UMI or trimmed barcode read. Respect the
actual experiment and read lengths.

## Reproducibility

- Lock one STAR version.
- Build and run the genome index with that exact version.
- Record reference name, FASTA/GTF release, `sjdbOverhang`, whitelist, geometry,
  STAR command, and tool versions.
- Do not reuse an index built by an unknown/incompatible STAR version.

## Velocity deliverables

When requested, validate:

- raw and filtered 10x `matrix.mtx.gz`, `features.tsv.gz`, `barcodes.tsv.gz`;
- spliced, unspliced, and ambiguous matrices;
- velocity features and barcodes;
- loom layer names and shapes;
- raw/filtered/velocity feature dimensions and filtered loom cell dimensions.
