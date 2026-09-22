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
| 执行默认 VS Code 初始化任务 | Bash；模板通过 `mkdir`、`cat` 写入 `.vscode/settings.json` |

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

`gpu` 必须替换为项目已有的环境名。脚本收集 Pixi 版本、工作区信息、配置层级和环境列表；指定环境时使用 `--frozen --no-install` 查询包。它不安装依赖，也不修改 manifest。JSON 中保留各项命令的返回码，应检查失败项，不能仅凭总状态判断所有配置查询都成功。

### TUNA URL 转换

先预览，目标文件不存在时不要把它列入命令：

```bash
python3 skills/pixi-environment-builder/scripts/convert_pixi_mirror_to_tuna.py \
  --dry-run /path/to/project/pixi.toml /path/to/project/pixi.lock
```

工具识别官方 `conda.anaconda.org`、Westlake 和 SJTU 三类来源中的 conda-forge / bioconda URL，报告逐文件及总替换次数。它不把所有任意镜像自动转换，也不改写裸 channel 名。

确认预览并决定执行后，去掉 `--dry-run` 即可原地修改文件。随后再运行同一条预览命令，预期替换数为 0。转换不会自动运行 `pixi lock` 或 `pixi install`，也不证明远端镜像当前可用。

### 新工作区默认行为

默认平台为 `linux-64`，其他平台需要明确指定。工作区名称先校验，默认采用合法的小写名称 `dinghowl_zhou`。新建 manifest 时添加 `init` 任务，并提供 [setup-vscode.sh](skills/pixi-environment-builder/assets/setup-vscode.sh) 模板，将 VS Code 的 Linux R 路径指向项目 `.pixi/envs/default/bin/R`。

执行 `pixi run init` 会写入 `.vscode/settings.json`，因此需明确要求执行；已有配置应先检查并合并。只要求诊断时保持只读，锁定、安装、清缓存和用户级内核注册按实际授权范围执行。

## 进一步说明

- [环境设计、迁移和多环境](skills/pixi-environment-builder/references/environment-design.md)
- [网络、包来源与镜像转换](skills/pixi-environment-builder/references/network-and-sources.md)
- [GPU、Jupyter 与故障处理](skills/pixi-environment-builder/references/troubleshooting.md)
