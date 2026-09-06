#!/usr/bin/env python3
"""Real aria2 fault injection plus process-kill recovery of publication/release."""
import csv
import gzip
import hashlib
import http.server
import json
import os
import random
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from scipy import sparse
from scipy.io import mmread
from artifact_integrity import capture_inputs, release_files, sha256
from integrity_test import fixture, run_audit
from publish_sample import publish, verify_delivery
from project_layout import default_policy, write_storage_policy, write_tsv_atomic, read_tsv
from self_test import child_env, gzip_matrix, gzip_lines

HERE=Path(__file__).resolve().parent


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_HEAD(self):
        server=self.server
        self.send_response(200)
        self.send_header('Content-Length',str(len(server.payload)))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('ETag',server.etag)
        self.end_headers()
    def do_GET(self):
        server=self.server
        if self.headers.get('If-Match') not in {None,server.etag}:
            self.send_error(412); return
        start=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0])
        server.offsets.append(start)
        body=server.payload[start:]
        self.send_response(206 if start else 200)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('ETag',server.etag)
        if start: self.send_header('Content-Range',f'bytes {start}-{len(server.payload)-1}/{len(server.payload)}')
        self.end_headers()
        interrupt=server.failures>0
        if interrupt: server.failures-=1
        limit=max(1,len(body)//3) if interrupt else len(body)
        try:
            for index in range(0,limit,16384):
                self.wfile.write(body[index:min(index+16384,limit)]); self.wfile.flush()
                if server.slow: time.sleep(0.04)
            if interrupt and server.change_version: server.etag='"version-two"'
            if interrupt: self.connection.shutdown(socket.SHUT_RDWR)
        except (BrokenPipeError,ConnectionResetError,OSError): pass
        self.close_connection=True


class FaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('aria2c'): raise RuntimeError('Real aria2c is required; run using the locked Pixi test environment')
        generator=random.Random(709)
        cls.sequences=[''.join(generator.choices('ACGT',k=60)) for _ in range(40000)]
        text=''.join(f'@r{i}\n{seq}\n+\n'+('I'*60)+'\n' for i,seq in enumerate(cls.sequences))
        cls.payload=gzip.compress(text.encode(),mtime=0)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='geo-fault-')
        self.root=Path(self.temp.name)
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.payload=self.payload; self.server.etag='"version-one"'
        self.server.failures=0; self.server.slow=False; self.server.change_version=False; self.server.offsets=[]
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=5); self.temp.cleanup()
    def prepare(self,product='fastq'):
        write_storage_policy(self.root,default_policy('GSE1',product=='fastq',assay_type='RNA-seq',raw_file_type='FASTQ',final_product=product,confirmed_at='fixture'))
        row=dict(gse='GSE1',gsm='GSM1',srr='SRR1',library_layout='SINGLE',expected_spots=str(len(self.sequences)),
                 selected_source='ena_fastq',selected_provenance='ARCHIVE_GENERATED_FASTQ',
                 selected_urls=f'http://127.0.0.1:{self.server.server_port}/reads.fastq.gz',selected_bytes=str(len(self.payload)),
                 selected_md5=hashlib.md5(self.payload).hexdigest(),read_roles='R1',final_product=product)
        write_tsv_atomic(self.root/'metadata/source_manifest.tsv',list(row),[row])
        return child_env(GEO_SRA_MAX_ATTEMPTS='3',GEO_SRA_RETRY_DELAYS='0,0,0',GEO_SRA_CONNECTIONS='1',GEO_SRA_RUN_FASTQC='0')
    def command(self): return ['bash',str(HERE/'download_run.sh'),str(self.root),'SRR1']
    def download(self,env,expected=0):
        result=subprocess.run(self.command(),env=env,capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,expected,result.stdout[-5000:]+result.stderr[-3000:])
        return result
    def test_repeated_interruptions_then_end_to_end_delivery(self):
        env=self.prepare('matrix_10x'); self.server.failures=2
        self.download(env)
        raw=self.root/'temporary/GSM1/fastq/SRR1_R1.fastq.gz'
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),hashlib.sha256(self.payload).hexdigest())
        self.assertGreaterEqual(len(self.server.offsets),3)
        capture_inputs(self.root,'GSM1')
        totals=[sum(seq.count(base) for seq in self.sequences) for base in 'ACGT']
        directory=self.root/'processed/GSM1/matrix_10x/raw_feature_bc_matrix'
        gzip_matrix(directory/'matrix.mtx.gz',sparse.csr_matrix([[value] for value in totals]))
        gzip_lines(directory/'features.tsv.gz',[f'fixture_{base}\t{base}\tGene Expression' for base in 'ACGT'])
        gzip_lines(directory/'barcodes.tsv.gz',['fixture_barcode'])
        prov=dict(gse='GSE1',gsm='GSM1',tool='synthetic-count-fixture',tool_version='1',input_fastq='temporary/GSM1/fastq/SRR1_R1.fastq.gz',
                  output_matrix='processed/GSM1/matrix_10x/raw_feature_bc_matrix/matrix.mtx.gz',validated_at='fixture',
                  reference='synthetic A/C/G/T features',counting_strategy='synthetic nucleotide counts for transport test')
        write_tsv_atomic(self.root/'reports/conversion_provenance.tsv',list(prov),[prov])
        self.assertEqual(run_audit(self.root),0)
        target=publish(self.root,'GSM1')
        observed=mmread(target/'matrix/raw_feature_bc_matrix/matrix.mtx.gz',spmatrix=True).toarray().ravel().tolist()
        self.assertEqual(observed,totals)
        result=subprocess.run([sys.executable,str(HERE/'apply_storage_policy.py'),'--root',str(self.root),'--gsm','GSM1','--confirm-delete'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(raw.exists()); verify_delivery(self.root,'GSM1')
    def test_changed_remote_is_never_spliced(self):
        env=self.prepare(); self.server.failures=1; self.server.change_version=True
        result=subprocess.run(self.command(),env=env,capture_output=True,text=True,timeout=90)
        self.assertNotEqual(result.returncode,0)
        state=json.loads((self.root/'reports/status/SRR1.transfer.json').read_text())
        self.assertEqual(state['error_class'],'remote_changed')
        self.assertFalse((self.root/'reports/status/SRR1.complete').exists())
        self.assertEqual(len(self.server.offsets),1)
    def test_sigkill_download_recovers_identical_bytes(self):
        env=self.prepare(); self.server.slow=True
        log=(self.root/'kill.log').open('w')
        process=subprocess.Popen(self.command(),env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        part=self.root/'temporary/GSM1/work/SRR1/staging/download/SRR1_R1.fastq.gz.part'
        try:
            deadline=time.monotonic()+20
            while (not part.exists() or part.stat().st_size<65536) and time.monotonic()<deadline:
                if process.poll() is not None: self.fail('Download finished before fault injection')
                time.sleep(0.05)
            self.assertTrue(part.exists())
            os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=10)
        finally:
            if process.poll() is None: os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=10)
            log.close()
        self.assertFalse((self.root/'reports/status/SRR1.complete').exists())
        self.server.slow=False; self.download(env)
        self.assertEqual((self.root/'raw/GSM1/fastq/SRR1_R1.fastq.gz').read_bytes(),self.payload)
    def test_disk_write_failure_preserves_partial(self):
        env=self.prepare()
        stubs=self.root/'stubs'; stubs.mkdir()
        stub=stubs/'aria2c'
        stub.write_text('''#!/usr/bin/env python3
import sys
from pathlib import Path
args=sys.argv[1:]
def option(name): return next(arg.split('=',1)[1] for arg in args if arg.startswith(name+'='))
p=Path(option('--dir'))/option('--out'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'partial')
raise SystemExit(9)
'''); stub.chmod(0o755)
        env['PATH']=str(stubs)+':'+env['PATH']; self.download(env,expected=1)
        state=json.loads((self.root/'reports/status/SRR1.transfer.json').read_text())
        self.assertEqual(state['error_class'],'disk_or_conversion')
        self.assertFalse((self.root/'reports/status/SRR1.complete').exists())
        self.assertTrue(list((self.root/'temporary').rglob('*.part')))
    def test_real_process_kill_during_sample_publish_and_release(self):
        project=self.root/'sample'; files=fixture(project)
        self.assertEqual(run_audit(project),0)
        prefix=f'import sys,os,signal; sys.path.insert(0,{str(HERE)!r}); from pathlib import Path; root=Path({str(project)!r}); '
        code=prefix+"from publish_sample import publish; publish(root,'GSM1',before_commit=lambda _:os.kill(os.getpid(),signal.SIGKILL))"
        result=subprocess.run([sys.executable,'-c',code])
        self.assertEqual(result.returncode,-signal.SIGKILL)
        self.assertFalse((project/'deliverables/GSM1').exists())
        publish(project,'GSM1')
        names=[p.relative_to(project).as_posix() for p in files]
        code=prefix+f"from artifact_integrity import release_files; release_files(root,'GSM1',{names!r},after_unlink=lambda _:os.kill(os.getpid(),signal.SIGKILL))"
        result=subprocess.run([sys.executable,'-c',code])
        self.assertEqual(result.returncode,-signal.SIGKILL)
        self.assertEqual(sum(p.exists() for p in files),1)
        journal=release_files(project,'GSM1',[name for name in names if (project/name).exists()])
        self.assertEqual(journal['status'],'released'); verify_delivery(project,'GSM1')


if __name__=='__main__': unittest.main()
