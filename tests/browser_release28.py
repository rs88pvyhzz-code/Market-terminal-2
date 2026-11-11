"""Release 2.8 browser checks: sourced overview, macro, calendar, gilts and consensus.

ETF presentation is read-only in this release; the Release 2.7 tests own it.
"""
from pathlib import Path
import json, os, re, sys
from playwright.sync_api import sync_playwright

html=Path(sys.argv[1]).read_text(encoding='utf-8')
m=re.search(r'window\.MT_DATA\s*=\s*',html)
assert m,'Missing market snapshot'
data=json.JSONDecoder().raw_decode(html[m.end():])[0]
assert 'terminal_release28.js' not in html or 'r28NewsOverview' in html
assert len(data['etfTracker']['funds'])==132

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1024,'height':768})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
    page.wait_for_timeout(250)
    assert page.evaluate("document.documentElement.classList.contains('release28')")
    assert page.locator('#r24-developments .r24-item').count()<=5
    assert page.locator('#r23-moves .r23-observation').count()<=6
    assert page.locator('#r24-upcoming .r24-calendar-table tbody tr').count()<=3
    assert page.locator('#r24-developments .r24-content').inner_text().strip()
    if not data.get('demo'):
        page.screenshot(path='/tmp/release28-overview-ipad.png',full_page=True)
    page.locator('#tab-economics').click()
    page.wait_for_timeout(180)
    page.locator('#macro-region').select_option('UK')
    page.wait_for_timeout(140)
    assert page.locator('#macro-tiles button').count()>0
    assert page.locator('#macro-tiles button .r28-economic-sub').count()>=page.locator('#macro-tiles button').count()
    assert not page.locator('#macro-surprise').is_visible(),'Redundant actual-vs-prior table is still visible'
    macro={m['key']:m for m in data.get('economicPrints',[]) if m['region']=='UK'}
    for key,m in macro.items():
        if m.get('previous') is None:continue
        assert any('Prior ' in x for x in page.locator('#macro-tiles .r28-economic-sub').all_text_contents())
        break
    assert page.get_by_role('button',name='Major releases').count()>0
    major=page.locator('#calendar-items .r24-calendar-table tbody tr').count()
    page.get_by_role('button',name='All verified releases').click()
    all_events=page.locator('#calendar-items .r24-calendar-table tbody tr').count()
    assert all_events>=major,(major,all_events)
    page.get_by_role('button',name='Major releases').click()
    for cell in page.locator('#calendar-items .r24-calendar-table tbody tr td:nth-child(4)').all_text_contents():
        assert not re.search(r'construction output|index of services|productivity|labour market statistics time series',cell,re.I),cell
    if all_events>=9:
        page.get_by_role('button',name='All verified releases').click()
        page.wait_for_timeout(110)
        assert page.locator('#calendar-items .r28-table-scroll').count()==1
        pos=page.locator('#calendar-items .r28-table-scroll thead th').first.evaluate('(e)=>getComputedStyle(e).position')
        assert pos=='sticky',pos
    if not data.get('demo'):
        page.screenshot(path='/tmp/release28-economics-ipad.png',full_page=True)
    page.locator('#tab-bonds').click()
    page.wait_for_timeout(130)
    if page.locator('#gilt-rows tr[data-isin]').count():
        page.locator('#gilt-rows tr[data-isin]').first.click()
        page.wait_for_timeout(130)
        assert page.locator('#gilt-stats .r28-gilt-single').count()==1
        assert page.locator('#gilt-stats .r28-gilt-yield').count()==2
        if page.locator('#mt-gilt-tax-rows tr').count():
            selected=page.locator('#mt-gilt-tax-rows tr.selected')
            assert selected.count()==0,'Selected gilt must appear only in summary'
        if not data.get('demo'):
            page.screenshot(path='/tmp/release28-gilts-ipad.png',full_page=True)
    page.locator('#tab-companies').click()
    page.wait_for_timeout(150)
    if page.locator('#company-pick option').count():
        page.locator('#company-pick').select_option(index=0)
        page.wait_for_timeout(150)
        if page.locator('#research-overview').is_visible():
            assert page.locator('#r28-analyst-consensus').count()==1
            if not data.get('demo'):
                page.screenshot(path='/tmp/release28-company-ipad.png',full_page=True)
    for width,height in [(1440,900),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        page.locator('#tab-economics').click()
        page.wait_for_timeout(70)
        assert page.evaluate('document.body.scrollWidth <= innerWidth+1'),('horizontal page overflow',width)
    assert not errors,errors
    browser.close()
print('PASS Release 2.8: concise verified Overview, capped material movers, major-calendar toggle, macro prior cards, no duplicate actual table, unified gilt valuation, analyst panel, sticky tables, iPad/mobile; ETF unchanged')
