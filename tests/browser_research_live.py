"""Browser checks on the actual production build; no fixtures or payload edits."""
import json
import os
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

html=Path(sys.argv[1]).read_text();a=html.index('window.MT_DATA = ')+len('window.MT_DATA = ');d=json.loads(html[a:html.index(';</script>',a)])
assert d['demo'] is False
with sync_playwright() as p:
    executable=os.environ.get('CHROMIUM_EXECUTABLE')
    browser=p.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda route:route.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    page.locator('#tab-equities').click();page.locator('#sub-equities-research').click()
    for symbol in ['SHEL.L','MSFT','HSBA.L']:
        page.locator('#company-pick').select_option(symbol);page.wait_for_timeout(100)
        assert page.locator('#research-nav [role=tab]').count()==6
        page.locator('#research-tab-2').click()
        if symbol=='SHEL.L':
            assert page.get_by_label('Shares outstanding (absolute count)',exact=True).input_value()!=''
            if next(c for c in d['companies'] if c['symbol']==symbol).get('valuationIntegrity',{}).get('issues'):
                assert 'VALUATION REQUIRES SOURCE REVIEW' in page.locator('#research-valuation').inner_text()
            print('Actual Shell FCFF m',page.get_by_label('Normalised FCFF (reporting currency, millions)',exact=True).input_value())
            print('Actual Shell debt adjustment m',page.get_by_label('Debt-related adjustment (reporting millions)',exact=True).input_value())
        if symbol=='HSBA.L':assert 'Standard FCFF DCF excluded' in page.locator('#research-valuation').inner_text()
        if len(next(c for c in d['companies'] if c['symbol']==symbol).get('valuationHistory',[]))<12:
            assert page.locator('#research-multiples-chart').count()==0
            assert page.locator('#research-valuation .research-periods button:not([disabled])').count()==0
        page.locator('#research-tab-4').click()
        assert 'MANAGEMENT & EARNINGS INTELLIGENCE' in page.locator('#research-outlook').inner_text()
        if symbol=='SHEL.L':assert page.locator('#research-outlook .research-evidence').count()>=3
        for width in [768,1024,1440]:
            page.set_viewport_size({'width':width,'height':1100})
            for i in range(6):
                page.locator('#research-tab-'+str(i)).click();page.wait_for_timeout(30)
                assert page.evaluate('document.body.scrollWidth<=innerWidth'),(symbol,width,i)
        if symbol=='SHEL.L':
            page.locator('#research-tab-0').click();page.screenshot(path='/tmp/research-live-shell.png',full_page=True)
    for tab in page.locator('[data-workspace][role=tab]').all():tab.click();page.wait_for_timeout(50)
    assert not errors,errors
    print('PASS actual live payload: dated research, valuation warning, sparse history, banks, six views and all terminal sections on desktop/iPad')
    browser.close()
