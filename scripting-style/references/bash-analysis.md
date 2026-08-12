# Bash 分析脚本

只在目标文件为 `.sh` 时读取本指南。Bash 分析脚本应直接展示外部工具命令及其处理的项目输入。

## 直接写命令顺序

一种有用形态是：

```text
shebang 与风险相称的 shell safety
-> 项目和工具变量
-> 一个显式 sample 或 stage 块
-> 检查或记录相关输出
-> 下一个显式 sample 或 stage 块
```

会影响科学或计算含义的 tool options 放在对应命令旁边。只有能提高真实命令可读性时，才使用 array 或 line continuation。

不要仅因某个 flag 常见于来源范例或教程就添加它。若省略该 flag 会让请求产生科学歧义，应把选择明确留作待定，或询问缺失信息；不得把决定藏进工具 default。

同样不要为“完整”而显式展开工具的全部 defaults、额外 resource flags、log settings 或未经请求的 post-processing。只保留当前命令成立且可审查所需的 options。

`set -euo pipefail`、quoting 和 `mkdir -p` 是新 Bash 脚本合理的安全增强，但不能因此建立通用执行层，也不能宣称所有来源范例都有这些习惯。

## 保留显式 sample 块

两个或少数已知样本存在有意义差异时，可以保留完整重复块：

```bash
sample_id="sample_a"
input_dir="inputs/sample_a"
output_dir="derived/sample_a"
mkdir -p "$output_dir"

analysis_tool \
  --input "$input_dir" \
  --output "$output_dir"

sample_id="sample_b"
input_dir="inputs/sample_b"
output_dir="derived/sample_b"
mkdir -p "$output_dir"

analysis_tool \
  --input "$input_dir" \
  --output "$output_dir"
```

这种重复让每个样本的路径和 options 可独立阅读。只有同一命令确实适用于显式样本列表，且差异仍然清楚时，loop 才更合适。不要仅为少写几行创建 `case` dispatcher、generic stage runner、config parser、task registry 或 completion discovery。

重复块真的开始意外漂移时，只抽取共同 command invocation，或使用小型显式 loop。不要把 sample-specific 科学设置藏进通用函数。

## 让探索和人工控制保持可见

参数比较期间，可以保留替代候选命令或昂贵可选 stage，并用注释说明原因。对一次项目分析，清楚标记的人工块优于新造 execution mode。

区分科研交接与运维状态。下一科学步骤使用的输出是合理产物；`.done`、pass table、run registry、自动发现完成目录、retry 和 dashboard 不是默认输出。

## 克制硬检查

引用路径，并只验证缺失或错配会造成误导运行的输入。不要为假想环境写很长的 `if` 链。不得从来源范例加入 destructive cleanup、机器路径、package installation、credential handling 或 environment activation。

## 保存外部工具的真实产物

清楚命名输入和输出目录，让工具实际产物成为输出。只有末尾摘要能表达科学结果或用户明确要求时才添加；不要默认打印通用完成状态。
