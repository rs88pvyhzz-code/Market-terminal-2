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
    page.locator('#tab-companies').dispatch_event('click')
    for symbol in ['SHEL.L','MSFT','HSBA.L']:
        page.locator('#company-pick').select_option(symbol);page.wait_for_timeout(100)
        assert page.locator('#research-nav [role=tab]').count()==6
        page.locator('#research-tab-0').click()
        assert page.locator('#research-overview .research-card').count()>=6
        page.locator('#research-tab-1').click()
        assert page.locator('#research-statements').count()==1
        page.locator('#research-tab-2').click()
        assert page.locator('#research-valuation .t11-metric').count()==6
        assert page.locator('#research-valuation input').count()==0
        assert page.locator('#research-valuation button').count()==0
        page.locator('#research-tab-4').click()
        assert 'MANAGEMENT & EARNINGS INTELLIGENCE' in page.locator('#research-outlook').inner_text()
        if symbol=='SHEL.L':
            assert page.locator('#research-outlook .research-evidence').count()>=3
        for width in [768,1024,1440]:
            page.set_viewport_size({'width':width,'height':1100})
            for i in range(6):
                page.locator('#research-tab-'+str(i)).click();page.wait_for_timeout(30)
                assert page.evaluate('document.body.scrollWidth<=innerWidth+1'),(symbol,width,i)
        if symbol=='SHEL.L':
            page.locator('#research-tab-0').click()
            page.screenshot(path='/tmp/research-live-shell.png',full_page=True)
    for tab in page.locator('[data-workspace][role=tab]').all():
        tab.dispatch_event('click');page.wait_for_timeout(50)
    page.locator('#tab-quality').dispatch_event('click')
    assert page.locator('#terminal1-source-register').count()==1
    assert not errors,errors
    print('PASS actual live payload: dated company evidence, read-only ratios, full source register and ten original-workspace layouts on desktop/iPad')
    browser.close()
