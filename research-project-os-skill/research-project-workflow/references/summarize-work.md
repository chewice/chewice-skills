# 总结工作

仅在 Human 输入“总结工作”时执行本流程。

## 1. 核对事实

读取根 `AGENTS.md`、根 Project Router、Active context 的局部 Handoff（若声明）、active BRIEF/RESULT、它们明确引用的必要 receipt/validation，以及只读 Git 摘要。不要扫描整个仓库或未声明 context。

按以下边界核对：Question 与事前 Design 在 BRIEF；事后 Evidence/Inference 在 RESULT；Handoff 只负责路由。区分 observed facts、Agent inference、Human decisions 与待确认内容。technical validation、scientific support、Human approval、Question closure 和 implementation reuse 分别报告，不相互代替。

## 2. 输出总结

总结当前研究问题、事前设计是否已审核、新增 evidence（包括 null/negative/contradictory）、当前 inference 与 qualified claim、限制、Human 已作决定、最后验证点、blocker 和 next decisive action。若存在多个 context，只总结 Active context 和显式 cross-context dependencies。

## 3. 更新发生变化的事实源

生成一个带时区的 ISO 8601 时间戳并在本次更新中复用：

- 设计或 Human design review 变化时更新 BRIEF 及 `QUESTIONS.md` 对应索引行；不把事后结果写回 BRIEF。
- evidence、validation、inference、Human review 或 reuse 变化时更新当前 RESULT；不自行批准、拒绝或宣称 scientific validity。
- Question closure 只有 Human 明确决定时写入 BRIEF metadata，并机械同步索引。
- 更新 Active context 的 checkpoint、blocker、next decisive action 与 Required Reads；根 Router 只更新对应 Context Map 行和必要 cross-context dependency，不复制 BRIEF/RESULT。
- 只有发现新的、长期有效且跨 Question 复用的行为规则时才更新 `AGENTS.md`。

没有变化的 canonical record 不重写。用户已明确要求“总结工作”时，以上项目内、非覆盖/非破坏性更新无需再次确认；任何覆盖冲突、删除、Git mutation 或外部写入仍停止。

## 4. 验证与交接

运行只读 Validator，报告 `structure_consistent`、warnings 与 errors。Validator 失败时列出结构问题，不宣称科学工作无效；Validator 通过时也不宣称研究设计或结论有效。最后给出可直接恢复的 Active context、Required Reads 与 Next decisive action，不自动开始下一项分析或生成正式 Report。
