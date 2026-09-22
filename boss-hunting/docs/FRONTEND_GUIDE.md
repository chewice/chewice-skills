# Boss Hunting / Advisor Atlas 前端使用与维护指引

这份文档同时面向 Web 用户和后续维护前端的人。每次调整前端阶段、按钮、输出文件或 Skill 契约时，都必须同步更新本页。

## 用户看到的完整流程

### Phase 1：发现与客观筛选

1. 新建申请项目。
2. 选择通用导师匹配或 Boss Hunting 医学/生物医学配置。
3. 医学配置按下表完成对应输入；通用配置仍需要目标范围及一份可读取的真实 CV，研究兴趣作为补充。
4. 申请者真实姓名是后续 RP 与套磁信的生成门槛；医学方向探索不因此被阻止。
5. 选择希望保留的 shortlist 数量。
6. 保存资料后启动导师搜索；只补问当前模式缺失的信息。

医学四步为 **领域 → 疾病/机制、研究方式与训练目标 → 地区及申请入口 → 发现、筛选与比较**。允许泛癌、机制优先、跨领域、明确未定/不限；已有能力与未来训练愿望分开保存。`target` 是地区/院校范围的权威字段，不能与画像中的派生地区发生冲突。

| 医学模式 | 前提与结果 |
| --- | --- |
| `discovery` 方向探索 | 已确认医学领域、疾病/机制、研究方式及地区，允许明确未定/不限；无需 CV、学位或批次。输出真实导师探索视图与证据，不判断个人资格已通过 |
| `application` 申请筛选 | 复用画像，补目标学位、批次、硬约束及相关真实背景。可读 CV 或足够的结构化学历/经历/资格均可；背景来源标 `self_reported` 或 `documented`，缺失资格保持 `needs_confirmation` |

Phase 1 后，通用/已映射项目的候选可选择精确导师—项目组合进入 Phase 2。医学探索可以只在 `advisor_records.json` 中保存导师，并展示派生的“导师探索视图”；此时 `candidates.json` 可以为空，不得为了进入背调或材料模块伪造项目、批次或 `advisorProgramId`。转申请时复用科研记录，仅补缺失的入口与条件。Phase 1 不自动调查所有导师的社区风评。

### Phase 2：按需背调

1. 选择要调查的导师。
2. 勾选调查维度。
3. 核对来源范围和最终摘要，再明确确认。
4. 按确认版本启动背调。

通用模式默认前三个维度；医学默认七项：基础身份、近期研究、当前项目与招生、研究轨迹、博士培养样本、资源与资助、合作网络。菜单统一由共享契约生成。医学 `sourcePolicy: public_only` 下，勾选资源维度不会自动询问或下载匿名社区资料；只有用户显式扩展为 `community_allowed` 后，才执行原独立社区授权门。

页面出现绿色的“P2 已完成”状态和“这轮背调已经完成”提示后，下面展示的是已完成结果，不需要再次点击背调。只有希望增加导师、增加维度或更新旧证据时，才使用“补充或重新背调”。

### 直接调用 Skills 时的同等流程

Codex CLI、Codex Desktop 或 Claude Code 直接调用 `$boss-hunting`（兼容入口 `advisor-pipeline`）时，
必须执行与上述页面相同的选择门，只是将复选框转换为编号菜单：

1. 展示已经映射真实项目的 shortlist；尚无项目的医学探索导师保留在探索视图。
2. 用户选择精确组合，不能由 Agent 自动取 Top N。
3. 展示与前端相同顺序的 11 个调查维度，按通用三项或医学七项预设选择。
4. 按导师数 × 维度数显示较低、中等或较高的预计消耗。
5. 来源范围允许社区资料且选择了相关维度时，单独询问本地下载授权，默认不允许；医学公开调查不触发无关授权。
6. 显示最终摘要并得到明确确认后，才保存配置并开始 Phase 2。

Web 复选框和 CLI 菜单在确认前都只是 `investigation.draft`。最终确认会
生成带 revision 和 fingerprint 的 `investigation.confirmed` 快照；Phase 2
和社区资料刷新只能使用仍与当前草稿一致的确认快照。修改任一导师、项目、
维度、社区资料或研究范围/模式后，相关确认失效，必须重新确认。医学范围指纹同时约束后续比较与申请材料，不能靠复用旧结果恢复权限。

直接调用 `advisor-detective` 时，如果项目尚未保存精确选择，也必须先
补做这套菜单，不得只要求用户填写内部 ID，也不得静默按排名开始。

正式运行会自动在当前项目的 `outputs/` 文件夹生成：

- `detective-results.json`：前端读取的结构化结果
- `advisor_detective_YYYYMMDD.xlsx`：完整背调工作簿

Skill 同时从共享记录更新按领域命名的 HTML 主报告。P2 产物校验仍以本次确认匹配的调查结果和工作簿为依据；最终 HTML 主报告在 Finder/比较阶段独立检查。

### Phase 3：证据比较或通用排名

Phase 3 复用 Phase 1 和 Phase 2 信息，不重新发现全部导师。前端摘要展示前三条及重要待确认项；医学序号是展示顺序，不是导师质量排名。

医学默认 `evaluationMode: evidence_profile`：分列科学问题与训练匹配、资格、招生机会、资源、研究经费、博士资助、培养样本、未知与下一步；`fit`、`profileMatch`、`overallMatch` 为 `null`，`competitiveness` 为 `unknown`。不使用旧 0.6/0.4 综合分、竞争配额或网页数量暗中排序。通用模式保留原数值匹配与排名。

正式运行会自动在当前项目的 `outputs/` 文件夹生成：

- `<学科领域或方向>-导师调研.html`：主要结果，简洁呈现候选比较、来源、缺口与下一步
- `ranking.json`：当前比较或通用排名；医学使用带确认版本和指纹的对象封装
- `advisor_application_ready_YYYYMMDD.xlsx`：申请阶段补充工作簿；医学探索使用 `advisor_research_discovery_YYYYMMDD.xlsx`

页面顶部“查看已保存 HTML 报告”通过 `GET /api/projects/:id/report` 打开当前项目、当前主题对应的本地报告。报告页顶部显示文件保存时间，并提示配置或证据可能已更新。打开报告不会重新调研，能打开旧快照也不代表本轮任务完成。不存在时返回明确的尚未生成提示；项目范围外路径不会被读取。Excel 可从项目 `outputs/` 本地打开。

HTML 由现有共享 JSON 生成，文件名从医学领域/机制/问题或通用研究兴趣派生，并清理不安全字符；没有主题时回退项目名。它不维护另一份事实源，也不在生成时联网。

### 排名后的申请材料（独立确认）

当前比较/排名完成后，页面提供可选的 RP / 陶瓷信区。用户必须从完整结果中选择一个精确
`advisorProgramId`，勾选材料并确定顺序，再检查最终摘要并确认。草稿变化会立即
使旧确认失效；系统不会自动使用排名第一，也不会批量生成。医学探索无 CV 的许可不延伸到申请材料：仍要求可读真实 CV、申请者身份、真实项目和当前比较。失效的医学调查或比较不能解锁材料。

每个材料运行必须同时核验 `advisor_work` 与 `field_work`。实际引用文献从合法公开
来源下载到目标目录，manifest 记录 URL、公开获取依据、读取层级、本地路径、用途、
SHA-256 和文件大小。第二个材料只有在已确认顺序中的前一个材料通过产物校验后才解锁。
页面不会发送邮件或提交 RP。

## 如何判断一个阶段是否真的完成

前端不能只根据 `status.json` 中的阶段名称判断完成，因为中断的 Agent 可能已经提前更新状态。

- 通用 Phase 1 完成：`outputs/candidates.json` 为非空合法数组，候选具有稳定的 `advisorProgramId`、完整匹配字段和确定性审计；本次产生完整 shortlist 工作簿及主题 HTML。
- 医学 `discovery` 完成：真实 `advisor_records.json` 能派生导师视图，共享证据和匹配审计合法；允许没有项目候选，不伪造 ID。完成范围为 `research_discovery`，并有本轮探索工作簿与主题 HTML；未做的资格筛选不能标完成。
- 医学 `application` Finder 完成：真实导师—项目—学位—批次映射有效，匹配契约 v3 审计对应候选数量，证据画像及资格/机会状态有适用证据；本次产生 shortlist 工作簿和主题 HTML。未知资格仍可明确待确认。
- Phase 2 完成：`outputs/detective-results.json` 非空，`confirmedRevision` / `confirmedFingerprint` 与本次确认一致，每个已选维度都有结论或显式的 `not_completed` 标记；本次运行还生成了完整的 `advisor_detective_YYYYMMDD.xlsx`。
- 通用 Phase 3 完成：保留原排名数组及 `{rankings: [...]}` / `{ranking: [...]}` 兼容形式，结果有唯一真实 ID、必要匹配字段以及展示顺序或可比较分数；本次产生完整申请工作簿和主题 HTML。
- 医学 Phase 3 完成：当前调查结果已就绪，`ranking.json` 使用下述确认封装，且每个结果引用既有真实候选 ID、含证据画像、没有旧分数/竞争分组；本次产生相应工作簿和主题 HTML。不以“至少一个分数”作为医学完成条件。
- RP 完成：当前真实 CV 可读取且申请者姓名已确认；先记录目标项目官方文档类型、模板和篇幅；`research-proposal.tex`、`references.bib`、编译后的 `research-proposal.pdf`、`proposal-build.json` 和两个审计文件均存在，源码/PDF 哈希与确认版本一致。manifest 同时包含导师/团队与领域文献；导师文献必须记录可核验的本人署名或团队作者关系，领域文献不得把导师署名论文伪装成独立证据；BibTeX key 使用 literatureId，所有实际引用均有合法公开本地 PDF 并在 `proposal-evidence.md` 记录。若官方要求匿名 RP，姓名可不印在 PDF 上，但前置身份核验不能跳过。
- 陶瓷信完成：当前真实 CV 可读取、申请者姓名已确认且最终签名使用该姓名；干净可复制的 `outreach-email.txt` 与 `outreach-audit.md` 存在，并通过同样的文献包与关系证据校验；所有论文驱动的个性化在审计中记录 literatureId。Web 会直接列出 ID、分类、题名、作者、canonical URL 和本地路径。对外正文不得出现内部 TEST/DRAFT/DO NOT SEND/SUBMIT 标记。

医学比较的确认封装如下；版本与指纹须来自当前明确确认的调查，不能手造或沿用旧确认：

```json
{
  "rankingMode": "evidence_profile",
  "confirmedRevision": 1,
  "confirmedFingerprint": "当前调查确认指纹",
  "rankings": []
}
```

上例仅示意容器，并非可提交的完成结果。裸数组、未绑定或过期的医学比较不能当作当前评价/材料目标；历史结果可保留作追溯。只重做调查不会让旧比较自动变新，须按新证据重新评价。报告能打开与产物校验通过是不同状态：校验还检查本次运行后写入、完整 HTML/XLSX 等条件，不以旧文件存在代替本轮成果。

这套校验由后端在任务结束时执行（`web/local-runtime/run-artifacts.mjs`），前端不再自行判断。运行状态因此有六种：

| 状态 | 含义 |
| --- | --- |
| `completed` | 模型正常结束，且产物通过校验 |
| `partial` | 模型正常结束，但产物缺失、非法或属于旧确认版本；界面会列出缺了什么 |
| `needs_input` | Agent 通过 `input.requested` 事件请求补充资料；原进程和 thread 保持存活，提交表单后由 `/continue` 在同一会话续跑 |
| `failed` | 模型或进程异常结束 |
| `cancelled` | 用户明确点了“取消任务” |
| `interrupted` | 本地运行服务在任务结束前重启，重启时自动改写 |

## 运行的并发与恢复

- 同一个项目同时只允许一个任务。重复 `POST /api/runs` 返回 409，并在 `activeRun` 中带上现有的 runId、mode、状态和开始时间。
- `GET /api/runs?projectId=` 返回 `{active, recent}`；`active` 里包含还没处理完的授权或资料请求。前端在加载和切换项目时调用它；若最近任务因服务重启成为 `interrupted`，顶栏会明确提示。
- `GET /api/runs/:runId/stream` 重新接入正在运行的任务：先回放事件缓冲，再推送 `run.attached`（含待处理授权），随后是实时事件。
- 关闭运行面板只隐藏面板，不会停止任务；顶栏保留“任务运行中”标志。停止是独立的 `POST /api/runs/:runId/stop`。
- `project.json` 的写入先经过进程内队列，再使用项目目录中的共享文件锁；Web 与独立 CLI 脚本也会互斥。文件本身通过临时文件 + rename 原子替换。

## 事件分级

运行事件带 `level` 字段：`progress` / `warning` / `action_required` / `error` / `diagnostic`。主日志只显示前四类；`diagnostic` 收进默认折叠的“技术细节”区。反复的连接失败（MCP、HTTP 5xx、socket hang up 等）合并成一条“模型工具连接不稳定，正在重试（第 N 次）”。分类优先看来源和流（`web/local-runtime/run-events.mjs`），正则只作兼容补充。

## 文件与数据边界

每个申请项目位于：

```text
projects/<project-id>/
├── project.json
├── status.json
├── inputs/
├── outputs/
├── community-cache/
└── runs/
```

- `project.json` 保存用户输入、调查草稿/确认快照，以及独立的申请材料草稿/确认快照；草稿不能直接授权背调、搜索文献或写材料。
- `status.json` 保存轻量阶段计数，不是结果内容的唯一依据。
- `outputs/` 保存唯一事实源 JSON、派生 HTML 主报告和补充 Excel。
- `runs/` 保存每次 Agent 运行事件。
- `community-cache/` 仅在用户明确授权后生成。

## Agent 权限

Codex、Claude Code 或自定义 API 需要命令、文件或网络权限时，前端运行面板会暂停并显示授权卡。

Custom API 并不是在浏览器中直接执行 Agent：本地后端使用项目随附的 Codex
app-server 驱动工具与授权协议，再把模型请求发送到用户填写的 Responses API。
`@openai/codex` 因此属于 Web 的运行依赖，但 Custom API 不要求 Codex 登录。
连接前必须先确认该本地运行引擎可启动；不能只凭 `GET /models` 成功就把整个
执行链标记为可用。

- “允许一次”：只允许当前请求。
- “本次运行允许”：只复用同类工具或同一命令入口。
- “拒绝”：拒绝当前操作，Agent 可选择替代方案或停止。

项目工作区内已经预授权的写入可能不会弹卡；这不代表前端遗漏了请求。

医学公开调查默认先用 GPT 宿主实际暴露的内置搜索/网页工具，按其 schema 支持的动作执行。`backend` 默认 `builtin_web`，旧 `auto` 同样内置优先，用户显式指定的其他后端保留。内置路径不足时回退官方静态页/只读 API；动态JS表单才调用已有交互浏览器。页面开关不证明工具已安装或已测试；没有交互浏览器也能继续内置网页调查。内置检索记录 `retrieval_method: static_web` 和实际工具/提供方，不等同 Browser Use 实操。深查仍需精确候选/维度确认；安装、个人登录/会话、付费云、上传材料、发信和提交申请不在公开浏览许可内。详见 [浏览器策略](../skills/advisor-pipeline/references/browser-research-policy.md)；联网/浏览器测试结果只按实际运行证据报告。

## 前端维护清单

调整工作流时，至少同时检查：

1. 页面按钮是否区分“首次运行”和“补充或重新运行”。
2. 完成态是否由真实输出文件驱动。
3. P2 是否默认先展示结果，而不是先展示配置表单。
4. P3 摘要是否区分医学展示序号与通用排名；已保存 HTML 链接是否可用、显示保存时间且不冒充本轮新成果。
5. Agent prompt 与后端是否同步要求共享 JSON、主题 HTML 和兼容工作簿；探索是否允许只有真实导师记录。
6. 精确导师 ID、`selectedSections`、来源范围、研究范围指纹和社区授权是否正确持久化；医学比较是否绑定当前调查确认。
7. 权限卡是否能处理 Codex 和 Claude Code 的当前协议。
8. 桌面与窄屏布局是否都没有横向溢出。
9. `pixi run test`、`pixi run lint` 和必要的界面回归是否实际执行；未安装依赖、跳过测试或未跑 live 浏览器时是否如实记录。
10. 本文档、根目录 `README.md` 和 `web/README.md` 是否同步更新。
11. CLI 是否复用同一 11 维度目录、通用三项/医学七项预设、成本阈值和 public-only/社区授权边界。
12. 医学无 CV 探索、真实结构化背景申请、通用原流程及申请材料门控是否分别回归。

## 本地启动

在仓库根目录使用 [pixi.toml](../pixi.toml) 管理 Node.js/Python；目前 manifest 目标平台为 `linux-64`（Windows 使用对应 Linux/WSL 环境），不据此承诺原生 Windows/macOS 的 Pixi 环境可用。Node.js 约束为 `>=22.13,<23`，Python 为 `>=3.11,<3.13`。Web 依赖继续使用 `web/package-lock.json`，由 Pixi 的 Node/npm 执行 `npm ci`，不替换 npm 锁或另装全局包。

下面包含实际依赖下载，需遵循已有环境授权；尚未安装依赖时不能宣称测试或界面已可用：

```bash
pixi install
pixi run check-runtime
pixi run web-install
pixi run dev
```

打开 <http://localhost:3000/>，前端和本地桥接服务一起启动。维护命令在仓库根目录执行：

```bash
pixi run test
pixi run typecheck
pixi run lint
pixi run report --project-root /absolute/path/to/project
```

`pixi run test-core` 是跳过前端 server-rendering 测试的有限脚本回归，不能替代完整 Web 测试、构建或浏览器交互验证。`pixi run report` 只从已有记录重导出报告，不重复调研。Pixi `init` 任务会覆盖 VS Code 设置，是可选编辑器配置，启动前端不必运行它。

`test` 会先构建 Web；也可单独执行 `pixi run web-build`。`typecheck` 需要这份构建生成的真实配置，使用现有 Wrangler 生成本地 Worker 声明，再分别检查浏览器和 Worker 源码；不新增部署配置、不创建数据库绑定或连接云端部署。生成的声明被忽略，不提交到仓库。
