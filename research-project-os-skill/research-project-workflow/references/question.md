# Question 与事前 Study Design

## 读取范围

通过根 `CURRENT_HANDOFF.md` 的 Context Map 定位目标 context，读取该 context 的 Handoff、`QUESTIONS.md` 中目标行、对应 `BRIEF.md`，以及 BRIEF 明确引用的资料。不要加载其他 Question。

## 创建 Question

明确收到创建问题的请求后，可直接执行项目内、非覆盖记录：

```bash
pixi run record-project new-question \
  --project /path/to/project --context root --question "研究问题"
pixi run record-project new-question \
  --project /path/to/project --context root --question "研究问题" --apply
```

命令从项目级最大 Q-ID 递增分配 `Q-NNN`，用同一 ISO 8601 时间戳创建 `docs/questions/<Q-ID>/BRIEF.md`、更新 `QUESTIONS.md` 与目标 Context Map 行。默认 dry-run；`--apply` 才写入，拒绝覆盖。ID 分配与索引同步是机械工作，不需要 Human 再次确认；Human 原始问题必须保留，Agent 不得把自己的解释冒充原问题。

`QUESTIONS.md` 只保存以下索引列：`Q-ID | Research question | Design review | Closure decision | Brief | Updated`。BRIEF 是研究问题与设计的事实源，Handoff 只引用 active ID 和 checkpoint，不复制设计内容。

## BRIEF 合同：只记录事前设计

顶层 metadata 至少包含：

- `Q-ID`、`Created`、`Updated`
- `Design review`、`Reviewed at`、`Review rationale`
- `Closure decision`、`Closed at`、`Closure rationale`

`Design review` 只允许 `pending | approved | rejected`；`Closure decision` 只允许 `open | answered | stopped`。只有 Human 可以把 review 改为 approved/rejected，或把 closure 从 open 改为 answered/stopped；决定、时间和理由必须共同记录。

固定章节如下：

1. `Research Question and Decision`
2. `Hypotheses and Falsifiers`
3. `Estimand and Inference Unit`
4. `Study Design and Evidence Eligibility`
5. `Analysis and Uncertainty`
6. `Claim-Evidence Matrix`
7. `Acceptance, Stopping and Risks`

BRIEF 必须回答：研究结果要改变什么决定；什么 observation 会反驳 hypothesis；研究对象、比较、outcome、时间与 inference unit 是什么；哪些 evidence 有资格进入推断；exploratory/confirmatory 边界、assumptions、confounding、missingness 与 uncertainty 如何处理；每条 planned qualified claim 由哪些 Evidence ID 检验；接受、停止和风险边界是什么。不适用的项目写明 `not applicable` 及理由，不用空泛占位符代替判断。

`Claim-Evidence Matrix` 使用 `Claim | Decisive evidence | Current evidence | Assessment` 四列，`Claim` 单元以 `C-NNN: qualified claim` 表示；它是最小映射，不创建额外 Evidence Registry。设计阶段预先写清什么 evidence 会改变判断，`Current evidence` 只引用 Evidence ID，不复制观察结果。事后 observation、effect、解释或运行 receipt 不得回填进 BRIEF，应写入 RESULT；若设计发生变更，保留 deviation 与时间，不把 post hoc 决定伪装成事前设计。

## 更新与关闭

Agent 可在不改变 Human 决定的前提下补全结构、风险、候选 falsifier 与 next decisive design。影响研究范围、estimand、证据资格、验收/停止条件的实质变更需 Human review。关闭 Question 前，必须引用支持 closure 的 RESULT/Evidence，给出 qualified claim 与未解决边界；`answered` 不等于所有 alternative explanation 已排除。
