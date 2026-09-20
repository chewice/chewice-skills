#!/usr/bin/env python3
"""Exact-key ODP fallback; AWS transfers never publish an unvalidated partial."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from artifact_integrity import atomic_json, fsync_dir
from acquisition_runtime import managed_run, network_env, ResourceReservation

BUCKET = 'sra-pub-run-odp'


def project_root(root=None):
    root = root or os.environ.get('GEO_SRA_PROJECT_ROOT') or os.environ.get('GEO_SRA_ROOT')
    if not root:
        raise ValueError('ODP operations require --root or GEO_SRA_PROJECT_ROOT')
    return Path(root).resolve()


def md5(path):
    digest = hashlib.md5()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def aws_env(root=None):
    env = network_env(project_root(root))
    env.update(AWS_MAX_ATTEMPTS='1', AWS_RETRY_MODE='standard', AWS_PAGER='', AWS_EC2_METADATA_DISABLED='true')
    return env


def list_object(run, root=None):
    root = project_root(root)
    key = f'sra/{run}/{run}'
    command = ['aws','s3api','list-objects-v2','--bucket',BUCKET,'--prefix',key,
               '--max-keys','2','--no-paginate','--output','json','--no-sign-request',
               '--region','us-east-1','--cli-connect-timeout','20','--cli-read-timeout','40']
    try:
        result = managed_run(root, command, network=True, env=aws_env(root), capture_output=True, text=True, timeout=70)
        if result.returncode:
            return {'status':'unreachable','method':'aws_list','exit_code':result.returncode}
        data = json.loads(result.stdout)
        objects = [item for item in data.get('Contents',[]) if item.get('Key') == key]
        if len(objects) == 1 and isinstance(objects[0].get('Size'),int) and objects[0]['Size'] > 0:
            item = objects[0]
            return {'status':'available','method':'aws_list','key':key,'bytes':item['Size'],
                    'etag':item.get('ETag',''),'last_modified':item.get('LastModified','')}
        # An empty/partial listing does not authorize a source or quality downgrade.
        return {'status':'unreachable','method':'aws_list','reason':'exact key not established'}
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, AttributeError):
        return {'status':'unreachable','method':'aws_list','reason':'AWS unavailable or invalid response'}


def probe(run, root=None):
    root = project_root(root)
    url = f'https://{BUCKET}.s3.amazonaws.com/sra/{run}/{run}'
    with tempfile.TemporaryDirectory(prefix='geo-odp-head-') as directory:
        headers = Path(directory)/'headers'
        try:
            result = managed_run(root, ['curl','-sS','-I','--connect-timeout','20','--max-time','40','--retry','0',
                                     '-D',str(headers),'-o','/dev/null','-w','%{http_code}',url],
                                    network=True, url=url, env=aws_env(root),capture_output=True,text=True,timeout=45)
            raw_code = result.stdout.strip()
            code = raw_code if result.returncode == 0 and re.fullmatch(r'[1-5][0-9]{2}', raw_code) else '000'
        except (OSError, subprocess.TimeoutExpired):
            code = '000'
        values = {}
        for line in headers.read_text().splitlines() if headers.exists() else []:
            if line.startswith('HTTP/'):
                values = {}
            elif ':' in line:
                key,value = line.split(':',1); values[key.lower()] = value.strip()
    if code == '404' or (code != '000' and values.get('x-amz-delete-marker','').lower() == 'true'):
        return {'status':'missing','method':'head','http_code':code,'delete_marker':values.get('x-amz-delete-marker','')}
    if code == '200':
        return {'status':'available','method':'http','http_code':code,'bytes':values.get('content-length','')}
    evidence = list_object(run, root)
    return {**evidence, 'http_code':code}


def copy_object(args):
    root = project_root(getattr(args, 'root', None))
    selected = json.loads(args.evidence.read_text())
    if selected.get('method') != 'aws_list' or selected.get('status') != 'available':
        return 2
    target = args.destination
    part = target.with_name(target.name+'.aws.part')
    pending = target.with_name(target.name+'.aws.pending.json')
    identity_keys = ('key','bytes','etag','last_modified')
    # A completed local transfer survives a failed final metadata request.
    if pending.exists():
        state = json.loads(pending.read_text())
        before = state['remote_identity']
        if any(before.get(key) != selected.get(key) for key in identity_keys):
            return 4
        candidate = part if part.is_file() else target
        if not candidate.is_file() or candidate.stat().st_size != before['bytes']:
            return 3
        if md5(candidate) != state['local_md5']:
            return 3
        if (args.expected_bytes and int(args.expected_bytes) != before['bytes']) or (
                args.expected_md5 and args.expected_md5 != state['local_md5']):
            return 4
        after = list_object(args.run, root)
        if after.get('status') != 'available':
            return 1
        if any(after.get(key) != before.get(key) for key in identity_keys):
            return 4
        if candidate == part:
            os.replace(part, target); fsync_dir(target.parent)
        atomic_json(args.evidence, {**before, 'copy_status':'validated',
                                   'integrity':'size+vdb-validate', 'remote_identity_after':after})
        pending.unlink(); fsync_dir(pending.parent)
        return 0
    before = list_object(args.run, root)
    if before.get('status') != 'available':
        return 1
    if any(before.get(key) != selected.get(key) for key in identity_keys):
        return 4
    before['http_code'] = selected.get('http_code','')
    if args.expected_bytes and int(args.expected_bytes) != before['bytes']:
        return 4
    target.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(target.parent).free < before['bytes']:
        return 2
    # aws s3 cp is not a cross-process resume protocol. Preserve old partials, never append to them.
    if part.exists():
        os.replace(part, part.with_name(part.name+f'.interrupted.{time.time_ns()}'))
    try:
        reservation = ResourceReservation(root, f'odp-{args.run}', before['bytes'], before['bytes'],
                                          paths=(part,), temporary_paths=(part,))
        with reservation:
            result = managed_run(root, ['aws','s3','cp',f's3://{BUCKET}/{before["key"]}',str(part),
                                     '--no-sign-request','--region','us-east-1','--only-show-errors',
                                     '--cli-connect-timeout','20','--cli-read-timeout','40'],
                                 network=True, env=aws_env(root), reservation=reservation)
        if result.returncode:
            return 1
        if not part.is_file() or part.stat().st_size != before['bytes']:
            return 3
        local_md5 = md5(part)
        if args.expected_md5 and local_md5 != args.expected_md5:
            return 3
        if managed_run(root, ['vdb-validate',str(part)]).returncode:
            return 3
        with part.open('rb') as handle: os.fsync(handle.fileno())
        atomic_json(pending, {'phase':'awaiting_identity', 'remote_identity':before, 'local_md5':local_md5})
        after = list_object(args.run, root)
        if after.get('status') != 'available':
            return 1
        if any(after.get(key) != before.get(key) for key in identity_keys):
            return 4
        with part.open('rb') as handle: os.fsync(handle.fileno())
        os.replace(part,target); fsync_dir(target.parent)
        atomic_json(args.evidence,{**before,'copy_status':'validated','integrity':'size+vdb-validate',
                                   'remote_identity_after':after})
        pending.unlink(); fsync_dir(pending.parent)
        return 0
    except OSError:
        return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command',choices=['probe','copy'])
    parser.add_argument('--run',required=True)
    parser.add_argument('--root',type=Path)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--expected-bytes',default='')
    parser.add_argument('--expected-md5',default='')
    args=parser.parse_args()
    args.root = args.root or Path(os.environ.get('GEO_SRA_PROJECT_ROOT') or os.environ.get('GEO_SRA_ROOT') or args.evidence.parent.parent.parent)
    if not re.fullmatch(r'[SED]RR\d+',args.run): parser.error('Invalid INSDC run')
    if args.command == 'probe':
        evidence=probe(args.run,args.root); atomic_json(args.evidence,evidence)
        print(evidence['status']+'\t'+evidence['method'])
        return 0
    if not args.destination: parser.error('copy requires --destination')
    return copy_object(args)


if __name__ == '__main__': raise SystemExit(main())
