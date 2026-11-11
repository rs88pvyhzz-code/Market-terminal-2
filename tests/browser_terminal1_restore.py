"""Browser acceptance for restored original Market Terminal interface.

Deliberately supersedes historical assertions for the eight-tab UI and manually
editable DCF/stress models. Does NOT supersede numerical/unit/source tests.
Runs against both synthetic demo and actual independently collected payloads.
"""
import json, os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

markup = Path(sys.argv[1]).read_text(encoding='utf-8')
hit = re.search(r'window\.MT_DATA\s*=\s*', markup)
assert hit, 'No MT_DATA payload'
data = json.JSONDecoder().raw_decode(markup[hit.end():])[0]
assert len(data['etfTracker']['funds']) == 132, 'The full ETF catalogue changed'
workspace = [
  ('overview','OVERVIEW'),('fx','MARKETS'),('equities','EQUITIES'),
  ('companies','COMPANY RESEARCH'),('bonds','BONDS & RATES'),
  ('analytics','ANALYTICS'),('etfs','ETF TRACKERS'),
  ('economics','ECONOMICS'),('watchlist','MY WATCHLIST'),('quality','DATA QUALITY')
]
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),
        args=['--no-sandbox']
    )
    page = browser.new_page(viewport={'width':1440,'height':900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('http://localhost:8765/**',
        lambda route: route.fulfill(body=markup,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
    page.wait_for_timeout(250)
    assert page.evaluate("document.documentElement.classList.contains('terminal1-restored')")
    tabs = page.locator('#workspace-tabs [data-workspace]')
    assert tabs.count()==10, tabs.count()
    assert tabs.all_text_contents()==[label for _,label in workspace]
    assert page.locator('#workspace-tabs .terminal-subnav').count()==0
    for width,height in ((1440,900),(1024,768),(390,844)):
        page.set_viewport_size({'width':width,'height':height})
        for key,label in workspace:
            page.locator('#tab-'+key).click()
            page.wait_for_timeout(80)
            assert page.locator('#view-'+key).is_visible(),(width,key)
            assert page.locator('#tab-'+key).get_attribute('aria-selected')=='true'
            assert page.evaluate('document.body.scrollWidth <= innerWidth+1'),(width,key,
                page.evaluate('document.body.scrollWidth'),page.evaluate('innerWidth'))
        if width==1024:
            page.locator('#tab-overview').click()
            page.screenshot(path='/tmp/terminal1-restored-overview-ipad.png',full_page=True)
            page.locator('#tab-companies').click()
            page.screenshot(path='/tmp/terminal1-restored-company-ipad.png',full_page=True)
            page.locator('#tab-analytics').click()
            page.screenshot(path='/tmp/terminal1-restored-analytics-ipad.png',full_page=True)
            page.locator('#tab-etfs').click()
            page.screenshot(path='/tmp/terminal1-restored-etfs-ipad.png',full_page=True)
            page.locator('#tab-quality').click()
            page.screenshot(path='/tmp/terminal1-restored-data-quality-ipad.png',full_page=True)
    page.set_viewport_size({'width':1024,'height':768})
    page.locator('#tab-overview').click()
    assert page.locator('#market-pulse .r24-snapshot-item').count()==14
    assert page.locator('#r24-developments').count()==1
    assert page.locator('#view-overview #news').count()==0
    page.locator('#tab-fx').click()
    assert page.locator('#view-fx #monitor').count()==1
    assert page.locator('#view-fx #news').count()==1
    assert page.locator('#view-fx #r23-alerts').count()==1
    assert page.locator('#sub-fx-news').count()==0
    page.locator('#tab-equities').click()
    assert page.locator('#view-equities #equity-screener').count()==1
    assert page.locator('#view-equities #constituents').count()==1
    assert page.locator('#view-equities #companies').count()==0
    page.locator('#tab-companies').click()
    assert page.locator('#view-companies #companies').count()==1
    assert page.locator('#view-companies #company-events-panel').count()==1
    assert page.locator('#sub-equities-research').count()==0
    assert page.locator('#research-nav [role=tab]').count()==6
    assert not page.locator('#research-tab-2').is_visible(), 'Editable valuation tab still shown'
    assert not page.locator('#research-view-2').is_visible()
    page.locator('#research-tab-0').click()
    assert page.locator('#research-valuation').is_visible()
    assert page.locator('#research-valuation .t1-ratio-tile').count()==6
    assert page.locator('#research-valuation input').count()==0
    assert page.get_by_role('button',name=re.compile('OPEN ADVANCED DCF')).count()==0
    assert page.locator('#research-view-0 .r29-market-cap').count()==1
    assert page.locator('#research-view-0 #r29-coverage').count()==0, 'Quality details leaked into research'
    assert 'margin of safety' not in page.locator('#research-executive').inner_text().lower()
    assert page.locator('#research-tab-1').is_visible()
    page.locator('#research-tab-1').click()
    assert page.locator('#research-statements').is_visible()
    page.locator('#research-tab-3').click()
    assert page.locator('#research-business').is_visible()
    page.locator('#tab-analytics').click()
    assert page.locator('#view-analytics #analytics-rolling').count()==1
    assert page.locator('#view-analytics #market-valuations').count()==1
    assert page.locator('#view-analytics #compare').count()==1
    page.locator('#tab-bonds').click()
    assert page.locator('#view-bonds #gilts').count()==1
    assert page.locator('#gilt-freshness').count()==1 and not page.locator('#gilt-freshness').is_visible()
    assert page.locator('#gilts .gilt-table-scroll table thead th').first.evaluate(
      "(e)=>getComputedStyle(e).position")=='sticky'
    page.locator('#tab-etfs').click()
    assert page.locator('#etf-tracker-panel .etf-table thead th').count()==8
    assert page.locator('#etf-tracker-panel #etf-stats').count()==0
    assert page.locator('#etf-tracker-panel .etf-table-scroll').evaluate(
      "(e)=>getComputedStyle(e).overflowY")=='auto'
    page.locator('#tab-quality').click()
    assert page.locator('#t1-source-ledger').is_visible()
    for section in ['etf-stats','gilt-freshness','gilt-retrieval','r29-coverage']:
        assert page.locator('#t1-source-'+section).count()==1,section
    assert page.locator('#view-quality #etf-stats').count()==1
    assert page.locator('#view-quality #gilt-freshness').count()==1
    assert page.locator('#view-quality #r29-coverage').count()==1
    assert page.locator('#etf-audit-panel').count()==1
    assert not errors,errors
    browser.close()
print('PASS Terminal 1 restored: original 10 tabs, separate research/analytics, no manual valuation, sourced static ratios, isolated Data Quality, original ETF layout, preserved 132 funds, iPad/mobile.')
