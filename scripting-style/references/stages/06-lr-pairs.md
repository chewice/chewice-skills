# 06 — Ligand–receptor pairs

## 任务主线

1. 汇总输入对象并检查 sender、receiver、sample 和 stage。
2. 准备目标细胞或组织子集。
3. 对每个样本运行 CellChat 或用户指定 LR 方法。
4. 检查网络对象、通路数量和可用分组。
5. 生成样本级或整体网络图。
6. 比较 stage 间 interaction number、weight 或其他明确指标。
7. 聚焦特定 ligand–receptor 对并整理可解释表格和图。
8. 保存样本对象、比较表和最终图。

## 保持可见的决定

- sender/receiver、目标细胞和样本范围；
- 数据库或 signaling 类型；
- stage 定义与比较方向；
- 比较的是数量、权重还是表达；
- 聚焦 LR pair 的选择依据。

## 局部函数

单样本重复运行、网络图保存和同构汇总可以使用小函数。函数调用处显式传入分组、数据库、
比较指标和输出 stem。不要把整条 CellChat 研究问题藏进 `run_cellchat()` 默认值。

## 平行脚本

LR number 与 weight 的比较可保留独立脚本，使变化的指标和输出直接可见。只有技术步骤
长期同步修改并已出现漂移时，才抽取最小共同函数。

## 不应泛化

不得复制 early/late 定义、特定细胞对、LR pair、数据库或绘图尺度。
