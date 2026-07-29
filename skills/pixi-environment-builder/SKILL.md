---
name: pixi-environment-builder
description: "创建、迁移、审查或诊断 Pixi 工作区和环境，并预览或转换 pixi.toml、pixi.lock 中的 TUNA 镜像 URL。覆盖科学 Python、生物信息学、Conda 到 Pixi 迁移、Conda/PyPI 混合依赖、CUDA/PyTorch、Jupyter/VS Code 内核、镜像与网络、conda-pypi 映射和求解冲突。用户要求编写或修复 Pixi manifest、解释安装错误、复现旧环境、设计多环境工作区，或将 conda-forge/bioconda 地址切换到清华 TUNA 时使用。仅管理独立 CLI 工具时优先考虑 pixi global；只解释通用 Conda/Python 概念且不涉及 Pixi 时不使用。"
---

# Pixi 环境构建与诊断

先查明项目事实，再修改 manifest。不要把旧环境的全部传递依赖机械复制到
`pixi.toml`。

## 固定流程

1. 检查仓库中的 `pixi.toml`、`pyproject.toml`、`pixi.lock`、
   `environment.yml`、导入语句、notebook 版本输出和错误日志。
2. 确认运行平台、Python/R/CUDA 等兼容锚点、环境用途、网络限制和验收命令。
3. 为重要依赖明确唯一来源：Conda、PyPI、Git 或本地路径。
4. 先设计最小顶层依赖，再根据求解器和运行验证补充约束。
5. 使用 Pixi CLI 修改或初始化 manifest 时，优先采用当前安装版本支持的命令。
6. 创建 `pixi.toml` 时，默认添加 `[tasks.init]`，令其执行项目根目录的
   `setup-vscode.sh`，并从 `assets/setup-vscode.sh` 复制该脚本。
7. 运行锁定、安装或缓存清理前说明会发生的状态变化；用户只要求诊断时保持只读。
8. 用导入、版本、CLI、GPU 或 kernel 检查验证实际目标，而不只确认安装成功。

## 按需读取

- 设计新环境、迁移 Conda 或拆分 features/environments：读取
  [references/environment-design.md](references/environment-design.md)。
- 处理镜像、代理、PyPI index、私有源或 conda-pypi 映射：读取
  [references/network-and-sources.md](references/network-and-sources.md)。
- 处理 CUDA、PyTorch、Jupyter、VS Code 或具体报错：读取
  [references/troubleshooting.md](references/troubleshooting.md)。

只读取与当前任务相关的 reference。

## 新建工作区默认初始化

新建 `pixi.toml` 时必须包含：

```toml
[tasks.init]
cmd = "bash setup-vscode.sh"
```

同时将 [assets/setup-vscode.sh](assets/setup-vscode.sh) 复制到项目根目录。保留脚本中的
`${workspaceFolder}` 字面量，不要在复制时展开。创建后运行 `bash -n setup-vscode.sh`
并检查 manifest 中的任务；只有用户要求时才执行 `pixi run init`，因为它会覆盖
`.vscode/settings.json`。

## 只读诊断

需要收集 Pixi 版本、工作区信息、配置层级和环境列表时运行：

```bash
python3 scripts/pixi_diagnose.py --manifest-path /path/to/project
```

指定环境并输出机器可读结果：

```bash
python3 scripts/pixi_diagnose.py \
  --manifest-path /path/to/project \
  --environment gpu \
  --extended \
  --json
```

脚本不得安装包或修改 manifest。敏感配置只报告存在状态，不输出值。

## TUNA 镜像转换

用户明确要求把 `pixi.toml` 或 `pixi.lock` 中的 conda-forge、bioconda
地址转换为清华 TUNA 时，先读取
[references/network-and-sources.md](references/network-and-sources.md)，再运行：

```bash
python3 scripts/convert_pixi_mirror_to_tuna.py --dry-run \
  /path/to/pixi.toml /path/to/pixi.lock
```

确认预览结果后，去掉 `--dry-run` 执行转换。转换完成后再次运行 dry-run，
确认替换数为 0，并检查旧镜像字符串已不存在。不要自行运行 `pixi lock` 或
`pixi install`，除非用户同时要求更新锁文件或安装环境。

## 交付要求

- 说明每个主要包由哪个生态负责，以及选择原因。
- 区分网络、包不存在、版本冲突、映射失败和运行时错误。
- 报告 TUNA 转换涉及的文件、替换数量和幂等性检查结果。
- 对新增环境提供至少一个可重复的验证任务或命令。
- 不编造版本、镜像地址、私有仓库、CUDA 能力或本地路径。
- 不在未经授权时执行安装、删除环境、清缓存或注册用户级 kernel。
