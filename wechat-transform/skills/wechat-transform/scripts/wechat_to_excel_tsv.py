"""Convert WeChat-style Chinese registration notes to paste-ready TSV."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


NORMAL_COLUMNS = [
    "序号",
    "其他编号",
    "评估日期",
    "院号",
    "姓名",
    "推荐医生",
    "评估员",
    "诊断",
    "是否评估ADHD量表",
    "CRF",
    "HAMD评分",
    "是否为简化版",
    "",
    "是否随访",
    "是否留取标本",
    "留取标本类型",
]

FOLLOWUP_COLUMNS = ["姓名", "日期", "CRF", "评估员", "留取样本类型", "V1标记"]

RUIMEITE_COLUMNS = [
    "序号",       # A
    "姓名",       # B
    "",           # C
    "",           # D
    "",           # E
    "",           # F
    "",           # G
    "推荐医生",   # H
    "评估员",     # I
    "",           # J
    "统计归类",   # K
    "",           # L
    "HAMD/HAMA评分",  # M
    "诊断",       # N
    "评估日期",   # O
]

# 统计归类 → K列组别（第1层：归类反查组别标签）
CATEGORY_TO_GROUP = {
    "抑郁症": "试验组",
    "双相障碍": "干扰组(BD)",
    "精神分裂症": "干扰组(SZ)",
    "焦虑障碍": "干扰组(焦虑)",
    "代谢性疾病": "干扰组(代谢)",
    "强迫障碍": "干扰组(强迫)",
    "睡眠障碍": "干扰组(失眠)",
    "健康对照": "对照组",
}

# Layer 2: 诊断模糊推断 (按顺序匹配，命中即止)
DIAGNOSIS_CATEGORY_RULES = [
    (["抑郁发作", "抑郁障碍", "抑郁症", "重性抑郁", "单相抑郁", "重度抑郁",
      "复发性抑郁", "恶劣心境", "未特定的抑郁"], "抑郁症"),
    (["双相I型", "双相1型", "双相II型", "双相2型", "双相障碍", "双相情感",
      "躁狂发作", "双相Ⅰ型", "双相Ⅱ型", "轻躁狂", "环性心境"], "双相障碍"),
    (["精神分裂症", "分裂情感", "偏执型精神分裂", "精神分裂",
      "青春型精神分裂", "未分化型精神分裂"], "精神分裂症"),
    (["焦虑障碍", "广泛性焦虑", "惊恐障碍", "社交焦虑", "焦虑状态",
      "分离性焦虑", "场所恐惧", "特定恐惧"], "焦虑障碍"),
    (["代谢性疾病", "代谢综合征"], "代谢性疾病"),
    (["强迫障碍", "强迫症", "强迫性障碍", "强迫思维", "强迫行为"], "强迫障碍"),
    (["睡眠障碍", "失眠症", "非器质性失眠症", "失眠", "原发性失眠",
      "慢性失眠", "入睡困难", "睡眠维持障碍", "早醒", "嗜睡症",
      "发作性睡病", "睡眠-觉醒节律障碍"], "睡眠障碍"),
    (["健康", "无异常", "未见异常"], "健康对照"),
]


def strip_md(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^\s*[-*]\s+", "", line)
    line = re.sub(r"^\s{0,3}#+\s*", "", line)
    return line.strip()


def label_value(block: str, label: str) -> str:
    pattern = rf"^[ \t]*(?:[-*][ \t]*)?{re.escape(label)}[ \t]*[：:][ \t]*([^\r\n]*)[ \t]*$"
    match = re.search(pattern, block, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_brain_id(block: str) -> str:
    """Extract full brain-project ID preserving prefix, separator and leading zeros.
    Prefers HWn/HWbd project IDs over HWt tube IDs:
    HWn-0772 -> HWn-0772, HWbd-0004 -> HWbd-0004, HWt-0621 -> HWt-0621."""
    match = re.search(r"HW(?:n|bd)\s*[-_]?\d+", block, flags=re.IGNORECASE)
    if match:
        return match.group(0)
    match = re.search(r"HW[a-z]*\s*[-_]?\d+", block, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def extract_hwn_full(block: str) -> str:
    """Extract full HWn identifier without hyphen: HWn-3148 -> HWn3148, HWn-0687 -> HWn0687"""
    match = re.search(r"HWn\s*[-_]?(\d+)", block, flags=re.IGNORECASE)
    if not match:
        return ""
    return f"HWn{match.group(1)}"


def extract_hwt(block: str) -> str:
    """Extract full HWt identifier preserving format: HWt-0621 -> HWt-0621"""
    match = re.search(r"HWt\s*[-_]?\d+", block, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def extract_date(block: str) -> str:
    match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", block)
    if match:
        return f"{match.group(1)}.{int(match.group(2))}.{int(match.group(3))}"
    match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", block)
    if match:
        return f"{match.group(1)}.{int(match.group(2))}.{int(match.group(3))}"
    return ""


def extract_date_ruimeite(block: str) -> str:
    """Extract date in 2026/7/14 format for ruimeite sheet."""
    match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", block)
    if match:
        return f"{match.group(1)}/{int(match.group(2))}/{int(match.group(3))}"
    match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", block)
    if match:
        return f"{match.group(1)}/{int(match.group(2))}/{int(match.group(3))}"
    return ""


def is_followup(block: str) -> bool:
    if re.search(r"拒绝.{0,6}随访|随访.{0,6}拒绝", block):
        return False
    return bool(re.search(r"随访|V\s*\d+", block, flags=re.IGNORECASE))


def is_ruimeite(block: str) -> bool:
    return bool(re.search(r"瑞美特", block))


def has_sample_refusal(text: str) -> bool:
    return bool(re.search(r"(拒绝|未|无|没有).{0,6}(留样|留取标本|留取样本|标本|样本)", text))


def number_before_or_after(text: str, color_pattern: str) -> int:
    before = re.findall(rf"(\d+)\s*{color_pattern}", text)
    if before:
        return sum(int(value) for value in before)
    after = re.findall(rf"{color_pattern}\s*(\d+)\s*(?:管|支|个)?", text)
    total = sum(int(value) for value in after)
    if total == 0 and re.search(rf"{color_pattern}(?:色)?管", text):
        total = 1
    return total


def extract_samples(block: str) -> tuple[str, str]:
    compact = block.replace("，", ",").replace("、", ",").replace("＋", "+")
    edta = number_before_or_after(compact, r"紫(?:色)?(?:管)?")
    serum = number_before_or_after(compact, r"黄(?:色)?(?:管)?")

    saliva = 0
    saliva_match = re.search(r"唾液\s*(\d+(?:\.\d+)?)\s*(ml|mL|管)?", compact)
    if saliva_match:
        saliva = 1
    elif "唾液" in compact:
        saliva = 1

    parts = []
    if edta:
        parts.append(f"EDTA抗凝管{edta}管")
    if serum:
        parts.append(f"促凝管{serum}管")
    if saliva:
        parts.append("唾液1ml")

    if parts:
        return "是", "、".join(parts)
    if has_sample_refusal(compact):
        return "否", ""
    return "", ""


def extract_crf(block: str) -> str:
    text = block.replace("，", ",").replace("、", ",")
    has_other = bool(re.search(r"他评", text))
    has_self = bool(re.search(r"自评", text))
    self_refused = bool(re.search(r"自评.{0,6}拒绝|拒绝.{0,6}自评", text))
    self_positive = bool(re.search(r"自评.{0,8}(完成|已做|跟进|跟踪)|已做.{0,8}自评", text))

    if has_other and has_self and self_positive and not self_refused:
        return "电子版他评+自评"
    if has_other:
        return "电子版他评"
    return ""


def split_records(text: str) -> list[str]:
    records: list[list[str]] = []
    current: list[str] = []
    start_prefix_re = re.compile(r"^(脑计划|瑞美特)", re.IGNORECASE)
    start_id_re = re.compile(r"HW[a-z]*\s*[-_]?\d+", re.IGNORECASE)
    control_re = re.compile(r"(开始|转换|开始转换)[。.!！?？:：,，、\s]*")
    wechat_datetime_re = re.compile(
        r"^20\d{2}年\d{1,2}月\d{1,2}日(?:\s+\d{1,2}[:：]\d{2}(?::\d{2})?)?$"
    )
    date_re = re.compile(r"20\d{2}[年./-]\d{1,2}[月./-]\d{1,2}日?")
    separator_re = re.compile(r"^[椎脊]$")
    clinical_note_re = re.compile(r"他评|自评|留样|留取|随访|拒绝|完成|已做|跟进")

    def _is_record_start(line: str) -> bool:
        if start_prefix_re.match(line):
            return True
        if start_id_re.search(line):
            return True
        return False

    def _flush() -> None:
        nonlocal current
        if current:
            records.append(current)
            current = []

    def _is_date_header(line: str) -> bool:
        if "姓名" in line or _is_record_start(line):
            return False
        if wechat_datetime_re.fullmatch(line):
            return True
        if "：" in line or ":" in line:
            return False
        return bool(date_re.search(line))

    def _looks_like_wechat_nickname(line: str) -> bool:
        if "：" in line or ":" in line:
            return False
        if _is_record_start(line) or _is_date_header(line):
            return False
        if clinical_note_re.search(line):
            return False
        if "，" in line or "," in line:
            return False
        return len(line) <= 20

    def _has_record_body(lines: list[str]) -> bool:
        return any(_is_record_start(x) and "姓名" not in x for x in lines)

    for raw_line in text.splitlines():
        line = strip_md(raw_line)
        if not line:
            _flush()
            continue
        if control_re.fullmatch(line):
            _flush()
            continue
        if re.fullmatch(r"(正常|随访|转化|转换|补充)[:：]?", line):
            if current and re.fullmatch(r"(随访|转化|转换)[:：]?", line):
                _flush()
            continue
        if line.startswith("|") or re.match(r"^-{3,}$", line):
            continue
        if separator_re.fullmatch(line):
            continue
        if _is_date_header(line):
            if current and _looks_like_wechat_nickname(current[-1]):
                current.pop()
            _flush()
            current = [line]
            continue
        if _is_record_start(line) and ("姓名" not in line):
            if current and _has_record_body(current):
                _flush()
                current = [line]
            elif current:
                current.append(line)
            else:
                current = [line]
            continue
        if _looks_like_wechat_nickname(line) and not current:
            continue
        if current:
            current.append(line)
        else:
            current = [line]

    _flush()
    return ["\n".join(lines) for lines in records]


def record_to_normal(block: str) -> dict[str, str]:
    sample_status, sample_type = extract_samples(block)
    return {
        "序号": extract_brain_id(block),
        "其他编号": extract_hwt(block),
        "评估日期": extract_date(block),
        "院号": label_value(block, "院号"),
        "姓名": label_value(block, "姓名"),
        "推荐医生": label_value(block, "推荐医生"),
        "评估员": label_value(block, "评估员"),
        "诊断": label_value(block, "诊断"),
        "是否评估ADHD量表": label_value(block, "是否评估ADHD量表"),
        "CRF": extract_crf(block),
        "HAMD评分": label_value(block, "HAMD"),
        "是否为简化版": "是" if "简化" in block else "否",
        "是否随访": "否" if re.search(r"拒绝.{0,6}随访|随访.{0,6}拒绝", block) else "是",
        "是否留取标本": sample_status,
        "留取标本类型": sample_type,
    }


def record_to_followup(block: str) -> dict[str, str]:
    v1_flag = "是" if re.search(r"V1|v1", block) else ""
    _, sample_type = extract_samples(block)
    return {
        "姓名": label_value(block, "姓名"),
        "日期": extract_date(block),
        "CRF": extract_crf(block),
        "评估员": label_value(block, "评估员"),
        "留取样本类型": sample_type,
        "V1标记": v1_flag,
    }


def resolve_ruimeite_group(block: str) -> str:
    """K列组别: 诊断→统计归类→组别标签。先走第2层诊断模糊匹配确定归类，再通过第1层映射为组别填入K列。"""
    diagnosis = label_value(block, "诊断")
    if diagnosis:
        for keywords, category in DIAGNOSIS_CATEGORY_RULES:
            for kw in keywords:
                if kw in diagnosis:
                    return CATEGORY_TO_GROUP.get(category, "")
    return ""


def record_to_ruimeite(block: str) -> dict[str, str]:
    # HAMD -> bare number; HAMA fallback -> "HAMA：N"
    hamd = label_value(block, "HAMD")
    hama = label_value(block, "HAMA")
    if hamd:
        score = hamd
    elif hama:
        score = f"HAMA：{hama}"
    else:
        score = ""
    return {
        "序号": extract_hwn_full(block),
        "姓名": label_value(block, "姓名"),
        "推荐医生": label_value(block, "推荐医生"),
        "评估员": label_value(block, "评估员"),
        "统计归类": resolve_ruimeite_group(block),
        "HAMD/HAMA评分": score,
        "诊断": label_value(block, "诊断"),
        "评估日期": extract_date_ruimeite(block),
    }


def to_tsv(columns: list[str], rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(row.get(column, "").replace("\t", " ").replace("\n", " ") for column in columns))
    return "\n".join(lines)


def parse(text: str, mode: str) -> dict[str, str]:
    records = split_records(text)
    normal_rows = []
    followup_rows = []
    ruimeite_rows = []

    for block in records:
        if mode == "normal":
            normal_rows.append(record_to_normal(block))
        elif mode == "followup":
            followup_rows.append(record_to_followup(block))
        elif is_followup(block):
            followup_rows.append(record_to_followup(block))
        else:
            normal_rows.append(record_to_normal(block))

        if is_ruimeite(block):
            ruimeite_rows.append(record_to_ruimeite(block))

    output = {}
    if normal_rows:
        output["normal"] = to_tsv(NORMAL_COLUMNS, normal_rows)
    if followup_rows:
        output["followup"] = to_tsv(FOLLOWUP_COLUMNS, followup_rows)
    if ruimeite_rows:
        output["ruimeite"] = to_tsv(RUIMEITE_COLUMNS, ruimeite_rows)
    return output


def read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def _resolve_xlsx_path(arg_value: str | None) -> str:
    if arg_value:
        return arg_value
    return os.environ.get("WECHAT_TRANSFORM_XLSX", "wechat-transform.xlsx")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Input text/Markdown file. Reads stdin when omitted.")
    parser.add_argument("--mode", choices=["auto", "normal", "followup"], default="auto")
    parser.add_argument("--raw-tsv", action="store_true", help="Emit only TSV without labels or fences.")
    parser.add_argument(
        "--output-xlsx",
        nargs="?",
        const=True,
        help="Directly write parsed records to xlsx (requires openpyxl). "
             "Value is the target xlsx path; omit to use $WECHAT_TRANSFORM_XLSX or ./wechat-transform.xlsx.",
    )
    args = parser.parse_args()

    text = read_input(args.input)
    parsed = parse(text, args.mode)

    if not parsed:
        return 1

    if args.output_xlsx is not None:
        xlsx_path = _resolve_xlsx_path(
            args.output_xlsx if isinstance(args.output_xlsx, str) else None
        )
        _scripts_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(_scripts_dir))
        from tsv_append_xlsx import append_tsv_to_xlsx  # noqa: E402

        labels = {"normal": "正常", "followup": "随访", "ruimeite": "瑞美特"}
        for key in ("normal", "followup", "ruimeite"):
            if key in parsed:
                n = append_tsv_to_xlsx(xlsx_path, labels[key], parsed[key])
                print(f"{labels[key]}: {n} rows", file=sys.stderr)
        return 0

    if args.raw_tsv:
        print("\n\n".join(parsed.values()))
        return 0

    labels = {"normal": "正常", "followup": "随访", "ruimeite": "瑞美特"}
    chunks = []
    for key in ("normal", "followup", "ruimeite"):
        if key in parsed:
            chunks.append(f"{labels[key]}\n\n```tsv\n{parsed[key]}\n```")
    print("\n\n".join(chunks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
