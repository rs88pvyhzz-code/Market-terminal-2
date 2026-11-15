"""Reading hierarchy and table controls on the supplied demo or live payload."""
import os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':1024})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('http://localhost:8765/**',lambda route:route.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
    page.locator('#tab-overview').click()
    page.wait_for_timeout(250)
    assert page.locator('#pulse-time-basis').inner_text()=='Quote times in UTC'
    assert page.locator('#market-pulse .reading-timestamp').count()>0
    assert all('UTC' not in t for t in page.locator('#market-pulse .reading-timestamp').all_text_contents())
    assert page.locator('#market-pulse .r24-snapshot-item').first.evaluate('(e)=>parseFloat(getComputedStyle(e.children[3]).fontSize)<parseFloat(getComputedStyle(e.children[2]).fontSize)')
    assert 'rerun Python' not in page.locator('#stamp').inner_text()
    assert page.locator('.reading-breadth-table').count()>0
    page.locator('#tab-equities').click()
    page.wait_for_timeout(250)
    assert not page.locator('#screen-rows tr').first.locator('td').nth(11).is_visible()
    page.locator('#screen-source-toggle').click()
    assert page.locator('#screen-rows tr').first.locator('td').nth(11).is_visible()
    page.locator('#screen-source-toggle').click()
    assert page.locator('#screen-source-toggle').get_attribute('aria-expanded')=='false'
    page.locator('#tab-economics').click()
    page.wait_for_timeout(250)
    prior=page.locator('#macro-tiles .prior-value')
    if prior.count():
        assert prior.first.evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)>=17')
        assert page.locator('#macro-tiles .prior-period').count()==prior.count()
    page.locator('#tab-analytics').click()
    page.wait_for_timeout(250)
    assert page.locator('#mt-movers-table th.mt-selected-period').count()==0
    page.locator('#mt-movers-table button[data-mt-period="1Y"]').click()
    assert page.locator('#mt-movers-table th[aria-sort="descending"]').count()==1
    # No visible section heading ends a shortened table without its own data row.
    assert page.locator('#mt-movers-matrix').evaluate('''body=>[...body.rows].every((r,i,rows)=>{
        if(!r.matches('.watch-section')||r.classList.contains('polish-cut'))return true;
        for(let j=i+1;j<rows.length&&!rows[j].matches('.watch-section');j++)if(!rows[j].classList.contains('polish-cut'))return true;
        return false;
    })''')
    page.screenshot(path='/tmp/reading-analytics-ipad.png',full_page=True)
    assert not errors,errors
    browser.close()
print('PASS reading hierarchy, timestamps, source columns, prior figures and sorted headings')
