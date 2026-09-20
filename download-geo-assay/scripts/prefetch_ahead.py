#!/usr/bin/env python3
"""Bounded acquisition-only lookahead using the same queue, locks and budgets."""
from __future__ import annotations

import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from acquisition_runtime import (RuntimeSupervisor, RuntimeCancelled, effective_config,
                                 managed_run)
from project_layout import read_tsv

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--current-run', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    config = effective_config(root)
    limit = int(config.get('prefetch_ahead_runs', '0'))
    if not 1 <= limit <= 3:
        parser.error('Opt in with prefetch_ahead_runs=1..3; default is disabled')
    rows = read_tsv(root / 'metadata/source_manifest.tsv')
    current = [i for i, row in enumerate(rows) if row['srr'] == args.current_run]
    if len(current) != 1:
        parser.error('current-run must identify one source-manifest row')
    status = root / 'reports/status'
    status.mkdir(parents=True, exist_ok=True)
    with (status / 'queue.lock').open('a+') as lease:
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('prefetch_idle: active queue already manages concurrent acquisition')
            return 0
        occupied = set()
        for row in rows:
            run = row['srr']
            if run == args.current_run:
                continue
            work = root / 'temporary' / row['gsm'] / 'work' / run
            cache = root / 'temporary/prefetch_cache' / run
            if (status / f'{run}.ready.json').exists() or any(
                p.is_file() and p.stat().st_size for directory in (work / 'staging', work / 'ncbi', cache)
                for p in directory.rglob('*')
            ):
                occupied.add(run)
        selected = []
        for row in rows[current[0] + 1:]:
            run = row['srr']
            if (status / f'{run}.complete').exists():
                continue
            if run not in occupied and len(occupied) >= limit:
                continue
            selected.append(run)
            occupied.add(run)
            if len(selected) >= limit:
                break
        if not selected:
            print(f'prefetch_idle: occupied={len(occupied)} limit={limit}')
            return 0
        try:
            with RuntimeSupervisor(root) as supervisor:
                def acquire(run):
                    try:
                        return managed_run(root, ['bash', str(HERE / 'download_run.sh'), str(root),
                            run, '--stage', 'acquire'], pass_fds=(lease.fileno(),)).returncode
                    except Exception:
                        supervisor.cancel()
                        raise
                with ThreadPoolExecutor(max_workers=min(limit, int(config['download_workers']))) as pool:
                    results = list(pool.map(acquire, selected))
                return next((rc for rc in results if rc), 0)
        except RuntimeCancelled as exc:
            return exc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
