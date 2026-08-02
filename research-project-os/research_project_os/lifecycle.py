"""Question-led exploration, audited runs, archives, and pipelines."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

from .core import (
    ANALYSIS_SCHEMA_VERSION,
    ARCHIVE_VERSION_PATTERN,
    QUESTION_ID_PATTERN,
    RUN_ID_PATTERN,
    RUN_SCHEMA_VERSION,
    TASK_NAME_PATTERN,
    append_lifecycle_event,
    atomic_write,
    ensure_manifest,
    environment_hashes,
    file_records,
    git_commit,
    git_status,
    hash_path,
    load_yaml,
    markdown_field,
    parse_markdown_section,
    relative_to_root,
    safe_project_path,
    sha256_file,
    sha256_text,
    stable_json,
    utc_now,
    utc_text,
    yaml_text,
)
from .reporting import (
    REPORT_SCHEMA_VERSION,
    ReportKind,
    build_report_text,
    parse_report_source,
    validate_report,
)


PLACEHOLDERS = ("尚未填写", "待讨论", "TODO", "TBD", "pending")
QUESTION_STATUSES = frozenset(
    {"queued", "current", "answered", "deferred", "cancelled"}
)
REVIEW_DECISIONS = frozenset(
    {
        "pending",
        "accepted",
        "accepted_with_limitations",
        "inconclusive",
        "rework_required",
        "not_applicable",
    }
)
QUESTION_REVIEW_MATRIX = {
    "queued": frozenset({"pending"}),
    "current": frozenset({"pending", "rework_required"}),
    "answered": frozenset(
        {"accepted", "accepted_with_limitations", "inconclusive"}
    ),
    "deferred": frozenset({"pending", "inconclusive", "rework_required"}),
    "cancelled": frozenset({"not_applicable"}),
}
QUESTION_BLOCK_HEADING_PATTERN = re.compile(
    r"^(?P<id>Q-\d{3})(?:\s+(?:—|-)\s+(?P<title>.+))?$"
)
SCRIPT_SUFFIXES = {".py", ".r", ".sh"}
CHINESE_PATTERN = re.compile(r"[\u3400-\u9fff]")
REPORTING_LOGIC_PATTERN = re.compile(
    r"research_project_os\.reporting|"
    r"\b(?:build_report|validate_report|write_html)\s*\(|"
    r"<!doctype\s+html|<html\b|<style\b|\bREPORT_CSS\b|\bjinja2\b",
    flags=re.IGNORECASE,
)


def question_subsection(block: str, heading: str) -> str:
    match = re.search(
        rf"^#### {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^#### |^### |^## |\Z)",
        block,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else ""


def parse_question_blocks(text: str) -> list[dict[str, str]]:
    section = parse_markdown_section(text, "Questions")
    if not section:
        return []
    headings = list(
        re.finditer(r"^###\s+(?P<heading>.+?)\s*$", section, flags=re.MULTILINE)
    )
    questions = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        body = section[heading.end() : end].strip()
        rendered_heading = heading.group("heading").strip()
        parsed = QUESTION_BLOCK_HEADING_PATTERN.fullmatch(rendered_heading)
        questions.append(
            {
                "heading": rendered_heading,
                "id": parsed.group("id") if parsed else "",
                "title": (parsed.group("title") or "").strip() if parsed else "",
                "status": (markdown_field(body, "Status") or "").lower(),
                "depends_on": markdown_field(body, "Depends on") or "",
                "review_decision": (
                    markdown_field(body, "Review decision") or ""
                ).lower(),
                "reviewed_on": markdown_field(body, "Reviewed on") or "",
                "question": question_subsection(body, "Question"),
                "inputs": question_subsection(body, "Inputs"),
                "method_reference": question_subsection(body, "Method reference"),
                "expected_outputs": question_subsection(body, "Expected outputs"),
                "completion_criterion": question_subsection(
                    body, "Completion criterion"
                ),
                "reviewed_outcome": question_subsection(body, "Reviewed outcome"),
                "evidence": question_subsection(body, "Evidence"),
            }
        )
    return questions


def legacy_markdown_field(section: str, label: str) -> str:
    lines = section.splitlines()
    for index, line in enumerate(lines):
        match = re.match(rf"^- {re.escape(label)}:\s*(.*)$", line)
        if match is None:
            continue
        values = [match.group(1).strip().strip("`")]
        for continuation in lines[index + 1 :]:
            if continuation.startswith(("  ", "\t")):
                values.append(continuation.strip())
                continue
            if not continuation.strip() and any(values):
                continue
            break
        return " ".join(value for value in values if value).strip()
    return ""


def legacy_current_question(text: str) -> dict[str, str]:
    section = parse_markdown_section(text, "Current question")
    if not section:
        raise ValueError(
            "QUESTIONS.md must contain a block-based Questions section or a legacy "
            "Current question section"
        )
    return {
        "id": legacy_markdown_field(section, "ID"),
        "question": legacy_markdown_field(section, "Question"),
        "inputs": "",
        "method_reference": legacy_markdown_field(section, "Method reference"),
        "expected_outputs": "",
        "completion_criterion": legacy_markdown_field(
            section, "Completion criterion"
        ),
        "format": "legacy",
    }


def contains_placeholder(value: str) -> bool:
    return not value or any(marker.lower() in value.lower() for marker in PLACEHOLDERS)


def current_research_question(root: Path) -> dict[str, str]:
    path = root / "QUESTIONS.md"
    if not path.is_file():
        raise ValueError("Missing human-owned QUESTIONS.md")
    text = path.read_text(encoding="utf-8")
    if parse_markdown_section(text, "Questions"):
        questions = parse_question_blocks(text)
        invalid = [question["heading"] for question in questions if not question["id"]]
        if invalid:
            raise ValueError(
                "QUESTIONS.md has invalid question block headings: " + ", ".join(invalid)
            )
        current = [question for question in questions if question["status"] == "current"]
        if len(current) != 1:
            raise ValueError(
                "QUESTIONS.md must contain exactly one question block with Status: current"
            )
        question = {**current[0], "format": "blocks"}
        decision = question["review_decision"]
        if decision not in QUESTION_REVIEW_MATRIX["current"]:
            allowed = ", ".join(sorted(QUESTION_REVIEW_MATRIX["current"]))
            raise ValueError(
                "QUESTIONS.md current Review decision must be one of: " + allowed
            )
        reviewed_on = question["reviewed_on"].strip().strip("`")
        if decision == "pending" and reviewed_on.lower() != "pending":
            raise ValueError(
                "QUESTIONS.md pending current question must use Reviewed on: pending"
            )
        if decision == "rework_required":
            try:
                date.fromisoformat(reviewed_on)
            except ValueError as error:
                raise ValueError(
                    "QUESTIONS.md rework_required current question needs "
                    "Reviewed on: YYYY-MM-DD"
                ) from error
            if contains_placeholder(question["reviewed_outcome"]):
                raise ValueError(
                    "QUESTIONS.md rework_required current question must explain "
                    "Reviewed outcome"
                )
        required = (
            "question",
            "inputs",
            "expected_outputs",
            "completion_criterion",
        )
    else:
        question = legacy_current_question(text)
        required = ("question", "completion_criterion")
    if QUESTION_ID_PATTERN.fullmatch(question["id"]) is None:
        raise ValueError("QUESTIONS.md current ID must match Q-NNN")
    for field in required:
        if contains_placeholder(question[field]):
            raise ValueError(f"QUESTIONS.md current {field} has not been filled in")
    return question


def normalize_task_name(order: int, core: str, summary: str) -> str:
    if order < 0:
        raise ValueError("Task order must be non-negative")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,23}", core):
        raise ValueError("Task core must be one short ASCII token")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,63}", summary):
        raise ValueError("Task summary must be a short ASCII phrase")
    rendered = re.sub(r"[^A-Za-z0-9]+", "-", summary).strip("-").lower()
    task_name = f"P{order}-{core}-{rendered}"
    if TASK_NAME_PATTERN.fullmatch(task_name) is None:
        raise ValueError(f"Invalid task name: {task_name}")
    return task_name


def parse_task_name(task_name: str) -> dict[str, Any]:
    match = TASK_NAME_PATTERN.fullmatch(task_name)
    if match is None:
        raise ValueError("Task name must match P<order>-<core>-<summary>")
    return {
        "name": task_name,
        "order": int(match.group("order")),
        "core": match.group("core"),
        "summary": match.group("summary"),
    }


def explore_task_paths(root: Path) -> list[Path]:
    explore = root / "explore"
    if not explore.is_dir():
        return []
    return [
        path
        for path in sorted(explore.iterdir())
        if path.is_dir() and TASK_NAME_PATTERN.fullmatch(path.name)
    ]


def verify_archive_snapshot(root: Path, selector: str) -> dict[str, Any]:
    if "@" not in selector:
        return {"ok": False, "selector": selector, "errors": ["Missing @vNNN"]}
    task_name, version = selector.rsplit("@", 1)
    errors: list[str] = []
    try:
        parse_task_name(task_name)
    except ValueError as error:
        errors.append(str(error))
    if ARCHIVE_VERSION_PATTERN.fullmatch(version) is None:
        errors.append("Archive version must match vNNN")
    target = root / "archive" / task_name / version
    manifest_path = target / "archive_manifest.yaml"
    if errors:
        return {"ok": False, "selector": selector, "errors": errors}
    if not manifest_path.is_file():
        return {
            "ok": False,
            "selector": selector,
            "errors": [f"Missing archive manifest: {manifest_path}"],
        }
    try:
        manifest = load_yaml(manifest_path)
        if manifest.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
            errors.append(f"Unsupported archive schema: {manifest_path}")
        snapshot = manifest.get("snapshot")
        if not isinstance(snapshot, dict) or snapshot.get("selector") != selector:
            errors.append(f"Archive selector mismatch: {manifest_path}")
        review = manifest.get("review")
        if (
            not isinstance(review, dict)
            or review.get("status") != "human_approved"
            or not isinstance(review.get("note"), str)
            or not review["note"].strip()
        ):
            errors.append(f"Archive lacks human review: {manifest_path}")
        expected = manifest.get("files")
        if not isinstance(expected, list):
            errors.append(f"Archive files must be a list: {manifest_path}")
            expected = []
        actual = file_records(target, exclude={"archive_manifest.yaml"})
        if actual != expected:
            errors.append(f"Archive files or hashes changed: {selector}")
    except (OSError, ValueError) as error:
        errors.append(str(error))
    return {
        "ok": not errors,
        "selector": selector,
        "archive_path": (
            target.relative_to(root).as_posix() if target.exists() else None
        ),
        "manifest_sha256": (
            sha256_file(manifest_path) if manifest_path.is_file() else None
        ),
        "errors": errors,
    }


def task_has_archive(root: Path, task_name: str) -> bool:
    parent = root / "archive" / task_name
    if not parent.is_dir():
        return False
    return any(
        (version / "archive_manifest.yaml").is_file()
        for version in parent.iterdir()
        if version.is_dir() and ARCHIVE_VERSION_PATTERN.fullmatch(version.name)
    )


def unresolved_tasks(root: Path) -> list[str]:
    values = []
    for task_root in explore_task_paths(root):
        task_file = task_root / "task.yaml"
        status = None
        if task_file.is_file():
            task = load_yaml(task_file).get("task")
            status = task.get("status") if isinstance(task, dict) else None
        if status != "cancelled" and not task_has_archive(root, task_root.name):
            values.append(task_root.name)
    return values


def active_task(root: Path) -> Path:
    tasks = unresolved_tasks(root)
    if len(tasks) != 1:
        raise ValueError(
            "Exactly one active explore task is required; found "
            + (", ".join(tasks) if tasks else "none")
        )
    return root / "explore" / tasks[0]


def report_source_text(task_name: str, question: dict[str, str]) -> str:
    frontmatter = yaml_text(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "kind": "explore",
            "language": "zh-CN",
            "title": f"{question['id']}：{question['question']}",
            "task": task_name,
            "run_receipts": [],
        }
    ).rstrip()
    return f"""---
{frontmatter}
---

# {question["question"]}

## 研究问题

{question["question"]}

完成标准：{question["completion_criterion"]}

## 输入与方法

尚未填写

## 结果

尚未填写

## 限制

尚未填写

## 结论与下一问题

尚未填写

## 可复现信息

尚未填写
"""


def report_build_metadata(root: Path, output: Path) -> dict[str, Any]:
    manifest_path = output.with_suffix(".build.yaml")
    manifest = load_yaml(manifest_path)
    report = manifest.get("report")
    if not isinstance(report, dict):
        raise ValueError(f"Malformed report build manifest: {manifest_path}")
    metadata = report.get("source_metadata")
    if isinstance(metadata, dict):
        return metadata
    source_value = report.get("source")
    if not isinstance(source_value, str):
        raise ValueError(f"Report build manifest lacks source metadata: {manifest_path}")
    source = safe_project_path(
        root,
        source_value,
        label="report source",
        must_exist=True,
        reject_symlink=True,
    )
    metadata, _ = parse_report_source(source)
    return metadata


def task_readme_text(task_name: str, question: dict[str, str]) -> str:
    return f"""# {task_name}

## Direction

- Question ID: `{question["id"]}`
- Question: {question["question"]}
- Completion criterion: {question["completion_criterion"]}

## Inputs

{question.get("inputs") or "- 尚未填写"}

## Method

{question.get("method_reference") or "- 尚未填写"}

## Expected outputs

{question.get("expected_outputs") or "- 尚未填写"}

## Stop condition

- {question["completion_criterion"]}

## Run order

1. 尚未填写

## Observations

- 尚未填写

## Limitations

- 尚未填写

## Code contract

- code 按实际执行顺序线性组织，保留 intermediate objects 和 diagnostics。
- 优先减少函数封装和工程化代码，单次逻辑保持 inline。
- 每个 script 顶部使用中文 outline 和对应编号中文 section headings。
- 允许少量重复；不提前创建 generic helpers、classes、wrappers 或 config layers。
- HTML 仅由独立 `report-build` API 生成，不写入 analysis scripts。
"""


def analysis_script_text() -> str:
    return """# 提纲
# 1. 读取输入与参数
# 2. 执行当前问题的探索
# 3. 检查中间结果与限制
# 4. 写出 task-local 结果

# %% 1. 读取输入与参数
# 按当前问题填写只读输入、明确参数与假设。

# %% 2. 执行当前问题的探索
# 减少函数封装和工程化代码，保持单次逻辑线性可读。
# 直接显示关键 intermediate objects。

# %% 3. 检查中间结果与限制
# 输出 diagnostics、observations，并记录 interpretation boundary。

# %% 4. 写出 task-local 结果
# 仅写入 ../derived/ 或 ../figures/。
"""


def plan_explore_task(
    root: Path,
    *,
    order: int,
    core: str,
    summary: str,
) -> dict[str, Any]:
    ensure_manifest(root)
    question = current_research_question(root)
    unresolved = unresolved_tasks(root)
    if unresolved:
        raise ValueError(
            "Resolve the current explore task before starting another: "
            + ", ".join(unresolved)
        )
    task_name = normalize_task_name(order, core, summary)
    for task_root in explore_task_paths(root):
        parsed = parse_task_name(task_root.name)
        if parsed["order"] == order:
            raise ValueError(f"Task order P{order} is already used")
        document = load_yaml(task_root / "task.yaml")
        direction = document.get("direction")
        if (
            isinstance(direction, dict)
            and direction.get("question_id") == question["id"]
            and document.get("task", {}).get("status") != "cancelled"
        ):
            raise ValueError(f"Question {question['id']} already has a task")
    parsed = parse_task_name(task_name)
    task = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "task": {
            "id": f"TASK-{order:03d}",
            **parsed,
            "stage": "explore",
            "status": "ready",
        },
        "direction": {
            "question_id": question["id"],
            "question": question["question"],
            "completion_criterion": question["completion_criterion"],
            "approval": "human_confirmed_in_interaction",
        },
        "ownership": {
            "human_owned": ["QUESTIONS.md"],
            "agent_owned": [
                "README.md",
                "report.md",
                "scripts/",
                "derived/",
                "figures/",
            ],
            "cli_owned": ["task.yaml", "report.html", "report.build.yaml", "runs/"],
        },
        "code_style": {
            "style": "narrative_linear",
            "outline_language": "zh-CN",
            "outline_required": True,
            "function_policy": "extract_after_stabilization",
            "html_in_analysis_scripts": False,
        },
    }
    relative = Path("explore") / task_name
    return {
        "mode": "explore-create",
        "project": str(root),
        "task_name": task_name,
        "task_path": relative.as_posix(),
        "questions_sha256": sha256_file(root / "QUESTIONS.md"),
        "directories": [
            (relative / child).as_posix()
            for child in ("scripts", "derived", "figures", "runs")
        ],
        "task": task,
        "task_yaml": yaml_text(task),
        "readme": task_readme_text(task_name, question),
        "report_source": report_source_text(task_name, question),
        "analysis_script": analysis_script_text(),
    }


def apply_explore_task(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    ensure_manifest(root)
    if sha256_file(root / "QUESTIONS.md") != plan["questions_sha256"]:
        raise ValueError("QUESTIONS.md changed after explore planning")
    if unresolved_tasks(root):
        raise ValueError("Another unresolved task appeared after explore planning")
    task_root = root / plan["task_path"]
    if task_root.exists():
        raise FileExistsError(f"Refusing to overwrite {task_root}")
    for relative in plan["directories"]:
        (root / relative).mkdir(parents=True, exist_ok=False)
    atomic_write(task_root / "task.yaml", plan["task_yaml"])
    atomic_write(task_root / "README.md", plan["readme"])
    atomic_write(task_root / "scripts/analysis.py", plan["analysis_script"])
    build = build_report_text(
        source_text=plan["report_source"],
        source_base=task_root,
        output=task_root / "report.html",
        project_root=root,
        kind=ReportKind.EXPLORE,
    )
    event = append_lifecycle_event(
        root,
        action="explore-create",
        subject=plan["task_name"],
        result="applied",
        related_id=plan["task"]["task"]["id"],
    )
    return {
        "written": True,
        "task_path": plan["task_path"],
        "report": build.to_dict(),
        "event": event,
    }


def plan_explore_cancellation(
    root: Path,
    *,
    task_name: str,
    review_note: str,
) -> dict[str, Any]:
    ensure_manifest(root)
    if not review_note.strip():
        raise ValueError("review_note must not be empty")
    task_root = root / "explore" / task_name
    task_path = task_root / "task.yaml"
    if not task_path.is_file():
        raise ValueError(f"Missing explore task: {task_name}")
    if task_has_archive(root, task_name):
        raise ValueError("An archived task cannot be cancelled")
    document = load_yaml(task_path)
    task = document.get("task")
    if not isinstance(task, dict) or task.get("name") != task_name:
        raise ValueError(f"Malformed task manifest: {task_path}")
    if task.get("status") == "cancelled":
        raise ValueError(f"Task is already cancelled: {task_name}")
    document["task"]["status"] = "cancelled"
    document["cancellation"] = {
        "review_note": review_note.strip(),
        "cancelled_on": date.today().isoformat(),
    }
    return {
        "mode": "explore-cancel",
        "project": str(root),
        "task_name": task_name,
        "task_path": task_path.relative_to(root).as_posix(),
        "source_sha256": sha256_file(task_path),
        "task_yaml": yaml_text(document),
    }


def apply_explore_cancellation(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    path = root / plan["task_path"]
    if not path.is_file() or sha256_file(path) != plan["source_sha256"]:
        raise ValueError("Task manifest changed after cancellation planning")
    atomic_write(path, plan["task_yaml"])
    event = append_lifecycle_event(
        root,
        action="explore-cancel",
        subject=plan["task_name"],
        result="applied",
    )
    return {
        "written": True,
        "task_path": plan["task_path"],
        "event": event,
    }


def next_run_id(task_root: Path) -> str:
    today = utc_now().strftime("%Y%m%d")
    ordinals = []
    runs = task_root / "runs"
    if runs.is_dir():
        for path in runs.iterdir():
            if path.is_dir() and RUN_ID_PATTERN.fullmatch(path.name):
                if path.name.startswith(f"RUN-{today}-"):
                    ordinals.append(int(path.name.rsplit("-", 1)[1]))
    return f"RUN-{today}-{max(ordinals, default=0) + 1:03d}"


def safe_task_output(task_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ValueError(f"Output must be relative to the active task: {value}")
    return safe_project_path(
        task_root,
        candidate,
        label="output",
        reject_symlink=True,
    )


def plan_run(
    root: Path,
    *,
    inputs: list[str],
    outputs: list[str],
    cwd: str | None,
    command: list[str],
) -> dict[str, Any]:
    ensure_manifest(root)
    task_root = active_task(root)
    if not inputs:
        raise ValueError("At least one --input is required")
    if not outputs:
        raise ValueError("At least one --output is required")
    if not command:
        raise ValueError("A command is required after --")
    input_paths = [
        safe_project_path(
            root,
            value,
            label="input",
            must_exist=True,
            reject_symlink=True,
        )
        for value in inputs
    ]
    output_paths = [safe_task_output(task_root, value) for value in outputs]
    cwd_path = (
        safe_project_path(
            root,
            cwd,
            label="cwd",
            must_exist=True,
            allow_root=True,
            reject_symlink=True,
        )
        if cwd
        else task_root
    )
    if not cwd_path.is_dir():
        raise ValueError("cwd must be a directory")
    run_id = next_run_id(task_root)
    return {
        "mode": "run",
        "project": str(root),
        "task": task_root.name,
        "run_id": run_id,
        "cwd": relative_to_root(root, cwd_path),
        "inputs": [relative_to_root(root, path) for path in input_paths],
        "outputs": [path.relative_to(task_root).as_posix() for path in output_paths],
        "command": command,
        "receipt_path": (task_root / "runs" / run_id / "receipt.yaml")
        .relative_to(root)
        .as_posix(),
    }


def apply_run(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    task_root = root / "explore" / plan["task"]
    if active_task(root) != task_root:
        raise ValueError("Active task changed after the run plan was created")
    run_root = task_root / "runs" / plan["run_id"]
    if run_root.exists():
        raise FileExistsError(f"Refusing to overwrite run receipt: {run_root}")
    run_root.mkdir(parents=True, exist_ok=False)
    started = utc_text()
    environment = environment_hashes(root)
    git_before = git_status(root)
    violations: list[str] = []
    input_paths = []
    for value in plan["inputs"]:
        try:
            input_paths.append(
                safe_project_path(
                    root,
                    value,
                    label="input",
                    must_exist=True,
                    reject_symlink=True,
                )
            )
        except ValueError as error:
            violations.append(f"input preflight failed: {error}")
    output_paths = []
    for value in plan["outputs"]:
        try:
            output_paths.append(safe_task_output(task_root, value))
        except ValueError as error:
            violations.append(f"output preflight failed: {error}")
    try:
        cwd = safe_project_path(
            root,
            plan["cwd"],
            label="cwd",
            must_exist=True,
            allow_root=True,
            reject_symlink=True,
        )
    except ValueError as error:
        cwd = task_root
        violations.append(f"cwd preflight failed: {error}")

    before = []
    for path in input_paths:
        try:
            before.append(hash_path(root, path))
        except (OSError, ValueError) as error:
            violations.append(f"input hash before execution failed: {error}")

    stdout = ""
    stderr = ""
    exit_code: int | None = None
    if not violations:
        try:
            completed = subprocess.run(
                plan["command"],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except OSError as error:
            stderr = f"{type(error).__name__}: {error}\n"
            violations.append(f"command could not start: {error}")

    after = []
    for path in input_paths:
        try:
            after.append(hash_path(root, path))
        except (OSError, ValueError) as error:
            violations.append(f"input hash after execution failed: {error}")
    if stable_json(before) != stable_json(after):
        violations.append("declared inputs changed during execution")
    output_records = []
    for path in output_paths:
        if not path.exists():
            violations.append(
                f"declared output is missing: {path.relative_to(task_root)}"
            )
            continue
        try:
            output_records.append(hash_path(root, path))
        except (OSError, ValueError) as error:
            violations.append(f"output validation failed: {error}")
    if exit_code not in {None, 0}:
        violations.append(f"command exited with code {exit_code}")
    status = "success" if not violations else "violation"
    atomic_write(run_root / "stdout.log", stdout)
    atomic_write(run_root / "stderr.log", stderr)
    receipt = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run": {
            "id": plan["run_id"],
            "task": plan["task"],
            "status": status,
            "started_at": started,
            "finished_at": utc_text(),
            "cwd": plan["cwd"],
            "command": plan["command"],
            "exit_code": exit_code,
        },
        "inputs_before": before,
        "inputs_after": after,
        "outputs": output_records,
        "provenance": {
            "git_before": git_before,
            "git_after": git_status(root),
            "environment": environment,
            "environment_after": environment_hashes(root),
        },
        "logs": {
            "stdout": {
                "path": "stdout.log",
                "size": (run_root / "stdout.log").stat().st_size,
                "sha256": sha256_file(run_root / "stdout.log"),
            },
            "stderr": {
                "path": "stderr.log",
                "size": (run_root / "stderr.log").stat().st_size,
                "sha256": sha256_file(run_root / "stderr.log"),
            },
        },
        "violations": violations,
    }
    atomic_write(run_root / "receipt.yaml", yaml_text(receipt))
    event = append_lifecycle_event(
        root,
        action="run",
        subject=plan["task"],
        result=status,
        related_id=plan["run_id"],
    )
    return {
        "written": True,
        "status": status,
        "exit_code": exit_code,
        "violations": violations,
        "receipt_path": plan["receipt_path"],
        "event": event,
    }


def validate_run_receipts(root: Path, task_root: Path) -> dict[str, Any]:
    errors = []
    receipts = []
    runs = task_root / "runs"
    for run_root in sorted(runs.iterdir()) if runs.is_dir() else []:
        if not run_root.is_dir() or RUN_ID_PATTERN.fullmatch(run_root.name) is None:
            errors.append(f"Invalid run directory: {run_root}")
            continue
        receipt_path = run_root / "receipt.yaml"
        if not receipt_path.is_file():
            errors.append(f"Missing run receipt: {receipt_path}")
            continue
        try:
            receipt = load_yaml(receipt_path)
            run = receipt.get("run")
            if receipt.get("schema_version") != RUN_SCHEMA_VERSION:
                errors.append(f"Unsupported run schema: {receipt_path}")
            if (
                not isinstance(run, dict)
                or run.get("id") != run_root.name
                or run.get("status") != "success"
            ):
                errors.append(f"Run is not successful: {receipt_path}")
            if receipt.get("violations"):
                errors.append(f"Run contains violations: {receipt_path}")
            inputs_before = receipt.get("inputs_before")
            inputs_after = receipt.get("inputs_after")
            if not isinstance(inputs_before, list) or not isinstance(
                inputs_after,
                list,
            ):
                errors.append(f"Run input hashes are malformed: {receipt_path}")
                inputs_after = []
            elif stable_json(inputs_before) != stable_json(inputs_after):
                errors.append(f"Run inputs changed during execution: {receipt_path}")
            for input_record in inputs_after:
                if not isinstance(input_record, dict) or not isinstance(
                    input_record.get("path"),
                    str,
                ):
                    errors.append(f"Malformed run input: {receipt_path}")
                    continue
                path = safe_project_path(
                    root,
                    input_record["path"],
                    label="run input",
                    must_exist=True,
                    reject_symlink=True,
                )
                if hash_path(root, path) != input_record:
                    errors.append(f"Run input changed after execution: {path}")
            outputs = receipt.get("outputs")
            if not isinstance(outputs, list):
                errors.append(f"Run outputs are malformed: {receipt_path}")
                outputs = []
            for output in outputs:
                if not isinstance(output, dict) or not isinstance(
                    output.get("path"), str
                ):
                    errors.append(f"Malformed run output: {receipt_path}")
                    continue
                path = safe_project_path(
                    root,
                    output["path"],
                    label="run output",
                    must_exist=True,
                    reject_symlink=True,
                )
                if not path.is_relative_to(task_root):
                    errors.append(f"Run output is outside its task: {path}")
                if hash_path(root, path) != output:
                    errors.append(f"Run output changed: {path}")
            logs = receipt.get("logs")
            if not isinstance(logs, dict):
                errors.append(f"Run logs are malformed: {receipt_path}")
            else:
                for stream in ("stdout", "stderr"):
                    record = logs.get(stream)
                    if not isinstance(record, dict) or not isinstance(
                        record.get("path"),
                        str,
                    ):
                        errors.append(f"Run {stream} log is malformed: {receipt_path}")
                        continue
                    if record["path"] != f"{stream}.log":
                        errors.append(
                            f"Run {stream} log path is invalid: {receipt_path}"
                        )
                        continue
                    log_path = run_root / record["path"]
                    if (
                        not log_path.is_file()
                        or record.get("size") != log_path.stat().st_size
                        or record.get("sha256") != sha256_file(log_path)
                    ):
                        errors.append(f"Run {stream} log changed: {log_path}")
            receipts.append(receipt_path.relative_to(task_root).as_posix())
        except (OSError, ValueError) as error:
            errors.append(str(error))
    if not receipts:
        errors.append(f"Task has no audited run receipts: {task_root.name}")
    return {"ok": not errors, "errors": errors, "receipts": receipts}


def readme_completion_errors(task_root: Path) -> list[str]:
    path = task_root / "README.md"
    if not path.is_file():
        return [f"Missing task README: {path}"]
    text = path.read_text(encoding="utf-8")
    errors = []
    for heading in (
        "Inputs",
        "Method",
        "Expected outputs",
        "Stop condition",
        "Run order",
        "Observations",
        "Limitations",
    ):
        section = parse_markdown_section(text, heading)
        if not section:
            errors.append(f"Task README lacks section: {heading}")
        elif any(marker.lower() in section.lower() for marker in PLACEHOLDERS):
            errors.append(f"Task README section is incomplete: {heading}")
    return errors


def script_contract_errors(script_roots: list[Path]) -> list[str]:
    errors = []
    scripts = sorted(
        path
        for root in script_roots
        if root.exists()
        for path in ([root] if root.is_file() else root.rglob("*"))
        if path.is_file() and path.suffix.lower() in SCRIPT_SUFFIXES
    )
    if not scripts:
        return ["No executable .py, .r, or .sh scripts were found"]
    for path in scripts:
        text = path.read_text(encoding="utf-8")
        top = "\n".join(text.splitlines()[:20])
        if "提纲" not in top:
            errors.append(f"Script lacks a top Chinese outline: {path}")
        section_lines = [
            line
            for line in text.splitlines()
            if re.match(r"^#\s*(?:%%|----)?\s*1\.", line)
        ]
        if not section_lines or not CHINESE_PATTERN.search(section_lines[0]):
            errors.append(f"Script lacks a numbered Chinese section: {path}")
        if REPORTING_LOGIC_PATTERN.search(text):
            errors.append(f"Script contains forbidden report rendering logic: {path}")
    return errors


def next_archive_version(root: Path, task_name: str) -> str:
    parent = root / "archive" / task_name
    values = (
        [
            int(path.name[1:])
            for path in parent.iterdir()
            if path.is_dir() and ARCHIVE_VERSION_PATTERN.fullmatch(path.name)
        ]
        if parent.is_dir()
        else []
    )
    return f"v{max(values, default=0) + 1:03d}"


def plan_archive_promotion(
    root: Path,
    *,
    task_name: str,
    review_note: str,
) -> dict[str, Any]:
    ensure_manifest(root)
    if not review_note.strip():
        raise ValueError("review_note must not be empty")
    task_root = root / "explore" / task_name
    if not task_root.is_dir():
        raise ValueError(f"Missing explore task: {task_name}")
    task = load_yaml(task_root / "task.yaml")
    if task.get("task", {}).get("status") == "cancelled":
        raise ValueError("A cancelled task cannot be archived")
    errors = readme_completion_errors(task_root)
    errors.extend(script_contract_errors([task_root / "scripts"]))
    receipt_check = validate_run_receipts(root, task_root)
    errors.extend(receipt_check["errors"])
    report_check = validate_report(
        output=task_root / "report.html",
        project_root=root,
        kind=ReportKind.EXPLORE,
        require_complete=True,
    )
    errors.extend(report_check["errors"])
    if not errors:
        metadata = report_build_metadata(root, task_root / "report.html")
        if metadata.get("task") != task_name:
            errors.append("Report task does not match the explore task")
        declared = set(str(value) for value in metadata.get("run_receipts", []))
        actual = {
            f"runs/{value}" if not value.startswith("runs/") else value
            for value in receipt_check["receipts"]
        }
        if declared != actual:
            errors.append("Report run_receipts do not match audited task receipts")
    if errors:
        raise ValueError("; ".join(errors))
    version = next_archive_version(root, task_name)
    selector = f"{task_name}@{version}"
    records = file_records(task_root)
    manifest = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "snapshot": {
            "selector": selector,
            "task": task_name,
            "task_id": task.get("task", {}).get("id"),
            "question_id": task.get("direction", {}).get("question_id"),
            "version": version,
            "created_on": date.today().isoformat(),
            "git_commit": git_commit(root),
        },
        "review": {
            "status": "human_approved",
            "note": review_note.strip(),
        },
        "files": records,
    }
    return {
        "mode": "archive-promote",
        "project": str(root),
        "task_name": task_name,
        "selector": selector,
        "source_path": task_root.relative_to(root).as_posix(),
        "archive_path": f"archive/{task_name}/{version}",
        "source_files": records,
        "manifest": manifest,
        "manifest_yaml": yaml_text(manifest),
    }


def apply_archive_promotion(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    source = root / plan["source_path"]
    destination = root / plan["archive_path"]
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite archive: {destination}")
    if file_records(source) != plan["source_files"]:
        raise ValueError("Explore task changed after archive planning")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_parent = Path(
        tempfile.mkdtemp(prefix=".archive-", dir=destination.parent)
    )
    try:
        snapshot = temporary_parent / destination.name
        shutil.copytree(source, snapshot)
        atomic_write(snapshot / "archive_manifest.yaml", plan["manifest_yaml"])
        snapshot.replace(destination)
    finally:
        shutil.rmtree(temporary_parent, ignore_errors=True)
    event = append_lifecycle_event(
        root,
        action="archive-promote",
        subject=plan["task_name"],
        result="applied",
        related_id=plan["selector"],
    )
    return {
        "written": True,
        "selector": plan["selector"],
        "archive_path": plan["archive_path"],
        "event": event,
    }


def release_report_source(selectors: list[str]) -> str:
    frontmatter = yaml_text(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "kind": "release",
            "language": "zh-CN",
            "title": "项目正式报告",
            "snapshots": selectors,
            "run_receipts": [],
        }
    ).rstrip()
    return f"""---
{frontmatter}
---

# 项目正式报告

## 项目目的

尚未填写

## 输入与方法

尚未填写

## 主要结果

尚未填写

## 限制

尚未填写

## 结论

尚未填写

## 可复现信息

尚未填写
"""


def plan_pipeline_creation(root: Path, *, selectors: list[str]) -> dict[str, Any]:
    ensure_manifest(root)
    if not selectors:
        raise ValueError("At least one archive snapshot is required")
    pipeline_path = root / "pipeline/pipeline.yaml"
    if pipeline_path.exists():
        raise FileExistsError("pipeline/pipeline.yaml already exists")
    sources = []
    source_verifications = []
    steps = []
    orders = set()
    for selector in selectors:
        verification = verify_archive_snapshot(root, selector)
        if not verification["ok"]:
            raise ValueError("; ".join(verification["errors"]))
        task_name = selector.rsplit("@", 1)[0]
        parsed = parse_task_name(task_name)
        if parsed["order"] in orders:
            raise ValueError(f"Duplicate pipeline order P{parsed['order']}")
        orders.add(parsed["order"])
        sources.append(
            {
                "selector": selector,
                "manifest_sha256": verification["manifest_sha256"],
            }
        )
        source_verifications.append(
            {
                "selector": selector,
                "manifest_sha256": verification["manifest_sha256"],
            }
        )
        steps.append(
            {
                "order": parsed["order"],
                "core": parsed["core"],
                "derived_from": selector,
                "implementation": None,
            }
        )
    pipeline = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "pipeline": {
            "status": "candidate",
            "entrypoint": None,
            "runtime_independent_from": ["explore", "archive"],
        },
        "code_style": {
            "outline_language": "zh-CN",
            "outline_required": True,
        },
        "sources": sources,
        "steps": sorted(steps, key=lambda value: value["order"]),
    }
    return {
        "mode": "pipeline-create",
        "project": str(root),
        "selectors": selectors,
        "source_verifications": source_verifications,
        "directories": ["pipeline/src", "pipeline/config", "pipeline/tests"],
        "pipeline_yaml": yaml_text(pipeline),
        "report_source": release_report_source(selectors),
    }


def apply_pipeline_creation(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    path = root / "pipeline/pipeline.yaml"
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    for planned in plan["source_verifications"]:
        selector = planned["selector"]
        verification = verify_archive_snapshot(root, selector)
        if not verification["ok"]:
            raise ValueError("; ".join(verification["errors"]))
        if verification["manifest_sha256"] != planned["manifest_sha256"]:
            raise ValueError(f"Archive changed after pipeline planning: {selector}")
    for relative in plan["directories"]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    atomic_write(path, plan["pipeline_yaml"])
    event = append_lifecycle_event(
        root,
        action="pipeline-create",
        subject="pipeline",
        result="applied",
    )
    return {
        "written": True,
        "pipeline_path": "pipeline/pipeline.yaml",
        "report_template_sha256": sha256_text(plan["report_source"]),
        "event": event,
    }


def pipeline_runtime_errors(root: Path, files: list[Path]) -> list[str]:
    forbidden = re.compile(
        r"(?<![A-Za-z0-9_-])(?:\.\./)*(?:explore|archive)/",
        re.IGNORECASE,
    )
    errors = []
    for path in files:
        if path.suffix.lower() not in {
            ".json",
            ".md",
            ".py",
            ".r",
            ".sh",
            ".toml",
            ".yaml",
            ".yml",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if forbidden.search(text):
            errors.append(f"Pipeline runtime references explore/archive: {path}")
    return errors


def pipeline_runtime_files(root: Path, explicit: list[Path]) -> list[Path]:
    files = {path for path in explicit if path.is_file()}
    for relative in ("pipeline/src", "pipeline/config"):
        directory = root / relative
        if directory.is_dir():
            files.update(path for path in directory.rglob("*") if path.is_file())
    return sorted(files)


def plan_pipeline_release(
    root: Path,
    *,
    report: str,
    review_note: str,
) -> dict[str, Any]:
    ensure_manifest(root)
    if not review_note.strip():
        raise ValueError("review_note must not be empty")
    release_path = root / "pipeline/release.yaml"
    if release_path.exists():
        raise FileExistsError("pipeline/release.yaml already exists")
    pipeline_path = root / "pipeline/pipeline.yaml"
    if not pipeline_path.is_file():
        raise ValueError("Missing pipeline/pipeline.yaml")
    pipeline = load_yaml(pipeline_path)
    entrypoint = pipeline.get("pipeline", {}).get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        raise ValueError("pipeline.entrypoint must be set before release")
    entrypoint_path = safe_project_path(
        root,
        f"pipeline/{entrypoint}",
        label="pipeline entrypoint",
        must_exist=True,
        reject_symlink=True,
    )
    if not entrypoint_path.is_file():
        raise ValueError("pipeline.entrypoint must name a regular file")
    implementations = []
    for step in pipeline.get("steps", []):
        value = step.get("implementation") if isinstance(step, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Every pipeline step requires implementation")
        implementations.append(
            safe_project_path(
                root,
                f"pipeline/{value}",
                label="pipeline implementation",
                must_exist=True,
                reject_symlink=True,
            )
        )
    if any(not path.is_file() for path in implementations):
        raise ValueError("Every pipeline implementation must be a regular file")
    runtime_errors = pipeline_runtime_errors(
        root,
        pipeline_runtime_files(root, [entrypoint_path, *implementations]),
    )
    if runtime_errors:
        raise ValueError("; ".join(runtime_errors))
    style_errors = script_contract_errors(
        pipeline_runtime_files(root, [entrypoint_path, *implementations])
    )
    if style_errors:
        raise ValueError("; ".join(style_errors))
    report_path = safe_project_path(
        root,
        report,
        label="release report",
        must_exist=True,
        reject_symlink=True,
    )
    if not report_path.is_relative_to(root / "reports"):
        raise ValueError("Release report must be inside reports/")
    report_check = validate_report(
        output=report_path,
        project_root=root,
        kind=ReportKind.RELEASE,
        require_complete=True,
    )
    if not report_check["ok"]:
        raise ValueError("; ".join(report_check["errors"]))
    sources = pipeline.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Pipeline requires archive sources")
    source_selectors = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Pipeline source must be a mapping")
        selector = source.get("selector")
        verification = verify_archive_snapshot(root, str(selector))
        if not verification["ok"]:
            raise ValueError("; ".join(verification["errors"]))
        if source.get("manifest_sha256") != verification["manifest_sha256"]:
            raise ValueError(f"Pipeline source manifest changed: {selector}")
        source_selectors.append(str(selector))
    report_metadata = report_build_metadata(root, report_path)
    if report_metadata.get("snapshots") != source_selectors:
        raise ValueError("Release report snapshots do not match pipeline sources")
    pipeline_records = file_records(root / "pipeline", exclude={"release.yaml"})
    release = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "release": {
            "status": "release-ready",
            "created_on": date.today().isoformat(),
            "review_note": review_note.strip(),
            "git_commit": git_commit(root),
            "report": relative_to_root(root, report_path),
            "report_sha256": sha256_file(report_path),
        },
        "sources": sources,
        "pipeline_files": pipeline_records,
    }
    return {
        "mode": "pipeline-release",
        "project": str(root),
        "release_path": "pipeline/release.yaml",
        "release": release,
        "release_yaml": yaml_text(release),
    }


def apply_pipeline_release(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    path = root / plan["release_path"]
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    current = file_records(root / "pipeline", exclude={"release.yaml"})
    if current != plan["release"]["pipeline_files"]:
        raise ValueError("Pipeline changed after release planning")
    for source in plan["release"]["sources"]:
        verification = verify_archive_snapshot(root, source["selector"])
        if not verification["ok"]:
            raise ValueError("; ".join(verification["errors"]))
        if verification["manifest_sha256"] != source["manifest_sha256"]:
            raise ValueError(
                f"Archive changed after release planning: {source['selector']}"
            )
    report = safe_project_path(
        root,
        plan["release"]["release"]["report"],
        label="release report",
        must_exist=True,
        reject_symlink=True,
    )
    if sha256_file(report) != plan["release"]["release"]["report_sha256"]:
        raise ValueError("Release report changed after planning")
    report_check = validate_report(
        output=report,
        project_root=root,
        kind=ReportKind.RELEASE,
        require_complete=True,
    )
    if not report_check["ok"]:
        raise ValueError("; ".join(report_check["errors"]))
    atomic_write(path, plan["release_yaml"])
    event = append_lifecycle_event(
        root,
        action="pipeline-release",
        subject="pipeline",
        result="applied",
        related_id=sha256_file(path)[:16],
    )
    return {"written": True, "release_path": plan["release_path"], "event": event}


def verify_pipeline_release(root: Path) -> dict[str, Any]:
    path = root / "pipeline/release.yaml"
    if not path.is_file():
        return {"ok": True, "released": False, "errors": []}
    errors = []
    try:
        release = load_yaml(path)
        if release.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
            errors.append(f"Unsupported release schema: {path}")
        expected = release.get("pipeline_files")
        if not isinstance(expected, list):
            errors.append("Release pipeline_files must be a list")
            expected = []
        actual = file_records(root / "pipeline", exclude={"release.yaml"})
        if expected != actual:
            errors.append("Pipeline changed after release")
        info = release.get("release")
        if not isinstance(info, dict):
            errors.append("Release metadata must be a mapping")
        else:
            report = safe_project_path(
                root,
                str(info.get("report", "")),
                label="release report",
                must_exist=True,
                reject_symlink=True,
            )
            if info.get("report_sha256") != sha256_file(report):
                errors.append("Release report changed")
            report_check = validate_report(
                output=report,
                project_root=root,
                kind=ReportKind.RELEASE,
                require_complete=True,
            )
            errors.extend(report_check["errors"])
        sources = release.get("sources")
        if not isinstance(sources, list):
            errors.append("Release sources must be a list")
            sources = []
        for source in sources:
            if not isinstance(source, dict):
                errors.append("Release source must be a mapping")
                continue
            selector = source.get("selector")
            verification = verify_archive_snapshot(root, str(selector))
            errors.extend(verification["errors"])
            if source.get("manifest_sha256") != verification.get("manifest_sha256"):
                errors.append(f"Release source manifest changed: {selector}")
    except (OSError, ValueError) as error:
        errors.append(str(error))
    return {"ok": not errors, "released": True, "errors": errors}
