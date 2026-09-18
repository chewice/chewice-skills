"""TODO: 当前科学问题，以及上游输入来自哪里。"""

# %% 读取并检查样本信息
# 查看实际字段和少量记录，再确定分组与对齐方式。
# 本例使用 TSV；按目标对象的真实格式调整读取调用。
from pathlib import Path

import pandas as pd

metadata_path = Path("inputs/TODO_METADATA.tsv")
metadata = pd.read_csv(metadata_path, sep="\t")
print(metadata.head())
print(metadata.columns)

# %% 根据观察继续分析
# TODO：在同一会话中检查前段输出后，写入下一步及选择依据。
# 不预填未知分组、阈值或模型，也不把 None 传入尚未决定的下游步骤。
# 新增片段按需展示局部内容、摘要或诊断，再决定是否继续。
# 使用已有对象，不在每个 cell 重复加载数据；只保存有明确用途的结果。
