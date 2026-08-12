# 冲突与不确定性

## 2026-08-13 已决定

- section syntax 由项目决定；R OUTLINE 是条件分支，不是 corpus default。
- 函数抽取没有重复次数门槛；需要稳定 batch kernel 或已经观察到的维护漂移。
- 观察性 checkpoint 是默认；assertion 只保护 silent-corruption contract。
- 大型 sample、method 和 lineage branch 可以保持独立。
- Python 与 Bash 不再被限制为 utility / runner，Notebook 是独立一等文件类型。
- table/figure/object bundle 与 operational completion summary 均不强制。
- Phase 1/Phase 2 只在用户要求迭代 Skill 时加载。

## 保留的证据边界

- standalone Python corpus 只有一个文件，因此通用 Python 分析指导必须保持 principle-based 和 project-sensitive。
- Notebook source cells 有用，但 execution order、stored output、magic 与环境清理不是可靠风格证据。
- `View()` 只适合交互式项目，不是通用要求或禁令。
- shell strict mode 是安全模板选择，不是全部历史范例的共同事实。
- working-directory anchor、output directory name 和 overwrite policy 继续由项目决定。
- 成熟项目 API 可以封装算法实现，但不因此允许隐藏周围的科学决定。

## Counterexample 边界

一个 R 文件明显是 API/CLI-like，另一个 LR 脚本具有较多函数和 fallback。它们用于识别代码何时真的成为 reusable tool，而不是默认项目分析应怎样写。package installation、绝对路径、unsafe deletion、复制后未定义变量和 stale cache field 同样被排除，而不是标准化为规则。
