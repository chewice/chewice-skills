# Report Validation

验证必须只读执行，至少检查：

- 输出位于 `reports/<Q-ID>/`，HTML 与 build metadata 均存在；
- HTML 使用 UTF-8、`lang="zh-CN"`，包含 title、main 和来源信息；
- metadata 中的 Question、Artifact、输入 hash、HTML hash 与实际文件一致；
- 所有 Artifact 仍为“审核通过”，BRIEF 仍具有 Human review；
- 本地资源存在于报告 `assets/`，hash 与 metadata 一致；
- 不含 `javascript:`、`vbscript:`、`file:`、远程图片、raw script 或越界链接；
- 不包含明显 placeholder。

报告生成后验证失败时，不得宣称交付完成。不得通过修改 BRIEF、RESULT 或研究状态来“修复”报告门槛；应回到 Human review 或上游事实源处理。
