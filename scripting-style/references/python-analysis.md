# Python analysis scripts

Read only for `.py` targets. A Python file may contain a complete scientific analysis or a narrow project conversion; neither inherently requires a CLI. Follow the core boundaries on current needs, scientific checks, and no speculative recovery or legacy adapters. Adapt example comment language to the user/project.

## Start with top-level analysis

After imports and a small input block, enter the actual transformation or model. Keep the visible sequence appropriate to the question:

`question and paths → read → inspect contents/types/categories → scientific transformation → inspect results → save useful outputs`

Use the `.py` directory as the working directory and relative `Path` values for input, intermediate, and output files. Initialize once from the actual launch location. From a project root running `scripts/analysis.py`:

```python
import os
from pathlib import Path

os.chdir("scripts")
print(Path.cwd())
```

If already in the script directory, use `os.chdir(".")`. Do not repeat initialization in later `# %%` fragments or rely on `__file__` in an interactive session where it may be absent. Do not add root discovery, old-path probing, or multi-branch location logic. Keep paths near their reads/writes, for example `Path("../data/metadata.tsv")`.

Paths can precede reading; columns, groups, and comparisons that depend on data must follow inspection. Names such as `df`, `adata`, `fig`, and `ax` are appropriate when their roles are clear.

## Use analysis-step sections

For new exploratory scripts, use lightweight headings such as `# %% Inspect sample composition`; preserve clear existing conventions when editing. Name the actual analysis step, not “Continue after inspection.” Short comments explain scientific purpose and observations to examine, not each line's syntax. A section can be run as a line, selection, or cell; it need not initialize independently.

Within a step, put one blank line between input preparation, transformation, inspection, and saving groups. Keep tightly related statements adjacent; do not insert a blank line after every statement or split by fixed line count. Small groups usually do not need separate `# %%` headings. Wrap long calls within parentheses by argument with indentation; do not impose checkpoint labels.

```python
# %% Read sample metadata
# Inspect available fields before deciding group assignment and alignment.
metadata = pd.read_csv(metadata_path)

print(metadata.head())
print(metadata.columns)
```

Use one Python session and its objects. `# %%` does not pause a normal Python process. Execute the current fragment, inspect output, then write and execute dependent code. Do not repeatedly use `python -c`, here-documents, or temporary scripts to reload a large object. Rerun affected downstream work after upstream changes; keep dependencies in the file for replay.

Do not add `argparse`, `click`, `main()`, configuration objects, subcommands, logging frameworks, runners, or status files to an analysis. Honor a current positional/environment contract when an existing caller requires it; do not generalize it or preserve obsolete versions. A requested reusable tool is a separate scope.

## Show real evidence

Normal `.py` execution needs explicit prints; bare expressions display only in an established interactive-chunk workflow. Choose relevant inspection calls rather than printing this whole list everywhere:

```python
print(data.shape)
print(data.head())
print(data.dtypes)
print(data[group_column].value_counts(dropna=False))
print(result.describe())
```

Use `type()` after reading, extracting, or converting an object when type matters; use `.dtypes` for table columns. Do not mechanically mirror R or repeat all structure checks. Preview actual contents, not just shape or a completion message: NumPy slices, DataFrame `.head()`/`.iloc`, AnnData `.obs.head()`, or the needed expression-layer slice. Use `.toarray()` only on a small sparse slice, never the whole object. Do not choose or replace assays/layers silently.

After consequential transformations, show the content, category counts, metrics, or plots that inform the next decision. Print or explicitly display plots as needed; do not assume notebook display in a script. No general preview helper or assertion framework.

Apply the shared criteria for confirmed settings, necessary comparisons, and unresolved decisions. Keep candidates, diagnostics, and the resulting selection adjacent; use comments for pending questions and omit dependent calls. Notebook examples do not establish standalone Python syntax conventions.

## Extract only a useful, stable calculation

When a current batch task still needs understanding, run a representative item inline and inspect it first. Extract the stable per-item calculation only after inputs, transformation, and outputs are clear and reuse is needed now. Omit a prototype/batch structure for a direct one-off transformation.

Two similar blocks alone do not justify abstraction. Preserve separate dataset/method blocks when their differences are clearer that way. Extract the smallest common technical part when actual drift impairs understanding. Numeric kernels, required parsers, and repeated plotting can use narrow functions; scientific choices stay at first use in the main analysis.

For concrete scientific conditions, use a compact `assert` or direct exception. Apply the shared exception-handling criteria; broad `try/except` must not hide failed comparisons or substitute scientific inputs.

## Save scientific artifacts

Apply the shared saving criteria and project formats. For a metadata table needed by later plotting:

```python
out_path = Path("../results/sample-overview")
out_path.mkdir(parents=True, exist_ok=True)
fn = out_path / "metadata.tsv"

metadata.to_csv(fn, sep="\t", index=False)
```

In a later session, reestablish the same relative path, use `pd.read_csv(fn, sep="\t")`, and inspect its contents.

Keep plot preparation, plotting, display, and `fig.savefig(...)` near each other, using the current library and object interfaces. Do not import R plotting/device conventions or introduce a general wrapper. Record conclusions only after observing results; otherwise retain the specific next question.
