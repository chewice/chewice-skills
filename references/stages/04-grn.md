# 04 — GRN

## 任务主线

1. 明确表达矩阵、metadata、目标细胞和 regulon/TF 资源。
2. 准备 metacell、pySCENIC 或用户提供 API 所需输入。
3. 检查细胞数、基因数、分组和标识符一致性。
4. 调用外部工具或不透明 API。
5. 检查 regulon、activity 或 target 结果结构。
6. 先做 unsupervised 总览，再按明确生物学假设聚焦。
7. 保存中间对象、regulon 表、activity 矩阵和解释性图。

## 保持可见的决定

- 分析细胞范围与分组；
- metacell 或其他聚合参数；
- regulon/TF/target 的筛选条件；
- unsupervised 与 hypothesis-driven 问题的区别；
- 选择特定 regulon 或 target 的生物学依据。

## API 与函数

顶层 GRN API 一律视为不透明边界，使用“准备—调用—检查—保存”。局部函数可承担
purity、bootstrap、重复绘图或其他窄技术计算；不要把完整假设检验主线隐藏进函数。

## 特殊样例边界

`02-regulon_activity_score.R` 是已确认的 API-like 反例，不用于学习分析脚本主风格。
`04-hypothesis_driven_partII.R` 与 `06-screen_TFs_for_given_target.R` 被用户确认具有
未分类的特殊地位；在角色明确前，不据其新增规则或宣称 legacy。

## 不应泛化

不得复制 TF 列表、target、activity cutoff、特定细胞类型或外部资源路径。
