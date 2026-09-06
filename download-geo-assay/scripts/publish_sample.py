#!/usr/bin/env python3
"""Publish a validated sample as an atomic, software-independent delivery directory."""
from __future__ import annotations
import argparse
import csv
import fcntl
import json
import os
import re
import shutil
from pathlib import Path

from artifact_integrity import (IntegrityError, atomic_json, check_receipt, fsync_dir,
                                load, safe_path, sha256, snapshot, verify)
from project_layout import read_tsv


def sample_identity(root, gsm):
    records = read_tsv(root/'metadata/sample_units.tsv')
    matches = [row for row in records if row.get('gsm') == gsm]
    if records and len(matches) != 1:
        raise IntegrityError('sample_units must uniquely identify this GSM/library')
    row = matches[0] if matches else dict(gsm=gsm,sample_id=gsm,library_id=gsm,assignment_status='library_only')
    for key in ['sample_id','library_id']:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',row.get(key,'')) or row[key] in {'.','..'}:
            raise IntegrityError(f'Invalid {key}')
    if row.get('assignment_status') not in {'resolved','library_only'}:
        raise IntegrityError('Ambiguous/pooled sample assignment; retain library identity until resolved')
    if sum(other.get('sample_id') == row['sample_id'] for other in records) > 1:
        raise IntegrityError('Multiple libraries target one sample package; resolve units before publishing')
    return row


def verify_package(path):
    marker = load(path/'.complete')
    if marker.get('status') != 'PASS' or sha256(path/'checksums.sha256') != marker.get('checksums_sha256'):
        raise IntegrityError('Delivery completion/checksum manifest mismatch')
    expected=set()
    for line in (path/'checksums.sha256').read_text().splitlines():
        digest,name=line.split('  ',1)
        if name in expected:
            raise IntegrityError('Duplicate delivery checksum entry')
        expected.add(name)
        if sha256(safe_path(path,name)) != digest:
            raise IntegrityError(f'Delivery checksum mismatch: {name}')
    actual={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
    if actual != expected | {'checksums.sha256','.complete'}:
        raise IntegrityError('Unexpected/missing files in delivery')
    return marker


def verify_delivery(root,gsm):
    identity=sample_identity(root,gsm)
    path=safe_path(root, f'deliverables/{identity["sample_id"]}', exists=False)
    marker=verify_package(path)
    if marker.get('gsm') != gsm or marker.get('receipt_sha256') != sha256(root/f'reports/processed_receipts/{gsm}.json'):
        raise IntegrityError('Delivery belongs to a different audit/sample')
    if load(path/'provenance.json').get('sample_identity') != identity:
        raise IntegrityError('Sample assignment changed since publication')
    return path


def publish(root,gsm,*,before_commit=None):
    identity = sample_identity(root,gsm)
    lock_path = root / f'reports/publication.{identity["sample_id"]}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise IntegrityError('Another sample publication is active') from exc
        return _publish(root,gsm,before_commit=before_commit)


def _publish(root,gsm,*,before_commit=None):
    receipt=check_receipt(root,gsm)
    identity=sample_identity(root,gsm)
    target=root/'deliverables'/identity['sample_id']
    if target.exists():
        verify_delivery(root,gsm)
        atomic_json(root/f'reports/deliveries/{gsm}.json',{'path':target.relative_to(root).as_posix(),'status':'PASS'})
        return target
    staging=root/'deliverables/.staging'/identity['sample_id']
    staging.mkdir(parents=True,exist_ok=True)
    safe_path(root,staging.relative_to(root).as_posix(),exists=False)
    product=receipt['context']['policy']['final_product']
    mapping={}
    for entry in receipt['outputs']:
        source=entry['path']
        prefix=f'processed/{gsm}/'
        if not source.startswith(prefix):
            raise IntegrityError('Delivery products must be independently stored under their GSM')
        relative=source[len(prefix):]
        if relative.startswith('matrix_10x/'):
            relative='matrix/'+relative[len('matrix_10x/'):]
        elif relative=='counts/counts.tsv.gz':
            relative='counts.tsv.gz'
        if not relative.endswith(('.tsv','.tsv.gz','.mtx.gz','.txt','.txt.gz')):
            raise IntegrityError(f'Non-open product in required delivery: {relative}')
        mapping[source]=relative
    if not mapping:
        raise IntegrityError('No standard deliverable files')
    expected=set(mapping.values()) | {'sample.tsv','provenance.json','validation.json','checksums.sha256','.complete'}
    if any(p.relative_to(staging).as_posix() not in expected for p in staging.rglob('*') if p.is_file()):
        raise IntegrityError('Staging contains files from a different publication; inspect before retry')
    if shutil.disk_usage(staging).free < sum(entry['bytes'] for entry in receipt['outputs']):
        raise IntegrityError('Insufficient free space for sample publication; raw retained')
    for source,dest in mapping.items():
        path=staging/dest
        path.parent.mkdir(parents=True,exist_ok=True)
        safe_path(root,path.relative_to(root).as_posix(),exists=False)
        original=safe_path(root,source)
        if not path.exists() or sha256(path)!=sha256(original):
            with original.open('rb') as inp,path.open('wb') as out:
                shutil.copyfileobj(inp,out,8*1024*1024)
                out.flush(); os.fsync(out.fileno())
    # Scientific reference/strategy choices belong to conversion provenance, not inferred from file names.
    prov=receipt['provenance']
    if product in {'matrix_10x','matrix_velocity','gene_count_matrix'} and (not prov.get('reference') or not prov.get('counting_strategy')):
        raise IntegrityError('Record reference assembly/annotation and counting_strategy before delivery')
    with (staging/'sample.tsv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(identity),delimiter='\t',lineterminator='\n')
        writer.writeheader(); writer.writerow(identity)
        handle.flush(); os.fsync(handle.fileno())
    atomic_json(staging/'provenance.json',{'gsm':gsm,'sample_identity':identity,'conversion':prov,
                'source_objects':receipt['context']['sources'],'inputs':receipt['inputs'],
                'input_semantics':'original sequencing/assay inputs; quality class follows source records',
                'download_records':read_tsv(root/f'metadata/download_manifests/{gsm}.tsv'),
                'product':product,'matrix_orientation':'features_by_barcodes' if product.startswith('matrix') else 'features_by_count_columns',
                'counts':'unnormalized counts' if product in {'matrix_10x','matrix_velocity','gene_count_matrix'} else 'declared assay values',
                'missing_values':'not permitted; omitted sparse entries represent zero'})
    entries=snapshot(staging,mapping.values())
    atomic_json(staging/'validation.json',{'status':'PASS','format':'open_sample_v1','files':entries,
                'checks':['full_count_body','identifiers','input_role_coverage','content_bound_provenance'],
                'receipt_sha256':sha256(root/f'reports/processed_receipts/{gsm}.json')})
    files=[*mapping.values(),'sample.tsv','provenance.json','validation.json']
    with (staging/'checksums.sha256').open('w') as handle:
        for name in sorted(files): handle.write(f'{sha256(staging/name)}  {name}\n')
        handle.flush(); os.fsync(handle.fileno())
    atomic_json(staging/'.complete',{'status':'PASS','gsm':gsm,
                'receipt_sha256':sha256(root/f'reports/processed_receipts/{gsm}.json'),
                'checksums_sha256':sha256(staging/'checksums.sha256')})
    verify_package(staging)
    # Recheck originals and the copied data before atomic commit.
    check_receipt(root,gsm)
    for entry in receipt['outputs']:
        if sha256(staging/mapping[entry['path']])!=entry['sha256']:
            raise IntegrityError('Source changed while copying delivery')
    for directory in sorted((p for p in staging.rglob('*') if p.is_dir()),reverse=True): fsync_dir(directory)
    fsync_dir(staging)
    if before_commit: before_commit(staging)
    os.replace(staging,target)
    fsync_dir(target.parent)
    atomic_json(root/f'reports/deliveries/{gsm}.json',{'path':target.relative_to(root).as_posix(),'status':'PASS'})
    return target


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--gsm',required=True)
    args=parser.parse_args()
    print(f'DELIVERED {publish(args.root.resolve(),args.gsm)}')


if __name__=='__main__': main()
