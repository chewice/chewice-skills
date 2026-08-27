# Field Rules

When multiple WeChat message blocks are supplied, merge all normal assessment records into one normal table. If any record is a follow-up, create one separate follow-up table containing only follow-up rows. Records containing "瑞美特" are also extracted to a third 瑞美特 sheet.

A single paste may contain several forwarded WeChat blocks separated by blank lines. Each block typically starts with:

1. Sender nickname (e.g. `Howl`) — ignore; not 姓名 or 评估员.
2. Timestamp (e.g. `2026年08月27日 18:28`) — this date belongs **only** to the following `姓名` in the same block, and formats to `2026.8.27`.
3. Record body (`脑计划HWn-...`, labeled fields, sample notes).

## Normal Assessment Table

Use these columns, in this exact order:

```text
序号    其他编号        评估日期        院号    姓名    推荐医生        评估员  诊断    是否评估ADHD量表        CRF     HAMD评分        是否为简化版    （空列）  是否随访        是否留取标本    留取标本类型
```

Rules:

- Extract `序号` from `HWn-0687`, `HWn0687`, `HWbd-0004` or similar project IDs, **preserving the original format including prefix, separator, and leading zeros**. Examples: `HWn-0687` -> `HWn-0687`, `HWbd-0004` -> `HWbd-0004`. `HWt-...` 编号归入 `其他编号`，不进 `序号`。
- Fill `其他编号` only when an explicit `HWt-...` style identifier appears; preserve its original format including leading zeros (e.g. `HWt-0621` -> `HWt-0621`).
- `评估日期` 来源：优先取**本消息块**微信转发头第二行时间戳（发送者昵称下一行，如 `2026年08月27日 18:28`），其次取块内正文中的日期。支持数字格式（`2026-07-09`/`2026/07/09`/`2026.07.09`）和中文格式（`2026年07月09日`，可带时间），均转为 `2026.8.27`（点分隔，月日去掉前导零，丢弃时分）。一条记录只用自己块内的日期，禁止用其他块的日期补空。Leave `院号` and `是否评估ADHD量表` blank unless the source explicitly provides them.
- Extract `姓名`, `推荐医生`, `评估员`, `诊断`, and `HAMD评分` from matching labels.
- Set `是否为简化版` to `否` unless the source explicitly says simplified/简化版.
- Set `是否随访` to `是` for normal assessment rows; set to `否` when the source says 拒绝随访.
- Set `是否留取标本` to `是` when any sample is retained; set to `否` when the source says refused/no sample/no 留样/拒绝留样; otherwise leave blank.
- Set `CRF` to `电子版他评+自评` when both other-rating and self-rating are completed or self-rating is being followed up (自评跟进/自评完成/自评已做). Set it to ` 电子版他评` when only other-rating is done or self-rating is refused (拒绝自评). Preserve uncertainty in notes rather than inventing completion.
- **拒绝自评、随访、留样** 的记录仍然归入正常表：是否随访=否，是否留取标本=否，CRF=电子版他评，留取标本类型留空。

## Follow-up Table

Use these columns, in this exact order:

```text
姓名    日期    CRF     评估员  留取样本类型
```

Rules:

- Records with `V2`/`V3`/`随访` in the header are classified as follow-up records, **unless** the record says 拒绝随访 (which stays in the normal table with 是否随访=否).
- Extract `姓名` from matching labels in the source block.
- `日期` 来源与格式同正常表的 `评估日期`：本块微信转发头时间戳或块内日期，转为 `2026.8.27`。Leave blank unless the source explicitly provides it. 写入 xlsx 后按日期先后排序（较早的日期在前）。
- Set `CRF` to `电子版他评+自评` when both follow-up other-rating and self-rating are done or self-rating is being followed up.
- Set `评估员` from the matching label.
- Set `留取样本类型` from the sample rules below.

## 瑞美特 Table

Use these columns, in this exact order:

```text
序号(A)  姓名(B)  (C-G空)  推荐医生(H)  评估员(I)  (J空)  统计归类(K)  (L空)  HAMD/HAMA评分(M)  诊断(N)  评估日期(O)
```

Rules:

- Only records containing "瑞美特" in the source block are extracted to this sheet.
- 瑞美特 records are **also** written to 正常/随访 sheets following their respective rules — the 瑞美特 sheet is an additional extraction.
- `序号`: full HWn identifier without hyphen, e.g. `HWn-3148` -> `HWn3148`, `HWn-0687` -> `HWn0687`.
- `评估日期`: format as `2026/7/14` (slash, no zero-padding on month/day). Supports same input formats as normal assessment date.
- `姓名`, `推荐医生`, `评估员`, `诊断`: extracted from matching labels.
- `HAMD/HAMA评分` (M列): 优先提取 `HAMD：` 后面的数值（纯数字，如 `6`）；如为空则提取 `HAMA：` 后面的值并保留标签（如 `HAMA：6`）；均无则留空。
- `统计归类` (K列): 写入**组别标签**（如 `试验组`、`干扰组(焦虑)`），通过两层映射：
  - 第2层（诊断→统计归类）：从 `诊断：` 字段模糊推断统计归类（抑郁发作/抑郁障碍→抑郁症，双相I型/双相II型/躁狂发作→双相障碍，精神分裂症→精神分裂症，焦虑障碍/广泛性焦虑→焦虑障碍，代谢综合征→代谢性疾病，强迫障碍/强迫症→强迫障碍，失眠症/非器质性失眠症/嗜睡症/发作性睡病→睡眠障碍，健康/无异常→健康对照）。
  - 第1层（统计归类→组别）：抑郁症→试验组，双相障碍→干扰组(BD)，精神分裂症→干扰组(SZ)，焦虑障碍→干扰组(焦虑)，代谢性疾病→干扰组(代谢)，强迫障碍→干扰组(强迫)，睡眠障碍→干扰组(失眠)，健康对照→对照组。
  - 诊断匹配不到任何归类时留空。
- Columns C-G, J, L: always empty.
- Font: 等线 11pt.
- No sorting — append in order of appearance.

## Sample Rules

Normalize sample descriptions into the target table wording:

- `紫`, `紫管`, `紫色管`: `EDTA抗凝管N管`
- `黄`, `黄管`, `黄色管`: `促凝管N管`
- `唾液`: `唾液1ml`（固定值）

Counting:

- `1紫`, `1 紫`, `紫1`, `紫管1管` -> `EDTA抗凝管1管`
- `2紫`, `2 紫`, `紫2`, `紫管2管` -> `EDTA抗凝管2管`
- `1黄`, `1 黄`, `黄1`, `黄管1管` -> `促凝管1管`
- If a color is present with no count, default to 1 管.

### Output Format

- 输出顺序固定为：**EDTA抗凝管 → 促凝管 → 唾液**，以中文顿号 `、` 分隔。
- 当某类样本数量为 0 时，**跳过该类型不输出**，后续类型前移补齐，不留空位。
  - 例：EDTA=2, 促凝管=0, 唾液=1 → `EDTA抗凝管2管、唾液1ml`
  - 例：EDTA=1, 促凝管=1, 唾液=1 → `EDTA抗凝管1管、促凝管1管、唾液1ml`
  - 例：EDTA=0, 促凝管=1, 唾液=0 → `促凝管1管`

If the source says refused sample, refused 留样, or no sample, set sample availability to `否` and leave sample type blank.
## Privacy And Missing Data

- Do not include raw source messages in the final answer unless the user asks.
- Do not fill dates from the chat/session/system clock. WeChat forward-header timestamps inside each message block **must** be extracted and bound to that block's `姓名`. Do not copy another block's date.
- Do not guess clinical values. Empty cells are preferable to invented data.
- If a field is ambiguous, leave the cell blank and add a short note after the TSV block.

## V1 随访高亮规则

- 当随访记录的原始微信消息块中出现 `V1` 或 `v1`（大小写均纳入）时，写入 xlsx 后该行 **B 列（日期）底色设为 `#FFFF00`**（明黄）。
- `V2`、`V3`、`v2`、`v3` 等其他版本号不触发高亮。
- 该规则仅在随访工作表中生效，正常表和瑞美特表不受影响。
