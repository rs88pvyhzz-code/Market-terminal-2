"""Independent DMO network/freshness audit. No fabricated prices or yields."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import gilt_market
if '--existing' in sys.argv:
    latest=json.loads(gilt_market.LATEST.read_text());rows=latest['bonds'];warnings=[]
    existing=json.loads(Path('.terminal_sources/dmo_verification.json').read_text());fresh=existing.get('downloadedFresh',False)
else:rows,history,warnings,fresh=gilt_market.collect(None,SimpleNamespace(offline=False))
path=Path('.terminal_sources/dmo_verification.json')
d=json.loads(path.read_text()) if path.exists() else {}
print(json.dumps(d,indent=2));print('Warnings:',warnings)
print('Fresh official download:',bool(fresh),'quotation:',d.get('quotationDate'),'expected:',d.get('expectedQuotationDate'))
# A cached or stale report cannot pass this dedicated check merely because the site builds.
if not fresh or d.get('stale') or not d.get('calendarCovered'):sys.exit(1)
# Reuse the exact existing gross/net/tax-equivalent maths against current quotes.
import subprocess,tempfile
html=Path('terminal_template.html').read_text();a=html.index('function giltDay(');b=html.index('const ladderState',a)
model=html[a:b].replace("document.getElementById('mt-gilt-tax-rate')?.value",'undefined')
js="const D={generatedAt:"+json.dumps(d['quotationDate'])+"};\n"+model+'\nconst rows='+json.dumps(rows)+''';
let reconciled=0,total=0;const exceptions=[];
for(const g of rows){if(g.indexLinked)continue;total++;
 const v=giltValuation(g,g.askClean,g.asOf,g.askDirty),n0=giltNetYield(g,g.askClean,0,g.asOf,g.askDirty),n40=giltNetYield(g,g.askClean,40,g.asOf,g.askDirty);
 if(!v||Math.abs(n0-v.ytm)>1e-6||!(n40<=n0+1e-6)||!Number.isFinite(n40/.6))throw Error('Yield regression '+g.isin);
 const cf=giltCashflows(g,g.asOf,true);if(cf&&Math.abs(cf.accrued-(g.askDirty-g.askClean))<.0005)reconciled++;else exceptions.push({isin:g.isin,name:g.name});
}
if(reconciled/total<.95)throw Error('Accrued reconciliation failed');
console.log('Current official DMO quotes: gross/net/zero-tax/gross-equivalent verified; accrued reconciles '+reconciled+'/'+total);
console.log(JSON.stringify({conventional:total,accruedReconciled:reconciled,modelConventionExceptions:exceptions}));
'''
with tempfile.NamedTemporaryFile('w',suffix='.js') as f:
 f.write(js);f.flush();result=subprocess.run(['node',f.name],check=True,text=True,capture_output=True)
 print(result.stdout);d['yieldValidation']=json.loads(result.stdout.strip().splitlines()[-1]);path.write_text(json.dumps(d,indent=2)+'\n')
