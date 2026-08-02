"""Command-line interface for Research Project OS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .audit import audit_project, inspect_project
from .core import (
    RELEASE_VERSION,
    append_lifecycle_event,
    project_root,
    relative_to_root,
    safe_project_path,
    sha256_text,
)
from .handoff import apply_close, plan_close, start_context
from .lifecycle import (
    apply_archive_promotion,
    apply_explore_cancellation,
    apply_explore_task,
    apply_pipeline_creation,
    apply_pipeline_release,
    apply_run,
    plan_archive_promotion,
    plan_explore_cancellation,
    plan_explore_task,
    plan_pipeline_creation,
    plan_pipeline_release,
    plan_run,
    verify_archive_snapshot,
)
from .reporting import (
    ReportKind,
    build_report,
    build_report_text,
    reject_immutable_report_output,
)
from .scaffold import (
    apply_scaffold,
    plan_scaffold,
    plan_to_dict,
)


def add_project(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path, default=Path("."))


def add_apply_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=RELEASE_VERSION)
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("inspect", "start", "audit"):
        command = commands.add_parser(name)
        add_project(command)
        command.add_argument("--json", action="store_true")

    for name in ("init", "adopt"):
        command = commands.add_parser(name)
        add_project(command)
        add_apply_json(command)
        command.add_argument("--overwrite", action="store_true")
        command.add_argument("--init-git", action="store_true")

    close = commands.add_parser("close")
    add_project(close)
    add_apply_json(close)
    close.add_argument("--summary", required=True)
    close.add_argument("--completed", action="append", default=[])
    close.add_argument("--output", action="append", default=[])
    close.add_argument("--next-step", required=True)
    close.add_argument("--owner", default="unassigned")
    close.add_argument("--overwrite", action="store_true")

    explore = commands.add_parser("explore-create")
    add_project(explore)
    add_apply_json(explore)
    explore.add_argument("--order", type=int, required=True)
    explore.add_argument("--core", required=True)
    explore.add_argument("--summary", required=True)

    cancel = commands.add_parser("explore-cancel")
    add_project(cancel)
    add_apply_json(cancel)
    cancel.add_argument("--task", required=True)
    cancel.add_argument("--review-note", required=True)

    run = commands.add_parser("run")
    add_project(run)
    add_apply_json(run)
    run.add_argument("--input", action="append", required=True)
    run.add_argument("--output", action="append", required=True)
    run.add_argument("--cwd")
    run.add_argument("run_command", nargs=argparse.REMAINDER)

    report = commands.add_parser("report-build")
    add_project(report)
    add_apply_json(report)
    report_source = report.add_mutually_exclusive_group(required=True)
    report_source.add_argument("--source")
    report_source.add_argument("--stdin", action="store_true")
    report.add_argument("--source-base")
    report.add_argument("--output", required=True)
    report.add_argument(
        "--kind", choices=[value.value for value in ReportKind], required=True
    )
    report.add_argument("--asset-mode", choices=("embed", "relative"), default="embed")

    promote = commands.add_parser("archive-promote")
    add_project(promote)
    add_apply_json(promote)
    promote.add_argument("--task", required=True)
    promote.add_argument("--review-note", required=True)

    verify = commands.add_parser("archive-verify")
    add_project(verify)
    verify.add_argument("--snapshot", required=True)
    verify.add_argument("--json", action="store_true")

    pipeline = commands.add_parser("pipeline-create")
    add_project(pipeline)
    add_apply_json(pipeline)
    pipeline.add_argument("--snapshot", action="append", required=True)

    release = commands.add_parser("pipeline-release")
    add_project(release)
    add_apply_json(release)
    release.add_argument("--report", required=True)
    release.add_argument("--review-note", required=True)
    return parser.parse_args(arguments)


def serializable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def emit(value: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, default=serializable))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"context", "task", "pipeline_yaml", "report_source"}:
                continue
            if isinstance(item, (dict, list)):
                print(
                    f"{key}: {json.dumps(item, ensure_ascii=False, default=serializable)}"
                )
            else:
                print(f"{key}: {item}")
    else:
        print(value)


def mutation_result(
    plan: dict[str, Any],
    applied: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "mode": plan["mode"],
        "dry_run": applied is None,
        "plan": plan,
        "applied": applied,
    }


def main(arguments: list[str] | None = None) -> None:
    args = parse_args(arguments)
    root = project_root(args.project)
    try:
        if args.command == "inspect":
            emit(inspect_project(root), as_json=args.json)
            return
        if args.command == "start":
            value = start_context(root)
            if args.json:
                emit(value, as_json=True)
            else:
                print("# Context pack")
                for path, content in value["context"].items():
                    print(f"\n## {path}\n\n{content.rstrip()}")
                if value["active_task"]:
                    print(
                        "\n## Active task\n\n"
                        + json.dumps(
                            value["active_task"],
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                print("\n## Git\n\n" + (value["git"]["output"] or "unavailable"))
            return
        if args.command == "audit":
            value = audit_project(root)
            emit(value, as_json=args.json)
            if not value["ok"]:
                raise SystemExit(1)
            return
        if args.command in {"init", "adopt"}:
            plan = plan_scaffold(
                root,
                args.command,
                overwrite=args.overwrite,
            )
            applied = (
                apply_scaffold(plan, init_git=args.init_git) if args.apply else None
            )
            rendered = mutation_result(plan_to_dict(plan), applied)
            emit(rendered, as_json=args.json)
            return
        if args.command == "close":
            plan = plan_close(
                root,
                summary=args.summary,
                completed=args.completed,
                outputs=args.output,
                next_step=args.next_step,
                owner=args.owner,
            )
            applied = (
                apply_close(plan, overwrite=args.overwrite) if args.apply else None
            )
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        if args.command == "explore-create":
            plan = plan_explore_task(
                root,
                order=args.order,
                core=args.core,
                summary=args.summary,
            )
            applied = apply_explore_task(plan) if args.apply else None
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        if args.command == "explore-cancel":
            plan = plan_explore_cancellation(
                root,
                task_name=args.task,
                review_note=args.review_note,
            )
            applied = apply_explore_cancellation(plan) if args.apply else None
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        if args.command == "run":
            command = list(args.run_command)
            if command and command[0] == "--":
                command = command[1:]
            plan = plan_run(
                root,
                inputs=args.input,
                outputs=args.output,
                cwd=args.cwd,
                command=command,
            )
            applied = apply_run(plan) if args.apply else None
            emit(mutation_result(plan, applied), as_json=args.json)
            if applied and applied["status"] != "success":
                raise SystemExit(1)
            return
        if args.command == "report-build":
            output = safe_project_path(root, args.output, label="report output")
            reject_immutable_report_output(root, output)
            source = None
            source_text = None
            source_base = None
            if args.stdin:
                source_text = sys.stdin.read()
                if not source_text.strip():
                    raise ValueError("--stdin requires non-empty Markdown input")
                source_base = safe_project_path(
                    root,
                    args.source_base or output.parent,
                    label="report source base",
                    must_exist=True,
                    allow_root=True,
                    allow_absolute=True,
                    reject_symlink=True,
                )
            else:
                if args.source_base is not None:
                    raise ValueError("--source-base is only valid with --stdin")
                source = safe_project_path(
                    root,
                    args.source,
                    label="report source",
                    must_exist=True,
                )
            plan = {
                "mode": "report-build",
                "project": str(root),
                "source_mode": "inline" if args.stdin else "markdown",
                "source": relative_to_root(root, source) if source else None,
                "source_base": (
                    relative_to_root(root, source_base) if source_base else None
                ),
                "source_sha256": (
                    sha256_text(source_text) if source_text is not None else None
                ),
                "output": relative_to_root(root, output),
                "kind": args.kind,
                "asset_mode": args.asset_mode,
            }
            applied = None
            if args.apply:
                if source_text is not None and source_base is not None:
                    build = build_report_text(
                        source_text=source_text,
                        source_base=source_base,
                        output=output,
                        project_root=root,
                        kind=ReportKind(args.kind),
                        asset_mode=args.asset_mode,
                    )
                elif source is not None:
                    build = build_report(
                        source=source,
                        output=output,
                        project_root=root,
                        kind=ReportKind(args.kind),
                        asset_mode=args.asset_mode,
                    )
                else:
                    raise ValueError("Report source is required")
                event = append_lifecycle_event(
                    root,
                    action="report-build",
                    subject=build.output,
                    result="applied",
                    related_id=build.output_sha256[:16],
                )
                applied = {**build.to_dict(), "event": event}
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        if args.command == "archive-promote":
            plan = plan_archive_promotion(
                root,
                task_name=args.task,
                review_note=args.review_note,
            )
            applied = apply_archive_promotion(plan) if args.apply else None
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        if args.command == "archive-verify":
            value = verify_archive_snapshot(root, args.snapshot)
            emit(value, as_json=args.json)
            if not value["ok"]:
                raise SystemExit(1)
            return
        if args.command == "pipeline-create":
            plan = plan_pipeline_creation(root, selectors=args.snapshot)
            applied = apply_pipeline_creation(plan) if args.apply else None
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        if args.command == "pipeline-release":
            plan = plan_pipeline_release(
                root,
                report=args.report,
                review_note=args.review_note,
            )
            applied = apply_pipeline_release(plan) if args.apply else None
            emit(mutation_result(plan, applied), as_json=args.json)
            return
        raise AssertionError(f"Unhandled command: {args.command}")
    except (FileExistsError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
