#!/usr/bin/env python3
"""Offline regressions for field failures: proxy, Lite, cache, queue and quota."""
from __future__ import annotations

import csv
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from self_test import child_env, prefetch_resume_test, read_tsv, run, write_tsv
import probe_ncbi
import run_queue
import prefetch_ahead

HERE = Path(__file__).resolve().parent


def main():
    with tempfile.TemporaryDirectory(prefix='geo-field-regression-') as temporary:
        base = Path(temporary)
        prefetch_resume_test(base)
        original = base / 'prefetch_project'
        stubs = base / 'prefetch_stubs'
        (stubs / 'prefetch').write_text('''#!/usr/bin/env bash
set -eu
[[ -z ${all_proxy:-} && -z ${ALL_PROXY:-} ]]
[[ ${http_proxy:-} == http://proxy.example:8080 ]]
echo called >> "$CALLS"
run=$1
shift
while [[ $# -gt 0 ]]; do
 if [[ $1 == -O ]]; then out=$2; shift 2; else shift; fi
done
mkdir -p "$out/$run"
printf valid > "$out/$run/$run.${TEST_KIND:-sra}"
''')
        (stubs / 'curl').write_text('#!/usr/bin/env bash\necho curl >> "$CALLS"\nprintf "%s" "${TEST_HEAD:-404}"\n')
        aws = stubs / 'aws'
        aws.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
calls=Path(os.environ['CALLS'])
with calls.open('a') as handle: handle.write('aws-'+args[0]+'\\n')
assert '--no-sign-request' in args
assert os.environ['AWS_MAX_ATTEMPTS']=='1'
mode=os.environ.get('AWS_TEST_MODE','unreachable')
if mode=='unreachable': raise SystemExit(1)
if args[0]=='s3api':
    key=args[args.index('--prefix')+1]
    if mode=='prefix_only': key+='0'
    etag='v2' if (calls.parent/'changed').exists() else 'v1'
    print(json.dumps({'Contents':[{'Key':key,'Size':14,'ETag':etag}]}))
else:
    path=Path(args[3]); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'bad' if mode=='truncated' else b'validated-full')
    if mode=='copy_fail': raise SystemExit(1)
    if mode=='changed': (calls.parent/'changed').touch()
''')
        aws.chmod(0o755)
        (stubs/'vdb-validate').write_text('#!/usr/bin/env bash\n[[ -s $1 ]] || exit 1\n[[ ${AWS_TEST_MODE:-} != vdb_reject ]]\n')
        scripts = base / 'scripts'
        scripts.mkdir()
        for path in HERE.glob('*.py'):
            shutil.copy2(path, scripts / path.name)
        shutil.copy2(HERE / 'download_run.sh', scripts / 'download_run.sh')
        helper = scripts / 'transfer_state.py'
        helper.write_text(helper.read_text().replace('def publish(args: argparse.Namespace) -> int:', '''def publish(args: argparse.Namespace) -> int:
    if os.environ.get("TEST_PUBLISH_FAIL") == "1":
        return 99'''))

        def fixture(name, lite=True):
            project = base / name
            shutil.copytree(original / 'metadata', project / 'metadata')
            shutil.rmtree(project / 'metadata/download_manifests')
            manifest = project / 'metadata/source_manifest.tsv'
            rows = read_tsv(manifest)
            rows[0]['final_product'] = 'sra'
            write_tsv(manifest, list(rows[0]), rows)
            policy = project / 'metadata/storage_policy.tsv'
            rows = read_tsv(policy)
            rows[0]['allow_sra_lite'] = 'true' if lite else 'false'
            write_tsv(policy, list(rows[0]), rows)
            env = child_env(PATH=f'{stubs}:{Path(sys.executable).resolve().parent}:{os.environ.get("PATH", "")}',
                            CALLS=str(project / 'calls'), TEST_KIND='sralite', TEST_HEAD='404',
                            GEO_SRA_RUN_FASTQC='0', all_proxy='socks5://unused:9999', ALL_PROXY='socks5://unused:9999',
                            http_proxy='http://proxy.example:8080', GEO_SRA_RETRY_DELAYS='0,0,0')
            return project, env

        project, env = fixture('lite_publish_resume')
        command = ('bash', str(scripts / 'download_run.sh'), str(project), 'SRR40000001')
        run(*command, env={**env, 'TEST_PUBLISH_FAIL': '1'}, expect=99)
        assert not (project / 'reports/status/SRR40000001.complete').exists()
        calls = (project / 'calls').read_text()
        run(*command, env=env)
        observed = read_tsv(project / 'metadata/download_manifests/GSM400001.tsv')[0]
        assert (observed['provenance'], observed['quality_class']) == ('SRA_LITE', 'SIMPLIFIED')
        assert observed['replacement_note']
        assert (project / 'calls').read_text() == calls

        for source in ('ncbi_sra', 'ncbi_ondemand'):
            project, env = fixture('cache_' + source)
            cache = project / 'temporary/prefetch_cache/SRR40000001/SRR40000001.sra'
            cache.parent.mkdir(parents=True)
            cache.write_text('validated-full')
            manifest = project / 'metadata/source_manifest.tsv'
            rows = read_tsv(manifest)
            rows[0]['selected_source'] = source
            if source == 'ncbi_ondemand':
                rows[0]['selected_urls'] = 'https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR40000001/SRR40000001'
            write_tsv(manifest, list(rows[0]), rows)
            run('bash', str(scripts / 'download_run.sh'), str(project), 'SRR40000001', env=env)
            assert not (project / 'calls').exists(), 'Cache reuse must precede all network requests'
            assert read_tsv(project / 'metadata/download_manifests/GSM400001.tsv')[0]['quality_class'] == 'FULL'

        for name, allow, head in [('lite_denied', False, '404'), ('tls_not_absence', True, '000')]:
            project, env = fixture(name, lite=allow)
            env['TEST_HEAD'] = head
            command = ('bash', str(scripts / 'download_run.sh'), str(project), 'SRR40000001')
            run(*command, env=env, expect=1)
            calls = (project / 'calls').read_text()
            run(*command, env=env, expect=1)
            assert (project / 'calls').read_text() == calls, 'terminal restart must not spend more network attempts'
            lite = project / 'temporary/GSM400001/work/SRR40000001/ncbi/SRR40000001/SRR40000001.sralite'
            assert lite.is_file() == (head == '404')
            if head == '000':
                assert 'called' not in calls, 'Unknown ODP must not invoke prefetch'

        for source in ('ncbi_sra','ncbi_ondemand'):
            project, env = fixture('aws_success_'+source)
            env.update(TEST_HEAD='000',AWS_TEST_MODE='available')
            manifest=project/'metadata/source_manifest.tsv'; rows=read_tsv(manifest)
            rows[0]['selected_source']=source
            if source=='ncbi_ondemand':
                rows[0]['selected_urls']='https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR40000001/SRR40000001'
                rows[0]['selected_bytes']='14'
            write_tsv(manifest,list(rows[0]),rows)
            run('bash',str(scripts/'download_run.sh'),str(project),'SRR40000001',env=env)
            assert (project/'raw/GSM400001/sra/SRR40000001.sra').read_bytes()==b'validated-full'
            assert 'called' not in (project/'calls').read_text()
            evidence=read_tsv(project/'metadata/download_manifests/GSM400001.tsv')[0]
            assert json.loads(evidence['odp_evidence'])['copy_status']=='validated'
            assert evidence['quality_class']=='FULL'

        for mode in ('prefix_only','truncated','changed','copy_fail','vdb_reject'):
            project,env=fixture('aws_failure_'+mode)
            env.update(TEST_HEAD='000',AWS_TEST_MODE=mode,GEO_SRA_MAX_ATTEMPTS='2')
            run('bash',str(scripts/'download_run.sh'),str(project),'SRR40000001',env=env,expect=1)
            assert not (project/'reports/status/SRR40000001.complete').exists()
            assert 'called' not in (project/'calls').read_text()
            if mode != 'prefix_only': assert list((project/'temporary/prefetch_cache').rglob('*.aws.part*'))

        # clear-error is deliberately cosmetic; explicit archival starts a new epoch.
        project,env=fixture('retry_budget')
        state=project/'reports/status/SRR40000001.transfer.json'
        update=[sys.executable,str(scripts/'transfer_state.py'),'update','--path',str(state),
                '--run','SRR40000001','--fingerprint','fixture']
        for _ in range(3): run(*update,'--error-class','network_interrupted')
        run(*update,'--clear-error')
        run(*update,'--error-class','network_interrupted')
        assert json.loads(state.read_text())['same_error_count']==4
        previous=state.read_bytes()
        command=[sys.executable,str(scripts/'transfer_state.py'),'archive-retry','--root',str(project),
                 '--run','SRR40000001','--reason','Validated full cache after proxy outage']
        lock_path=project/'temporary/GSM400001/work/SRR40000001/run.lock'
        lock_path.parent.mkdir(parents=True,exist_ok=True)
        with lock_path.open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            run(*command,expect=1)
        assert state.read_bytes()==previous
        run(*command)
        assert list(state.parent.glob('*.archived.json'))[0].read_bytes()==previous
        run(*update,'--error-class','network_interrupted')
        assert json.loads(state.read_text())['same_error_count']==1

        project,env=fixture('recover_with_valid_cache')
        env.update(TEST_HEAD='000',GEO_SRA_MAX_ATTEMPTS='2')
        command=['bash',str(scripts/'download_run.sh'),str(project),'SRR40000001']
        run(*command,env=env,expect=1)
        cache=project/'temporary/prefetch_cache/SRR40000001/SRR40000001.sra'
        cache.parent.mkdir(parents=True,exist_ok=True); cache.write_bytes(b'validated-full')
        calls=(project/'calls').read_text()
        run(*command,env=env,expect=1)
        run(sys.executable,str(scripts/'transfer_state.py'),'archive-retry','--root',str(project),
            '--run','SRR40000001','--reason','Repaired full cache verified')
        run(*command,env=env)
        assert (project/'calls').read_text()==calls, 'Recovered cache must precede every network call'

        for status, expected in [(200, 'available'), (404, 'missing'), (503, 'unreachable'), (0, 'unreachable')]:
            rows = probe_ncbi.probe_run('SRR1', {'SRR1': {'odp_status': status, 'odp_bytes': '12'}})
            assert rows[-1]['status'] == expected
        with patch.object(probe_ncbi, 'fetch', return_value=(503, b'', {})), patch('ncbi_odp.list_object',return_value={'status':'unreachable'}):
            assert all(row['status'] == 'unreachable' for row in probe_ncbi.probe_run('SRR1'))
        with patch.object(probe_ncbi,'fetch',return_value=(0,b'',{})), patch('ncbi_odp.list_object',return_value={'status':'available','bytes':14}):
            assert probe_ncbi.probe_run('SRR1')[-1]['status']=='available'
        import ncbi_odp
        def delete_marker(command,**kwargs):
            Path(command[command.index('-D')+1]).write_text('HTTP/1.1 405 Method Not Allowed\nx-amz-delete-marker: true\n')
            return subprocess.CompletedProcess(command,0,'405','')
        with patch.object(ncbi_odp.subprocess,'run',side_effect=delete_marker), patch.object(ncbi_odp,'list_object') as listing:
            assert ncbi_odp.probe('SRR1')['status']=='missing'
            listing.assert_not_called()
        objects = probe_ncbi.source_objects('SRR1', 'bucket', b'<ListBucketResult><Contents><Key>SRR10/read.fastq</Key><Size>5</Size></Contents></ListBucketResult>')
        assert objects == [], 'Accession prefix must not include another run'

        queue = base / 'queue'
        (queue / 'reports/status').mkdir(parents=True)
        (queue / 'reports/status/SRR1.transfer.json').write_text(json.dumps({'status': 'terminal_failed'}))
        invoked = []
        def fake_run(command, **kwargs):
            invoked.append(command)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(run_queue.subprocess, 'run', side_effect=fake_run):
            assert run_queue.execute(queue, {'GSM1': ['SRR1'], 'GSM2': ['SRR2']}, set(), None, 'bulk_rnaseq', 0) == 0
        assert [row['status'] for row in read_tsv(queue / 'reports/queue_bulk_rnaseq.tsv')] == ['parked', 'done']
        downloads = [cmd for cmd in invoked if Path(cmd[1]).name == 'download_run.sh']
        assert [cmd[-1] for cmd in downloads] == ['SRR2']
        with patch.object(run_queue.subprocess, 'run', side_effect=fake_run):
            run_queue.execute(queue, {'GSM3': ['SRR3'], 'GSM4': ['SRR4']}, set(), None, 'bulk_rnaseq', 1)
        assert read_tsv(queue / 'reports/queue_bulk_rnaseq.tsv')[-1]['status'] == 'not_started'

        checks = {}
        invoked.clear()
        def mode_b_run(command, **kwargs):
            invoked.append(command)
            name = Path(command[1]).name
            if name == 'audit_processed_outputs.py':
                gsm = command[-1]
                checks[gsm] = checks.get(gsm, 0) + 1
                return subprocess.CompletedProcess(command, 1 if checks[gsm] == 1 else 0)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(run_queue.subprocess, 'run', side_effect=mode_b_run):
            run_queue.execute(queue, {'GSM3': ['SRR3'], 'GSM4': ['SRR4']}, {'GSM3', 'GSM4'}, Path('convert.sh'), 'bulk_rnaseq', 0)
        release = next(i for i, cmd in enumerate(invoked) if Path(cmd[1]).name == 'apply_storage_policy.py')
        second_download = next(i for i, cmd in enumerate(invoked) if Path(cmd[1]).name == 'download_run.sh' and cmd[-1] == 'SRR4')
        assert release < second_download, 'Release GSM before moving to the next GSM'

        # Full cache slots cause idle without invoking prefetch or a budget probe.
        ahead = base / 'ahead'
        for accession in ['SRR2', 'SRR3', 'SRR4']:
            directory = ahead / 'temporary/prefetch_cache' / accession
            directory.mkdir(parents=True)
            (directory / f'{accession}.sralite').write_text('keep')
        write_tsv(ahead / 'metadata/acquisition_config.tsv', ['key', 'value'], [{'key': 'prefetch_ahead_runs', 'value': '3'}])
        write_tsv(ahead / 'metadata/source_manifest.tsv', ['srr', 'gsm', 'selected_source'], [
            {'srr': 'SRR1', 'gsm': 'GSM1', 'selected_source': 'ncbi_sra'},
            {'srr': 'SRR5', 'gsm': 'GSM5', 'selected_source': 'ncbi_sra'}])
        with patch.object(sys, 'argv', ['prefetch_ahead.py', '--root', str(ahead), '--current-run', 'SRR1']), patch.object(prefetch_ahead.subprocess, 'run') as process:
            assert prefetch_ahead.main() == 0
            process.assert_not_called()
        for status in ('unreachable','available','missing'):
            project=base/f'ahead_{status}'
            write_tsv(project/'metadata/acquisition_config.tsv',['key','value'],[{'key':'prefetch_ahead_runs','value':'1'}])
            write_tsv(project/'metadata/source_manifest.tsv',['srr','gsm','selected_source'],[
                {'srr':'SRR1','gsm':'GSM1','selected_source':'ncbi_sra'},
                {'srr':'SRR2','gsm':'GSM2','selected_source':'ncbi_sra'}])
            invoked.clear()
            with patch.object(sys,'argv',['prefetch_ahead.py','--root',str(project),'--current-run','SRR1']), \
                 patch.object(prefetch_ahead,'probe',return_value={'status':status,'method':'aws_list'}), \
                 patch.object(prefetch_ahead.subprocess,'run',side_effect=fake_run):
                assert prefetch_ahead.main()==0
            assert any(cmd[0]=='prefetch' for cmd in invoked)==(status=='missing')
            assert any('copy' in cmd for cmd in invoked)==(status=='available')
    print('PASS field regressions: HEAD/AWS routing, exact key, partial/identity/vdb failures, explicit retry archival, cache recovery, Lite, queue and quota')


if __name__ == '__main__':
    main()
