# pixi-environment-builder

用于创建、迁移、审查和诊断 Pixi 项目环境，处理 Conda / PyPI 依赖来源、求解冲突、CUDA / PyTorch、Jupyter 内核与镜像问题。附带只读诊断脚本，以及将指定 Conda 镜像 URL 转换为清华 TUNA 的工具。

该 skill 根据项目代码、已有 manifest、锁文件和错误信息设计最小直接依赖；单独管理一个 CLI 工具时优先考虑 `pixi global`。

## 运行必需依赖

| 使用路径 | 必需依赖 |
| --- | --- |
| 使用 skill | 能加载 `SKILL.md` 并执行本地命令的 Codex / 兼容 Agent；可访问目标项目及其环境需求 |
| 创建、安装或诊断 Pixi 环境 | `pixi` CLI，可从 `PATH` 调用；应使用本机版本实际支持的参数 |
| 运行附带 Python 工具 | Python 3；两个脚本均只使用标准库，无第三方 Python 包依赖 |
| 运行 `pixi_diagnose.py` | Python 3 和 `pixi`；目标项目的 `pixi.toml` / `pyproject.toml` 或工作区目录 |
| 运行 TUNA 转换工具 | Python 3 和目标文件；只做本地文本转换，无需安装 Pixi，也无需联网 |
| 按需使用 Linux VS Code R 模板 | Bash；模板通过 `mkdir`、`cat` 写入 `.vscode/settings.json` |

Conda CLI 只在需要从旧 Conda 环境导出信息时使用。Python/R 包、`ipykernel`、CUDA 驱动、PyTorch、Jupyter 和 VS Code 按目标项目的实际功能准备，不是运行本 skill 所有路径的统一前置依赖。安装或求解新依赖时，需要可用的包源与网络，或相应本地缓存。

## 如何使用

实际可分发目录为 [skills/pixi-environment-builder](skills/pixi-environment-builder/)，入口为 [SKILL.md](skills/pixi-environment-builder/SKILL.md)。让 Agent 加载该目录后，可以这样提出请求：

> 使用 pixi-environment-builder，根据当前项目的 Python 和 R 脚本设计一个 Linux Pixi 环境。先列出直接依赖、包来源和会修改的文件，再按确认范围创建环境。

> 使用 pixi-environment-builder，只读诊断这个项目的 Pixi 求解错误，区分网络问题、Conda/PyPI 名称映射和版本冲突。

> 使用 pixi-environment-builder，预览将项目 `pixi.toml` 与 `pixi.lock` 中支持的 conda-forge / bioconda URL 改为清华 TUNA；先不要写入文件。

提供项目路径、运行平台、已有环境文件、必要的 Python/R/CUDA 版本约束、失败命令与完整错误，以及希望验证的功能。Skill 会按需读取环境设计、网络或故障诊断参考。

### 只读诊断

下面的命令从本 README 所在目录执行。将 `/path/to/project` 替换为实际项目目录，也可以直接指定 manifest 文件：

```bash
python3 skills/pixi-environment-builder/scripts/pixi_diagnose.py \
  --manifest-path /path/to/project
```

需要查看指定环境并保留结构化结果时：

```bash
python3 skills/pixi-environment-builder/scripts/pixi_diagnose.py \
  --manifest-path /path/to/project \
  --environment gpu \
  --extended \
  --json
```

`gpu` 必须替换为项目已有的环境名。脚本检查 Pixi 版本、工作区、配置层级和环境列表；指定环境时使用 `--frozen --no-install` 查询包。它不安装依赖，也不修改 manifest。为避免泄露凭据，命令的原始输出不包含在结果中；JSON 保留返回码、输出存在状态及 JSON 有效性，所有检查均计入总状态。路径及环境名仍会显示，分享前应检查。需要详细错误时在本机单独运行相应命令并手动脱敏。

### TUNA URL 转换

先预览，目标文件不存在时不要把它列入命令：

```bash
python3 skills/pixi-environment-builder/scripts/convert_pixi_mirror_to_tuna.py \
  --dry-run /path/to/project/pixi.toml /path/to/project/pixi.lock
```

工具识别官方 `conda.anaconda.org`、Westlake 和 SJTU 三类来源中的 conda-forge / bioconda URL，报告逐文件及总替换次数。它不把所有任意镜像自动转换，也不改写裸 channel 名。

确认预览并决定执行后，去掉 `--dry-run` 即可原地修改文件。随后再运行同一条预览命令，预期替换数为 0。转换不会自动运行 `pixi lock` 或 `pixi install`，也不证明远端镜像当前可用。

### 新工作区行为

根据项目和运行目标选择平台及工作区名称；未指定平台时以当前运行平台为起点。`dinghowl_zhou` 是特定个人工作流的可选名称，不用于无关项目。

[setup-vscode.sh](skills/pixi-environment-builder/assets/setup-vscode.sh) 是按需使用的 Linux VS Code R 模板，会写入 `.vscode/settings.json`；使用前确认平台、环境名和已有配置，保留并合并用户设置。只要求诊断时保持只读，锁定、安装、清缓存和用户级内核注册按实际授权范围执行。

## 进一步说明

- [环境设计、迁移和多环境](skills/pixi-environment-builder/references/environment-design.md)
- [网络、包来源与镜像转换](skills/pixi-environment-builder/references/network-and-sources.md)
- [GPU、Jupyter 与故障处理](skills/pixi-environment-builder/references/troubleshooting.md)
