"""TODO: 当前科学问题，以及上游输入来自哪里。"""

# %% 工作目录
# 从项目根启动 scripts/analysis.py；若已在文件目录，将目标改为 "."。只运行一次。
import os
from pathlib import Path

os.chdir("scripts")
print(Path.cwd())

import pandas as pd

# %% 读取样本信息
# 查看字段、类型和少量记录，再确定后续分组。
data_path = Path("../data")
fn = data_path / "TODO_METADATA.tsv"
metadata = pd.read_csv(fn, sep="\t")

print(type(metadata))
print(metadata.head())
print(metadata.columns)

# %% 根据观察继续
# TODO：检查实际输出后续写下一步，选择依据放在调用附近。

# 后续确需这份表时，可在对应片段保存；格式与列名沿用项目约定。
# out_path = Path("../results/TODO_STEP")
# out_path.mkdir(parents=True, exist_ok=True)
# fn = out_path / "metadata.tsv"
# metadata.to_csv(fn, sep="\t", index=False)
