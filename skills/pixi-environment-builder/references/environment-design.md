# 环境设计与迁移

## 设计原则

- 项目工作流使用仓库级 Pixi workspace；独立 CLI 工具才使用 `pixi global`。
- 只声明用户直接依赖、运行时锚点和硬件约束。
- 为同一个包族指定一个主要来源，避免 Conda 和 PyPI 同时无约束声明。
- 把结果复现所需的版本与旧环境偶然存在的传递依赖分开。
- 先使用宽但有意义的兼容范围；只有证据要求时才固定补丁版本。

## 新工作区

优先通过 CLI 初始化，避免手写当前版本不支持的字段：

```bash
pixi init --format pixi --channel conda-forge .
pixi add python
```

最小 manifest 通常包含 workspace 名称、channels、platforms 和顶层依赖。需要支持多个
操作系统时，先确认包在所有目标平台均可用；平台专用依赖应放入 target 或 feature，
不要让一个平台的 CUDA 包破坏其他平台求解。

## 包来源

通常优先使用 Conda：

- Python/R 运行时和原生 ABI 依赖
- 生物信息学 CLI、系统库和难以本地编译的科学包
- 希望由 Conda 二进制统一管理的 CUDA/PyTorch 栈

通常优先使用 PyPI：

- 官方主要发布渠道是 PyPI 的 Python 包
- Conda 缺失或明显滞后的纯 Python 包
- Git、editable 或本地源码包

不要同时这样声明同一依赖图：

```toml
[dependencies]
scanpy = "*"
anndata = "*"

[pypi-dependencies]
framework-that-depends-on-scanpy = "*"
```

先让顶层框架拥有其 Python 依赖；只有 ABI 或已验证兼容要求存在时，才把子依赖固定在
Conda 侧。

## 从 Conda 迁移

1. 按路径导出，避免同名环境：

   ```bash
   conda env export -p /path/to/env --no-builds
   conda list -p /path/to/env
   ```

2. 搜索代码和 notebook 的直接依赖及版本证据：

   ```bash
   rg -n "^(import|from) " scripts src tests --glob '*.py'
   rg -n "__version__|sessionInfo|packageVersion" . --glob '*.ipynb' --glob '*.R'
   ```

3. 分类为直接依赖、运行时依赖、传递依赖、Git/本地包和历史遗留包。
4. 保留论文流程、已发布结果、模型权重或 CUDA 栈要求的兼容锚点。
5. 先生成最小 manifest，再通过锁定和验收补齐。

## Features 与 Environments

- 包集合不同但共享 workspace 时使用 features。
- 需要不同组合时使用 named environments。
- 环境必须共享相同版本时使用 solve group；确需独立求解时才分开。

示意：

```toml
[feature.gpu.dependencies]
pytorch = "*"

[feature.r.dependencies]
r-base = "*"

[environments]
default = []
gpu = ["gpu"]
r-analysis = ["r"]
```

通过当前 Pixi CLI 的 `pixi workspace feature` 和
`pixi workspace environment` 命令确认或修改结构。

## 验收

为关键目标添加任务，例如：

```toml
[tasks]
check = "python -c \"import sys; print(sys.version)\""
```

验收至少覆盖：

- 关键 import 和版本
- 需要的 CLI 是否可执行
- GPU 可用性和设备名（如果是 GPU 项目）
- Jupyter kernel 是否注册（如果用户要求）
- 项目最小 smoke test
