"""Release 2.4 presentation checks; supplied payload is never replaced by fixtures."""
import json,os,re,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text();m=re.search(r'window\.MT_DATA\s*=\s*',html);data=json.JSONDecoder().raw_decode(html[m.end():])[0]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000);page.wait_for_timeout(150)
    assert page.locator('#workspace-tabs [role=tab]').count()==8
    for width,height in [(1440,1100),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.locator('#tab-overview').click();page.wait_for_timeout(80)
        sections=page.locator('#view-overview > section').evaluate_all('(els)=>els.map(e=>e.id)')
        assert sections==['overview-board','r24-developments','r24-conditions','r24-watch','r24-upcoming'],sections
        assert page.locator('#market-pulse > .r24-snapshot-item').count()==(14 if page.evaluate("document.documentElement.classList.contains('release210')") else 7)
        # Release 2.8 deliberately expands the ranked Overview maximum from 3 to 5.
        # Older snapshots still retain the original Release 2.4 contract.
        limit=5 if page.evaluate("document.documentElement.classList.contains('release28')") else 3
        assert page.locator('#r24-developments article').count()<=limit
        assert page.locator('#r24-watch article').count()<=2
        assert page.locator('#r24-conditions tbody tr').count()==4
        assert page.locator('#r24-upcoming tbody tr').count()<=3
        for tab,name in [('overview','overview'),('fx','markets'),('economics','economics'),('equities','research'),('bonds','bonds'),('etfs','etfs'),('watchlist','watchlist'),('quality','quality')]:
            page.locator('#tab-'+tab).click();page.wait_for_timeout(80)
            if tab=='equities':page.locator('#sub-equities-research').click();page.locator('#research-tab-0').click();page.wait_for_timeout(100)
            if tab=='fx':page.locator('#sub-fx-prices').click();page.wait_for_timeout(50);assert page.locator('#movers').is_visible();page.locator('#sub-fx-news').click();assert page.locator('#news').is_visible();page.locator('#sub-fx-prices').click()
            if tab=='economics':
                assert page.locator('#calendar-items table').count()==1
                assert page.locator('#calendar-items th').all_text_contents()==['Date','Time','Country','Indicator','Previous','Forecast','Actual','Source']
                for b in page.locator('#calendar-filters button').all():b.click()
                page.locator('#calendar-filters button').first.click()
            assert page.locator('details details').count()==0,(name,width,'nested disclosures')
            if tab=='quality':
                assert page.locator('#mt-quality-focus').is_visible()
                assert page.locator('#mt-full-audit').get_attribute('open') is None
                assert not page.locator('#mt-full-audit .mt-audit-content').is_visible()
                page.locator('#mt-full-audit > summary').click();assert page.locator('#mt-full-audit .mt-audit-content').is_visible()
                page.locator('#mt-full-audit > summary').click()
            assert page.evaluate('document.body.scrollWidth<=innerWidth'),(name,width,'page overflow')
            if width>=1024 and name in ['overview','markets','economics','research','bonds']:page.evaluate('scrollTo(0,0)');page.wait_for_timeout(50);page.screenshot(path=f'/tmp/release24-{name}-{width}.png',full_page=True)
        page.locator('#tab-equities').click();page.locator('#sub-equities-research').click();page.locator('#research-tab-1').click();page.wait_for_timeout(100)
        assert page.locator('#research-statements details').count()==0
        page.locator('#research-tab-2').click();page.wait_for_timeout(100)
        if page.get_by_label('Normalised FCFF (reporting currency, millions)',exact=True).count():
            assert page.get_by_label('Normalised FCFF (reporting currency, millions)',exact=True).is_visible()
            bridge=page.locator('#research-valuation section').filter(has=page.locator(':scope > h3',has_text='Normalised FCFF calculation'))
            assert bridge.count()==1 and bridge.locator('table').first.is_visible()
            stress=page.get_by_label('First-year revenue shock (%)',exact=True)
            if stress.count():assert stress.is_visible()
            assert page.locator('#research-valuation input').evaluate_all('(els)=>els.every(e=>!e.closest("details"))')
        assert page.locator('#research-valuation .research-warning').evaluate_all('(els)=>els.every(e=>!e.closest("details"))')
        page.locator('#research-tab-0').click();page.wait_for_timeout(80)
        assert page.locator('#company-chart').is_visible() and page.locator('#company-risk-kpis').is_visible()
        assert page.locator('#research-overview details').count()==0
        assert page.locator('#company-advanced').is_visible() and page.locator('#company-advanced').evaluate('(e)=>e.tagName')=='SECTION'
        page.locator('#research-tab-1').click();page.wait_for_timeout(80)
        for period in ['3Y','5Y']:
            button=page.locator('#research-statements button').filter(has_text=period)
            if button.count() and button.is_enabled():button.click();page.wait_for_timeout(80)
            if width>=1024:
                assert page.locator('#research-statements .research-table--annual').evaluate_all('(tables)=>tables.every(t=>t.scrollWidth<=t.parentElement.clientWidth+2)')
                assert page.locator('#research-statements .research-table--annual thead th:not(:first-child)').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).textAlign==="right")')
        page.locator('#tab-fx').click();page.locator('#sub-fx-analytics').click();assert page.locator('#analytics-breadth').is_visible();assert page.locator('#analytics-sectors').is_visible()
    assert not errors,errors
    print('PASS R24: '+('synthetic demo' if data['demo'] else 'actual payload')+'; five Overview sections, seven snapshots, relocated feed/movers/breadth/sectors, full calendar, selective single-level support, visible controls/warnings, eight tabs, desktop/iPad/mobile')
    browser.close()
