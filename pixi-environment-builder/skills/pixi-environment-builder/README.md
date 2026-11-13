# pixi-environment-builder

创建、迁移或诊断 Pixi 环境，梳理 Conda / PyPI 包来源、版本冲突、GPU 与 Jupyter 配置，并按请求转换 TUNA 镜像 URL。入口为 [SKILL.md](SKILL.md)。

## 运行必需依赖

- 环境管理和诊断：`PATH` 中可用的 `pixi` CLI。
- 附带工具：Python 3，两个脚本都只使用标准库。仅做 TUNA 文本转换时不需要 Pixi 或网络。
- 按需使用 Linux VS Code R 模板：Bash，以及基础命令 `mkdir`、`cat`。
- 项目依赖按用途准备；R、CUDA、PyTorch、`ipykernel` 等不是所有使用路径的统一要求。实际安装包需要可用包源或缓存。

## 如何使用

在支持 skill 的 Agent 中提出：

> 使用 pixi-environment-builder，只读诊断当前项目的 Pixi 错误，并说明依赖来源及需要修改的配置。

从本目录运行附带工具，将示例路径替换为实际项目路径：

```bash
python3 scripts/pixi_diagnose.py --manifest-path /path/to/project --json
python3 scripts/convert_pixi_mirror_to_tuna.py --dry-run /path/to/project/pixi.toml
```

诊断不安装依赖，仅输出命令状态和元数据，不输出原始命令结果；路径和环境名仍需在分享前检查。转换预览只报告替换次数。决定修改后去掉 `--dry-run`，再次预览检查替换数为 0。新工作区的平台和名称按项目目标选择；Linux VS Code R 配置模板仅按需使用，注意保留已有配置。

完整示例见[源码包使用说明](../../README.md)。独立安装本目录后，可直接查看[环境设计](references/environment-design.md)、[网络与镜像](references/network-and-sources.md)、[故障处理](references/troubleshooting.md)。
