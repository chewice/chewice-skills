# 07 — Trajectory

## 任务主线

1. 读取目标细胞对象并检查 embedding、cluster 和样本构成。
2. 比较降维参数或候选表示。
3. 明确 root、terminal 和候选 lineage。
4. 构建 MST、principal curve 或用户指定轨迹。
5. 检查 pseudotime、分支和已知 marker 的一致性。
6. 按 lineage 拟合 dynamic genes。
7. 必要时做 imputation、NMF 或动态 module。
8. 解释 module function 与潜在 regulators。
9. 保存 lineage 对象、pseudotime、基因/模块表和诊断图。

## 保持可见的决定

- 降维方法、维数和邻域参数；
- root、terminal、lineage 和分支选择；
- pseudotime 方向；
- 动态基因模型、cutoff 和多重检验；
- imputation/NMF 的必要性；
- module 数量、功能和 regulator 筛选依据。

## 函数与重复

逐基因拟合、重复绘图和昂贵计算缓存适合窄局部函数。不同 lineage 可以保留平行脚本和
少量重复，以便每条分支的参数和生物学决定独立可读。不要建立隐藏端点选择的通用
trajectory pipeline。

## 检查重点

embedding 与 lineage 叠加、pseudotime 分布、已知 marker 趋势、模型成功率、
dynamic-gene 数量、module 稳定性和分组混杂。

## 不应泛化

不得复制 Mega/Ery/Mono/CLP/pDC 等具体谱系、端点、基因、module 数或 cutoff。
