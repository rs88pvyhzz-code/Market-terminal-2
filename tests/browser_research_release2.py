"""Offline, real-source Release 2 UI regression. Usage: script built-demo.html."""
from pathlib import Path
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import company_research
import research_intelligence
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
html=Path(sys.argv[1]).read_text();marker='window.MT_DATA = '
a=html.index(marker)+len(marker);b=html.index(';</script>',a)
payload=json.loads(html[a:b]);assert payload['demo'] is True
payload['generatedAt']='2026-11-09 23:00 UTC'
cs=json.loads((root/'tests/fixtures/release2_companies.json').read_text())['companies']
records=json.loads((root/'tests/fixtures/release2_evidence.json').read_text())['records']
for c in cs:
    c['research']=company_research.analyse(c['annual'],company_research.financial_sector(c))
    c['intelligence']=research_intelligence.compose(c,records[c['symbol']],cs,asof='2026-11-09')
updated={c['symbol']:c for c in cs}
payload['companies']=[updated.get(c['symbol'],c) for c in payload['companies']]
fx=json.loads((root/'tests/fixtures/shell_live_validation_2026_11_09.json').read_text())['fxObservation']
payload['history']=[r for r in payload['history'] if not(r['symbol']=='GBPUSD=X' and r['date']==fx['date'])]+[fx]
html=html[:a]+json.dumps(payload).replace('</','<\\/')+html[b:]

with sync_playwright() as p:
    executable=os.environ.get('CHROMIUM_EXECUTABLE')
    browser=p.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    assert page.locator('[data-workspace][role=tab]').count()==10
    page.locator('#tab-companies').dispatch_event('click')
    for symbol in ['SHEL.L','MSFT','HSBA.L']:
        page.locator('#company-pick').select_option(symbol);page.wait_for_timeout(70)
        assert page.locator('#research-nav [role=tab]').count()==6
        page.locator('#research-tab-0').click()
        assert page.locator('#research-executive .research-executive-card').count()==6
        assert 'EXECUTIVE RESEARCH SUMMARY' in page.locator('#research-executive').inner_text()
        page.locator('#research-tab-3').click()
        assert 'Five-year capital allocation' in page.locator('#research-business').inner_text()
        if symbol!='HSBA.L':assert 'Reported revenue segments' in page.locator('#research-business').inner_text()
        page.locator('#research-tab-4').click()
        assert 'MANAGEMENT & EARNINGS INTELLIGENCE' in page.locator('#research-outlook').inner_text()
        if symbol=='SHEL.L':
            assert '$23-$25 billion' in page.locator('#research-outlook').inner_text()
            assert '$24-$26 billion' in page.locator('#research-outlook').inner_text()
        if symbol=='HSBA.L':assert 'RoTE' in page.locator('#research-outlook').inner_text()
        for link in page.locator('#research-outlook a.research-source[href]').all():
            assert link.get_attribute('href').startswith('https://')
        page.locator('#research-tab-5').click()
        assert page.locator('#research-warning-priority > .small-scroll tbody tr').count()==5
        page.locator('#research-tab-2').click()
        assert page.locator('#research-valuation .t11-metric').count()==6
        assert page.locator('#research-valuation input').count()==0
        assert page.locator('#research-stress-panel').count()==0
        for width in [744,768,1024,1440]:
            page.set_viewport_size({'width':width,'height':1100})
            for i in [0,1,2,3,4,5]:
                page.locator('#research-tab-'+str(i)).click();page.wait_for_timeout(30)
                assert page.locator('#research-view-'+str(i)).is_visible()
                assert page.evaluate('document.body.scrollWidth<=innerWidth+1'),(symbol,width,i)
        page.locator('#research-tab-3').click()
        page.locator('#research-business .research-notebook').evaluate('(d)=>d.open=true')
        page.get_by_label('Competitive advantages & supporting evidence',exact=True).fill(symbol+' personal evidence note')
    page.locator('#company-pick').select_option('SHEL.L');page.locator('#research-tab-3').click()
    assert page.get_by_label('Competitive advantages & supporting evidence',exact=True).input_value()=='SHEL.L personal evidence note'
    page.locator('#research-tab-0').click();page.evaluate('scrollTo(0,0)');page.wait_for_timeout(50)
    page.screenshot(path='/tmp/research-r2-summary.png',full_page=True)
    page.set_viewport_size({'width':768,'height':1024});page.locator('#research-tab-2').click();page.wait_for_timeout(100)
    page.screenshot(path='/tmp/research-r2-stress-ipad.png',full_page=True)
    for key in ['overview','fx','equities','companies','bonds','analytics','etfs','economics','watchlist','quality']:
        page.locator('#tab-'+key).dispatch_event('click');page.wait_for_timeout(60)
        assert page.locator('#view-'+key).is_visible()
    assert not errors,errors
    print('PASS Release 2: primary issuer evidence, guidance, capital allocation, warning indicators, read-only valuations, personal notes and ten restored workspaces')
    browser.close()
