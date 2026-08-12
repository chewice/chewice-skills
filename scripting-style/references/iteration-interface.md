# Skill 迭代接口

只有用户要求审查新范例或改善 `scripting-style` 时才读取本文件。它是开发入口，不属于日常脚本生成上下文。

## 目标

用新的 `.R`、`.py`、`.sh` 或 `.ipynb` 证据改善 Skill，同时防止一个范例、历史 output 或环境痕迹静默改写规则。确定性 validator 只检查请求形态、路径、hash 和人工确认字段；语义比较与后续修改仍由 agent 负责。

## 请求契约

现有 contract 保持 `schema_version: "1.0"`。

| 字段 | 必需 | 含义 |
|---|---|---|
| `schema_version` | 是 | 固定为 `"1.0"` |
| `iteration_id` | 是 | 由字母、数字、`-` 或 `_` 组成的可读标识 |
| `phase` | 是 | `phase1` 或 `phase2` |
| `target_skill` | 是 | 包含 `SKILL.md` 的 Skill root |
| `new_examples` | 是 | `.R`、`.py`、`.sh`、`.ipynb` 文件或其目录 |
| `context_readmes` | 否 | 只用于理解任务与顺序的显式 `README.md` |
| `notes` | 否 | 用户提供的角色、API 边界和排除项 |
| `phase1_review_dir` | Phase 2 | 已完成的 Phase 1 review directory |
| `approval.confirmed` | 是 | Phase 1 为 `false`，Phase 2 为 `true` |
| `approval.accepted_decisions` | Phase 2 | 可对应审查结论的非空决定列表 |

每个 `new_examples` 项可以是 path string，也可以是包含 `path`、可选 `role_hint` 和可选 `stage_hint` 的 mapping。`stage_hint` 仅为向后兼容和语境备注保留，永远不选择阶段指南；所有比较都按准确文件类型路由。

使用请求文件或标准输入运行只读预检：

```bash
python3 scripts/validate-iteration-request.py /path/to/request.json
python3 scripts/validate-iteration-request.py -
```

validator 只向 stdout 写 JSON manifest。它不创建 iteration directory、不复制范例、不修改规则，也不授予 Phase 2 写权限。`phase2_request_complete: true` 只表示 Phase 2 请求通过结构检查；它不能证明 decisions 与 Phase 1 对应，也不能取代当前对话确认。

## 来源发现与隐私

目录包含一个或多个 `scripts/` 时，只检查这些目录；否则把输入视为纯范例目录。只发现四种支持的扩展名，并排除 `.git/`、`.pixi/`、`data/`、`R/`、`resources/`、`softwares/`、`参考文献/`、所有 hidden directories、`__pycache__/` 和 `setup-vscode.sh` 等脚手架入口。

显式 `README.md` 只能解释目的、顺序和输入输出关系。不得学习其排版、安装说明或环境配置。被排除的项目 API 始终视为不透明边界。

来源范例保持只读。review artifact 可能含本机路径，因此 `iterations/` 保持 gitignored；准备提交的证据必须清除个人绝对路径、参数、私有数据和生物学结论。`notes`、`stage_hint` 和 `role_hint` 仅是 reviewer context；validator 不把它们解释成 selector 或科学事实。

对 Notebook，validator 只 hash bytes，不验证 Notebook JSON 或执行语义。Phase 1 必须检查 source cells 和顺序，并拒绝或分类 malformed artifact。stored outputs、execution counts、transient widgets 和环境 metadata 都是未验证历史状态，不得升级为代码或结论。

## Phase 1：只读证据审查

Phase 1 可以：

1. 校验请求，并用 hash 清点允许的文件；
2. 读取当前 Skill、索引和既有验证；
3. 只用同类型指南与范例比较每个新文件；
4. 区分 learning candidate、complement、holdout、counterexample 和 exclusion；
5. 识别已支持、冲突、不确定或遗漏的模式；
6. 提出最小规则、trigger、template、index 或测试变化。

Phase 1 不得修改 `SKILL.md`、references、examples、templates、agents metadata、validator behavior 或已提交 validation files。它只能在下列目录写有实际内容的 review：

```text
iterations/<iteration_id>/phase1/
```

有效 review 可包含 intake manifest、corpus delta、candidate changes、实际存在的 conflict / exclusion、learning/holdout split 和 confirmation request；不必为凑齐目录制造所有可能报告。

汇报后停止，请用户确认 learning candidates、counterexamples、exclusions、holdouts、保持不变的规则与 proposed changes。

## Phase 2：实施已确认决定

Phase 2 必须同时满足：

1. `phase` 为 `phase2`；
2. `approval.confirmed` 为 `true`；
3. `phase1_review_dir` 存在；
4. `approval.accepted_decisions` 非空且可追溯到 Phase 1；
5. 当前对话包含用户明确确认。

随后：

1. 重读 accepted decisions 与 exclusions；
2. 先更新准确文件类型对应的 index、guide 和 template；
3. 只有真正共享的原则或用户明确规则才修改 `SKILL.md`；
4. 保留仓库原句 `You may use superpowers, but do not write any spec or plan.`；
5. 新同类型 holdout 在用于修订前先完成验证；
6. 重跑既有跨任务 holdout 与结构测试；
7. 记录实际修改、未采用候选和仍然不确定之处。

文件类型规则需要重复的同类型证据或用户明确决定。跨类型规则只能来自最高原则层面的证据，不能规定具体语法。证据冲突时收窄规则，不得增加抽象层掩盖冲突。

Phase 2 记录位于：

```text
iterations/<iteration_id>/phase2/
├── accepted-decisions.yaml
├── change-summary.md
├── new-holdout-validation.md
├── regression-validation.md
└── final-validation.md
```

只创建有内容的文件。这些记录不能替代功能 Skill 或 validation output。

## 完成标准

- 来源 hash 未变，且没有复制或修改来源文件；
- exact-type routing 保持成立；
- holdout 没有泄漏进 initial change；
- 新旧 holdout 均被检查；
- 没有把历史参数、生物学结论、机器路径、credential、cache 或 stale Notebook output 变成 default；
- Skill 没有增加 generic CLI、public helper library、config platform、runner 或 pipeline；
- frontmatter、YAML、JSON、links、templates 与 request compatibility 全部通过。
