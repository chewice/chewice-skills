"""TODO: Current scientific question and upstream input provenance."""

# %% Working directory
# Launch from the project root; use "." if already in the script directory.
import os
from pathlib import Path

os.chdir("scripts")
print(Path.cwd())

import pandas as pd

# %% Read sample metadata
# Inspect fields, types, and records before defining groups.
data_path = Path("../data")
fn = data_path / "TODO_METADATA.tsv"
metadata = pd.read_csv(fn, sep="\t")

print(type(metadata))
print(metadata.head())
print(metadata.columns)
