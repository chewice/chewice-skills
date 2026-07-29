# scripting-style

`scripting-style` 是面向生物信息学分析脚本的 Codex Skill。它帮助 Codex 编写
顺序可读、科学决策可见、少封装且不过度工程化的 R、Python 和 Bash 脚本。

## 适用任务

- scRNA-seq / snRNA-seq QC
- 细胞聚类与注释
- 数据整合与批次效应诊断
- GRN 与 regulon 分析
- program、pathway 和 metabolism activity
- ligand–receptor / CellChat 分析
- trajectory、lineage、dynamic genes 和 modules

它不提供固定分析方法、历史参数、环境配置或公共函数库。

## 使用

将本目录复制或链接到 Codex Skill 目录，并以 `$scripting-style` 调用。例如：

```text
使用 $scripting-style，根据当前对象和项目 API 编写一个轨迹分析 R 脚本。
```

Skill 会先给出简短工作提要，再生成线性脚本。提要只存在于对话中，不创建 spec 或
plan 文件。

## 迭代接口

需要用新的脚本范例改善 Skill 时，可直接调用：

```text
使用 $scripting-style 的迭代接口执行 Phase 1。
目标 Skill：<SKILL_ROOT>
新范例：
- /absolute/path/to/example.R
- /absolute/path/to/example.sh
```

也可以填写 [迭代请求模板](templates/iteration-request.json)，再运行：

```bash
python3 scripts/validate-iteration-request.py /path/to/iteration-request.json
```

Phase 1 只读分析新证据并等待确认；Phase 2 才更新 Skill，并对新旧 holdout 同时验证。
完整契约见 [Skill 迭代接口](references/iteration-interface.md)。

## 内容

- `SKILL.md`：核心工作流与边界。
- `references/`：全局及 01–07 阶段指南。
- `examples/`：只引用来源脚本路径的范例索引。
- `templates/`：轻量 R、Python、Bash 结构模板。
- `scripts/validate-iteration-request.py`：迭代请求的只读确定性预检。
- `validation/`：隔离 holdout 的轻量验证记录。
- `review/`：Phase 1 语料审查与候选确认记录。

`PROMPT.md` 与 `review/` 属于开发证据；运行 Skill 时按 `SKILL.md` 的渐进披露指引
读取所需文件即可。
