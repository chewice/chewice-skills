#!/usr/bin/env python3
"""Export one GSM's STAR counts as portable TSV.gz; preserve unknown strand columns."""
import argparse
import csv
import gzip
import os
from pathlib import Path


def export(root,gsm,strandedness='unknown'):
    source=root/f'processed/{gsm}/counts/ReadsPerGene.out.tab'
    target=root/f'processed/{gsm}/counts/counts.tsv.gz'
    columns={'unstranded':1,'forward':2,'reverse':3}
    selected=list(columns) if strandedness=='unknown' else [strandedness]
    rows=[]; seen=set()
    with source.open() as handle:
        for line in handle:
            fields=line.rstrip('\r\n').split('\t')
            if fields[0].startswith('N_'): continue
            if len(fields)!=4 or not fields[0] or fields[0] in seen or any(not value.isdigit() for value in fields[1:]):
                raise ValueError('Invalid/duplicate STAR gene counts')
            seen.add(fields[0]); rows.append([fields[0],*[fields[columns[key]] for key in selected]])
    if not rows: raise ValueError('Empty gene counts')
    tmp=target.with_name(target.name+'.tmp')
    with tmp.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz:
            gz.write(('gene_id\t'+'\t'.join(selected)+'\n').encode())
            for row in rows: gz.write(('\t'.join(row)+'\n').encode())
        raw.flush(); os.fsync(raw.fileno())
    os.replace(tmp,target)
    return target


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--gsm',required=True)
    parser.add_argument('--strandedness',choices=['unknown','unstranded','forward','reverse'],default='unknown')
    args=parser.parse_args()
    print(export(args.root.resolve(),args.gsm,args.strandedness))


if __name__=='__main__': main()
