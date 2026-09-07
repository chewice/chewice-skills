---
name: baidu-netdisk-upload
description: 使用已登录的 BaiduPCS-Go 把本地目录或文件上传到百度网盘，并在上传前为每个文件的直接父目录 mkdir，避免错误码 -9「文件不存在」。用户提到「百度网盘上传」「BaiduPCS-Go upload」「代码 -9」「文件不存在」「先 mkdir 再上传」、或要把本地 data/GEO/reference 放到网盘路径时使用。不用于 GEO/ENA/SRA 下载，也不用于网盘 download。
---

# BaiduPCS-Go 上传（先建目录，避免 -9）

BaiduPCS-Go 的 `upload` **不会**自动创建缺失的目标子目录。上传前先 `list` 目标目录；目录不存在时接口返回 **代码 -9，消息「文件不存在」**，客户端把这次 list 失败当成上传失败。

`mkdir /a/b/c` **会**一次建好中间层。因此正确顺序永远是：**mkdir 文件的直接父目录 → 探针 upload → 批量 upload**。

## 何时加载

- 用户要把本地路径上传到百度网盘 / BaiduPCS-Go
- 用户报告 `-9`、`文件不存在`、`上传失败文件数`
- 用户问如何避免该错误，或要求先建目录再传

不要用本 skill 做 GEO 下载、网盘下载、或重新 `login`。登录问题先 `who` / `quota`；配置文件在 `~/.config/BaiduPCS-Go/pcs_config.json`。

## 硬约束

1. 每个待传文件的**直接父目录**必须先存在。空目录（本地有、里面没文件）可以不建。
2. 禁止先 `upload` 再补目录。禁止只建顶层就开传整棵树。
3. 出现 `-9` 时停止同一条 `upload`，补 `mkdir` 后再继续。不要把 `-9` 当成登录失效、文件损坏或需要换代理。
4. 不要为了避开 `-9` 而打包 tar/zip、扁平化或改文件名，除非用户明确要求。
5. 默认直连服务器出口。不要套用项目里的 `proxy.env`（那是 GEO/ENA 用的），除非用户指定 BaiduPCS 代理。
6. 同名文件策略用 `skip`（配置 `u_policy` / `--policy skip`）。已存在目录（错误码 **31061**）视为成功。
7. 长时间任务放 tmux，日志落到用户指定或项目 `logs/`。进程跑在服务器上，消耗的是**服务器流量**，不是操作者本机宽带。

## 固定流程

确认客户端可用后再动手：

```bash
command -v BaiduPCS-Go
BaiduPCS-Go who
BaiduPCS-Go quota
```

配置文件权限不足时，在非沙箱下执行（需要读 `~/.config/BaiduPCS-Go`）。不要打印 BDUSS / cookies。

记清两条路径：

| 变量 | 含义 | 例子 |
|---|---|---|
| `SRC` | 本地源目录 | `/home/.../project/data` |
| `REMOTE_PARENT` | 网盘父目录 | `/Bioinformatics_Data/GSE53987_GSE102556_GSE208338` |
| `REMOTE_ROOT` | 上传后的目录 | `$REMOTE_PARENT/$(basename "$SRC")` |

`BaiduPCS-Go upload "$SRC" "$REMOTE_PARENT"` 会把本地目录**名**放到父目录下，因此 mkdir 目标是 `$REMOTE_ROOT/...`，不是把文件直接摊进 `$REMOTE_PARENT`。

按顺序执行，禁止跳步：

1. `BaiduPCS-Go mkdir "$REMOTE_PARENT"`；已存在则继续。
2. `BaiduPCS-Go mkdir "$REMOTE_ROOT"`；已存在则继续。
3. 列出所有「包含文件的本地目录」，映射到 `$REMOTE_ROOT/<相对路径>`，逐个 `mkdir`。嵌套路径一次即可，不必一层层建。
4. 选一个小文件做探针：upload 到**已经 mkdir 好的叶子目录**。必须看到「上传文件成功」或「秒传成功」。
5. 探针成功后再：

```bash
BaiduPCS-Go upload --retry 5 -l 4 "$SRC" "$REMOTE_PARENT"
```

批量 mkdir + 上传可直接跑 skill 脚本（参数按任务替换）：

```bash
bash scripts/mkdir_then_upload.sh \
  --src /path/to/local/data \
  --remote-parent /Bioinformatics_Data/TargetDir \
  --log-dir /path/to/project/logs \
  --session baidu-netdisk-upload-data
```

脚本默认：先 mkdir，再探针，再 tmux 里 upload。加 `--mkdir-only` 则只建目录。

## -9 现场处理

日志出现：

```text
获取目录下的文件列表: 遇到错误, 远端服务器返回错误, 代码: -9, 消息: 文件不存在
上传失败文件数: 1
```

按下面做：

1. 从失败路径取出目标父目录。
2. `BaiduPCS-Go mkdir <该父目录>`。
3. 再 upload **那一个文件** 做探针。
4. 探针成功后，对剩余「有文件的目录」补齐 mkdir，再用 `skip` 续传整棵树。

不要提高 `-l` 来「硬闯」缺失目录；并行 upload 在目录不存在时只会批量 `-9`。

## 进度与网速

小文件（几百字节的 `.json` / `.complete`）日志里会出现 `122B/s`：这是接口往返开销，不是网卡只有这么快。数 MB 级文件常见约 2–3 MB/s。看现场：

```bash
tmux attach -t <session>
```

脱离用 `Ctrl-b` `d`。不要杀 pane。

## 不要做

- 在网页上手搓与本地完全一样的空目录树
- 未确认 `who` 就 `login`
- 把 GEO 代理写进 BaiduPCS-Go config
- 输出配置里的 BDUSS、cookies 或完整 `pcs_config.json`

详细错误码与探针反例见 [references/error-codes.md](references/error-codes.md)。
