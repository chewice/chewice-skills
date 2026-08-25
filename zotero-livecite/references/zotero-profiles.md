# Windows 下创建与切换隔离 Zotero Profile

在需要与日常主库隔离的 staging 时阅读。Word 引用工作流中始终只运行一个 Zotero 实例。

## 为何隔离

Word for Windows 不能在同一系统用户下指定某一个 Zotero 实例。同时运行多个 profile 时，插件可能连到错误的库。隔离 profile 还必须使用独立数据目录；新建 profile 并不自动等于库已隔离。

绝不能让两个运行中的实例共享同一个数据目录。

## 1. 打开 Profile Manager

先保存并关闭 Word，再退出 Zotero。运行：

```text
"<ZOTERO_EXECUTABLE>" -P
```

`<ZOTERO_EXECUTABLE>` 是本机 Zotero 可执行文件；`-P` 打开 Profile Manager。

## 2. 创建隔离 Profile

1. 选择 Create Profile；
2. 使用可辨识但不包含个人信息的名称，例如 `Citation-Migration`；
3. 启动后不要登录日常主库的同步账号；
4. 在 Settings → Advanced → Files and Folders 中检查 Data Directory Location；
5. 若新 profile 仍指向已有数据目录，手工选择一个独立目录；
6. 仅导入当前稿件的 cited-only 元数据。

Profile 和数据目录是两层概念。新建 profile 后仍要核对数据目录。

## 3. 在已有 Profile 之间切换

最简单的方法不是 PowerShell，而是 `Win + R`。关闭 Zotero 后，用「运行」窗口执行 `zotero.exe -P` 即可打开 Profile Manager。

### 方法 A：Win + R（推荐）

1. 保存 Word 文档并完全关闭 Word；
2. 完全退出 Zotero，确认任务栏托盘和任务管理器中没有仍在运行的 Zotero；
3. 按 **Win + R** 打开「运行」；
4. 输入（按本机实际路径替换）：

```text
"C:\Program Files\Zotero\zotero.exe" -P
```

5. 按 Enter，出现 **Zotero - Choose User Profile**；
6. 单击目标 Profile，然后点击 **Start Zotero**；
7. 若以后仍希望每次启动时手工选择 Profile，不要勾选 `Use the selected profile without asking at startup`；
8. Zotero 完全启动后，再打开 Word；
9. 在文档副本中先执行一次 Zotero `Refresh`，确认 Word 连接的是正确的库。

不要把某台机器上见过的 profile 名称写进脚本或当成默认值。名称由用户提供或当场从 Profile Manager 读取。

### 方法 B：PowerShell

路径被引号包住时需要调用运算符 `&`：

```powershell
& "C:\Program Files\Zotero\zotero.exe" -P
```

### 方法 C：CMD

```text
"C:\Program Files\Zotero\zotero.exe" -P
```

CMD 不需要 PowerShell 的 `&`。

### 如果提示找不到 Zotero

先确认默认安装路径：

```powershell
Test-Path "C:\Program Files\Zotero\zotero.exe"
```

返回 `True` 表示路径正确。若返回 `False`，在开始菜单中找到 Zotero → 右键 → **打开文件位置**，再查看快捷方式「属性」中的 **目标**，把实际 `zotero.exe` 路径替换进上述命令。

### 切换后必须核对：Profile ≠ 数据目录

启动目标 Profile 后，到 Zotero：

`Settings → Advanced → Files and Folders → Data Directory Location`

核对当前数据目录，并结合条目数量、已知题名和同步账号确认库身份。隔离迁移环境应使用独立数据目录，且不要同时打开日常主库 Profile。

## 4. 直接启动指定 Profile

如果已经确定要进入哪个 Profile，可以把 Profile 名称传给 `-P`。名称用占位，不要写死个人环境。

PowerShell：

```powershell
& "C:\Program Files\Zotero\zotero.exe" -P "<profile-name>"
```

Win + R / CMD：

```text
"C:\Program Files\Zotero\zotero.exe" -P "<profile-name>"
```

可分别建立两个 Windows 快捷方式，例如「Zotero - 日常库」和「Zotero - Citation Migration」，目标中填入对应 `-P` 参数。

进行 Word 引用工作时，不建议同时运行多个 Zotero Profile。先关闭全部 Zotero 实例，只启动目标 Profile，再打开 Word。

## 5. 多实例边界

不同 profile 和不同数据目录可以研究多实例运行；Windows/Linux 可能需要 `-no-remote`。但在 Word 引用工作流中，推荐始终只运行一个 Zotero 实例。

## 与 live 授权的关系

切换或启动 profile 本身还不是 Word COM / `ZoteroRefresh` 授权。打开 Word、运行 wrapper、调用 Refresh 仍须遵守 SKILL.md 的 live 门控和 `references/live-refresh-protocol.md`。
