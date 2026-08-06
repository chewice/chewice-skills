# 02 — Annotation

## 任务主线

1. 读取 QC 后对象并检查样本与已有标签。
2. 完成必要 normalization、降维和初步聚类。
3. 比较 PC、cell cycle、resolution 或其他诊断。
4. 生成 marker、参考映射或自动注释候选。
5. 明确区分检查点、决策点与专家判断。
6. 形成最终标签映射，检查 cluster 与 cell type 的关系。
7. 保存注释对象、marker 表、映射表和诊断图。

## 保持可见的决定

- 选择哪些 PCs 与 clustering resolution；
- 是否回归 cell cycle 或其他协变量；
- marker 证据、参考来源和冲突处理；
- manual 与 automated annotation 的分工；
- 合并、拆分或重命名 cluster 的理由。

## 局部函数

重复绘图或标签检查可用小函数。不要把 marker 选择、细胞类型判断或 label mapping
隐藏进不可见默认值。

## 检查重点

- 样本/cluster/cell type 交叉表；
- marker 表达与已知负 marker；
- 自动注释置信度及冲突；
- 注释前后细胞数量和未标注比例；
- 关键标签在降维图中的分布。

## 不应泛化

不得复制骨髓、PBMC 或其他组织的 marker、参考 atlas、标签和 resolution。
