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
    page.route('http://localhost:8765/**',lambda route:route.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    assert page.locator('[data-workspace][role=tab]').count()==8
    page.locator('#tab-equities').click();page.locator('#sub-equities-research').click()
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
        for link in page.locator('#research-outlook a.research-source[href]').all():assert link.get_attribute('href').startswith('https://')
        page.locator('#research-tab-5').click()
        assert page.locator('#research-warning-priority > .small-scroll tbody tr').count()==5
        assert 'unassessed' in page.locator('#research-warning-priority').inner_text()
        page.locator('#research-tab-2').click()
        if symbol=='HSBA.L':
            assert 'Corporate FCFF recession modelling is excluded' in page.locator('#research-stress-panel').inner_text()
            assert page.locator('#research-stress-panel input').count()==0
        else:
            base_rows=page.locator('#research-stress-panel > div[aria-live] > .small-scroll tbody tr')
            base=float(base_rows.nth(0).locator('td').nth(1).inner_text().replace(',',''))
            stress=float(base_rows.nth(1).locator('td').nth(1).inner_text().replace(',',''))
            assert stress<base,(symbol,base,stress)
            if symbol=='SHEL.L':
                assert abs(base-43.69)<.01  # Release 1 validated base remains unchanged
                evidence=page.locator('#research-stress-panel details').filter(has=page.locator('summary',has_text='Sector-specific evidence and sensitivity limits'))
                coefficient=page.get_by_label('Annual FCFF impact per +10% commodity price (reporting millions) · user assumption',exact=True)
                assert coefficient.is_visible()
                assert evidence.get_attribute('open') is None
                evidence.locator(':scope > summary').click()
                assert 'impairment' in evidence.inner_text()
                evidence.locator(':scope > summary').click()
                assert coefficient.is_visible()
                assert 'Commodity-linked DCF unavailable' in page.locator('#research-stress-panel').inner_text()
                page.get_by_label('Annual FCFF impact per +10% commodity price (reporting millions) · user assumption',exact=True).fill('1000')
                assert 'coefficient is not issuer guidance' in page.locator('#research-stress-panel').inner_text()
            page.get_by_label('First-year revenue shock (%)',exact=True).fill('')
            assert 'Stress value unavailable' in page.locator('#research-stress-panel').inner_text()
            page.get_by_label('First-year revenue shock (%)',exact=True).fill('-20')
        for width in [744,768,1024,1440]:
            page.set_viewport_size({'width':width,'height':1100})
            for i in [0,1,2,3,4,5]:
                page.locator('#research-tab-'+str(i)).click();page.wait_for_timeout(30)
                assert page.locator('#research-view-'+str(i)).is_visible()
                assert page.evaluate('document.body.scrollWidth<=innerWidth'),(symbol,width,i)
        page.locator('#research-tab-3').click()
        page.locator('#research-business .research-notebook').evaluate('(d)=>d.open=true')
        page.get_by_label('Competitive advantages & supporting evidence',exact=True).fill(symbol+' personal evidence note')
    page.locator('#company-pick').select_option('SHEL.L');page.locator('#research-tab-3').click()
    assert page.get_by_label('Competitive advantages & supporting evidence',exact=True).input_value()=='SHEL.L personal evidence note'
    page.locator('#research-tab-0').click();page.evaluate('scrollTo(0,0)');page.wait_for_timeout(50)
    page.screenshot(path='/tmp/research-r2-summary.png',full_page=True)
    page.set_viewport_size({'width':768,'height':1024});page.locator('#research-tab-2').click();page.wait_for_timeout(100);page.evaluate('scrollTo(0,0)')
    page.screenshot(path='/tmp/research-r2-stress-ipad.png',full_page=True)
    for key in ['overview','fx','equities','bonds','analytics','etfs','economics','watchlist','quality','companies']:
        page.locator('#tab-'+({'companies':'equities','analytics':'fx'}.get(key,key))).click()
        if key in ['companies','analytics']:page.locator('#sub-'+('equities-research' if key=='companies' else 'fx-analytics')).click()
        page.wait_for_timeout(60)
        assert page.locator('#view-'+({'companies':'equities','analytics':'fx'}.get(key,key))).is_visible()
    assert not errors,errors
    print('PASS Release 2: real source evidence, guidance comparison, allocation, five warning indicators, unchanged Shell base, real downturn, commodity gap/assumption, HSBC exclusion, personal notes and all workspaces/layouts')
    browser.close()
