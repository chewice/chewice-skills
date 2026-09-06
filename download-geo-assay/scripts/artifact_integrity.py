#!/usr/bin/env python3
"""Content-bound conversion evidence and resumable per-file release transactions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from project_layout import policy_for_gsm, read_tsv


class IntegrityError(ValueError):
    pass


def safe_path(root: Path, name: str, *, exists=True) -> Path:
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise IntegrityError(f'Unsafe relative path: {name}')
    path = root / relative
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise IntegrityError(f'Symlink in artifact path: {name}')
    if root.resolve() not in path.resolve().parents:
        raise IntegrityError(f'Path escapes project: {name}')
    if exists and (not path.is_file() or path.stat().st_size == 0):
        raise IntegrityError(f'Missing/empty file: {name}')
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def snapshot(root: Path, names) -> list[dict]:
    names = list(names)
    if not names or len(names) != len(set(names)):
        raise IntegrityError('File list is empty or contains duplicates')
    result = []
    for name in sorted(names):
        path = safe_path(root, name)
        before = path.stat()
        digest = sha256(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise IntegrityError(f'File changed while hashing: {name}')
        result.append(dict(path=name, bytes=after.st_size, sha256=digest))
    return result


def verify(root: Path, entries, *, allow_missing=False):
    if not entries:
        raise IntegrityError('Missing content fingerprints')
    for item in entries:
        path = safe_path(root, item['path'], exists=False)
        if allow_missing and not path.exists():
            continue
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise IntegrityError(f'Content changed/missing: {item["path"]}')


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fsync_dir(path.parent)


def fsync_dir(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise IntegrityError(f'Missing/invalid evidence: {path.name}') from exc


def split(value):
    return [part for part in value.split(';') if part]


def unit_sources(root, gsm):
    rows = [row for row in read_tsv(root/'metadata/source_manifest.tsv') if row.get('gsm') == gsm]
    return sorted(rows, key=lambda row: row['srr'])


def context(root, gsm):
    policy = policy_for_gsm(root, gsm)
    keys = ['gse', 'assay_type', 'modality', 'final_product', 'retain_raw_files', 'allow_sra_lite', 'confirmed_at']
    return {'sources': unit_sources(root, gsm), 'policy': {key: policy.get(key, '') for key in keys},
            'download_records':read_tsv(root/f'metadata/download_manifests/{gsm}.tsv'),
            'sample_units':[row for row in read_tsv(root/'metadata/sample_units.tsv') if row.get('gsm') == gsm],
            'supplement_sources':[row for row in read_tsv(root/'metadata/supplement_files.tsv') if row.get('gsm') == gsm]}


def verified_inputs(root: Path, gsm: str):
    sources = unit_sources(root, gsm)
    records = read_tsv(root/'metadata/download_manifests'/f'{gsm}.tsv')
    if not sources:
        # Array file members have their own manifest rather than SRA runs.
        if not records or any(row.get('validation') != 'PASS' for row in records):
            raise IntegrityError('No validated array download members')
        expected=[row for row in read_tsv(root/'metadata/supplement_files.tsv') if row.get('gsm') == gsm]
        if not expected or {row['url'] for row in expected} != {row['url'] for row in records}:
            raise IntegrityError('Array source members are incomplete')
        names=[]
        for row in records:
            name=row['path']; path=safe_path(root,name)
            if gsm not in Path(name).parts or str(path.stat().st_size) != row['observed_bytes']:
                raise IntegrityError('Array sample/size mismatch')
            digest=hashlib.md5()
            with path.open('rb') as handle:
                for block in iter(lambda:handle.read(8*1024*1024),b''): digest.update(block)
            if digest.hexdigest() != row['observed_md5']:
                raise IntegrityError('Array raw checksum differs from download record')
            names.append(name)
        return snapshot(root,names)
    if len({row['srr'] for row in sources}) != len(sources):
        raise IntegrityError('Duplicate source run')
    if len(records) != len(sources) or {row.get('srr') for row in records} != {row['srr'] for row in sources}:
        raise IntegrityError('Download records do not exactly cover source runs')
    names = []
    for source in sources:
        run = source['srr']
        row = next(row for row in records if row['srr'] == run)
        if row.get('validation') != 'PASS' or row.get('gsm') != gsm or row.get('gse') != source['gse']:
            raise IntegrityError(f'{run}: invalid download evidence')
        marker = dict(line.split('\t', 1) for line in (root/f'reports/status/{run}.complete').read_text().splitlines())
        if marker.get('validation') != 'PASS' or not row.get('source_fingerprint') or marker.get('source_fingerprint') != row['source_fingerprint']:
            raise IntegrityError(f'{run}: missing/mismatched completion evidence')
        payload = {key: source.get(column, '') for key, column in [
            ('source','selected_source'), ('urls','selected_urls'), ('bytes','selected_bytes'),
            ('md5','selected_md5'), ('roles','read_roles'), ('final_product','final_product')]}
        expected_fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if row['source_fingerprint'] != expected_fingerprint:
            raise IntegrityError(f'{run}: source selection changed')
        files, sizes, checks = (split(row.get(field, '')) for field in ['retained_files','retained_bytes','retained_md5'])
        if source.get('library_layout') not in {'PAIRED','SINGLE'}:
            raise IntegrityError('Explicit read layout required')
        roles = {'R1', 'R2'} if source.get('library_layout') == 'PAIRED' else {'R1'}
        roles |= set(split(source.get('read_roles',''))) & {'I1','I2'}
        expected_names = {f'{run}_{role}.fastq.gz' for role in roles}
        if source.get('final_product') == 'sra':
            expected_names = {f'{run}.sra'}
        if len(files) != len(set(files)) or {Path(name).name for name in files} != expected_names or not len(files) == len(sizes) == len(checks):
            raise IntegrityError(f'{run}: exact read-role coverage failed')
        for name, size, checksum in zip(files, sizes, checks):
            path = safe_path(root, name)
            if gsm not in Path(name).parts:
                raise IntegrityError(f'{run}: wrong sample input')
            digest = hashlib.md5()
            with path.open('rb') as handle:
                for block in iter(lambda: handle.read(8*1024*1024), b''):
                    digest.update(block)
            if str(path.stat().st_size) != size or digest.hexdigest() != checksum:
                raise IntegrityError(f'{run}: raw content differs from download validation')
        names.extend(files)
    return snapshot(root, names)


def capture_inputs(root, gsm):
    if not re.fullmatch(r'GSM\d+', gsm):
        raise IntegrityError('Invalid GSM')
    receipt = {'version':1, 'gsm':gsm, 'context':context(root,gsm), 'inputs':verified_inputs(root,gsm)}
    atomic_json(root/f'reports/conversion_inputs/{gsm}.json', receipt)
    return receipt


def conversion_receipt(root, gsm, output_names):
    before = load(root/f'reports/conversion_inputs/{gsm}.json')
    if before['context'] != context(root,gsm):
        raise IntegrityError('Source/policy changed since conversion began')
    verify(root, before['inputs'])
    rows = [row for row in read_tsv(root/'reports/conversion_provenance.tsv') if row.get('gsm') == gsm]
    if len(rows) != 1:
        raise IntegrityError('Conversion provenance must have exactly one row per GSM')
    row = rows[0]
    names = split(row.get('input_files') or row.get('input_fastq',''))
    if len(names) != len(set(names)) or set(names) != {item['path'] for item in before['inputs']}:
        raise IntegrityError('Conversion input list does not exactly match all downloaded read roles')
    if not row.get('tool') or not row.get('tool_version') or row.get('gse') != before['context']['policy']['gse']:
        raise IntegrityError('Missing conversion tool/version/GSE')
    declared = split(row.get('output_matrix',''))
    if not declared or not set(declared).issubset(set(output_names)):
        raise IntegrityError('Declared output is outside the audited product set')
    return {**before, 'provenance':row, 'outputs':snapshot(root, output_names), 'status':'PASS'}


def check_receipt(root, gsm, *, allow_missing_inputs=False):
    receipt = load(root/f'reports/processed_receipts/{gsm}.json')
    if receipt.get('status') != 'PASS' or receipt['context'] != context(root,gsm):
        raise IntegrityError('Audit receipt does not match current source/policy')
    rows = [row for row in read_tsv(root/'reports/conversion_provenance.tsv') if row.get('gsm') == gsm]
    if rows != [receipt['provenance']]:
        raise IntegrityError('Conversion provenance changed since audit')
    verify(root,receipt['outputs'])
    verify(root,receipt['inputs'],allow_missing=allow_missing_inputs)
    return receipt


def release_files(root, gsm, names, *, after_unlink=None):
    from publish_sample import verify_delivery
    verify_delivery(root,gsm)
    path = root/f'reports/release_journals/{gsm}.json'
    if path.exists():
        journal = load(path)
        if journal['gsm'] != gsm:
            raise IntegrityError('Release journal sample mismatch')
        check_receipt(root,gsm,allow_missing_inputs=True)
        verify(root,journal['files'],allow_missing=True)
        expected = {item['path'] for item in journal['files']}
        if set(names) - expected:
            raise IntegrityError('New raw files appeared during interrupted release')
    else:
        receipt = check_receipt(root,gsm)
        journal = {'gsm':gsm,'receipt_sha256':sha256(root/f'reports/processed_receipts/{gsm}.json'),
                   'files':snapshot(root,names),'deleted':[],'status':'deleting'}
        atomic_json(path,journal)
    if journal['receipt_sha256'] != sha256(root/f'reports/processed_receipts/{gsm}.json'):
        raise IntegrityError('Release receipt changed')
    for item in journal['files']:
        name = item['path']
        candidate = safe_path(root,name,exists=False)
        if name in journal['deleted']:
            if candidate.exists():
                raise IntegrityError('Deleted raw path reappeared')
            continue
        verify(root,[item],allow_missing=True)
        if candidate.exists():
            candidate.unlink()
            fsync_dir(candidate.parent)
            if after_unlink:
                after_unlink(name)
        journal['deleted'].append(name)
        atomic_json(path,journal)
    journal['status'] = 'released'
    atomic_json(path,journal)
    return journal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--gsm', required=True)
    args = parser.parse_args()
    capture_inputs(args.root.resolve(),args.gsm)
    print(f'INPUTS_VERIFIED {args.gsm}')


if __name__ == '__main__':
    main()
