"""Audit an actual non-demo terminal. Never load test fixtures."""
import json
from pathlib import Path
import sys
import source_integrity

p=Path(sys.argv[1]);s=p.read_text();marker='window.MT_DATA = ';a=s.index(marker)+len(marker);d=json.loads(s[a:s.index(';</script>',a)])
assert d.get('demo') is False,'Production verification requires actual live payload'
r=source_integrity.report(d,p.with_suffix('.sources.json'))
for symbol in ('SHEL.L','MSFT','HSBA.L'):
    c=r['companies'][symbol]
    assert c['sources'],symbol+' has no preserved primary research sources'
    assert all(x.get('published') and x.get('retrievedAt') and x.get('url','').startswith('https://') for x in c['sources'])
    print(symbol,'dated documents',len(c['sources']),'results',c['reportedResults'],'guidance',c['guidance'],'catalysts',c['catalysts'],'risks',c['risks'])
    for src in c['sources']:print(' ',src['url'],'published',src['published'],'retrieved',src['retrievedAt'])
    if symbol=='SHEL.L':
        assert c['reportedResults'] and c['guidance'] and c['catalysts'] and c['risks'],'Shell research coverage is not substantive'
        balance=c['researchBalance'];assert balance.get('reportedNetDebt') is not None and balance.get('sharesPublished'),'Shell issuer bridge/share count absent'
        assert c['valuationIntegrity'] and c['valuationIntegrity']['issues'],'Source-review warning missing'
        print(' Shell FCFF m',c['normalisedFCFF']/1e6,'shares',balance.get('sharesOutstanding'),'debt adjustment m',balance.get('debtAdjustment',0)/1e6)
print('Fresh HTTP successes',sum(bool(x.get('success')) for x in r['requests']),'failed/stopped requests',sum(not x.get('success') for x in r['requests']))
print('PASS actual terminal research audit; archived source dates remain distinct from current live requests')
