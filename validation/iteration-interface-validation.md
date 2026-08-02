# 迭代接口验证

## 范围

- 验证日期：2026-07-30
- 路径边界回归：2026-08-02
- 接口：自然语言入口、JSON request contract、只读预检脚本
- 脚本：`scripts/validate-iteration-request.py`
- 目标：验证 Phase 1/2 阶段门、范例发现、排除规则和无写入属性

## 验证结果

| 场景 | 预期 | 结果 |
|---|---|---|
| 单个 R 脚本进入 Phase 1 | 生成一个 manifest 项；只允许 iteration review 写入 | Pass |
| 整个项目目录进入 Phase 1 | 只发现 `scripts/` 下 3 个脚本 | Pass |
| 项目根目录含 `setup-vscode.sh` | 不进入范例 manifest | Pass |
| 显式输入 `setup-vscode.sh` | 拒绝请求 | Pass |
| 已确认的 Phase 2 request | contract 完整，但 validator 不授予写权限 | Pass |
| 未确认的 Phase 2 request | 拒绝请求 | Pass |
| 请求模板 | 标准 JSON 可解析 | Pass |
| 预检脚本 | Python 语法有效，无第三方依赖 | Pass |
| `/home/data/...` 中的合法脚本 | 不把机器祖先目录 `data` 误判为来源内部目录 | Pass |
| 来源 repository 内部 `data/` 与 `R/` | 显式文件输入被拒绝，目录扫描不发现 | Pass |

## 阶段门

### Phase 1

有效请求必须满足：

- `phase` 为 `phase1`；
- `approval.confirmed` 严格为 `false`；
- `target_skill` 包含 `SKILL.md`；
- 至少发现一个 `.R`、`.py` 或 `.sh`；
- manifest 标记来源范例只读、Skill 规则不可写；
- 只允许后续工作流写入本次 `iterations/<iteration_id>/phase1/`；
- manifest 始终标记 `validator_grants_write_authority: false`。

### Phase 2

有效 contract 必须满足：

- `phase` 为 `phase2`；
- `approval.confirmed` 严格为 `true`；
- `accepted_decisions` 非空；
- `phase1_review_dir` 存在；
- manifest 标记仍要求当前对话中的用户确认；
- validator 本身不授予文件写权限。

因此 request 文件不能绕过会话中的人工确认。

## 范例发现

目录输入按以下规则验证：

1. 如果发现 `scripts/`，只扫描这些目录。
2. 没有 `scripts/` 时，才把输入目录视为纯脚本集合。
3. 跳过 `.git`、`.pixi`、`data`、`R`、`resources`、`softwares`、
   `参考文献`、cache 和隐藏目录。
4. 跳过 `setup-vscode.sh`。
5. 只输出路径、语言、行数、文件大小、SHA-256 和用户提示，不输出源代码。

使用 `01-scrna-qc` 项目根目录测试时，准确发现：

- `scripts/01-cellranger.sh`
- `scripts/02-starsolo.sh`
- `scripts/03-calculate_metrics.R`

根目录脚手架没有进入 manifest。

2026-08-02 回归进一步把 excluded-directory 检查限定在最近 repository root 内部。
合法来源即使位于机器级 `/home/data/...` 路径也能通过；fixture repository 内部的
`data/ignored.R` 与 `R/ignored.R` 仍被拒绝，目录输入只发现 `scripts/example.R`。

## 无写入验证

预检脚本自身：

- 只读取 request、目标 `SKILL.md`、新范例和显式 README；
- 只向 stdout 输出 JSON；
- 不创建 `iterations/`；
- 不复制或修改范例；
- 不修改目标 Skill；
- 不生成 cache。

Phase 1/2 的报告和 Skill 修改只能由 Codex 按
`references/iteration-interface.md` 的语义工作流执行。

## 结论

迭代接口可以接收单个脚本或项目目录，在 Phase 1 建立干净的新范例 manifest，并阻止
未经确认的 Phase 2。接口保持轻量：一个 JSON contract、一个单入口标准库脚本和一份
渐进披露参考，没有引入服务、数据库、公共函数库或工作流平台。
