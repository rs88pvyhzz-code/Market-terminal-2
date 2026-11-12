"""Exercise the refined dashboard on desktop, iPad and phone; save review images."""
import os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text()
with sync_playwright() as p:
    kwargs={'executable_path':os.environ['CHROMIUM_EXECUTABLE']} if os.environ.get('CHROMIUM_EXECUTABLE') else {}
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],**kwargs)
    for width,height,label in [(1440,1000,'desktop'),(1024,1366,'ipad'),(390,844,'phone')]:
        page=browser.new_page(viewport={'width':width,'height':height});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
        page.goto('http://localhost:8765/');page.wait_for_timeout(600)
        page.locator('#tab-companies').click();page.wait_for_timeout(300)
        assert page.locator('#layout-company-metrics section').count()==3
        assert page.locator('#layout-company-metrics').inner_text().count('MARKET CAPITALISATION')==1
        assert page.locator('#layout-company-metrics').inner_text().count('PRICE & VALUATION')==1
        page.locator('#layout-company-metrics').screenshot(path='/tmp/refinements-'+label+'.png')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        page.locator('#tab-fx').click();page.wait_for_timeout(300)
        assert 'UK 10Y spot gilt yield' in page.locator('#watch-rows').inner_text()
        assert page.locator('#valuation-rows tr').count()==10
        assert not errors,errors
        page.close()
    browser.close()
print('Refinement browser checks passed')
