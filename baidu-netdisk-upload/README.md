# baidu-netdisk-upload

## 用途

使用已登录的 BaiduPCS-Go 将本地文件或目录上传到百度网盘。上传前先为每个文件建立网盘父目录，再用一个小文件验证上传，最后批量传输，处理缺失目录导致的 `-9`「文件不存在」错误。

保持本地目录层级和文件名，同名文件采用 `skip` 策略。本 Skill 不负责网盘下载、GEO 数据下载或重新登录。完整流程见 [SKILL.md](SKILL.md)。

## 运行必需依赖

| 场景 | 必需条件 |
| --- | --- |
| 通过 Agent 使用 | 能读取本 Skill、运行终端命令的 Agent；本地源文件读取权限和日志目录写入权限 |
| 实际上传 | PATH 中可调用的 `BaiduPCS-Go`、已登录且可用的百度网盘账户、足够的网盘空间，以及访问百度网盘的网络 |
| 使用随附脚本 | Bash、GNU coreutils（包括 `readlink -f`、`stdbuf`）、支持 `-printf` 的 GNU find，以及 `grep`；适合 Linux/WSL 环境 |
| 默认后台上传 | `tmux`；使用 `--no-tmux` 前台上传或 `--mkdir-only` 时不需要 |

不需要 Python、R 或 Node.js。macOS 原生 `find` 和 `readlink` 的参数与脚本要求不同，不能直接假定兼容。默认使用直连；只有用户明确指定时才使用 BaiduPCS 代理，不自动继承 GEO/ENA 下载代理。

## 如何使用

让 Agent 加载本目录完整内容，并给出本地源路径、网盘父目录和日志位置。例如在对话中输入：

```text
$baidu-netdisk-upload
把 /path/to/project/data 上传到网盘 /Bioinformatics_Data/StudyA 下，
保持目录结构，同名文件跳过；先检查账户和空间，再建齐目录、探针上传。
日志保存到 /path/to/project/logs，本次后台会话名为 study-a-upload。
```

未发现 Skill 时，可指定本目录 `SKILL.md` 的实际路径请 Agent 读取。账户应事先配置好；上传前在实际执行环境检查：

```bash
command -v BaiduPCS-Go
BaiduPCS-Go who
BaiduPCS-Go quota
```

目录上传也可直接使用脚本。以下命令从本 Skill 目录执行，先替换示例路径；运行会实际创建网盘目录并上传文件：

```bash
bash scripts/mkdir_then_upload.sh \
  --src /path/to/project/data \
  --remote-parent /Bioinformatics_Data/StudyA \
  --log-dir /path/to/project/logs \
  --session study-a-upload
```

该示例的远端根目录是 `/Bioinformatics_Data/StudyA/data`：`--remote-parent` 是父目录，脚本保留源目录名 `data`。脚本只接受目录；单个文件由 Agent 按 Skill 流程先建父目录再上传。

- `--mkdir-only`：只创建网盘目录，仍会修改远端，不是预览模式。
- `--no-tmux`：在当前终端前台上传。
- `--retry N`、`--load N`：调整重试次数和同时上传文件数，默认分别为 `5`、`4`。

日志目录包含 `baidupcs_mkdir.log`、`baidupcs_upload.log` 和 `baidupcs_dirlist.txt`。不同任务使用独立日志目录和会话名；脚本可能覆盖同名日志。后台会话可用 `tmux attach -t study-a-upload` 查看，用 `Ctrl-b` 后按 `d` 脱离。启动后台会话不代表上传完成，需检查上传结果和失败文件记录。

遇到 `-9` 时先补建失败文件的直接父目录，再验证该文件；详细说明见 [错误码与处理](references/error-codes.md)。
