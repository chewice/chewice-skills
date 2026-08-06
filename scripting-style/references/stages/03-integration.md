# 03 — Integration

## 任务主线

1. 加载各样本对象并确认共有 feature 与 metadata。
2. 先建立未校正 baseline，观察 batch 与生物学分组。
3. 说明为什么需要整合以及选择当前方法的依据。
4. 准备方法所需输入，显式设置关键参数。
5. 执行整合并生成与 baseline 可比较的诊断。
6. 检查批次混合与生物学结构是否同时保留。
7. 保存整合对象与比较图，必要时单独导出下游对象。

## 保持可见的决定

- 是否需要校正；
- RPCA、Harmony 或其他方法的选择；
- feature、PC、anchor、theta 等方法参数依据；
- 哪些变量是 batch，哪些是要保留的生物学信号；
- 最终采用哪个结果进入下游。

## 风格边界

不同整合方法可以用独立短脚本表达，不必建立统一 integration wrapper。保持 baseline 和
校正后图使用可比较的分组、颜色和坐标设置。

## 检查重点

按 sample、batch、condition 和 cell type 查看降维图与数量分布；记录过度校正、
混合不足和稀有群丢失的证据。

## 不应泛化

不得把 RPCA、Harmony 或范例参数设为默认优选。
