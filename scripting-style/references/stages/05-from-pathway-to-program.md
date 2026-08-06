# 05 — From pathway to program

## 任务主线

1. 读取 program/activity 结果和对应 metadata。
2. 检查 program 数量、样本构成和矩阵方向。
3. 汇总 activity、variance、usage 或 top genes。
4. 明确选择需要解释的 program、gene set 或数据库。
5. 做 enrichment、pathway 或 metabolism scoring。
6. 比较分组并生成热图或排序图。
7. 按下游复查与复用需要，保存分数矩阵、富集表、top-gene 表或图。

## 保持可见的决定

- 选择哪个 program 及其依据；
- top genes 数量和筛选方法；
- gene set 来源、方向和重叠处理；
- 分组比较、排序和 cutoff；
- activity score 的解释边界。

## 函数边界

读取多个同构 gene-set 文件或重复保存图可以使用小函数。program 选择、基因筛选和
enrichment 问题应保留在主线。

## 证据边界

范例允许范围从 `02` 开始，只支持学习“解释已有 cNMF/program 结果”，不能据此假设
完整 cNMF 生成流程。

## 不应泛化

不得复制 program 编号、数据库版本、top-gene 数量、通路名或 cutoff。
