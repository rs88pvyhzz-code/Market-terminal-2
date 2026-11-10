"""Identified, paced public requests. Never retry/bypass a denied provider."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
import urllib.request

_LOCK=threading.Lock()
_LAST=0.0
_BLOCKED=set()

def get(url, limit=24_000_000, fields=None):
    global _LAST
    host=urlparse(url).hostname
    sec=host in ('www.sec.gov','data.sec.gov')
    identity=os.environ.get('SEC_USER_AGENT','').strip()
    try:
        if sec and not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',identity):
            raise OSError('SEC identification unavailable: configure SEC_USER_AGENT with organisation and contact email')
        if host in _BLOCKED:raise OSError('Provider denied this run; further requests stopped')
        with _LOCK:
            time.sleep(max(0,.3-(time.monotonic()-_LAST)))
            _LAST=time.monotonic()
        req=urllib.request.Request(url,headers={'User-Agent':identity if sec else 'MarketTerminal/2.1 public financial research', 'Accept':'text/html,application/json,application/xml'})
        with urllib.request.urlopen(req,timeout=18) as response:
            raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Document exceeds bounded download limit')
        record(url,True,None,fields)
        return raw
    except Exception as exc:
        status=exc.code if isinstance(exc,HTTPError) else None
        if status in (403,429):_BLOCKED.add(host)
        record(url,False,status,fields,str(exc))
        raise

def record(url,ok,status,fields,error=None):
    path=Path('.terminal_sources/requests.jsonl');path.parent.mkdir(parents=True,exist_ok=True)
    item={'runId':os.environ.get('GITHUB_RUN_ID'),'url':url,'attemptedAt':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'success':ok,'status':status,
          'affectedFields':fields or ['research evidence'],'error':(error or '')[:180]}
    with path.open('a') as out:out.write(json.dumps(item)+'\n')
