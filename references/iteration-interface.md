# Skill 迭代接口

## 目录

- [目标](#目标)
- [调用方式](#调用方式)
- [输入契约](#输入契约)
- [范例读取边界](#范例读取边界)
- [Phase 1：只读差异审查](#phase-1只读差异审查)
- [Phase 2：改善 Skill](#phase-2改善-skill)
- [完成标准](#完成标准)

## 目标

接收新的 R、Python 或 Bash 脚本范例，通过两阶段证据核查，改进现有
`scripting-style` Skill，同时避免：

- 新范例未经确认就改变规则；
- 单个脚本被提升为全局规范；
- validation holdout 泄漏到初始规则提炼；
- 复制来源代码、绝对路径或历史参数；
- 迭代过程修改来源范例；
- Skill 随迭代不断工程化和膨胀。

确定性预检脚本只验证请求、路径和文件清单。真正的语义比较、规则判断和 Skill 修改由
Codex 按本接口执行。

## 调用方式

### 对话入口

```text
使用 $scripting-style 的迭代接口执行 Phase 1。
目标 Skill：<SKILL_ROOT>
新范例：
- /absolute/path/to/example-a.R
- /absolute/path/to/example-b.sh
上下文 README：
- /absolute/path/to/README.md
补充说明：这些脚本分别解决什么问题。
```

Phase 1 汇报后，用户需要明确确认候选、排除项、holdout 和规则变化，才能继续：

```text
确认本次 Phase 1。
接受的决定：
- ...
进入 Phase 2，更新 <SKILL_ROOT>。
```

### JSON 入口

复制 [迭代请求模板](../templates/iteration-request.json)，填写后运行只读预检：

```bash
python3 scripts/validate-iteration-request.py /path/to/iteration-request.json
```

也可以从标准输入传入 JSON：

```bash
python3 scripts/validate-iteration-request.py -
```

预检只向 stdout 输出 JSON manifest，不创建报告、不复制脚本、不修改 Skill。

## 输入契约

| 字段 | 必需 | 含义 |
|---|---|---|
| `schema_version` | 是 | 当前固定为 `"1.0"` |
| `iteration_id` | 是 | 唯一、可读的迭代标识，如 `20260730-new-qc-examples` |
| `phase` | 是 | `phase1` 或 `phase2` |
| `target_skill` | 是 | 待改进的 Skill 根目录，必须包含 `SKILL.md` |
| `new_examples` | 是 | 新脚本文件或目录；只接收 `.R`、`.py`、`.sh` |
| `context_readmes` | 否 | 只用于理解用途和顺序的明确 `README.md` 路径 |
| `notes` | 否 | 用户说明的任务角色、API 边界或不能泛化的内容 |
| `phase1_review_dir` | Phase 2 是 | 已完成且获确认的 Phase 1 报告目录 |
| `approval.confirmed` | 是 | Phase 1 必须为 `false`；Phase 2 必须为 `true` |
| `approval.accepted_decisions` | Phase 2 是 | 用户明确接受的候选、排除、holdout 和变化 |

`new_examples` 项可以是路径字符串，也可以带提示：

```json
{
  "new_examples": [
    {
      "path": "/absolute/path/to/example.R",
      "stage_hint": "07-trajectory",
      "role_hint": "candidate"
    }
  ]
}
```

提示不是结论。Phase 1 仍需独立核查。

## 范例读取边界

目录输入若包含一个或多个 `scripts/`，只扫描这些脚本目录；没有 `scripts/` 时，才把
输入目录视为纯脚本集合。只发现 `.R`、`.py`、`.sh`，并跳过：

- `.git/`
- `.pixi/`
- `data/`
- `resources/`
- `softwares/`
- `参考文献/`
- 顶层或嵌套 `R/`
- 隐藏 cache 与生成目录
- `setup-vscode.sh` 等明确脚手架入口

README 必须通过 `context_readmes` 显式提供，只用于理解任务、顺序和输入输出，不学习排版、
安装或环境风格。

默认不复制来源脚本到 Skill。迭代报告只记录路径、hash、结构观察和最小证据片段；不得
整篇复制源代码。

`iterations/` 默认由 `.gitignore` 排除，因为 manifest 可能包含本机来源路径。只有在
人工清理绝对路径、个人信息和敏感上下文后，才有意提交精简的迭代摘要。

## Phase 1：只读差异审查

### 允许

1. 运行请求预检并建立新范例 manifest。
2. 读取当前 Skill 规则、范例索引和已有验证结论。
3. 读取允许范围内的新脚本与明确 README。
4. 区分 learning candidates、counterexamples、special status 和 holdouts。
5. 比较新范例与当前 Skill：
   - 已被覆盖的模式；
   - 支持但尚未稳定的模式；
   - 与现有规则冲突的模式；
   - 可能改善触发、流程、参考、模板或验证的证据。
6. 提出最小规则变化和新的回归验证集。

### 禁止

- 修改 `target_skill` 中的 `SKILL.md`、references、examples、templates、agents、
  validation 或其他功能文件；Phase 1 只允许写本次 iteration review；
- 修改或复制来源范例；
- 生成最终规则或模板；
- 使用拟议 holdout 提炼初始变化；
- 打开被排除目录或推断外部 API；
- 自动进入 Phase 2。

### 输出

写入：

```text
<target_skill>/iterations/<iteration_id>/phase1/
├── intake-manifest.json
├── corpus-delta.md
├── new-example-inventory.csv
├── candidate-changes.md
├── conflicts-and-uncertainties.md
├── proposed-validation-split.md
└── confirmation-request.md
```

只创建有内容的文件。完成后停止，并请求用户确认：

- learning candidates；
- counterexamples 与排除项；
- validation holdouts；
- 哪些规则保持不变；
- 哪些变化进入 Phase 2。

## Phase 2：改善 Skill

只有同时满足以下条件才允许修改：

1. 请求 `phase` 为 `phase2`；
2. `approval.confirmed` 为 `true`；
3. `phase1_review_dir` 存在；
4. `approval.accepted_decisions` 非空且可对应 Phase 1 报告；
5. 当前对话中有用户的明确确认。

执行顺序：

1. 重新读取已确认的 Phase 1 决定。
2. 先修改最具体的资源：
   - 范例索引；
   - 对应阶段指南；
   - 相关边界参考。
3. 只有跨阶段证据成立时才修改全局指南或 `SKILL.md`。
4. 只有现有模板无法表达稳定模式时才修改模板。
5. 保持 `AGENTS.md` 中以下约束不变：
   - 遵循第一性原理；
   - `You may use superpowers, but do not write any spec or plan.`
   - 减少函数封装和工程化代码。
6. 使用新 holdout 做 forward validation，再使用旧 holdout 做 regression validation。
7. 运行 Skill、YAML/JSON、链接和模板语法校验。

### 证据门槛

- **全局规则**：至少两个新范例、跨两个阶段支持，且旧回归集不反对；或用户显式规定。
- **阶段规则**：至少两个同阶段范例支持；或用户显式规定。
- **单脚本模式**：只进入范例说明或不确定项，不升级为强制规则。
- **模板变化**：必须代表重复出现的结构，并通过语法与 holdout 检查。
- **函数抽取**：仍需通过局部函数门槛，不因迭代接口本身增加 helper 层。

若新证据与旧证据冲突，优先收窄规则适用范围，不用更复杂的抽象掩盖冲突。

### 输出

原地改善 `target_skill`，并写入：

```text
<target_skill>/iterations/<iteration_id>/phase2/
├── accepted-decisions.yaml
├── change-summary.md
├── new-holdout-validation.md
├── regression-validation.md
└── final-validation.md
```

`change-summary.md` 必须列出：

- 修改了哪些 Skill 文件；
- 每项修改由哪些新证据支持；
- 哪些候选没有进入规则及原因；
- 是否改变触发描述、全局规则、阶段规则、模板或范例索引；
- 哪些不确定项仍保留。

## 完成标准

- 来源范例保持只读；
- Phase 1 和 Phase 2 有清楚人工确认边界；
- 新 holdout 未泄漏进初始规则；
- 原有稳定行为通过回归；
- 没有把单个脚本、环境路径或历史参数升级为通用规则；
- Skill 没有因迭代引入 class、公共函数库、配置平台或统一 pipeline；
- 校验全部通过，输出目录无 credentials、真实数据或 cache。
