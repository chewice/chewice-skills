# 研究项目工作流 Skill 优化任务清单

**版本时间：** 2026-08-03T17:49:00+08:00

## 一、最终架构决策

本次优化后，只保留两个面向团队的 Skill：

```text
1. research-project-workflow
2. report-generation
```

其中：

- `research-project-workflow`：负责研究项目脚手架、问题管理、Explore、Human 审核、Pipeline 晋升、Handoff 和“总结工作”。
- `report-generation`：负责将审核通过的研究内容生成 HTML/PDF 报告，并输出到 `reports/`。

不再将 Scaffold、Question、Explore 和 Handoff 拆成四个独立 Skill。

主 Skill 内部通过按需 reference 文件区分工作流程：

```text
research-project-workflow/
├── SKILL.md
├── references/
│   ├── scaffold.md
│   ├── question.md
│   ├── explore.md
│   ├── handoff.md
│   └── summarize-work.md
├── assets/
├── scripts/
├── tests/
├── pixi.toml
└── pixi.lock
```

原则：

> 团队只需要理解两个 Skill；Agent 每次只加载当前任务对应的 reference。

------

# 二、研究项目最终脚手架

```text
project/
├── AGENTS.md
├── QUESTIONS.md
├── CURRENT_HANDOFF.md
├── README.md
│
├── docs/
│   ├── questions/
│   ├── references/
│   │   ├── papers/
│   │   ├── official/
│   │   └── datasets/
│   ├── template/
│   ├── methods/
│   └── runbooks/
│
├── explore/
├── pipeline/
├── results/
├── reports/
├── logs/
├── configs/
├── tests/
│
├── pixi.toml
├── pixi.lock
└── .gitignore
```

## 明确不创建

```text
project_manifest.yaml
plans/current-plan.md
PLAN.md
SPEC.md
docs/architecture/
docs/paradigms/
docs/decisions/
external/
```

## 不提前创建实例目录

```text
docs/questions/Q-001/
explore/Q-001/
explore/Q-001/A-001/
results/Q-001/
reports/Q-001/
```

这些目录只有在真实 Question、Artifact、结果或报告产生时才建立。

------

# 三、任务 1：取消 RPOS 相关命名

删除所有用户可见的：

```text
RPOS
rpos
Research Project Operating System
```

统一采用直接描述用途的名称：

```text
research-project-workflow
report-generation
研究项目工作流 Skill
报告生成 Skill
```

研究项目仓库内部不出现 Skill 品牌名。

## 验收标准

- README、SKILL、代码注释和示例中不再使用 RPOS。
- 不存在 `rpos ...` 命令。
- 团队成员可直接根据名称理解用途。

------

# 四、任务 2：重构主 Skill 的内部结构

## `SKILL.md`

只保存：

1. Skill 的适用范围；
2. 触发条件；
3. 必须遵守的 Human ownership；
4. 当前任务应加载哪个 reference；
5. 禁止事项；
6. 停止和审核条件。

`SKILL.md` 不保存完整操作细节。

## 按需 references

### `references/scaffold.md`

负责：

- 初始化或接管项目；
- 创建稳定父目录；
- 创建根控制文件；
- 文件放置规则；
- Pixi 脚手架任务；
- 非破坏性写入要求。

### `references/question.md`

负责：

- 创建 Question；
- 更新 `QUESTIONS.md`；
- 创建和维护 `BRIEF.md`；
- Evidence Basis；
- Human 与 AI 的责任边界；
- Question 状态流转。

### `references/explore.md`

负责：

- 创建 Explore Artifact；
- 技术验证；
- 生成 `RESULT.md`；
- Human 审核；
- 拒绝版本保留；
- 审核通过后晋升到 `pipeline/`。

### `references/handoff.md`

负责：

- 恢复当前会话；
- 切换 Question 或 Workstream；
- 跨子项目摘要；
- Read Map；
- 更新 `CURRENT_HANDOFF.md`。

### `references/summarize-work.md`

负责关键语：

```text
总结工作
```

触发后的收尾和记忆更新流程。

## 验收标准

- `SKILL.md` 不重复五个 reference 的详细内容。
- Agent 只加载当前任务所需 reference。
- references 之间不重复维护同一状态定义。

------

# 五、任务 3：脚手架生成

只保留一个可选脚本：

```text
scripts/scaffold_project.py
```

通过 Pixi 运行：

```bash
pixi run scaffold-project
pixi run scaffold-project --apply
```

默认只显示拟创建内容，显式使用 `--apply` 后才写入。

## 脚手架创建

```text
AGENTS.md
QUESTIONS.md
CURRENT_HANDOFF.md
README.md
docs/questions/
docs/references/papers/
docs/references/official/
docs/references/datasets/
docs/template/
docs/methods/
docs/runbooks/
explore/
pipeline/
results/
reports/
logs/
configs/
tests/
pixi.toml
.gitignore
```

## 脚手架不得

- 覆盖已有文件；
- 删除已有内容；
- 创建虚假的 Q-ID 或 Artifact ID；
- 自动创建研究问题；
- 自动生成 Pipeline 实现；
- 自动执行 Git commit 或 push；
- 自动扫描 `docs/template/`；
- 自动修改已有研究结果。

------

# 六、任务 4：AGENTS.md 不可删除约束

生成和更新 `AGENTS.md` 时，必须原样保留：

```markdown
## Language

- 面向 human 的说明默认使用中文。 
- 专业术语、code、paths、commands、IDs 和 machine-readable values 等agent方便识别的内容保持英文。

## Reasoning

- 遵循第一性原理

## Superpowers

- You may use superpowers, but do not write any spec or plan.
```

## 约束

- 不得删除、改名、合并或弱化。
- Human 未明确要求时不得改写文字。
- Validator 必须检查三段是否完整。
- Skill 不创建独立 `SPEC.md`、`PLAN.md` 或 `current-plan.md`。

问题解决依据写入 `BRIEF.md`，当前动作写入 `CURRENT_HANDOFF.md`，Explore 结果写入 `RESULT.md`。

------

# 七、任务 5：QUESTIONS.md

`QUESTIONS.md` 只作为问题索引。

```markdown
| Q-ID | Question | Status | Brief | Updated |
|---|---|---|---|---|
| Q-001 | 如何评估当前整合策略？ | 解决中 | docs/questions/Q-001/BRIEF.md | 2026-08-03T17:49:00+08:00 |
```

## 字段

- `Q-ID`
- Human 原始问题的简短表达
- `Status`
- `BRIEF.md` 相对路径
- `Updated`

## Question 状态

```text
拟定
解决中
已解决
废弃
```

### 定义

- `拟定`：问题已记录，尚未正式开始。
- `解决中`：正在调研、讨论、Explore 或审核。
- `已解决`：Human 已接受最终结论。
- `废弃`：Human 决定不再继续，但保留提出和处理经过。

`QUESTIONS.md` 不保存完整 Evidence、方案、结果、日志或审核论证。

------

# 八、任务 6：BRIEF.md

路径：

```text
docs/questions/<Q-ID>/BRIEF.md
```

## 定位

`BRIEF.md` 是 AI 维护、Human 审批的问题工作依据。

## 模板

```markdown
# Q-XXX Brief

Status:
Created:
Updated:
Human review status:

## 1. Human Question

## 2. Problem Interpretation

## 3. Context and Scope
### Context
### In Scope
### Out of Scope

## 4. Evidence Basis
### Project Evidence
### Literature and Official Guidance
### Reference Code

## 5. Evidence Synthesis

## 6. Proposed Resolution

## 7. Inputs, Outputs and Dependencies

## 8. Validation and Acceptance Criteria

## 9. Open Questions and Risks

## 10. Human Review

## 11. Closure Summary
```

## Human 负责

- 提出问题；
- 确认问题是否开始；
- 确认不可突破的限制；
- 确认 Evidence Basis；
- 确认解决方式；
- 确认验收条件；
- 审核 Artifact；
- 决定 Question 状态；
- 决定是否进入 Pipeline。

## AI 负责

- 结构化问题；
- 补充项目上下文；
- 调研文献和官方资料；
- 阅读 Human 明确指定的参考代码；
- 起草 Evidence Synthesis；
- 起草解决方案；
- 设计验证；
- 更新风险与开放问题；
- 记录 Human 决定；
- 维护 BRIEF；
- 在“总结工作”时更新 Closure Summary。

------

# 九、任务 7：docs 目录边界

## `docs/questions/`

保存具体 Question 的 `BRIEF.md`。

## `docs/references/`

```text
papers/    文献整理
official/  官方文档和官方 Pipeline
datasets/  数据库与数据资源说明
```

## `docs/template/`

保存 Human 主动提供的参考代码：

- GitHub 仓库副本；
- 论文源码；
- 教师脚本；
- 示例配置；
- 其他项目实现。

约束：

- Skill 不自动扫描；
- 不自动注册；
- 不自动更新；
- 不自动验证；
- 不自动同步 GitHub；
- 不作为 Pipeline 依赖；
- Human 明确 `@` 后 Agent 才读取。

## `docs/methods/`

只保存已经跨多个 Question 实际复用的方法。

## `docs/runbooks/`

保存恢复、重跑、故障处理和人工操作流程。

## 删除

```text
docs/architecture/
docs/paradigms/
docs/decisions/
```

目录说明统一放在根 `README.md`，强制规则摘要放在 `AGENTS.md`。

------

# 十、任务 8：Explore Artifact

目录示例：

```text
explore/
└── Q-001/
    ├── A-001/
    │   ├── RESULT.md
    │   ├── code/
    │   ├── config/
    │   └── logs/
    └── A-002/
```

## Artifact 状态

```text
草稿
待审核
审核通过
拒绝
```

### 定义

- `草稿`：仍在开发、运行或验证。
- `待审核`：最低技术验证通过，提交 Human 审核。
- `审核通过`：Human 接受该版本。
- `拒绝`：Human 不接受，保留记录但不得进入主线。

## 从草稿进入待审核的门槛

- 声明命令执行成功；
- 声明输出存在；
- 最小验证通过；
- `RESULT.md` 已生成；
- 关键限制已经记录。

技术验证是状态转换门槛，不单独设为状态。

## 拒绝版本

被拒绝的 `A-001` 不得覆盖。修订后建立 `A-002`。

## Promotion

Promotion 不增加 Artifact 状态，只记录：

```text
pipeline target
promotion commit
promoted at
promoted files
```

只有“审核通过”的 Artifact 可以进入 `pipeline/`。

------

# 十一、任务 9：Workstream 状态

只允许：

```text
待启动
进行中
已完成
终止
```

阻塞、等待审核、等待输入、暂停和验证待运行均不作为独立状态。

统一记录为：

```text
Status: 进行中
Blocker: ...
Current checkpoint: ...
```

Question、Artifact 和 Workstream 三个状态域必须独立。

------

# 十二、任务 10：CURRENT_HANDOFF.md

`CURRENT_HANDOFF.md` 是唯一默认状态入口。

```markdown
# CURRENT_HANDOFF

Updated:
Active question:
Active workstream:
Current artifact:
Current checkpoint:
Status:

## 1. 当前目标

## 2. 当前问题摘要

## 3. 跨工作流状态

| Workstream | Status | Dependency | Detail |
|---|---|---|---|

## 4. 最近完成

## 5. 当前阻塞

## 6. 立即下一步

## 7. 验证

## 8. 读取路由
### 必须读取
### 仅在需要时读取
### 不要加载
```

## 长度

```text
推荐：600–1,200 个中文字符
硬上限：2,000 字
```

## 不保存

- 完整历史；
- 所有 Question；
- 所有文献；
- 全部日志；
- 全部旧 Artifact；
- 完整聊天；
- 大型代码；
- 所有子项目详情。

旧 HANDOFF 历史由 Git 保存，不单独生成归档 Markdown。

------

# 十三、任务 11：“总结工作”触发流程

当 Human 输入：

```text
总结工作
```

主 Skill 加载：

```text
references/summarize-work.md
```

并执行以下流程。

## 1. 核对当前事实

读取：

```text
AGENTS.md
CURRENT_HANDOFF.md
当前 Question 的 QUESTIONS.md 索引行
当前 BRIEF.md
当前 RESULT.md
必要验证结果
git status
git diff --stat
最近相关 commit
```

不扫描整个仓库。

## 2. 输出今日工作总结

至少包括：

- 今天处理的问题；
- 完成的工作；
- 关键判断；
- 运行和验证结果；
- Human 已确认的决定；
- 未完成事项；
- 下一步入口。

## 3. 更新 QUESTIONS.md

更新：

- Question 状态；
- BRIEF 路径；
- `Updated`。

只有 Human 明确确认时，才可改为“已解决”或“废弃”。

## 4. 更新 BRIEF.md

更新：

- Context；
- Evidence Basis；
- Evidence Synthesis；
- Proposed Resolution；
- Validation；
- Human Review；
- Open Questions；
- Closure Summary；
- `Updated`。

## 5. 更新 RESULT.md

存在当前 Artifact 时，更新：

- Artifact 状态；
- 验证结果；
- Human 审核；
- 通过或拒绝原因；
- Promotion 事实；
- 时间戳。

## 6. 检查 AGENTS.md

只有发现新的、长期有效、可跨 Question 复用的行为规则时，才更新 `AGENTS.md`。

不得将当前进度、临时参数、错误或单次结果写入 `AGENTS.md`。

## 7. 更新 CURRENT_HANDOFF.md

覆盖更新当前状态、最近完成、阻塞、下一步、验证和 Read Map。

## 8. 运行 Validator

```bash
pixi run validate-project
```

验证失败时不得宣称工作已完成。

## 9. 统一时间戳

同一次收尾使用同一个 ISO 8601 时间戳：

```text
2026-08-03T17:49:00+08:00
```

## 禁止行为

“总结工作”不得：

- 自动 commit 或 push；
- 自动批准 Artifact；
- 自动将 Question 标记为已解决；
- 自动开始下一个 Question；
- 自动生成正式 Report；
- 自动修改 `docs/template/`；
- 自动伪造验证结果。

------

# 十四、任务 12：Pixi 辅助脚本

只保留两个辅助脚本。

## 脚手架脚本

```text
scripts/scaffold_project.py
pixi run scaffold-project
pixi run scaffold-project --apply
```

## 只读验证脚本

```text
scripts/validate_project.py
pixi run validate-project
```

Validator 检查：

- 根文件和父目录；
- `AGENTS.md` 三段不可删除规则；
- Question 状态；
- BRIEF 路径；
- Handoff 引用；
- Artifact 状态；
- 待审核 Artifact 的 `RESULT.md`；
- Human Review；
- 文件放置规则；
- Pipeline 是否直接依赖 `docs/template/`；
- 被删除的旧结构是否仍存在。

Validator 必须只读，不自动修复。

## Pixi tasks

至少包含：

```text
scaffold-project
validate-project
test
lint
```

------

# 十五、任务 13：tests、configs、results 和 reports

## `tests/`

保留，用于：

- Pipeline 自动测试；
- 数据转换验证；
- Schema 检查；
- 回归测试；
- 脚手架和 Validator 测试。

初始化时只建立父目录和说明文件。

## `configs/`

保留，用于：

- 跨模块共享的稳定配置；
- Pipeline 正式参数；
- 避免参数散落。

Explore 临时配置留在 Artifact 内，只有审核通过且具有复用价值时才进入根 `configs/`。

## `results/`

保存：

- 表格；
- 图；
- 模型；
- 统计结果；
- 机器可读产物。

## `reports/`

保存由独立 `report-generation` Skill 生成的正式报告。

------

# 十六、任务 14：独立 report-generation Skill

## Skill 结构

```text
report-generation/
├── SKILL.md
├── references/
│   ├── html.md
│   ├── pdf.md
│   ├── templates.md
│   └── validation.md
├── assets/
│   ├── templates/
│   └── css/
├── scripts/
├── tests/
├── pixi.toml
└── pixi.lock
```

## 输入

只读取经过审核的：

```text
docs/questions/<Q-ID>/BRIEF.md
explore/<Q-ID>/<A-ID>/RESULT.md
results/<Q-ID>/
必要的 Pipeline 说明
Human 指定的报告要求
```

## 输出

```text
reports/<Q-ID>/
├── report.html
├── report.pdf        # 可选
├── assets/
└── build metadata    # 可选
```

## 能力

- HTML 生成；
- PDF 生成；
- 模板管理；
- CSS；
- 图表和资源嵌入；
- 链接校验；
- 报告结构校验；
- 输出文件完整性验证。

## 禁止

Report Skill 不得：

- 修改 `QUESTIONS.md` 状态；
- 修改 Artifact 状态；
- 批准结果；
- 修改 Pipeline；
- 执行 Explore；
- 将未经审核的内容表述为正式结论；
- 将 Report 作为唯一科学事实源。

## 边界

```text
results/ = 分析事实与机器可读产物
reports/ = 面向 Human 的表达和交付
```

------

# 十七、任务 15：其他移出核心的能力如何处理

“移出核心”不等于生成多个新 Skill。

## 项目原生能力

以下由研究项目自身负责：

```text
Pipeline runtime
任务调度
Pixi analysis tasks
Snakemake/Nextflow
SLURM
正式测试
共享配置
结果生成
```

## 外部现有能力

以下调用现有工具：

```text
文献检索
GitHub clone/fetch/pull
Git 操作
PDF 获取
引文管理
```

## 可选未来工具

未来确有需要时，可开发为 Pixi 脚本或验证工具：

```text
不可变 release archive
vNNN snapshot
release-grade audit
强 provenance
大文件 hash 策略
```

不必现在拆成 Skill。

## 明确不管理

```text
docs/template/
```

由 Human 自行提供和 `@`，Skill 不做自动管理。

------

# 十八、任务 16：上下文与 token 控制

## 主 Skill 默认加载

### Scaffold

```text
SKILL.md
references/scaffold.md
目标目录浅层结构
已有 AGENTS.md
已有 Pixi 文件
```

### Question

```text
SKILL.md
references/question.md
CURRENT_HANDOFF.md
目标 Question 索引行
当前 BRIEF.md
BRIEF 明确引用的 references
Human 明确 @ 的 template
```

### Explore

```text
SKILL.md
references/explore.md
CURRENT_HANDOFF.md
当前 BRIEF.md
当前 Artifact
必要输入和指定日志
```

### Handoff

```text
SKILL.md
references/handoff.md
AGENTS.md
CURRENT_HANDOFF.md
git status
git diff --stat
Read Map 指定文件
```

### 总结工作

```text
SKILL.md
references/summarize-work.md
AGENTS.md
CURRENT_HANDOFF.md
当前 Question 索引行
当前 BRIEF.md
当前 RESULT.md
必要验证结果
Git 摘要
```

## 默认禁止加载

```text
所有历史 Question
所有 BRIEF
全部 references
整个 docs/template/
全部旧 Artifact
全部日志
所有子项目
旧 HANDOFF
```

## 长度建议

```text
主 SKILL.md：500–900 中文字符
scaffold.md：500–900 中文字符
question.md：800–1,300 中文字符
explore.md：800–1,300 中文字符
handoff.md：600–1,000 中文字符
summarize-work.md：800–1,300 中文字符
```

能够由 Validator 检查的规则，不重复写入所有 reference。

------

# 十九、任务 17：清理旧架构

删除或迁移：

```text
RPOS/rpos
project_manifest.yaml
current-plan.md
PLAN.md 强制依赖
SPEC.md
block-based QUESTIONS.md
旧 Question 状态
旧 Artifact 状态
复杂 Workstream 状态
docs/architecture/
docs/paradigms/
docs/decisions/
external/
核心 reporting.py
archive-promote
archive-verify
pipeline-create
pipeline-release
report-build
多层 lifecycle schema
默认全量 SHA-256
历史 HANDOFF Markdown 归档
```

旧项目只提供一次性迁移说明，不在新核心长期维护多版本兼容。

------

# 二十、最终保留

## 主研究项目工作流 Skill

```text
Scaffold
Question
BRIEF
Explore
Human Review
Promotion Contract
Handoff
总结工作
Validator
```

## 独立报告 Skill

```text
HTML
PDF
Templates
CSS
Report Validation
reports/ output
```

## 项目目录

```text
AGENTS.md
QUESTIONS.md
CURRENT_HANDOFF.md
README.md
docs/questions/
docs/references/
docs/template/
docs/methods/
docs/runbooks/
explore/
pipeline/
results/
reports/
logs/
configs/
tests/
Pixi
```

------

# 二十一、推荐实施顺序

```text
1. 清理 RPOS 和旧命名
2. 删除 project_manifest、current-plan 和旧目录
3. 固化 AGENTS.md 三段规则
4. 重建项目脚手架
5. 重构 QUESTIONS.md
6. 重构 BRIEF.md
7. 重构 Explore 和 RESULT.md
8. 压缩 Question、Artifact、Workstream 状态
9. 重构 CURRENT_HANDOFF.md
10. 实现“总结工作”
11. 实现 scaffold_project.py
12. 实现 validate_project.py
13. 补充 Pixi tasks 和 tests
14. 拆分独立 report-generation Skill
15. 更新主 SKILL.md 与五个 references
16. 清理旧 Reporting、Archive 和 CLI
17. 执行迁移测试和最终验收
```