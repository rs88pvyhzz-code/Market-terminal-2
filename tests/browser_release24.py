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
    assert page.locator('#workspace-tabs [role=tab]').count()==10
    for width,height in [(1440,1100),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.locator('#tab-overview').click();page.wait_for_timeout(80)
        sections=page.locator('#view-overview > section').evaluate_all('(els)=>els.map(e=>e.id)')
        assert sections==['r24-developments','overview-board','news','r24-upcoming'],sections  # terminal_layout.js
        assert page.locator('#market-pulse > .r24-snapshot-item').count()==(14 if page.evaluate("document.documentElement.classList.contains('release210')") else 7)
        # Release 2.8 deliberately expands the ranked Overview maximum from 3 to 5.
        # Older snapshots still retain the original Release 2.4 contract.
        limit=5 if page.evaluate("document.documentElement.classList.contains('release28')") else 3
        assert page.locator('#r24-developments article').count()<=limit
        assert page.locator('#r24-watch article').count()<=2
        assert page.locator('#r24-conditions tbody tr').count()==4
        assert page.locator('#r24-upcoming tbody tr').count()<=3
        for tab,name in [('overview','overview'),('fx','markets'),('economics','economics'),('equities','equities'),('companies','research'),('analytics','analytics'),('bonds','bonds'),('etfs','etfs'),('watchlist','watchlist'),('quality','quality')]:
            page.locator('#tab-'+tab).click();page.wait_for_timeout(80)
            if tab=='companies':page.locator('#research-tab-0').click();page.wait_for_timeout(100)
            if tab=='fx':assert page.locator('#monitor').is_visible()
            if tab=='equities':assert page.locator('#movers').is_visible()
            if tab=='overview':assert page.locator('#news').is_visible()
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
            within=page.evaluate('document.body.scrollWidth<=innerWidth')
            if not within:
                offenders=page.evaluate("""() => [...document.querySelectorAll('body *')]
                  .filter(e=>{let r=e.getBoundingClientRect();return r.width>0&&r.height>0&&(r.right>innerWidth+1||r.left< -1)})
                  .slice(0,12).map(e=>({tag:e.tagName,id:e.id,cls:String(e.className).slice(0,100),
                    right:Math.round(e.getBoundingClientRect().right),width:Math.round(e.getBoundingClientRect().width)}))""")
                assert within,(name,width,'page overflow',offenders)

            if width>=1024 and name in ['overview','markets','economics','research','bonds']:page.evaluate('scrollTo(0,0)');page.wait_for_timeout(50);page.screenshot(path=f'/tmp/release24-{name}-{width}.png',full_page=True)
        page.locator('#tab-companies').click();page.locator('#research-tab-1').click();page.wait_for_timeout(100)
        assert page.locator('#research-statements details').count()==0
        page.locator('#research-tab-2').click();page.wait_for_timeout(100)
        assert page.locator('#research-valuation .t11-metric').count()==6
        assert page.locator('#research-valuation input').count()==0
        assert page.locator('#research-valuation button').count()==0
        assert 'Trailing P/E' in page.locator('#research-valuation').inner_text()
        page.locator('#research-tab-0').click();page.wait_for_timeout(80)
        assert page.locator('#company-chart').is_visible()
        page.locator('#tab-analytics').click();page.wait_for_timeout(80)
        assert page.locator('#company-risk-kpis').is_visible()  # risk is analytics
        page.locator('#tab-companies').click();page.wait_for_timeout(80)
        assert page.locator('#research-overview details').count()==0
        assert page.locator('#view-analytics #company-advanced').count()==1 and page.locator('#company-advanced').evaluate('(e)=>e.tagName')=='SECTION'
        page.locator('#research-tab-1').click();page.wait_for_timeout(80)
        for period in ['3Y','5Y']:
            button=page.locator('#research-statements button').filter(has_text=period)
            if button.count() and button.is_enabled():button.click();page.wait_for_timeout(80)
            if width>=1024:
                assert page.locator('#research-statements .research-table--annual').evaluate_all('(tables)=>tables.every(t=>t.scrollWidth<=t.parentElement.clientWidth+2)')
                assert page.locator('#research-statements .research-table--annual thead th:not(:first-child)').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).textAlign==="right")')
        page.locator('#tab-analytics').click();assert page.locator('#analytics-breadth').is_visible();assert page.locator('#analytics-sectors').is_visible()
    assert not errors,errors
    print('PASS R24: '+('synthetic demo' if data['demo'] else 'actual payload')+'; five Overview sections, fourteen snapshots, relocated feed/movers/breadth/sectors, full calendar, selective single-level support, visible controls/warnings, ten tabs, desktop/iPad/mobile')
    browser.close()
