#!/usr/bin/env python3
"""Adversarial tests for count bodies, exact inputs, content receipts and release recovery."""
import argparse
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_processed_outputs as audit
from artifact_integrity import (IntegrityError, atomic_json, capture_inputs, check_receipt,
                                context, release_files, sha256, verified_inputs)
from project_layout import default_policy, write_storage_policy, write_tsv_atomic, read_tsv
from self_test import final_outputs
from publish_sample import publish, verify_delivery


def fixture(root, gsm='GSM1', run='SRR1', product='matrix_10x'):
    root.mkdir(parents=True, exist_ok=True)
    write_storage_policy(root, default_policy('GSE1',False,assay_type='RNA-seq',raw_file_type='FASTQ',
                                               final_product=product,confirmed_at='fixture'))
    files=[]
    for role in ['R1','R2']:
        path=root/f'temporary/{gsm}/fastq/{run}_{role}.fastq.gz'
        path.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(path,'wt') as h: h.write('@read/1\nACGT\n+\nIIII\n')
        files.append(path)
    source=dict(gse='GSE1',gsm=gsm,srr=run,library_layout='PAIRED',expected_spots='1',
                selected_source='ena_fastq',selected_provenance='ARCHIVE_GENERATED_FASTQ',
                selected_urls='https://example.invalid/R1;https://example.invalid/R2',
                selected_bytes=';'.join(str(p.stat().st_size) for p in files),
                selected_md5=';'.join(hashlib.md5(p.read_bytes()).hexdigest() for p in files),
                read_roles='R1;R2',final_product=product)
    write_tsv_atomic(root/'metadata/source_manifest.tsv',list(source),[source])
    payload={key:source[col] for key,col in [('source','selected_source'),('urls','selected_urls'),('bytes','selected_bytes'),('md5','selected_md5'),('roles','read_roles'),('final_product','final_product')]}
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    row={**source,'source':'ena_fastq','provenance':'ARCHIVE_GENERATED_FASTQ','validation':'PASS','source_fingerprint':fingerprint,
         'retained_files':';'.join(p.relative_to(root).as_posix() for p in files),
         'retained_bytes':source['selected_bytes'],'retained_md5':source['selected_md5']}
    write_tsv_atomic(root/f'metadata/download_manifests/{gsm}.tsv',list(row),[row])
    marker=root/f'reports/status/{run}.complete'; marker.parent.mkdir(parents=True,exist_ok=True)
    marker.write_text(f'validation\tPASS\nsource_fingerprint\t{fingerprint}\n')
    routing={'gse':'GSE1','gsm':gsm,'modality':'bulk_rnaseq' if product=='gene_count_matrix' else 'scRNAseq','workflow':'convert','assay_type':'RNA-seq','raw_file_type':'FASTQ'}
    write_tsv_atomic(root/'metadata/assay_routing.tsv',list(routing),[routing])
    capture_inputs(root,gsm)
    if product == 'gene_count_matrix':
        from export_star_counts import export
        path=root/f'processed/{gsm}/counts/ReadsPerGene.out.tab'
        path.parent.mkdir(parents=True)
        path.write_text('gene1\t3\t2\t1\ngene2\t4\t1\t3\n')
        export(root,gsm)
    else:
        final_outputs(root,gsm)
    prov={'gse':'GSE1','gsm':gsm,'tool':'STARsolo','tool_version':'fixture','input_fastq':row['retained_files'],
          'output_matrix':f'processed/{gsm}/counts/counts.tsv.gz' if product=='gene_count_matrix' else f'processed/{gsm}/matrix_10x/raw_feature_bc_matrix/matrix.mtx.gz','validated_at':'fixture','reference':'fixture genome/annotation','counting_strategy':'UMI exon counts'}
    write_tsv_atomic(root/'reports/conversion_provenance.tsv',list(prov),[prov])
    return files


def run_audit(root, gsm='GSM1'):
    with patch('sys.argv',['audit','--root',str(root),'--gsm',gsm]),patch.object(audit,'refresh_report'):
        return audit.main()


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='geo-integrity-')
        self.root=Path(self.temp.name)
        self.files=fixture(self.root)
    def tearDown(self): self.temp.cleanup()
    def matrix(self,text):
        path=self.root/'processed/GSM1/matrix_10x/raw_feature_bc_matrix/matrix.mtx.gz'
        with gzip.open(path,'wt') as h: h.write(text)
    def test_malformed_matrix_body(self):
        for body in ['3 3 2\n1 1 2\n','3 3 1\n4 1 -2\n','3 3 1\n1 1 -2\n','3 3 2\n1 1 2\n1 1 3\n']:
            self.matrix('%%MatrixMarket matrix coordinate integer general\n'+body)
            self.assertEqual(run_audit(self.root),1)
    def test_barcode_and_count_relationship(self):
        path=self.root/'processed/GSM1/matrix_10x/filtered_feature_bc_matrix/barcodes.tsv.gz'
        with gzip.open(path,'wt') as h: h.write('unknown\nbc2\n')
        self.assertEqual(run_audit(self.root),1)
    def test_raw_changed_before_conversion(self):
        self.files[0].write_bytes(b'damaged')
        with self.assertRaises(IntegrityError): verified_inputs(self.root,'GSM1')
        self.assertEqual(run_audit(self.root),1)
    def test_exact_mates_not_substrings(self):
        path=self.root/'reports/conversion_provenance.tsv'; rows=read_tsv(path)
        rows[0]['input_fastq']=rows[0]['input_fastq'].split(';')[0]
        write_tsv_atomic(path,list(rows[0]),rows)
        self.assertEqual(run_audit(self.root),1)
    def test_stale_pass_rejected(self):
        self.assertEqual(run_audit(self.root),0)
        publish(self.root,'GSM1')
        target=self.root/'processed/GSM1/matrix_10x/raw_feature_bc_matrix/features.tsv.gz'
        target.write_bytes(b'changed after PASS')
        with self.assertRaises(IntegrityError): check_receipt(self.root,'GSM1')
        with self.assertRaises(IntegrityError): release_files(self.root,'GSM1',[p.relative_to(self.root).as_posix() for p in self.files])
        self.assertTrue(all(p.exists() for p in self.files))
    def test_unlink_interruption_resumes(self):
        self.assertEqual(run_audit(self.root),0)
        publish(self.root,'GSM1')
        names=[p.relative_to(self.root).as_posix() for p in self.files]
        def crash(_): raise OSError('simulated process interruption after unlink')
        with self.assertRaises(OSError): release_files(self.root,'GSM1',names,after_unlink=crash)
        self.assertEqual(sum(p.exists() for p in self.files),1)
        journal=release_files(self.root,'GSM1',[name for name in names if (self.root/name).exists()])
        self.assertEqual(journal['status'],'released')
        self.assertEqual(set(journal['deleted']),set(names))
        self.assertTrue(all(not p.exists() for p in self.files))
    def test_changed_raw_during_release_rejected(self):
        self.assertEqual(run_audit(self.root),0)
        publish(self.root,'GSM1')
        names=[p.relative_to(self.root).as_posix() for p in self.files]
        def crash(_): raise OSError('crash')
        with self.assertRaises(OSError): release_files(self.root,'GSM1',names,after_unlink=crash)
        self.files[1].write_bytes(b'changed')
        with self.assertRaises(IntegrityError): release_files(self.root,'GSM1',names[1:])
        self.assertTrue(self.files[1].exists())


if __name__=='__main__': unittest.main()
