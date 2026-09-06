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

BUCKET = 'sra-pub-run-odp'


def aws_env():
    env = {k:v for k,v in os.environ.items() if k not in {'all_proxy','ALL_PROXY'}}
    env.update(AWS_MAX_ATTEMPTS='1', AWS_RETRY_MODE='standard', AWS_PAGER='', AWS_EC2_METADATA_DISABLED='true')
    return env


def list_object(run):
    key = f'sra/{run}/{run}'
    command = ['aws','s3api','list-objects-v2','--bucket',BUCKET,'--prefix',key,
               '--max-keys','2','--no-paginate','--output','json','--no-sign-request',
               '--region','us-east-1','--cli-connect-timeout','20','--cli-read-timeout','40']
    try:
        result = subprocess.run(command, env=aws_env(), capture_output=True, text=True, timeout=70)
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


def probe(run):
    url = f'https://{BUCKET}.s3.amazonaws.com/sra/{run}/{run}'
    with tempfile.TemporaryDirectory(prefix='geo-odp-head-') as directory:
        headers = Path(directory)/'headers'
        try:
            result = subprocess.run(['curl','-sS','-I','--connect-timeout','20','--max-time','40','--retry','0',
                                     '-D',str(headers),'-o','/dev/null','-w','%{http_code}',url],
                                    capture_output=True,text=True,timeout=45)
            code = result.stdout.strip() if result.returncode == 0 else '000'
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
    evidence = list_object(run)
    return {**evidence, 'http_code':code}


def copy_object(args):
    selected = json.loads(args.evidence.read_text())
    if selected.get('method') != 'aws_list' or selected.get('status') != 'available':
        return 2
    before = list_object(args.run)
    if before.get('status') != 'available':
        return 1
    if any(before.get(key) != selected.get(key) for key in ('key','bytes','etag','last_modified')):
        return 4
    before['http_code'] = selected.get('http_code','')
    if args.expected_bytes and int(args.expected_bytes) != before['bytes']:
        return 4
    target = args.destination
    target.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(target.parent).free < before['bytes']:
        return 2
    part = target.with_name(target.name+'.aws.part')
    # aws s3 cp is not a cross-process resume protocol. Preserve old partials, never append to them.
    if part.exists():
        os.replace(part, part.with_name(part.name+f'.interrupted.{time.time_ns()}'))
    try:
        result = subprocess.run(['aws','s3','cp',f's3://{BUCKET}/{before["key"]}',str(part),
                                 '--no-sign-request','--region','us-east-1','--only-show-errors',
                                 '--cli-connect-timeout','20','--cli-read-timeout','40'], env=aws_env())
        if result.returncode:
            return 1
        if not part.is_file() or part.stat().st_size != before['bytes']:
            return 3
        if args.expected_md5:
            with part.open('rb') as handle:
                if hashlib.file_digest(handle,'md5').hexdigest() != args.expected_md5:
                    return 3
        if subprocess.run(['vdb-validate',str(part)]).returncode:
            return 3
        after = list_object(args.run)
        if after.get('status') != 'available':
            return 1
        if any(after.get(key) != before.get(key) for key in ('key','bytes','etag','last_modified')):
            return 4
        with part.open('rb') as handle: os.fsync(handle.fileno())
        os.replace(part,target); fsync_dir(target.parent)
        atomic_json(args.evidence,{**before,'copy_status':'validated','integrity':'size+vdb-validate',
                                   'remote_identity_after':after})
        return 0
    except OSError:
        return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command',choices=['probe','copy'])
    parser.add_argument('--run',required=True)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--expected-bytes',default='')
    parser.add_argument('--expected-md5',default='')
    args=parser.parse_args()
    if not re.fullmatch(r'[SED]RR\d+',args.run): parser.error('Invalid INSDC run')
    if args.command == 'probe':
        evidence=probe(args.run); atomic_json(args.evidence,evidence)
        print(evidence['status']+'\t'+evidence['method'])
        return 0
    if not args.destination: parser.error('copy requires --destination')
    return copy_object(args)


if __name__ == '__main__': raise SystemExit(main())
