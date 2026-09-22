# persistent-analysis-session

为探索性分析建立或复用本机常驻 R / Python 会话，大型对象只读取一次，后续脚本通过 `/run` 使用同一份内存对象。入口是 [SKILL.md](SKILL.md)，具体分析脚本保存在目标项目中。

## 运行必需依赖

- Python 路径：Python 3，基础服务仅使用标准库。按数据格式另需 `joblib`、`scanpy` 或 `anndata`、`pandas`；Parquet 还需兼容的读取引擎。pickle 对象可能依赖创建它时使用的包。
- R 路径：R / `Rscript`、`httpuv`、`jsonlite`；读取 `.qs` 另需 `qs`，读取 `.rds` 使用 R 自带函数。
- HTTP 客户端：例如 `curl` 或 Windows PowerShell 的 `Invoke-RestMethod`。只选择项目所需的一种语言后端。

## 如何使用

在支持 skill 的 Agent 中提出：

> 使用 persistent-analysis-session，为当前项目的 `data/object.rds` 建立 R 常驻会话，对象名为 `obj`。先用空会话检查接口，并记录启动和提交脚本的方法。

从本目录手动启动不加载数据的 Python 会话：

```bash
PY_SESSION_SKIP_LOAD=1 python3 scripts/python_session_server.py
```

在另一个终端运行 `curl -sS http://127.0.0.1:8787/status` 检查状态。真实数据通过 `PY_SESSION_OBJECT_PATH` / `R_SESSION_OBJECT_PATH` 配置；后续提交的脚本直接使用内存对象，不重复读取文件。

默认仅监听本机 `127.0.0.1:8787`；`/run` 会执行提交的代码。退出进程会丢失内存状态。完整示例见[源码包使用说明](../../README.md)，独立安装本目录后也可查看 [Python](references/python.md)、[R](references/r.md) 和 [Windows](references/windows.md) 参考。
