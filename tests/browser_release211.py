"""Original Market Terminal 1 design over Market Terminal 2 data (Release 2.11).
Checks actual layout and navigability, retained read-only analytics, full source audit.
"""
from pathlib import Path
import json,os,sys,re
from playwright.sync_api import sync_playwright

html=Path(sys.argv[1]).read_text(encoding='utf-8')
m=re.search(r'window\.MT_DATA\s*=\s*',html)
assert m
data=json.JSONDecoder().raw_decode(html[m.end():])[0]
assert len(data['etfTracker']['funds'])==132
assert "terminal1-original-theme" in html and "terminal11-layout-adapter" in html
tabs=['OVERVIEW','MY WATCHLIST','MARKETS','ANALYTICS','EQUITIES','COMPANY RESEARCH','ETF TRACKERS','BONDS & RATES','ECONOMICS','DATA QUALITY']
keys=['overview','fx','equities','companies','bonds','analytics','etfs','economics','watchlist','quality']
with sync_playwright() as p:
    browser=p.chromium.launch(**({'executable_path':os.environ['CHROMIUM_EXECUTABLE']} if os.environ.get('CHROMIUM_EXECUTABLE') else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1024,'height':768});errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.route('http://localhost:8765/**',lambda route:route.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    assert page.evaluate("document.documentElement.classList.contains('terminal1-design')")
    assert page.locator('#workspace-tabs [role=tab]').all_text_contents()==tabs
    # Original typography and palette; Release 3.1 panel geometry (terminal_layout.css).
    assert page.locator('.brand').evaluate('(e)=>getComputedStyle(e).fontFamily').lower().find('monospace')>=0
    assert page.locator('#overview-board').evaluate('(e)=>getComputedStyle(e).borderRadius')=='5px'
    assert page.locator('#tab-overview').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(255, 160, 40)'
    assert page.locator('#market-pulse .r24-snapshot-item').count()==14
    for key in keys:
        page.locator('#tab-'+key).click();page.wait_for_timeout(45)
        assert page.locator('#view-'+key).is_visible(),key
        assert page.locator('#workspace-tabs #tab-'+key).get_attribute('aria-selected')=='true',key
    page.locator('#tab-companies').click()
    assert page.locator('#company-pick').count()==1
    assert page.locator('#research-nav [role=tab]').count()==6
    if page.locator('#company-pick option').count()>1:
        symbol=page.locator('#company-pick option').nth(1).get_attribute('value')
        page.locator('#company-pick').select_option(symbol)
    page.locator('#research-tab-0').click()
    assert page.locator('#r29-coverage .r29-coverage-cell').count()==6
    assert page.locator('#company-chart').is_visible()
    page.locator('#research-tab-2').click()
    assert page.locator('#research-valuation .t11-metric').count()==6
    assert page.locator('#research-valuation input').count()==0
    assert page.locator('#research-valuation button').count()==0
    assert page.locator('#research-stress-panel').count()==0
    assert 'MARKET RATIOS' in page.locator('#research-tab-2').inner_text()
    page.locator('#tab-analytics').click()
    assert page.locator('#mt-risk-comparison').is_visible()
    assert page.locator('#analytics-rolling').count()==1
    page.locator('#tab-etfs').click()
    assert page.locator('#etf-tracker-panel .etf-table thead th').count()==8
    assert page.locator('#etf-tracker-panel .etf-table-scroll').evaluate('(e)=>parseFloat(getComputedStyle(e).maxHeight)<=460')
    page.locator('#tab-bonds').click()
    for selector in ['#gilts .gilt-table-scroll','#ust-securities-scroll']:
        assert page.locator(selector).evaluate('(e)=>parseFloat(getComputedStyle(e).maxHeight)<=460')
        assert page.locator(selector+' thead th').first.evaluate('(e)=>getComputedStyle(e).position')=='sticky'
    page.locator('#tab-quality').click()
    assert page.locator('#terminal1-source-register').is_visible()
    assert page.locator('#t11-source-notes').count()==1
    assert page.locator('#t11-exception-details').count()==1
    assert page.locator('#quality-panel').count()==1
    # Per-tab 'data checks' shortcuts are retired; Data Quality is reached from its tab.
    page.locator('#tab-companies').click()
    assert page.locator('#view-companies .t11-quality-shortcut:visible').count()==0
    for width,height in [(1440,900),(1024,768),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        for key in keys:
            page.locator('#tab-'+key).click();page.wait_for_timeout(25)
            assert page.evaluate('document.body.scrollWidth<=innerWidth+1'),(width,key)
        if not data.get('demo') and width in [1024,768]:
            page.locator('#tab-companies').click()
            page.screenshot(path=f'/tmp/release211-original-company-{width}.png',full_page=True)
            page.locator('#tab-overview').click()
            page.screenshot(path=f'/tmp/release211-original-overview-{width}.png',full_page=True)
    assert not errors,errors
    browser.close()
print('PASS original 10 tabs, Terminal 1 typography and panel shape, Terminal 2 financial evidence, source register, short tables, no editable valuation model')
