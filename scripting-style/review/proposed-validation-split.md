# Type-first 验证拆分

holdout 按文件类型分组，并从 canonical learning examples 中排除。它们验证最高原则能否跨任务成立，同时不把 held-out method 或 syntax 升级成规则。本次原则优先重构发生在用户确认的全语料审查之后，所以 corpus holdout 是 retrospective regression，不是 pristine blind test；fresh forward tasks 才是隔离 evaluation surface。

| 类型 | Learning 重点 | Holdout 重点 |
|---|---|---|
| R | observation and choice、parallel methods、prototype-to-batch、purposeful cache | part continuation、alternative integration、single-output analysis、large repeated branch、copied-branch drift |
| Python | 带真实 positional contract 的直接项目转换 | 没有独立 corpus holdout；使用 fresh forward task，不超出当前证据作结论 |
| Bash | 显式已知样本与可见多阶段命令 | 不同 quantification tool、重复 sample block，以及不得泛化的 unsafe environment details |
| Notebook | candidate sweep 与完整 model-analysis cells | 带 stored-state noise 的 semi-supervised 和 alternative integration notebooks |

验证顺序：

1. 从确认的 learning evidence 写 initial change；
2. 检查同类型 regression set，记录 pass、partial 或 fail；
3. 只有真实 generalization failure 才做最小修订；
4. 重跑跨任务 regression 与结构检查；
5. 为 R、Python、Bash、Notebook 和既有脚本 minimal diff 运行 independent forward tasks。

holdout review 检查分析是否可见、决定是否诚实、抽象是否相称、API 是否保持不透明、输出是否有用途。它不验证生物学正确性，也不认可来源参数。
