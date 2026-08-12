# 迭代接口验证

## 范围

- 验证日期：2026-08-13
- contract：`schema_version: "1.0"`
- 支持来源扩展名：`.R`、`.py`、`.sh`、`.ipynb`
- 确定性测试：`python3 scripts/test-validate-iteration-request.py`
- validator：`scripts/validate-iteration-request.py`

该接口继续作为开发专用的 Phase 1 / Phase 2 gate，不参与日常科研脚本路由。

## 自动回归结果

| 场景 | 预期行为 | 结果 |
|---|---|---|
| 既有 schema 1.0 R request | 接受并标记 language `R` | Pass |
| schema 2.0 request | 拒绝 | Pass |
| 显式 Notebook | 接受并标记 language `Notebook` | Pass |
| 旧 `stage_hint` | 作为语境原样保留，永不用于选择指南 | Pass |
| 混合 fixture root | 只发现 `scripts/` 下的 R、Python、Bash、Notebook | Pass |
| 显式 01–07 项目目录列表 | 发现 51 R、1 Python、3 Bash、4 Notebook，共 59 个 | Pass |
| fixture `data/` 与 `R/` 输入 | 在 repository boundary 内明确拒绝 | Pass |
| repository 外机器祖先名为 `data` | 不误判为项目内部排除目录 | Pass |
| 后缀为 `.ipynb` 的 malformed 文件 | byte-level preflight 接受，留给语义审查 | Pass |
| Phase 1 使用 `approval.confirmed: true` | 拒绝 | Pass |
| Phase 2 的 accepted decisions 为空 | 拒绝 | Pass |
| 结构完整的 Phase 2 | 接受结构，但 authority 仍为 false，仍要求当前确认 | Pass |
| validator 调用前后 Skill fingerprint | 完全不变 | Pass |

## 发现边界

目录输入中存在 `scripts/` 时，validator 只搜索这些目录；否则把输入当作纯范例目录。它排除所有 hidden directories，以及显式的 `.git`、`.pixi`、`__pycache__`、`data`、`R`、`resources`、`softwares`、`参考文献`，并跳过 `setup-vscode.sh`。

repository-relative exclusion 不检查机器祖先目录名。无法检测 repository boundary 时，显式文件视为用户授权输入；目录扫描仍按名称排除子目录。

validator 读取 Notebook bytes 以计算 size 与 SHA-256，但有意不验证 Notebook JSON、cell execution 或 stored outputs；这些是 Phase 1 语义审查职责。单独的模板校验会解析 JSON，并要求新 Notebook code cells 使用空 outputs 与 `null` execution counts。

## Hint 与确认语义

`stage_hint` 和 `role_hint` 是为 schema 1.0 兼容保留的 opaque reviewer context。阶段指南已不存在，因此它们不能路由。agent 直接从原请求读取 `notes`；validator 不把这些字段解释成科学事实。

`phase2_request_complete: true` 只表示 JSON shape、review-directory 存在性、confirmation boolean 与 nonempty decisions 通过确定性检查。它不验证 decisions 是否对应 Phase 1，也不授予写权限。因此 manifest 始终保留：

- `validator_grants_write_authority: false`；
- Phase 2 的 `requires_current_conversation_confirmation: true`；
- `skill_rule_write_allowed: false`。

## 无写入属性

validator 读取 request、目标 `SKILL.md`、允许的 examples 与显式 README，再向 stdout 输出 JSON。回归测试在正负请求前后 fingerprint 所有持久 Skill 文件。它不创建 iteration report、source copy、cache、completion marker 或 Skill modification。
