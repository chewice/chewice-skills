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

Compare methods/parameters only when the task calls for it. Keep candidates, comparable metrics, and the later choice near each other. Inspect results before recording a winner and why it was selected; distinguish exploration from prespecified settings and retain meaningful negative results. Leave unresolved scientific questions in comments, without passing `None` to dependent calls. Notebook examples do not establish standalone Python syntax conventions.

Do not infer scientific cutoffs, top-N values, model settings, or other meaningful defaults from habit. Use confirmed values, design a comparison, or leave the decision pending. Do not enumerate unrequested algorithm switches, seeds, or sampling settings for apparent completeness. Figure dimensions and resolution may be set for the actual plot.

An output name does not resolve its estimand, comparison unit, test, or grouping. Keep missing decisions visible; do not invent a standard method for runnable code or connect unrelated upstream choices to a later analysis.

## Extract only a useful, stable calculation

When a current batch task still needs understanding, run a representative item inline and inspect it first. Extract the stable per-item calculation only after inputs, transformation, and outputs are clear and reuse is needed now. Omit a prototype/batch structure for a direct one-off transformation.

Two similar blocks alone do not justify abstraction. Preserve separate dataset/method blocks when their differences are clearer that way. Extract the smallest common technical part when actual drift impairs understanding. Numeric kernels, required parsers, and repeated plotting can use narrow functions; scientific choices stay at first use in the main analysis.

## Enforce scientific conditions, not hypothetical recovery

A compact assertion or direct exception is appropriate for current requirements such as aligned identifiers, unique keys, correct matrix orientation, or required categories. These checks need not wait for a previously observed failure.

Do not wrap analysis in broad `try/except`, fallback readers/models, automatic repair, or retry machinery. Never drop samples, impute values, or skip failed comparisons solely to finish. Diagnose the actual cause and repair owned code and known callers; report external boundaries. Direct format conversion or identifier mapping is allowed for a known current contract, with assumptions and information loss visible.

## Save scientific artifacts

Save a table, array, model, figure, or converted file only for a current scientific or downstream use. Expensive results can be saved and reused after confirming relevant inputs/settings still match. Do not add orchestration, completion messages, manifests, or pass markers as generic outputs.

Follow project formats and name the object or state. For a metadata table needed by later plotting:

```python
out_path = Path("../results/sample-overview")
out_path.mkdir(parents=True, exist_ok=True)
fn = out_path / "metadata.tsv"

metadata.to_csv(fn, sep="\t", index=False)
```

Later, reestablish the same relative path, use `pd.read_csv(fn, sep="\t")`, and inspect its contents. Do not automatically reload after every save. Protect original inputs and preserve meaningful failed or negative evidence when retiring obsolete code.

Keep plot preparation, plotting, display, and `fig.savefig(...)` near each other, using the current library and object interfaces. Do not import R plotting/device conventions or introduce a general wrapper. Record conclusions only after observing results; otherwise retain the specific next question.
