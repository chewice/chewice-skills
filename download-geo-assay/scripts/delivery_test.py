#!/usr/bin/env python3
"""Open-format delivery, sample isolation and atomic publication tests."""
import csv
import gzip
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scipy.io import mmread
from artifact_integrity import IntegrityError, sha256
from integrity_test import fixture, run_audit
from publish_sample import publish, verify_delivery, verify_package
from export_star_counts import export


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='geo-delivery-')
        self.root=Path(self.temp.name)
        fixture(self.root)
    def tearDown(self): self.temp.cleanup()
    def test_open_triplet_readback(self):
        self.assertEqual(run_audit(self.root),0)
        directory=publish(self.root,'GSM1')
        self.assertEqual(verify_delivery(self.root,'GSM1'),directory)
        self.assertFalse(any(path.suffix in {'.loom','.h5ad','.rds','.qs','.pkl'} for path in directory.rglob('*')))
        matrix=mmread(directory/'matrix/raw_feature_bc_matrix/matrix.mtx.gz',spmatrix=True).tocsr()
        with gzip.open(directory/'matrix/raw_feature_bc_matrix/features.tsv.gz','rt') as h:
            features=list(csv.reader(h,delimiter='\t'))
        self.assertEqual(matrix.shape,(3,3))
        self.assertEqual(len(features),3)
        self.assertEqual(int(matrix.sum()),15)
    def test_raw_only_10x_and_no_loom(self):
        shutil.rmtree(self.root/'processed/GSM1/matrix_10x/filtered_feature_bc_matrix')
        (self.root/'processed/GSM1/velocity/GSM1.loom').unlink()
        self.assertEqual(run_audit(self.root),0)
        directory=publish(self.root,'GSM1')
        self.assertTrue((directory/'matrix/raw_feature_bc_matrix/matrix.mtx.gz').is_file())
    def test_publish_interrupted_before_commit(self):
        self.assertEqual(run_audit(self.root),0)
        def crash(_): raise OSError('simulated process stop before atomic rename')
        with self.assertRaises(OSError): publish(self.root,'GSM1',before_commit=crash)
        self.assertFalse((self.root/'deliverables/GSM1').exists())
        directory=publish(self.root,'GSM1')
        verify_package(directory)
    def test_delivery_tampering_rejected(self):
        self.assertEqual(run_audit(self.root),0)
        directory=publish(self.root,'GSM1')
        (directory/'matrix/raw_feature_bc_matrix/features.tsv.gz').write_bytes(b'bad')
        with self.assertRaises(IntegrityError): verify_delivery(self.root,'GSM1')
    def test_unaudited_extra_matrix_is_not_delivered(self):
        (self.root/'processed/GSM1/matrix_10x/unrelated.mtx.gz').write_bytes(b'invalid')
        self.assertEqual(run_audit(self.root),0)
        directory=publish(self.root,'GSM1')
        self.assertFalse((directory/'matrix/unrelated.mtx.gz').exists())
    def test_array_gzip_is_fully_read(self):
        from audit_processed_outputs import audit_array_product
        from project_layout import write_tsv_atomic
        path=self.root/'processed/GSM2/intensity.tsv.gz'
        path.parent.mkdir(parents=True)
        with gzip.open(path,'wt') as handle: handle.write('probe_id\tGSM2\np1\t1.5\n')
        write_tsv_atomic(self.root/'reports/conversion_provenance.tsv',['gsm','output_matrix'],
                         [dict(gsm='GSM2',output_matrix='processed/GSM2/intensity.tsv.gz')])
        errors=[]; audit_array_product(self.root,'GSM2',errors)
        self.assertEqual(errors,[])
        path.write_bytes(path.read_bytes()[:-4])
        with self.assertRaises(EOFError): audit_array_product(self.root,'GSM2',[])
    def test_bulk_open_counts_preserve_unknown_strands(self):
        path=self.root/'processed/GSM2/counts/ReadsPerGene.out.tab'
        path.parent.mkdir(parents=True)
        path.write_text('N_unmapped\t1\t1\t1\ngene1\t4\t3\t1\ngene2\t8\t2\t6\n')
        target=export(self.root,'GSM2')
        with gzip.open(target,'rt') as h: rows=list(csv.DictReader(h,delimiter='\t'))
        self.assertEqual(set(rows[0]),{'gene_id','unstranded','forward','reverse'})
        self.assertEqual(rows[1]['reverse'],'6')
        from audit_processed_outputs import audit_gene_matrix
        errors=[]; audit_gene_matrix(self.root,'GSM2',errors)
        self.assertEqual(errors,[])
    def test_full_bulk_delivery(self):
        project=self.root/'bulk'
        fixture(project,product='gene_count_matrix')
        self.assertEqual(run_audit(project),0)
        directory=publish(project,'GSM1')
        self.assertTrue((directory/'counts.tsv.gz').is_file())
        verify_package(directory)

    @unittest.skipUnless(shutil.which('Rscript'), 'Rscript unavailable; Python readback still tested')
    def test_base_r_readback(self):
        self.assertEqual(run_audit(self.root),0)
        directory=publish(self.root,'GSM1')
        code = """p <- commandArgs(TRUE)[1]
        f <- read.delim(gzfile(file.path(p,'matrix/raw_feature_bc_matrix/features.tsv.gz')),header=FALSE)
        b <- read.delim(gzfile(file.path(p,'matrix/raw_feature_bc_matrix/barcodes.tsv.gz')),header=FALSE)
        lines <- readLines(gzfile(file.path(p,'matrix/raw_feature_bc_matrix/matrix.mtx.gz')))
        lines <- lines[!startsWith(lines,'%')]
        dims <- scan(text=lines[1],quiet=TRUE)
        entries <- read.table(text=paste(lines[-1],collapse='\\n'))
        stopifnot(nrow(f)==dims[1],nrow(b)==dims[2],nrow(entries)==dims[3],sum(entries$V3)==15)
        cat('R_OPEN_FORMAT_PASS\\n')"""
        result=subprocess.run(['Rscript','--vanilla','-e',code,str(directory)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('R_OPEN_FORMAT_PASS',result.stdout)

    def test_failed_sample_does_not_change_other_delivery(self):
        self.assertEqual(run_audit(self.root),0)
        directory=publish(self.root,'GSM1')
        before=sha256(directory/'checksums.sha256')
        with self.assertRaises(IntegrityError): publish(self.root,'GSM999')
        self.assertEqual(sha256(directory/'checksums.sha256'),before)
        verify_package(directory)


if __name__=='__main__': unittest.main()
