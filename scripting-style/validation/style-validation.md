# Type-first 风格验证

## 范围

- 验证日期：2026-08-13
- 路由契约：准确目标文件类型
- 来源 artifact：51 R、1 Python、3 Bash、4 Notebook
- 来源 aggregate SHA-256：`3ef2cdc9524bc3fd97ab29e4a73535f490cdb4a7a8ec7f061a5b764521e874e5`
- 来源访问：只读；顶层项目 API 与环境文件均排除
- 生物学执行：未运行；本验证只检查代码结构和证据可见性

旧 stage-first 验证由本记录取代，原文仍可从 Git 历史追溯。由于用户确认的重构建立在全语料审查上，下列 corpus holdout 是 `retrospective_same_type_regression`，不是 blind/unseen test。fresh forward tasks 才是隔离 evaluation surface。

## 当前契约

| ID | 契约 |
|---|---|
| C1 | Write the analysis, not an application around the analysis. |
| C2 | 具体代码形态只从目标文件类型和邻近同类型项目代码学习。 |
| C3 | 保留任务中真实存在的问题、试做、观察/比较、人工选择、批量扩展、证据与下一问。 |
| C4 | 只抽取稳定技术核；重复次数本身不是 helper 门槛。 |
| C5 | 观察性检查是正常分析；硬断言只保护 silent scientific corruption。 |
| C6 | part 文件、人工编辑 handoff、对象重载与有用途的昂贵 cache 是合理科研边界。 |
| C7 | 输出按用途选择，不强制 bundle；未运行代码不得声称观察结果。 |
| C8 | 修改既有代码时默认保留邻近结构并使用 minimal diff。 |

## R 回顾性回归

| 路径与 SHA-256 | 结果 | 支持契约 | mismatch class 与处理 |
|---|---|---|---|
| `02-annotation/scripts/03-HS_BM_auto_annotation-part2.R`<br>`40ab54571b0f1bf9b1f7b2111106f312d9462a4ed966eab5ceb19985f4fc8685` | Pass | C3、C5、C6、C7 | 无。part 边界与人工 annotation choice 是合理分析结构。 |
| `03-integration/scripts/03-inter-harmony.R`<br>`183f17ab9be2761136ececee8cbb768938d6bcfff6405e59e294c33cd634f863` | Pass | C1、C2、C3、C7 | 无。替代方法继续作为读取同一 baseline 的短独立脚本。 |
| `04-grn/scripts/04-hypothesis_driven_partIV.R`<br>`844046dd58566085f2db7a641f19ab108a776226bbd4897e040edebec00548e9` | Pass | C1、C3、C6、C7 | 无。科学问题与连续证据块保持可见，不需要 framework。 |
| `05-from-pathway-to-program/scripts/04-metabolisum_activity.R`<br>`d9ec7080a5651c953ea1b86f9da620e11b550e73031dea04e063ef5e5cee56e6` | Pass | C1、C5、C7 | 无。只保存 figure 的科学输出反证了 table/figure/object bundle。 |
| `06-lr-pairs/scripts/05-cellchat-stage-compare-weight.R`<br>`b0512c7394287489533d0efb7dbd9eb10ab52973a87f346f8566c57b064d85b5` | Pass | C3、C4、C7 | 无。大型平行比较块让统计量和输出保持独立可读。 |
| `07-trajectory/scripts/05-2-dynamic-genes-Ery.R`<br>`719da9b292f41c81cb4f16500f6ba39c8c5377426c1b8b5a232c9118e978f898` | Partial | C3、C4、C5 | `source_defect`：复制的 trial code 引用了只在后续 helper 内定义的变量。保留 prototype-before-batch，但要求原型自洽；真实漂移出现后抽最小技术核。 |
| `07-trajectory/scripts/07-2-dynamic-module-Mega.R`<br>`d615c6deab42e9f5f5c99535a0befd4e079a2c219742a17b76bce33b3f60a902` | Partial | C4、C6、C7 | `source_defect` + `nontransferable_artifact`：scientific cache 用途有效，但 stale field 和 machine path 不可学习，也不据此增加 cache system。 |

## Bash 回顾性回归

| 路径与 SHA-256 | 结果 | 支持契约 | mismatch class 与处理 |
|---|---|---|---|
| `01-scrna-qc/scripts/02-starsolo.sh`<br>`f329a11691a5d33b229e18923ef60f0baec3724733744e7db876106be376b033` | Partial | C1、C2、C4、C7 | `nontransferable_artifact`：直接重复 sample commands 有用；machine path、environment invocation 和 destructive temporary cleanup 排除。模板增加 quoting 与 strict mode，但没有 dispatcher。 |

## Notebook 回顾性回归

| 路径与 SHA-256 | 结果 | 支持契约 | mismatch class 与处理 |
|---|---|---|---|
| `03-integration/scripts/06-inter-scanvi.ipynb`<br>`d231fdd1d62a591f2b0f15e2bbea48d879a3d48330b62a3a5499806871d1004a` | Pass | C1、C2、C3、C7 | 无。direct model、latent representation、diagnostics 与 saving 保持同类型 cell sequence；stored outputs 不作当前证据。 |
| `03-integration/scripts/07-inter-bbknn.ipynb`<br>`75735aa7f65a564a069d4542d5800bad2e841d27ec6e454501b1681ef629b245` | Partial | C2、C3、C4 | `intentional_research_boundary` + `nontransferable_artifact`：较长一次性 plotting helper 可以位于 helper 边界；不连续 execution counts 与 stored outputs 排除。 |

## Python 证据缺口

没有独立 standalone Python corpus holdout。唯一 `.py` artifact 只为窄直接转换和真实 positional contract 提供 learning evidence，不能证明通用 Python 结构。因此 Python 必须用 fresh forward task 验证，且指南明确区分普通 script `print()` 与 Notebook display 语义。

## 共享边界结果

- exact-type routing 阻止 R sections、Python entrypoints、Bash dispatch 与 Notebook display behavior 跨类型迁移。
- runtime templates 不包含 generic argument parsing、config system、dispatcher、`run_analysis()` wrapper、completion marker 或 mandatory output bundle。
- R OUTLINE 只由明确请求 fixture 表达。
- Notebook templates 使用空 outputs 和 `null` execution counts。
- 来源缺陷与环境 artifact 被分类，而不是标准化为规则。

## Fresh forward tests

测试 prompt 只包含科研任务并调用安装中的 Skill，不泄漏预期诊断或偏好输出形态。

| 类型 | 任务 | 结果 | 观察 |
|---|---|---|---|
| R | 比较三个 PCA 维度、保存证据并延后人工选择 | Pass after corrective iteration | 较宽的初始任务先后暴露了 invented resolution/cutoffs/top-N、未授权 Wilcoxon estimand、虚假 PCA-to-marker 依赖，以及多余 algorithm/sampling settings；这些均促成规则收紧。最后的独立核心复测只读取已有 PCA，用一个直接 Elbow diagnostic 标出 15/25/35，保存证据，并以 `NA_integer_` 保留未决选择；没有额外模型、seed、sampling、CLI 或状态产物。 |
| Python | 读取固定 Parquet，按 donor/condition 汇总 score 并保存 TSV | Pass | 直接顶层 pandas 分析，显式 `print()` checkpoints，一个 required-column 硬契约，固定项目路径；无 CLI、`main()`、config、wrapper 或 completion state。 |
| Bash | 对两个已知 sample 运行 Salmon | Pass | 两个可独立修改的显式 command blocks，使用 quoting 与 strict mode；无 loop、dispatcher、config、runner 或 marker。 |
| Notebook | 比较 latent dimensions、显示诊断并延后选择 | Pass | 有效 raw Notebook JSON；sweep、可比 display、后续未决选择和 gated downstream 相邻。所有 code cells 都是 `execution_count: null` 与空 `outputs`；无 CLI、config、runner 或伪造诊断。 |

## Static minimal-diff 回归

`validation/fixtures/existing-minimal-diff.R` 保留邻近的 `## ... ====` section 与已有 `seu` 对象，只加入局部 candidate comparison 和未决决定。它通过 parse，没有归一化成 OUTLINE，也没有添加 application scaffolding。结果：Pass。
