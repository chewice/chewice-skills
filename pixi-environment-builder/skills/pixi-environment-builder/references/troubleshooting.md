# GPU、Kernel 与故障处理

## 故障处理顺序

1. 保存完整错误及失败命令。
2. 判断是网络、包发现、映射、求解、安装还是运行时错误。
3. 找出错误中被固定的包和约束来源。
4. 每次只做一个可解释的调整。
5. 用原失败命令和目标验收命令复测。

## 包不存在

可能原因：

- 包未发布到当前 Conda channel 或 PyPI index
- Conda 名、PyPI distribution 名和 import 名不同
- 包来自 Git、本地源码或私有源
- 目标平台没有构建

检查旧环境 `*.dist-info/direct_url.json` 和项目安装说明。确认来源前不要虚构依赖。

## Conda/PyPI 版本冲突

重点阅读求解器中的 pinned、requires 和 incompatible。常用处理方式：

- 从 Conda 侧移除只作为 PyPI 框架传递依赖的包
- 将真正的 ABI 锚点改为兼容范围
- 统一 PyTorch、TensorFlow 或 JAX 包族的来源
- 删除没有结果复现依据的传递依赖固定

不要用无边界 `*` 同时声明一组互相拥有的顶层框架。

## CUDA 与 PyTorch

先收集：

```bash
nvidia-smi
pixi list -e <environment> --explicit
```

区分宿主驱动、环境 CUDA runtime、框架构建版本和实际设备能力。验证：

```bash
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO GPU')"
```

不要仅凭 `nvidia-smi` 中显示的 CUDA 上限决定环境 runtime。一个包族应使用一致的
channel/source 策略。

## OpenCV

服务器通常优先使用 PyPI `opencv-python-headless`。只有确实需要 GUI/Qt 时才选择带
GUI 的 Conda OpenCV。不要同时安装 headless 和 GUI wheel。

## Jupyter 与 VS Code

- 环境中安装 `ipykernel`。
- 为每个需要暴露的 named environment 使用不同 kernel 名。
- kernel 注册是用户级状态变化，执行前征得授权。
- 注册后可以直接在 VS Code 中选择 kernel，不要求从 `pixi run` 启动编辑器。

示意命令：

```bash
pixi run -e analysis python -m ipykernel install \
  --user --name analysis --display-name "Python (analysis)"
jupyter kernelspec list
```

删除环境不会自动删除用户级 kernelspec，需要单独检查。

## 安装成功但 import 失败

检查：

- 当前解释器是否来自目标 Pixi environment
- distribution 名与 import 名是否不同
- 动态库、CUDA 或系统依赖是否缺失
- notebook kernel 是否仍指向旧环境
- editable/path 依赖是否仍可访问

用 `pixi run -e <environment> python -c ...` 明确解释器，避免在激活状态不明的 shell
中判断。

## 警告处理

将警告分为：

- 不影响当前目标但应记录
- 即将弃用，需要后续迁移
- 会破坏复现或运行，应立即处理

不要把所有 warning 当成故障，也不要在没有依据时忽略 ABI、lock 或认证警告。
