"""Audit a real collected build. Coverage failures are reported, never fixture-filled."""
import datetime as dt
import json
from pathlib import Path
import re
import sys
from market_briefing import timestamp,THRESHOLDS

def verify(path):
    html=Path(path).read_text();match=re.search(r'window\.MT_DATA\s*=\s*',html)
    data=json.JSONDecoder().raw_decode(html[match.end():])[0]
    assert data.get('demo') is False,'Production verification cannot use demo fixtures'
    stories=data.get('news',[]);ids=[s['id'] for s in stories];assert len(ids)==len(set(ids))
    now=timestamp(data['generatedAt'])
    for s in stories:
        assert s['url'].startswith('https://') and s.get('published')
        if not s['archived']:
            assert s.get('retrievedAt'),'Current news must have recorded retrieval provenance'
            assert 0<=(now-timestamp(s['published'])).total_seconds()<=THRESHOLDS['maxNewsAgeHours']*3600
            assert not s.get('restored')
    companies=[]
    for symbol in ['SHEL.L','MSFT','HSBA.L']:
        company=next((c for c in data.get('companies',[]) if c['symbol']==symbol),{})
        intel=company.get('intelligence',{})
        companies.append({'symbol':symbol,'issuerSources':[{'url':s.get('url'),'published':s.get('published'),'retrievedAt':s.get('retrievedAt')} for s in intel.get('sources',[])],'guidanceComparisons':sum(bool(g.get('previous')) for g in intel.get('guidance',[])),'newsCount':len(intel.get('news',[]))})
    report={'kind':'ACTUAL PRODUCTION COLLECTORS — NO TEST FIXTURES','buildDate':data['generatedAt'],'verifiedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'currentNews':sum(not s['archived'] for s in stories),'archivedNews':sum(s['archived'] for s in stories),'feeds':data.get('newsDiagnostics',[]),'companies':companies,'alerts':data.get('marketBriefing',{}).get('alerts',[]),'limitations':data.get('marketBriefing',{}).get('limitations',[])}
    Path('public').mkdir(exist_ok=True);Path('public/news_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':verify(sys.argv[1])
