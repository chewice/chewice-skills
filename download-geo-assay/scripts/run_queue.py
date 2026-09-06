#!/usr/bin/env python3
"""Run one assay's GSM queue, parking local failures and releasing Mode B units."""
from __future__ import annotations

import argparse
import fcntl
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from project_layout import policy_for_gsm, read_release_states, read_tsv, write_tsv_atomic

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--modality', required=True)
    parser.add_argument('--convert-script', type=Path, help='Reviewed bash script receiving root and GSM; writes conversion provenance')
    parser.add_argument('--pilot', type=int, default=0, help='Process only N pending GSMs; never denotes full completion')
    args = parser.parse_args()
    if args.pilot < 0 or not re.fullmatch(r'[A-Za-z0-9_]+', args.modality):
        parser.error('Invalid modality or pilot count')
    root = args.root.resolve()
    routing = read_tsv(root / 'metadata/assay_routing.tsv')
    selected = [row for row in routing if row.get('modality') == args.modality]
    if not selected or len({row.get('workflow') for row in selected}) != 1:
        parser.error('Complete detect_assay.py routing for one workflow/modality first')
    if any(row.get('raw_file_type') in {'CEL', 'IDAT'} for row in selected):
        parser.error('Array units use download_geo_supplement.py in a separate queue')
    gsms = {row['gsm'] for row in selected}
    rows = read_tsv(root / 'metadata/source_manifest.tsv')
    units = defaultdict(list)
    for row in rows:
        if row.get('gsm') in gsms:
            units[row['gsm']].append(row['srr'])
    if set(units) != gsms:
        parser.error('Source manifest does not cover every selected GSM')
    if any(not re.fullmatch(r'GSM\d+', gsm) or any(not re.fullmatch(r'(?:[SED]RR|CRR)\d+', run) for run in runs) for gsm, runs in units.items()):
        parser.error('Invalid GSM/run accession')
    policies = {gsm: policy_for_gsm(root, gsm) for gsm in units}
    mode_b = {gsm for gsm, policy in policies.items() if policy['retain_raw_files'] == 'false'}
    conversion_units = {gsm for gsm, policy in policies.items() if policy['final_product'] in {'gene_count_matrix', 'matrix_10x', 'matrix_velocity'}}
    converter = args.convert_script.resolve() if args.convert_script else None
    if (mode_b or conversion_units) and converter is None:
        parser.error('Requested standard products require a reviewed --convert-script before any downloads')
    if converter:
        subprocess.run(['bash', '-n', str(converter)], check=True)
    status_dir = root / 'reports/status'
    status_dir.mkdir(parents=True, exist_ok=True)
    # One sequencing queue per GSE also serializes STAR and shared audit files.
    with (status_dir / 'queue.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Another sequencing queue is active for this project')
        return execute(root, units, mode_b, converter, args.modality, args.pilot, conversion_units)


def execute(root, units, mode_b, converter, modality, pilot, conversion_units=None):
    conversion_units = mode_b if conversion_units is None else conversion_units
    outcomes = []
    output = root / f'reports/queue_{modality}.tsv'
    fields = ['gsm', 'status', 'failed_run', 'message']
    released = {row['gsm'] for row in read_release_states(root) if row['release_status'] == 'released'}
    attempted = 0

    def record(gsm, status, run='', message=''):
        outcomes.append(dict(gsm=gsm, status=status, failed_run=run, message=message))
        write_tsv_atomic(output, fields, outcomes)
        print(f'gsm={gsm} status={status} run={run} {message}', flush=True)

    def call(script, *extra):
        return subprocess.run([sys.executable, str(HERE / script), '--root', str(root), *extra]).returncode

    for gsm, runs in units.items():
        if (root / f'reports/release_journals/{gsm}.json').is_file() and gsm not in released:
            if call('apply_storage_policy.py', '--gsm', gsm, '--confirm-delete') == 0:
                record(gsm, 'release_resumed')
            else:
                record(gsm, 'parked', message='Interrupted release needs review')
            continue
        if gsm in released:
            from publish_sample import verify_delivery
            try:
                verify_delivery(root, gsm)
                delivery_ok = True
            except (ValueError, OSError):
                delivery_ok = False
            if delivery_ok and call('audit_processed_outputs.py', '--gsm', gsm) == 0:
                record(gsm, 'skip_released')
            else:
                record(gsm, 'parked', message='Released product no longer passes audit; manual recovery required')
            continue
        if pilot and attempted >= pilot:
            record(gsm, 'not_started', message='pilot limit')
            continue
        terminal = []
        for run in runs:
            state_path = root / f'reports/status/{run}.transfer.json'
            state = json.loads(state_path.read_text()) if state_path.is_file() else {}
            if state.get('status') == 'terminal_failed':
                terminal.append(run)
        if terminal:
            record(gsm, 'parked', ';'.join(terminal), 'terminal_failed requires manual review')
            continue
        attempted += 1
        if call('audit_manifest.py', '--manifest', str(root / 'metadata/source_manifest.tsv'), '--gsm', gsm):
            record(gsm, 'blocked', message='Preflight failed; queue paused')
            return 2
        print(f'gsm_start={gsm}', flush=True)
        # A bare ReadsPerGene file never suffices to skip downloading or to delete raw.
        if gsm in conversion_units and call('audit_processed_outputs.py', '--gsm', gsm) == 0:
            if call('publish_sample.py', '--gsm', gsm):
                record(gsm, 'parked', message='Open-format sample publication failed')
                continue
            if gsm not in mode_b or call('apply_storage_policy.py', '--gsm', gsm, '--confirm-delete') == 0:
                record(gsm, 'skip_processed_released' if gsm in mode_b else 'skip_processed')
                continue
            record(gsm, 'parked', message='Existing output release gate failed')
            continue
        failed = False
        for run in runs:
            state_path = root / f'reports/status/{run}.transfer.json'
            state = json.loads(state_path.read_text()) if state_path.is_file() else {}
            if state.get('status') == 'terminal_failed':
                record(gsm, 'parked', run, 'terminal_failed requires manual review')
                failed = True
                break
            rc = subprocess.run(['bash', str(HERE / 'download_run.sh'), str(root), run]).returncode
            if rc:
                state = json.loads(state_path.read_text()) if state_path.is_file() else {}
                if rc != 2 and state.get('status') == 'terminal_failed' and state.get('error_class') != 'disk_or_conversion':
                    record(gsm, 'parked', run, 'terminal_failed; raw preserved')
                    failed = True
                    break
                record(gsm, 'blocked', run, f'exit={rc}; inspect local state, syntax, lock or storage')
                return 2
        if failed:
            continue
        if gsm in conversion_units:
            if call('artifact_integrity.py', '--gsm', gsm):
                record(gsm, 'parked', message='Input integrity/role verification failed')
                continue
            rc = subprocess.run(['bash', str(converter), str(root), gsm]).returncode
            if rc == 2:
                record(gsm, 'blocked', message='Conversion exit=2; inspect script before restarting')
                return 2
            if rc or call('audit_processed_outputs.py', '--gsm', gsm):
                record(gsm, 'parked', message='Conversion/audit failed; raw preserved')
                continue
            if call('publish_sample.py', '--gsm', gsm):
                record(gsm, 'parked', message='Open-format sample publication failed')
                continue
            if gsm in mode_b and call('apply_storage_policy.py', '--gsm', gsm, '--confirm-delete'):
                record(gsm, 'parked', message='Release gate failed; raw preserved')
                continue
        record(gsm, 'done')
    parked = sum(row['status'] == 'parked' for row in outcomes)
    remaining = sum(row['status'] == 'not_started' for row in outcomes)
    phase = 'pilot_done' if pilot else ('queue_finished_with_failures' if parked else 'queue_complete')
    print(f'{phase}: parked={parked}; 未开始剩余 {remaining} 个 GSM; outcomes={output}', flush=True)
    # Exit 0 means a completed queue pass; the sidecar decides dataset completion.
    call('build_report.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
