"""Persist actual source responses with original timestamps, never test fixtures.

The checked-in recovery archive contains real responses collected 9 November.
Newer runner/Pages cache entries always win. No market values are embedded in code.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parent
NAME='primary_source_archive.json.gz'
PREFIXES=('.terminal_filings/','.terminal_research/documents/')
MAX_SIZE=110_000_000

def pack(root=ROOT):
    entries={}
    for prefix in PREFIXES:
        for f in (Path(root)/prefix).glob('*.json'):
            raw=f.read_text();json.loads(raw)
            entries[str(f.relative_to(root))]={'sha256':hashlib.sha256(raw.encode()).hexdigest(),'content':raw}
    return gzip.compress(json.dumps({'schema':1,'entries':entries},separators=(',',':')).encode(),mtime=0)

def restore_bytes(blob,root=ROOT):
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as z:raw=z.read(MAX_SIZE+1)
    if len(raw)>MAX_SIZE:raise ValueError('Source archive exceeds bound')
    data=json.loads(raw);count=0
    for name,entry in data['entries'].items():
        if not name.startswith(PREFIXES) or '..' in Path(name).parts or not name.endswith('.json'):raise ValueError('Unsafe archive path')
        content=entry['content']
        if hashlib.sha256(content.encode()).hexdigest()!=entry['sha256']:raise ValueError('Source hash mismatch')
        incoming=json.loads(content);target=Path(root)/name
        def stamp(d):
            # Supplement has independent verified balance/capital dates; merge below.
            return str(d.get('retrievedAt') or '')
        try:old=json.loads(target.read_text())
        except (OSError,ValueError):old={}
        if name.endswith('shell_supplemental.json') and old:
            merged={**incoming,**old};merged['documents']={**incoming.get('documents',{}),**old.get('documents',{})}
            for key,date in [('balance','period'),('capital','sharesPeriod')]:
                a=incoming.get(key) or {};b=old.get(key) or {}
                merged[key]=a if (a.get(date,''),stamp(a))>(b.get(date,''),stamp(b)) else b or a
            content=json.dumps(merged,separators=(',',':'))
        elif old and stamp(old)>=stamp(incoming):continue
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content);count+=1
    return count

def restore(root=ROOT,published=True):
    root=Path(root);count=0
    seed=root/'verified_sources'/NAME
    if seed.exists():count+=restore_bytes(seed.read_bytes(),root)
    repo=os.environ.get('GITHUB_REPOSITORY','')
    if published and '/' in repo:
        owner,name=repo.split('/',1)
        try:
            req=urllib.request.Request(f'https://{owner}.github.io/{name}/{NAME}',headers={'User-Agent':'MarketTerminal/2.1'})
            with urllib.request.urlopen(req,timeout=18) as r:blob=r.read(12_000_001)
            if len(blob)>12_000_000:raise ValueError('Compressed source archive exceeds bound')
            count+=restore_bytes(blob,root)
        except Exception as exc:print('Published source archive unavailable; local verified cache retained: '+str(exc)[:100],flush=True)
    return count

def publish(root=ROOT):
    path=Path(root)/'public'/NAME;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(pack(root))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['restore','publish']);a=p.parse_args()
    if a.action=='restore':print('Restored actual source responses:',restore())
    else:publish()
