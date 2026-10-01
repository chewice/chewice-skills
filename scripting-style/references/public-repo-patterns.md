# Supplemental public analysis examples

The primary writing sources are the [local GZDlab examples](../examples/example-index.yaml). Read this reference only for supplemental public-source evidence or notebook examples. Historical inspection date: **2026-09-18**. That review checked the relationship between the following code and Nature, Science, and Cell papers and inspected selected source cells at fixed revisions. It did not execute the papers' analyses or use stored outputs as evidence of conclusions.

Published code is often an edited analysis record. It can illustrate object transformations, display placement, and selection rationale, but does not reveal the authors' original exploration order or make an entire repository exemplary. Cell numbers below are **one-based**, including Markdown cells.

## Nature: Tabula Muris Senis

- Paper: [A single-cell transcriptomic atlas characterizes ageing tissues in the mouse](https://doi.org/10.1038/s41586-020-2496-1), Nature, 2020.
- Fixed commit: `5ee7b62ec7208c240634946180a8a105a7356816`.
- [Droplet-processing notebook](https://github.com/czbiohub-sf/tabula-muris-senis/blob/5ee7b62ec7208c240634946180a8a105a7356816/1_tabula_muris_senis/11_figure_1/tabula-muris-senis-droplet-processing.ipynb), Python; inspected cells 1–24.
- **Useful structure:** cells 3–6 display records/objects after loading; cells 9–12 display metadata, transform it, and inspect categories. Later sections process another input group. Objects and differences stay visible, with inspection part of the analysis.
- **Exclude:** machine paths, old Scanpy APIs, field mappings, historical filters, and category choices. A long loop demonstrates a possible structure, not that new data should immediately use it.

## Science: Tabula Sapiens

- Paper: [The Tabula Sapiens: A multiple-organ, single-cell transcriptomic atlas of humans](https://doi.org/10.1126/science.abl4896), Science, 2022.
- Fixed commit: `14de8b082a25dba79e12c39626843543ab92e5b5`; use only `paper1`, not later papers' code.
- [Fig2_cell_fractions notebook](https://github.com/czbiohub-sf/tabula-sapiens/blob/14de8b082a25dba79e12c39626843543ab92e5b5/paper1/Fig2/Fig2_cell_fractions.ipynb), Python; inspected cells 1–24.
- **Useful structure:** cells 12–18 distinguish reading, analysis, and transformation with headings, displaying input tables, local records, and summaries. Cell 20 plots; cells 22–24 read/display another table type. Computation, inspection, and plotting purpose are traceable.
- **Exclude:** large opening plot helpers, wildcard imports, personal paths, historical parameters, and extensive obsolete comments. Full-table display in a source does not justify displaying a large object in a new task.

## Cell: KPTracer

- Paper: [Lineage tracing reveals the phylodynamics, plasticity, and paths of tumor evolution](https://doi.org/10.1016/j.cell.2022.04.015), Cell, 2022.
- Fixed commit: `76a022bc6ab0bd3238127843a15acb00087d97ce`.
- [Figure3_S3_diffexp notebook](https://github.com/mattjones315/KPTracer-release/blob/76a022bc6ab0bd3238127843a15acb00087d97ce/reproducibility/Figure3_S3/Figure3_S3_diffexp.ipynb), **R source**; inspected all 21 cells.
- **Useful structure:** cells 7–9 separate computation, inspection, and later processing; cells 11–17 explain analysis purposes, computation, manual selection, and display. Choices remain visible and explicitly manual. Inspect the actual notebook language rather than assuming Python.
- **Exclude:** particular manual selections, thresholds, versions, and hidden upstream dependencies. Some choices and figures are fixed publication results, not defaults for new tasks. Batch scripts and algorithm libraries are not the default interactive analysis architecture.

## Applying this evidence

All three examples are `.ipynb`. They support notebook sectioning, inspection, and visible choices, not the concrete syntax of `.R`, `.py`, or `.sh`. R section conventions, Python `# %%`, and execution guided by output come from explicit user requirements and local type-specific guidance/validation.

Borrow only useful current structure, never historical parameters, identifiers, data, or conclusions. Public helpers/pipelines do not make those structures defaults. Narrow stable functions and confirmed mechanical repetition still have legitimate roles.

In the [local index](../examples/example-index.yaml), `<SOURCE_ROOT>` denotes the GZDlab root; older sc06 paths carry the `sc06/` prefix. Read same-type sources on demand. Do not override local preferences, search the user's machine, or force downloads when sources are absent.

See [validation records](../validation/interactive-analysis-validation.md) for the distinctions between source inspection, fragment execution, and scientific correctness. These notes preserve historical evidence; translation is not a new source verification.
