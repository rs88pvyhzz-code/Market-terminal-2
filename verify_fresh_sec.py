"""Cache-independent SEC verification; run inside Actions with the real identity.

Fresh means a successful network download now, not a new fiscal disclosure.
A provider denial stops further SEC requests, including the subsequent build.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import company_filings
import research_intelligence as research
import source_transport


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class FreshSources:
    """No disk-cache reads and no stale fallback; duplicate URLs reuse this run only."""
    def __init__(self,root):self.root=Path(root);self.downloads={}
    def get(self,url):
        if not research.valid_source(url):raise ValueError('Unapproved public source')
        if url in self.downloads:
            item=self.downloads[url];return item['body'],item['retrievedAt']
        raw=source_transport.get(url,fields=['fresh SEC source verification'])
        body=raw.decode('utf-8');stamp=research.now_iso()
        item={'url':url,'body':body,'retrievedAt':stamp,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        self.downloads[url]=item
        directory=self.root/'.terminal_research/documents';directory.mkdir(parents=True,exist_ok=True)
        (directory/(hashlib.sha256(url.encode()).hexdigest()+'.json')).write_text(json.dumps({'body':body,'retrievedAt':stamp},separators=(',',':')))
        return body,stamp


def run(root=Path(__file__).resolve().parent):
    root=Path(root);source=FreshSources(root)
    out={'runId':os.environ.get('GITHUB_RUN_ID'),'runAttempt':os.environ.get('GITHUB_RUN_ATTEMPT','1'),'startedAt':research.now_iso(),
         'identityConfigured':bool(os.environ.get('SEC_USER_AGENT','').strip()),
         'definition':'Fresh download = network response in this probe; it does not imply a new financial period or changed disclosure.',
         'companies':{}}
    cache=root/'.terminal_research'/research.CACHE_NAME
    try:records=json.loads(cache.read_text()).get('records',{})
    except (OSError,ValueError):records={}
    for symbol,(cik,_,currency) in company_filings.ISSUERS.items():
        item={'facts':{},'research':{},'recoveredDocuments':[{k:d.get(k) for k in ('url','published','period','retrievedAt')} for d in records.get(symbol,{}).get('documents',[])]}
        out['companies'][symbol]=item
        if source_transport.sec_denied():
            item['facts']={'status':'not_attempted_provider_denied'};item['research']={'status':'not_attempted_provider_denied'}
            continue
        url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
        facts_path=root/'.terminal_filings'/(symbol+'.json')
        try:
            try:prior=json.loads(facts_path.read_text())
            except (OSError,ValueError):prior={}
            body,stamp=source.get(url);data=json.loads(body)
            if int(data.get('cik',-1))!=int(cik) or not isinstance(data.get('facts'),dict):raise ValueError('Unexpected issuer facts response')
            rows=company_filings.parse_facts(data,symbol,stamp)
            if not rows:raise ValueError('No usable annual facts in response')
            facts_path.parent.mkdir(parents=True,exist_ok=True)
            facts_path.write_text(json.dumps({'data':data,'retrievedAt':stamp},separators=(',',':')))
            item['facts']={'status':'fresh_download','url':url,'retrievedAt':stamp,'httpStatus':200,
                           'sha256':source.downloads[url]['sha256'],'annualPeriods':[r['fiscalEnd'] for r in rows],
                           'contentChangedSinceCache':digest(data)!=digest(prior['data']) if prior.get('data') else None,
                           'priorRetrievedAt':prior.get('retrievedAt')}
        except Exception as exc:
            item['facts']={'status':'download_failed','url':url,'error':str(exc)[:180],
                           'httpStatus':getattr(exc,'code',None),'priorRetrievedAt':prior.get('retrievedAt')}
        if source_transport.sec_denied():
            item['research']={'status':'not_attempted_provider_denied'};continue
        try:
            c={'symbol':symbol,'financialCurrency':currency}
            record=research.parse_sources(c,source,previous={},asof=dt.date.today().isoformat())
            sec_docs=[d for d in record.get('documents',[]) if urlparse(d['url']).hostname in ('www.sec.gov','data.sec.gov') and d['url'] in source.downloads]
            subs=f'https://data.sec.gov/submissions/CIK{cik}.json'
            item['research']={'status':'fresh_documents' if sec_docs else 'no_fresh_SEC_documents',
                              'submissionsDownloaded':subs in source.downloads,
                              'documents':[research.source_ref(d) for d in sec_docs], 'warnings':record.get('warnings',[])}
            if sec_docs:
                previous=records.get(symbol,{})
                urls={d['url'] for d in record['documents']}
                record['documents']=(record['documents']+[d for d in previous.get('documents',[]) if d['url'] not in urls])[:8]
                # Let the normal collector recompute peer/competitor context with
                # the full universe; verification must not replace that analysis.
                record.update(checkedAt=None,attemptedAt=None)
                records[symbol]=record
        except Exception as exc:item['research']={'status':'download_failed','error':str(exc)[:180]}
    cache.parent.mkdir(parents=True,exist_ok=True)
    cache.write_text(json.dumps({'schema':research.SCHEMA,'records':records},separators=(',',':')))
    out['finishedAt']=research.now_iso();out['secRequestsStoppedAfterDenial']=source_transport.sec_denied()
    out['downloads']=[{k:v for k,v in d.items() if k!='body'} for d in source.downloads.values()]
    path=root/'.terminal_sources/fresh_sec_verification.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2)+'\n')
    print('SEC identity configured:',out['identityConfigured'])
    for symbol,item in out['companies'].items():
        print(symbol,'facts:',json.dumps(item['facts'],sort_keys=True),'research:',json.dumps(item['research'],sort_keys=True))
        print(symbol,'recovered cached documents:',len(item['recoveredDocuments']),'; original dates retained separately in artifact')
    print('Fresh network downloads:',len(out['downloads']),'; SEC stopped after denial:',out['secRequestsStoppedAfterDenial'])
    return out


if __name__=='__main__':run()
