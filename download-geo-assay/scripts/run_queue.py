#!/usr/bin/env python3
"""Run one assay's GSM queue, parking local failures and releasing Mode B units."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import threading
from collections import defaultdict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path

from project_layout import policy_for_gsm, read_release_states, read_tsv, write_tsv_atomic
from acquisition_runtime import (effective_config, ResourceReservation, ResourceLimitError,
                                 managed_run, RuntimeSupervisor, RuntimeCancelled)
from audit_manifest import unit_reservation

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--modality', required=True)
    parser.add_argument('--convert-script', type=Path, help='Reviewed bash script receiving root and GSM; writes conversion provenance')
    parser.add_argument('--pilot', type=int, default=0, help='Process only N pending GSMs; never denotes full completion')
    parser.add_argument('--download-workers', type=int, help='Override the project download worker count')
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
        if args.download_workers is not None:
            os.environ['GEO_SRA_DOWNLOAD_WORKERS'] = str(args.download_workers)
        settings = effective_config(root)
        workers = int(settings['download_workers'])
        if workers < 1 or int(settings['conversion_workers']) != 1:
            parser.error('download_workers must be positive and conversion_workers must equal 1')
        try:
            with RuntimeSupervisor(root) as supervisor:
                return execute(root, units, mode_b, converter, args.modality, args.pilot,
                               conversion_units, workers, supervisor, lock.fileno())
        except RuntimeCancelled as exc:
            return exc.returncode


def execute(root, units, mode_b, converter, modality, pilot, conversion_units=None,
            workers=2, supervisor=None, queue_lock_fd=None):
    conversion_units = mode_b if conversion_units is None else conversion_units
    output = root / f'reports/queue_{modality}.tsv'
    fields = ['gsm', 'status', 'failed_run', 'message']
    outcomes = {gsm: dict(gsm=gsm, status='not_started', failed_run='', message='') for gsm in units}
    record_lock = threading.Lock()
    released = {row['gsm'] for row in read_release_states(root) if row['release_status'] == 'released'}
    attempted = 0

    def record(gsm, status, run='', message=''):
        with record_lock:
            outcomes[gsm] = dict(gsm=gsm, status=status, failed_run=run, message=message)
            write_tsv_atomic(output, fields, list(outcomes.values()))
        print(f'gsm={gsm} status={status} run={run} {message}', flush=True)

    leases = () if queue_lock_fd is None else (queue_lock_fd,)

    def call(script, *extra, reservation=None):
        return managed_run(root, [sys.executable, str(HERE / script), '--root', str(root), *extra],
                           reservation=reservation, pass_fds=leases).returncode

    # Metadata is checked once. All writes below are separately admitted and monitored.
    if call('audit_manifest.py', '--manifest', str(root / 'metadata/source_manifest.tsv'), '--metadata-only'):
        for gsm in units:
            record(gsm, 'blocked', message='Manifest validation failed')
        return 2

    pending = []
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
        pending.append(gsm)

    source_rows = read_tsv(root / 'metadata/source_manifest.tsv')
    active = {}
    futures = {}
    stop_code = 0

    def phase(gsm, run, stage, reservation):
        return managed_run(root, ['bash', str(HERE / 'download_run.sh'), str(root), run, '--stage', stage],
                           reservation=reservation, pass_fds=leases).returncode

    def materialize(gsm, reservation):
        # One executor owns *all* expansion/compression and assay conversions.
        for run in units[gsm]:
            rc = phase(gsm, run, 'materialize', reservation)
            if rc:
                return rc, f'materialize failed for {run}'
        if gsm not in conversion_units:
            return 0, ''
        if call('audit_processed_outputs.py', '--gsm', gsm, reservation=reservation):
            if call('artifact_integrity.py', '--gsm', gsm, reservation=reservation):
                return 1, 'Input integrity/role verification failed'
            # Share the expansion/conversion slot with standalone downloaders.
            rc = managed_run(root, ['flock', str(root / 'reports/status/materialize.lock'),
                                   'bash', str(converter), str(root), gsm],
                             reservation=reservation, pass_fds=leases).returncode
            if rc:
                return rc, 'Conversion failed; raw preserved'
            if call('audit_processed_outputs.py', '--gsm', gsm, reservation=reservation):
                return 1, 'Converted product audit failed; raw preserved'
        if call('publish_sample.py', '--gsm', gsm, reservation=reservation):
            return 1, 'Sample publication failed; raw preserved'
        if gsm in mode_b and call('apply_storage_policy.py', '--gsm', gsm, '--confirm-delete', reservation=reservation):
            return 1, 'Release gate failed; raw preserved'
        return 0, ''

    @contextmanager
    def cancel_on_error():
        try:
            yield
        except BaseException:
            if supervisor is not None:
                supervisor.cancel()
            raise

    try:
        with ThreadPoolExecutor(max_workers=workers) as downloads, ThreadPoolExecutor(max_workers=1) as conversions, cancel_on_error():
            while pending or active or futures:
                if supervisor is not None and supervisor.cancelled:
                    stop_code = 130
                    break
                # Release a failed unit only after all of its writers have stopped.
                for gsm, state in list(active.items()):
                    if state['failed'] and not any(info[0] == gsm for info in futures.values()):
                        state['reservation'].__exit__(None, None, None)
                        del active[gsm]
                downloading = sum(info[1] == 'acquire' for info in futures.values())
                while downloading < workers:
                    candidate = next((gsm for gsm, state in active.items() if state['todo'] and not state['failed']), None)
                    if candidate is None:
                        if not pending or len(active) >= workers + 1:
                            break
                        gsm = pending[0]
                        try:
                            project, temporary, reusable = unit_reservation(root, [r for r in source_rows if r['gsm'] == gsm])
                            reservation = ResourceReservation(root, f'queue:{gsm}', project, temporary,
                                paths=reusable, temporary_paths=[p for p in reusable if p.is_relative_to(root / 'temporary')])
                            reservation.__enter__()
                        except (ResourceLimitError, ValueError) as exc:
                            record(gsm, 'waiting_space', message=str(exc))
                            if not futures and not active:
                                stop_code = 2
                            break
                        pending.pop(0)
                        active[gsm] = dict(todo=list(units[gsm]), acquired=set(), failed=False,
                                           reservation=reservation, converting=False)
                        record(gsm, 'acquiring')
                        candidate = gsm
                    state = active[candidate]
                    run = state['todo'].pop(0)
                    job = downloads.submit(phase, candidate, run, 'acquire', state['reservation'])
                    futures[job] = (candidate, 'acquire', run)
                    downloading += 1
                if stop_code:
                    break
                if not any(info[1] == 'materialize' for info in futures.values()):
                    gsm = next((g for g, s in active.items() if not s['failed'] and not s['converting']
                                and len(s['acquired']) == len(units[g])), None)
                    if gsm is not None:
                        state = active[gsm]
                        state['converting'] = True
                        record(gsm, 'converting')
                        futures[conversions.submit(materialize, gsm, state['reservation'])] = (gsm, 'materialize', '')
                if not futures:
                    if active:
                        raise RuntimeError('Queue has active units without runnable work')
                    continue
                completed, _ = wait(futures, timeout=1, return_when=FIRST_COMPLETED)
                for job in completed:
                    gsm, stage, run = futures.pop(job)
                    state = active[gsm]
                    try:
                        result = job.result()
                        rc, message = (result, '') if stage == 'acquire' else result
                    except RuntimeCancelled as exc:
                        rc, message = getattr(exc, 'returncode', 130), 'Interrupted; validated data retained'
                    except ResourceLimitError as exc:
                        rc, message = 2, str(exc)
                    except Exception as exc:
                        rc, message = 2, str(exc)
                    if rc:
                        state['failed'] = True
                        state['todo'].clear()
                        fatal = rc in {2, 130, 143} or rc < 0
                        record(gsm, 'blocked' if fatal else 'parked', run, message or f'{stage} exit={rc}')
                        if fatal:
                            stop_code = rc if rc > 0 else 130
                    elif stage == 'acquire':
                        state['acquired'].add(run)
                    else:
                        record(gsm, 'done')
                        state['reservation'].__exit__(None, None, None)
                        del active[gsm]
                if stop_code:
                    if supervisor is not None:
                        supervisor.cancel()
                    break
            if stop_code and supervisor is not None:
                supervisor.cancel()
    finally:
        # Executors have joined; no child should retain a reservation after release.
        for gsm, state in active.items():
            if outcomes[gsm]['status'] in {'acquiring', 'converting'}:
                record(gsm, 'interrupted', message='Queue stopped; resume the same entrypoint')
            state['reservation'].__exit__(None, None, None)
    if stop_code:
        return stop_code
    parked = sum(row['status'] == 'parked' for row in outcomes.values())
    remaining = sum(row['status'] == 'not_started' for row in outcomes.values())
    phase = 'pilot_done' if pilot else ('queue_finished_with_failures' if parked else 'queue_complete')
    print(f'{phase}: parked={parked}; 未开始剩余 {remaining} 个 GSM; outcomes={output}', flush=True)
    # Exit 0 means a completed queue pass; the sidecar decides dataset completion.
    call('build_report.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
