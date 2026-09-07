# BaiduPCS-Go 上传错误码

本页只在排查失败或需要向用户解释某条日志时读取。日常上传按 `SKILL.md` 的固定流程即可。

## -9 文件不存在

| 项 | 内容 |
|---|---|
| 接口含义 | 目标路径（通常是目录）在网盘上不存在 |
| 上传时何时出现 | `upload` 先 `list` 目标目录以判断 skip/overwrite；目录没有就 -9 |
| 常见日志 | `获取文件列表错误... 代码: -9, 消息: 文件不存在` 然后 `上传失败文件数: N` |
| 不是什么 | 不是登录掉了、不是本地文件损坏、不是代理错误、不是 MD5 失败 |
| 修复 | `mkdir` 该文件的直接父目录（mkdir 可一次建 `/a/b/c`），再 upload |
| 错误做法 | 立刻重试同一条整树 `upload`；改 tar；换 proxy；`logout`/`login` |

探针反例（目录不存在 → 必现 -9）：

```bash
# 假设 /dst/_probe/a/b 还不存在
BaiduPCS-Go upload /tmp/nested.txt /dst/_probe/a/b
```

探针正例（先 mkdir）：

```bash
BaiduPCS-Go mkdir /dst/_probe/a/b
BaiduPCS-Go upload /tmp/nested.txt /dst/_probe/a/b
```

## 31061 文件已存在

对 `mkdir`：目标目录已经在。当作成功，继续下一条。不要停整批。

对 `upload`：同名策略为 `skip` 时跳过该文件。续传依赖这一点，不要改成 `overwrite`，除非用户明确要求覆盖。

## 其他不要误判成 -9 的情况

| 现象 | 更可能的原因 |
|---|---|
| `config file permission denied` | 沙箱读不了 `~/.config/BaiduPCS-Go`，改在非沙箱执行 |
| `FATAL ERROR: config file error` | 同上，或配置文件权限过严 |
| 超大单文件失败（例如 >20 GB 的 STAR `SA`） | 账号单文件大小限制，与 -9 无关；记录原文后再决定是否拆分 |
| 小文件显示 `122B/s` 或 `0B/s in 6s` | 接口与 MD5 开销；等数 MB 以上文件再看吞吐 |
| `who` 无账号 | 未登录；询问用户如何提供已有登录，不要擅自用 cookies 登录 |

## 路径映射

```text
upload /abs/path/data   /pan/Target
     → /pan/Target/data/<相对路径>

mkdir 目标 = /pan/Target/data/<含文件的相对目录>
```

不要 mkdir `/pan/Target/<相对路径>` 却 upload 到 `/pan/Target`（会少一层 `data`），也不要 mkdir `/pan/Target/data` 却把 `GEO` `reference` 再包一层 `data/data`。

若用户已经建好 `REMOTE_ROOT` 并要求把子目录放进去，改为：

```bash
BaiduPCS-Go upload "$SRC/GEO" "$SRC/reference" "$REMOTE_ROOT"
```

此时 mkdir 目标是 `$REMOTE_ROOT/GEO/...` 与 `$REMOTE_ROOT/reference/...`。

## 网络

- 默认：服务器网卡直连（例如 `bond0`），走服务器流量。
- BaiduPCS-Go config 的 `proxy` 为空表示没用代理。
- 项目 `proxy.env` / `http://10.10.10.x:7897` 默认给 GEO/ENA，不自动写进网盘客户端。
- 用户明确要求走代理时才：

```bash
BaiduPCS-Go config set -proxy http://HOST:PORT
```

改完后用小文件探针确认，不要先改代理再传 70 GB。
