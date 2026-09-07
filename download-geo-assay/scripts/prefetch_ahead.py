#!/usr/bin/env python3
"""One bounded, optional NCBI lookahead pass; never launches conversion or a watchdog."""
from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import sys
from pathlib import Path

from project_layout import allow_sra_lite_for_gsm, read_config, read_tsv
from transfer_state import read_json, write_json
from ncbi_odp import probe, list_object

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--current-run', required=True, help='Active foreground run, always excluded')
    args = parser.parse_args()
    root = args.root.resolve()
    config = read_config(root)
    limit = int(config.get('prefetch_ahead_runs', '0'))
    if not 1 <= limit <= 3:
        parser.error('Opt in with acquisition_config.tsv prefetch_ahead_runs=1..3; default is disabled')
    rows = read_tsv(root / 'metadata/source_manifest.tsv')
    current = [i for i, row in enumerate(rows) if row['srr'] == args.current_run]
    if len(current) != 1:
        parser.error('current-run must identify one source-manifest row')
    active_gsm = rows[current[0]]['gsm']
    cache = root / 'temporary/prefetch_cache'
    cache.mkdir(parents=True, exist_ok=True)
    env = {key: value for key, value in os.environ.items() if key not in {'all_proxy', 'ALL_PROXY'}}
    with (cache / 'ahead.lock').open('a+') as worker_lock:
        try:
            fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        for row in rows[current[0] + 1:]:
            run = row['srr']
            if row['selected_source'] not in {'ncbi_sra', 'ncbi_ondemand'}:
                continue
            if (root / f'reports/status/{run}.complete').exists():
                continue
            occupied = {path.name for path in cache.iterdir() if path.is_dir() and any(path.iterdir())}
            if run not in occupied and len(occupied) >= limit:
                print(f'prefetch_idle: occupied={len(occupied)} limit={limit}')
                return 0
            rc = subprocess.run([sys.executable, str(HERE / 'audit_manifest.py'), '--root', str(root),
                                 '--manifest', str(root / 'metadata/source_manifest.tsv'), '--gsm', active_gsm]).returncode
            if rc:
                return 2
            work = root / 'temporary' / row['gsm'] / 'work' / run
            work.mkdir(parents=True, exist_ok=True)
            with (work / 'run.lock').open('a+') as run_lock, (cache / f'{run}.lock').open('a+') as cache_lock:
                try:
                    fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(cache_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                state_path = cache / f'{run}.prefetch.json'
                state = read_json(state_path)
                if state.get('attempts', 0) >= 3 or state.get('status') == 'terminal_failed':
                    continue
                full = cache / run / f'{run}.sra'
                lite = cache / run / f'{run}.sralite'
                valid = lambda path: path.is_file() and subprocess.run(['vdb-validate', str(path)], env=env).returncode == 0
                if valid(full):
                    continue
                # Durable attempt accounting survives restarting the optional worker.
                state.update(attempts=state.get('attempts', 0) + 1, status='in_progress')
                write_json(state_path, state)
                logs = root / 'reports/logs'
                logs.mkdir(parents=True, exist_ok=True)
                evidence = probe(run)
                allow_prefetch = evidence['status'] == 'missing' and row['selected_source'] == 'ncbi_sra'
                if evidence['status'] == 'available' and evidence['method'] != 'aws_list':
                    # This optional worker uses AWS; the foreground can still use HTTP/aria2.
                    evidence = {**list_object(run), 'http_code':evidence.get('http_code','')}
                evidence_path = root / f'reports/status/{run}.odp.json'
                write_json(evidence_path,evidence)
                # Recheck full-object availability, but never fetch an already validated Lite again.
                # Unresolved ODP must not authorize Lite; an available full archive still wins.
                if allow_prefetch and valid(lite):
                    allowed = allow_sra_lite_for_gsm(root, row['gsm'])
                    state.update(status='ready' if allowed else 'terminal_failed',
                                 exit_code=0, object_class='SRA_LITE',
                                 reason='validated_lite_cache' if allowed else 'lite_requires_authorization')
                    write_json(state_path, state)
                    continue
                with (logs / f'{run}.prefetch.log').open('a') as log:
                    if evidence['status'] == 'available':
                        command = [sys.executable,str(HERE/'ncbi_odp.py'),'copy','--run',run,
                                   '--evidence',str(evidence_path),'--destination',str(full),
                                   '--expected-bytes',row.get('selected_bytes','') if row['selected_source']=='ncbi_ondemand' else '',
                                   '--expected-md5',row.get('selected_md5','') if row['selected_source']=='ncbi_ondemand' else '']
                        rc = subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
                    elif allow_prefetch:
                        rc = subprocess.run(['prefetch', run, '--type', 'sra', '--max-size', 'u', '-O', str(cache)],
                                            env=env, stdout=log, stderr=subprocess.STDOUT).returncode
                    else:
                        rc = 1
                        log.write('ODP unresolved or selected ODP missing; prefetch/Lite not permitted\n')
                is_full, is_lite = valid(full), valid(lite)
                ready = is_full or (is_lite and allow_prefetch and allow_sra_lite_for_gsm(root, row['gsm']))
                state.update(status='ready' if ready else ('terminal_failed' if state['attempts'] >= 3 or is_lite else 'interrupted'),
                             exit_code=rc, object_class='FULL_QUALITY_ARCHIVE' if is_full else ('SRA_LITE' if is_lite else 'unknown'))
                write_json(state_path, state)
                # Keep all partial files and Lite; the foreground downloader checks ODP before adopting Lite.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
