# 候选范例说明

先按文件类型，再按任务相似度选择 candidate。runtime index 是 canonical 记录；本文件说明开发证据为何这样拆分。

- R learning examples 共同覆盖观察性检查、证据先于人工选择、method-specific 平行脚本、representative-trial-before-batch 与有用途的昂贵 cache。R API-like 与 function-heavy 文件保留为 counterexamples，而不是主风格来源。
- Python 只有一个窄 standalone 范例。它支持直接项目转换和已有 positional contract，不支持 `argparse`、`main()` 或通用 utility 形态。
- Bash learning 区分显式重复 sample commands 与多阶段 external analysis。STARsolo 保持 holdout，用于检查工具中立性，同时其中 environment 和 destructive temporary-path 细节被排除。
- Notebook learning 将 candidate-rank selection 与完整 model-analysis 配对。scANVI 与 BBKNN 保持同类型回归集，任何 stored output 都不被视作当前证据。

`primary`、`complement`、`validation_holdout` 和 `counterexample` 是证据角色，不是算法推荐或代码质量排名。任何来源参数、label、path 或生物学结果都不会因为角色而变得可迁移。
