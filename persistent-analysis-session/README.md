# persistent-analysis-session

让探索性 R / Python 分析复用一个常驻本机进程：大型对象只加载一次，后续分析脚本通过 HTTP 提交，在同一份内存对象上继续工作。适合反复读取 Seurat、AnnData、RDS、qs、pickle、joblib 等对象的场景。

本 skill 提供会话后端、启动方式与分析记录约定；具体分析和绘图脚本由目标项目按需求编写。生产批处理和 CI 通常继续使用独立进程。会话状态保存在进程内存中，退出或重启后需要重新加载对象。

## 运行必需依赖

只需选择 R 或 Python 其中一条路径，不必同时安装两套环境。

| 用途 | 必需依赖 |
| --- | --- |
| 使用 skill | 能加载 `SKILL.md` 并执行本地命令的 Codex / 兼容 Agent；目标项目及可读取的数据 |
| Python 后端 | Python 3；HTTP 服务及基础代码只使用标准库，无需 Flask / FastAPI |
| R 后端 | R / `Rscript`，以及 R 包 `httpuv`、`jsonlite`，即使跳过对象加载也需要这两个包 |
| Python 读取 `.pkl` / `.pickle` | 标准库 `pickle`；对象所属第三方类可能还需要其原始软件包 |
| Python 读取 `.joblib` | `joblib`，以及对象本身所需的软件包 |
| Python 读取 `.h5ad` | `scanpy` 或 `anndata`；脚本先尝试 `scanpy`，导入失败后尝试 `anndata` |
| Python 读取 `.csv` / `.parquet` | `pandas`；Parquet 还需要兼容的读取引擎 |
| R 读取 `.rds` / `.qs` | `.rds` 使用 R 自带 `readRDS()`；`.qs` 另需 `qs` |
| 提交脚本 | Linux / macOS 可用 `curl`；Windows PowerShell 可用 `Invoke-RestMethod` |

分析时用到的 Seurat、绘图包或其他领域工具属于项目依赖，按实际分析补充。`make`、`tmux`、`nohup` 是可选启动工具。本 skill 没有统一的环境锁文件，不能据此假定任意已有数据对象均可跨版本读取。

## 如何使用

实际可分发的 skill 目录是 [skills/persistent-analysis-session](skills/persistent-analysis-session/)，入口为 [SKILL.md](skills/persistent-analysis-session/SKILL.md)。让 Agent 加载该目录后，可以这样提出请求：

> 使用 persistent-analysis-session，为这个项目建立 Python 常驻会话。数据是 `data/cells.h5ad`，对象名为 `adata`；先跳过真实对象加载验证接口，再用项目环境加载数据。后续分析脚本放到 `analysis/`，记录运行方法和输出。

> 使用 persistent-analysis-session，复用已有的 R 会话；对象名是 `seu`。后续脚本直接使用它，不重复读取 RDS。

需提供语言、对象路径、对象名和项目环境。Agent 会先检查已有会话和项目约定，按需将后端模板放入项目 `tools/`，建立启动 / 提交命令，并记录在项目 `analysis/README.md` 或分析日志中。

### 手动验证 Python 接口

以下命令从本 README 所在目录运行，只启动空会话，不读取真实数据：

```bash
PY_SESSION_SKIP_LOAD=1 python3 skills/persistent-analysis-session/scripts/python_session_server.py
```

保持该终端运行，在第二个终端调用：

```bash
curl -sS http://127.0.0.1:8787/status
curl -sS --data-binary 'print("session ready")' http://127.0.0.1:8787/run
```

检查 JSON 中的 `ok` 和 `loaded`；空会话应显示 `loaded: false`。R 的对应启动命令如下，同样使用端口 `8787`，不要与 Python 示例同时占用该端口：

```bash
R_SESSION_SKIP_LOAD=1 Rscript skills/persistent-analysis-session/scripts/r_session_server.R
```

### 加载真实对象与提交分析

将所选后端复制到项目 `tools/` 后，从项目根目录启动。例如 Python：

```bash
PY_SESSION_OBJECT_PATH="data/cells.h5ad" \
PY_SESSION_OBJECT_NAME="adata" \
PY_SESSION_SKIP_LOAD=0 \
python3 tools/python_session_server.py
```

R 的对应示例：

```bash
R_SESSION_OBJECT_PATH="data/object.rds" \
R_SESSION_OBJECT_NAME="obj" \
R_SESSION_SKIP_LOAD=0 \
Rscript tools/r_session_server.R
```

在另一个终端逐段提交已经编写的项目脚本，R 时替换为对应 `.R` 文件：

```bash
curl -sS --data-binary @analysis/exploratory_step_01.py http://127.0.0.1:8787/run
```

脚本直接使用配置的对象名。返回 JSON 包含输出、消息和错误；R 还单独返回警告。服务端启动目录决定相对数据和结果路径，后续脚本应遵循项目的路径约定。

默认地址为 `127.0.0.1:8787`。`/run` 可以执行代码，应仅供本机可信请求使用。不要未经请求停止用户已有会话。Windows 使用原生 PowerShell 启动方式，不直接照搬 Bash 环境变量写法。

## 进一步说明

- [Python 加载器与环境变量](skills/persistent-analysis-session/references/python.md)
- [R 加载器与环境变量](skills/persistent-analysis-session/references/r.md)
- [Windows PowerShell 启动和请求](skills/persistent-analysis-session/references/windows.md)
- [分析记录模板](skills/persistent-analysis-session/references/analysis-record.md)
