"""Actual rendered tables: long returns, reading headers and gilt comparison."""
import os,sys,json,re
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text()
data=json.JSONDecoder().raw_decode(html[re.search(r'window.MT_DATA\s*=\s*',html).end():])[0]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    page.locator('#tab-fx').click();page.wait_for_timeout(300)
    assert page.locator('#market-mini-summary').count()==0
    table=page.locator('#watch-rows').locator('..')
    headers=table.locator('thead th').all_text_contents()
    assert 'Ticker' not in headers and '3Y p.a.' in headers and '5Y p.a.' in headers,headers
    assert page.locator('#watch-rows tr:not(.watch-section)').first.locator('td').count()==11
    table.evaluate('(t)=>window.scrollTo(0,t.getBoundingClientRect().top+scrollY+100)')
    page.wait_for_timeout(300)
    floating=page.locator('.table-reading-head').filter(has_text='Instrument')
    assert floating.count()==1
    assert floating.bounding_box()['y']>=page.locator('.commandbar').bounding_box()['height']-1
    floating.locator('th[data-sort=three]').click();page.wait_for_timeout(100)
    page.screenshot(path='/tmp/compact-market-headings.png')
    if any(q['symbol']=='XLV' for q in data['quotes']):
        page.locator('#main-pick').select_option('XLV')
        page.locator('#main-ranges button').filter(has_text=re.compile('^3Y$')).click()
        assert 'S&P 500' in page.locator('#main-detail').inner_text()
    page.locator('#tab-bonds').dispatch_event('click');page.wait_for_timeout(250)
    conventional=[g for g in data.get('gilts',[]) if not g.get('indexLinked') and g.get('quoted')]
    if conventional:
        # Select a conventional gilt explicitly; the snapshot may default to an index-linked bond.
        row=page.locator('#gilt-rows tr[data-isin="'+conventional[0]['isin']+'"]')
        if row.count():row.dispatch_event('click')
        body=page.locator('#mt-gilt-tax-rows')
        assert body.locator('tr').count()>0,'gilt comparison empty'
        page.locator('#mt-gilt-tax-rate').select_option('40')
        assert '40%' in page.locator('#mt-gilt-tax-heading').inner_text()
        for row in body.locator('tr').all():
            cells=row.locator('td').all_text_contents()
            if cells[3].endswith('%') and cells[4].endswith('%'):
                assert float(cells[4][:-1])<=float(cells[3][:-1])+0.001
        page.locator('#mt-gilt-tax').scroll_into_view_if_needed()
        page.screenshot(path='/tmp/compact-gilt-comparison.png')
    assert not errors,errors
    browser.close()
print('PASS market headings, 3Y/5Y columns, XLV comparator and populated gilt comparison')
