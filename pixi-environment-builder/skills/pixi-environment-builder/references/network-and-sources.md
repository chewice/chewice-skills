# 网络、镜像与包来源

## 先诊断层级

按顺序检查：

```bash
pixi config list --json
pixi config list --local --json
pixi config list --global --json
env | rg '^(PIXI|RATTLER|PIP|UV|HTTP_PROXY|HTTPS_PROXY|NO_PROXY)='
```

展示结果时隐藏 token、密码、认证 URL 和代理值。

需要快速收集信息时使用 `scripts/pixi_diagnose.py`。不要把用户级配置复制进仓库，
除非它是团队明确要求的项目配置。

## Conda 与 PyPI 分开处理

- Conda channel、repodata 和包下载属于 Conda 路径。
- PyPI simple index、wheel 元数据和文件下载属于 PyPI 路径。
- 一个镜像能够返回 simple index，不代表它能够返回所有 wheel 或 metadata。
- 一次只改变一个网络层，记录失败 URL 和 HTTP/解析错误。

PyPI 项目配置示意：

```toml
[pypi-options]
index-url = "https://mirror.example/simple"
```

只有用户或仓库已经给出可用镜像时才填写真实地址。不要猜测内部域名。

Conda 镜像通常放在项目 `.pixi/config.toml` 或用户配置中。修改前先确认作用域，
不要把个人镜像无条件写入共享项目。

## 清华 TUNA URL 转换

仅在用户明确要求切换到清华 TUNA 时，使用
`scripts/convert_pixi_mirror_to_tuna.py` 修改现有 `pixi.toml` 或
`pixi.lock`。脚本支持先预览：

```bash
python3 scripts/convert_pixi_mirror_to_tuna.py --dry-run \
  /path/to/pixi.toml /path/to/pixi.lock
```

目标 URL：

```text
https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda
```

脚本识别并替换下列旧来源中的 conda-forge 和 bioconda URL：

- `mirrors.westlake.edu.cn/ANACONDA/cloud`
- `mirror.sjtu.edu.cn/anaconda/cloud`
- `conda.anaconda.org`

执行修改后：

1. 再运行一次 `--dry-run`，确认替换数为 0。
2. 搜索上述旧来源，确认目标文件中不再残留。
3. 报告每个文件和总替换数量。
4. 不自动运行 `pixi lock` 或 `pixi install`。

## Conda/PyPI 名称映射

混合依赖可能需要将 Conda 包映射到 PyPI distribution。远程映射不可达或需要离线运行时，先查阅当前 Pixi 版本的官方文档，确认自定义映射的 manifest 字段、文件结构、覆盖语义和位置；不要假设普通 JSON 字符串字典一定是受支持的格式。

只加入有依据的映射；JSON 语法检查只是第一步。经授权后，使用当前版本的 Pixi 对包含目标混合依赖的最小工作区实际求解，并检查是否采用了预期映射；记录版本、命令和结果。求解可能更新 lockfile 或访问网络，应事先说明状态变化。映射不是版本兼容性保证；映射获取失败与依赖求解失败要分开报告。

## Git、本地与私有包

包不存在于 registry 时，先检查旧环境的 `direct_url.json`、项目安装文档和 Git
配置，不要反复尝试不同拼写。

本地依赖：

```toml
[pypi-dependencies]
my-package = { path = "/path/to/source" }
```

Git 依赖：

```toml
[pypi-dependencies]
my-package = { git = "ssh://git@example/org/repo.git", rev = "commit-sha" }
```

共享项目优先固定 tag 或 commit。不要提交嵌入凭据的 URL。

## 网络故障分类

- DNS、TLS、timeout：网络或代理问题。
- 401/403：认证或授权问题。
- 404 package：名称、源或发布状态问题。
- metadata 404：镜像文件/元数据覆盖不完整。
- solver conflict：依赖约束问题，不应通过换镜像掩盖。

只有确认缓存损坏且用户授权时才运行清理命令。缓存清理不是常规第一步。
