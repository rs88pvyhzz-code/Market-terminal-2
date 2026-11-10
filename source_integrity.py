"""Dated valuation coverage. Does not change accounting or DCF calculations."""
import datetime as dt
import json
from pathlib import Path

FIELDS=('operatingProfit','taxExpense','pretaxProfit','depreciation','capex','workingCapitalCashChange')

def assess(c,asof=None):
    today=asof or dt.date.today().isoformat();issues=[];details=[]
    balance=c.get('researchBalance') or {}
    if c.get('filingWarning'):issues.append('Primary-source refresh failed; retained verified inputs keep their original dates.')
    for key in ['totalDebt','cash','sharesOutstanding']:
        if balance.get(key) is None:issues.append('Missing '+key)
    if 'unverified' in str(balance.get('sharesSource','')).lower() or not balance.get('sharesPublished'):
        issues.append('Ordinary share count has not been verified against a dated issuer announcement.')
    if 'debtAdjustment' not in balance:issues.append('Debt-related adjustment is unverified; the model zero is an assumption, not a reported figure.')
    unverified=[]
    for row in (c.get('annual') or [])[:3]:
        for key in FIELDS:
            p=row.get('provenance',{}).get(key,{})
            details.append({'field':key,'period':row.get('fiscalEnd'),'source':p.get('source'),'retrievedAt':p.get('retrievedAt'),'url':p.get('url')})
            if row.get(key) is None or not p.get('retrievedAt') or 'SEC' not in p.get('source',''):unverified.append(key)
    if unverified:issues.append('FCFF includes secondary-source or missing components: '+', '.join(sorted(set(unverified)))+'. Review the component bridge.')
    for key in ['retrievedAt','sharesRetrievedAt']:
        try:age=(dt.date.fromisoformat(today)-dt.date.fromisoformat(str(balance.get(key,''))[:10])).days
        except ValueError:age=999
        if age>7:issues.append('Some valuation inputs were last retrieved over seven days ago.');break
    return {'status':'review_required' if issues else 'dated_sources_available','asof':today,'issues':list(dict.fromkeys(issues)),
        'components':details,'balancePeriod':balance.get('period'),'balanceRetrievedAt':balance.get('retrievedAt'),
        'sharesPeriod':balance.get('sharesPeriod'),'sharesRetrievedAt':balance.get('sharesRetrievedAt')}


def annotate(companies,asof=None):
    for c in companies:c['valuationIntegrity']=assess(c,asof)


def report(payload,output):
    result={'generatedAt':payload.get('generatedAt'),'demo':payload.get('demo'),'companies':{}}
    for c in payload.get('companies',[]):
        if c['symbol'] not in ('SHEL.L','MSFT','HSBA.L'):continue
        d=c.get('intelligence') or {};result['companies'][c['symbol']]={'valuationIntegrity':c.get('valuationIntegrity'),
            'normalisedFCFF':(c.get('research') or {}).get('normalisedFCFF'),'researchBalance':c.get('researchBalance'),
            'sources':d.get('sources',[]),'reportedResults':len(d.get('reportedResults',[])),'guidance':len(d.get('guidance',[])),
            'catalysts':len(d.get('topics',{}).get('catalysts',[])),'risks':len(d.get('topics',{}).get('risks',[])), 'warnings':d.get('gaps',[])}
    log=Path('.terminal_sources/requests.jsonl')
    result['requests']=[json.loads(s) for s in log.read_text().splitlines()[-500:]] if log.exists() else []
    import hashlib
    for request in result['requests']:
        url=request['url'];cache=Path('.terminal_research/documents')/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        try:request['lastVerifiedRetrievedAt']=json.loads(cache.read_text()).get('retrievedAt')
        except (OSError,ValueError):
            request['lastVerifiedRetrievedAt']=None
            for symbol,cik in [('SHEL.L','0001306965'),('MSFT','0000789019'),('HSBA.L','0001089113')]:
                if 'companyfacts/CIK'+cik in url:
                    try:request['lastVerifiedRetrievedAt']=json.loads((Path('.terminal_filings')/(symbol+'.json')).read_text()).get('retrievedAt')
                    except (OSError,ValueError):pass
            try:
                doc=json.loads(Path('.terminal_filings/shell_supplemental.json').read_text()).get('documents',{}).get(url,{})
                request['lastVerifiedRetrievedAt']=request['lastVerifiedRetrievedAt'] or doc.get('retrievedAt')
            except (OSError,ValueError):pass
    Path(output).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result
