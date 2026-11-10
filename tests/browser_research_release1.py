"""Optional Playwright regression: python tests/browser_research_release1.py HTML.

Uses real sourced company fixtures in an explicitly synthetic market demo.
No external data requests; changes only the in-memory browser test fixture.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import company_research
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
html=Path(sys.argv[1]).read_text()
marker='window.MT_DATA = '
a=html.index(marker)+len(marker);b=html.index(';</script>',a)
payload=json.loads(html[a:b]);assert payload['demo'] is True
payload['generatedAt']='2026-11-09 23:00 UTC'
validation=json.loads((root/'tests/fixtures/shell_live_validation_2026_11_09.json').read_text())
payload['history']=[r for r in payload['history'] if not(r['symbol']=='GBPUSD=X' and r['date']=='2026-11-09')]+[validation['fxObservation']]
companies=json.loads((root/'tests/fixtures/release1_companies.json').read_text())['companies']
with tempfile.TemporaryDirectory() as directory:
    with patch('company_profiles._restore_published',return_value={}):
        company_research.enrich(companies,[],directory,asof='2026-11-09T23:00:00+00:00')
new={c['symbol']:c for c in companies}
payload['companies']=[new.get(c['symbol'],c) for c in payload['companies']]
html=html[:a]+json.dumps(payload).replace('</','<\\/')+html[b:]

with sync_playwright() as p:
    executable=os.environ.get('CHROMIUM_EXECUTABLE')
    browser=p.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda route:route.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    page.locator('#tab-equities').click();page.locator('#sub-equities-research').click()
    assert page.locator('#research-nav button').count()==6
    for symbol in ['SHEL.L','MSFT','HSBA.L']:
        page.locator('#company-pick').select_option(symbol)
        page.wait_for_timeout(80)
        page.locator('#research-tab-0').click()
        assert page.locator('#research-overview .research-card').count()==6
        page.locator('#research-tab-1').click();page.wait_for_timeout(80)
        assert '5 of 5 annual periods sourced' in page.locator('#research-statements').inner_text()
        assert page.locator('#research-statements button',has_text='10Y').is_disabled()
        assert page.locator('#research-financial-chart svg').count()==1
        page.locator('#research-tab-2').click()
        if symbol=='HSBA.L':
            assert 'Standard FCFF DCF excluded' in page.locator('#research-valuation').inner_text()
            assert page.locator('#research-valuation input').count()==0
        else:
            assert page.get_by_label('Normalised FCFF (reporting currency, millions)',exact=True).input_value()!=''
            assert page.get_by_label('Debt (reporting currency, millions)',exact=True).input_value()!=''
            assert page.get_by_label('Shares outstanding (absolute count)',exact=True).input_value()!=''
            assert 'BASE' in page.locator('#research-valuation').inner_text()
            if symbol=='SHEL.L':
                assert page.get_by_label('Shares outstanding (absolute count)',exact=True).input_value()=='5701440412'
                assert page.get_by_label('Debt-related adjustment (reporting millions)',exact=True).input_value()=='83'
                assert '43.69' in page.locator('#research-valuation').inner_text()
                assert '2026-10-30' in page.locator('#research-valuation').inner_text()
            page.get_by_label('Base FCFF growth (%)',exact=True).fill('6')
            assert 'User assumption / override' in page.locator('#research-valuation').inner_text()
        for width in [390,768,1024,1440]:
            page.set_viewport_size({'width':width,'height':1000})
            for i in range(6):
                page.locator('#research-tab-'+str(i)).click();page.wait_for_timeout(30)
                assert page.locator('#research-view-'+str(i)).is_visible()
                assert page.evaluate('document.body.scrollWidth<=innerWidth'),(symbol,width,i)
        page.locator('#research-tab-5').click()
        assert page.locator('#forensic-symbol').inner_text()==symbol
    # Explicit old-balance review; dates cannot be silently treated as current.
    page.evaluate("window.MT_DATA.companies.find(c=>c.symbol==='SHEL.L').researchBalance.period='2024-12-31'")
    page.locator('#company-pick').select_option('SHEL.L');page.locator('#research-tab-2').click()
    assert 'Valuation paused' in page.locator('#research-valuation').inner_text()
    page.get_by_label('Use dated balances after review',exact=True).check()
    assert 'BASE' in page.locator('#research-valuation').inner_text()
    page.get_by_label('Shares outstanding (absolute count)',exact=True).fill('')
    assert 'Incomplete sourced inputs' in page.locator('#research-valuation').inner_text()
    page.locator('#research-valuation button',has_text='RESET TO SOURCED INPUTS').click()
    assert 'Valuation paused' in page.locator('#research-valuation').inner_text()
    # Notes and legacy workspaces remain usable.
    page.locator('#research-tab-3').click()
    page.locator('#research-business .research-notebook').evaluate('(d)=>d.open=true')
    page.get_by_label('Competitive advantages & supporting evidence',exact=True).fill('Dated evidence test')
    page.locator('#company-pick').select_option('MSFT')
    assert page.get_by_label('Competitive advantages & supporting evidence',exact=True).input_value()==''
    page.locator('#company-pick').select_option('SHEL.L')
    assert page.get_by_label('Competitive advantages & supporting evidence',exact=True).input_value()=='Dated evidence test'
    for key in ['overview','fx','equities','bonds','analytics','etfs','economics','watchlist','quality','companies']:
        page.locator('#tab-'+({'companies':'equities','analytics':'fx'}.get(key,key))).click()
        if key in ['companies','analytics']:page.locator('#sub-'+('equities-research' if key=='companies' else 'fx-analytics')).click()
        page.wait_for_timeout(60)
        assert page.locator('#view-'+({'companies':'equities','analytics':'fx'}.get(key,key))).is_visible()
    assert not errors,errors
    page.locator('#company-pick').select_option('MSFT');page.locator('#research-tab-0').click()
    page.evaluate('scrollTo(0,0)');page.wait_for_timeout(60)
    page.screenshot(path='/tmp/research-r1-overview.png',full_page=True)
    page.set_viewport_size({'width':768,'height':1024});page.locator('#research-tab-1').click();page.wait_for_timeout(80)
    page.evaluate('scrollTo(0,0)');page.wait_for_timeout(60)
    page.screenshot(path='/tmp/research-r1-ipad.png',full_page=True)
    print('PASS: Shell/MSFT/HSBC, automatic inputs, stale/missing data, bank exclusions, charts, 390/768/1024/1440px layouts, notes and all workspaces; no JS errors')
    browser.close()
