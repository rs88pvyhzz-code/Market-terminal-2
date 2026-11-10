"""Navigation and presentation regression using demo markets + actual DMO report.

No production collector reads test fixtures. The gilt prices here are the
unaltered official D10B response, not synthetic prices.
"""
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
import gilt_market,gilt_freshness
html=Path(sys.argv[1]).read_text();marker='window.MT_DATA = ';a=html.index(marker)+len(marker);b=html.index(';</script>',a);d=json.loads(html[a:b]);assert d['demo'] is True
d['gilts'],day=gilt_market.parse_dmo_xlsx((Path(__file__).resolve().parents[1]/'dmo_prices/DMO_D10B_2026-11-09.xls').read_bytes())
d['giltFreshness']={**gilt_freshness.assess(day.isoformat()),'downloadedFresh':False,'origin':'Official DMO file used for UI regression','retrievedAt':None};d['gilt_history']=[]
html=html[:a]+json.dumps(d).replace('</','<\\/')+html[b:]
with sync_playwright() as p:
    executable=os.environ.get('CHROMIUM_EXECUTABLE')
    browser=p.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'));page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    tabs=page.locator('#workspace-tabs [role=tab]');assert tabs.count()==8
    assert tabs.all_text_contents()==['OVERVIEW','MARKETS','EQUITIES & RESEARCH','BONDS & RATES','ETFs','ECONOMICS','MY WATCHLIST','DATA QUALITY']
    for route,subview in [('companies','equities-research'),('analytics','fx-analytics'),('constituents','equities-screen'),('analytics-sectors','equities-analytics')]:
        page.evaluate('(r)=>location.hash=r',route);page.wait_for_timeout(80);assert page.locator('#subview-'+subview).is_visible(),route
    for route,index in [('peer-panel',3),('company-events-panel',4),('forensic-panel',5)]:
        page.evaluate('(r)=>location.hash=r',route);page.wait_for_timeout(80);assert page.locator('#research-view-'+str(index)).is_visible(),route
    page.locator('#tab-fx').click();page.locator('#sub-fx-analytics').click();assert page.locator('#mt-risk-comparison').is_visible()
    assert page.locator('#mt-risk-rows tr').count()==8;page.locator('#mt-risk-period').select_option('3Y');assert page.locator('#mt-risk-rows tr').count()==8
    page.locator('#tab-quality').click();assert 'Equities & Research' in page.locator('#mt-quality-tab-filter').inner_text();assert 'Company Research' not in page.locator('#mt-quality-tab-filter').inner_text()
    page.locator('#tab-equities').click();page.locator('#sub-equities-research').click();assert page.locator('#research-nav [role=tab]').count()==6
    page.locator('#research-tab-0').click();page.wait_for_timeout(80)
    order=page.locator('#research-view-0 > [id]').evaluate_all('(els)=>els.map(e=>e.id)')
    expected=['company-price-block','company-benchmark-block','research-overview','company-risk-panel','research-executive','company-advanced']
    assert [order.index(x) for x in expected]==sorted(order.index(x) for x in expected),order
    for id in ['company-chart','company-benchmark-chart','company-risk-kpis','company-technical-kpis']:assert page.locator('#'+id).count()==1
    assert 'RSI' not in page.locator('#company-risk-kpis').inner_text()
    assert page.locator('#company-advanced').get_attribute('open') is None
    page.locator('#company-advanced > summary').click();assert 'RSI' in page.locator('#company-technical-kpis').inner_text()
    page.locator('#research-tab-3').click();page.locator('#research-business .research-notebook').evaluate('(d)=>d.open=true')
    page.get_by_label('Competitive advantages & supporting evidence',exact=True).fill('R22 retained note')
    page.reload(wait_until='domcontentloaded');page.wait_for_timeout(120)
    assert page.locator('#subview-equities-research').is_visible()
    page.locator('#research-tab-3').click();assert page.get_by_label('Competitive advantages & supporting evidence',exact=True).input_value()=='R22 retained note'
    page.locator('#global-search').fill('Shell');page.wait_for_timeout(60);page.locator('#global-results button').filter(has_text='Company · SHEL.L').click();assert page.locator('#subview-equities-research').is_visible()
    for width in [744,768,1024,1440]:
        page.set_viewport_size({'width':width,'height':1100})
        page.locator('#tab-bonds').click();page.wait_for_timeout(150)
        assert '2026-11-09' in page.locator('#gilt-freshness').inner_text();assert 'Website refreshed' in page.locator('#gilt-freshness').inner_text()
        assert page.locator('#gilt-rows tr').count()==103
        assert page.locator('.gilt-table').evaluate('(t)=>t.scrollWidth<=t.parentElement.clientWidth'),width
        assert page.locator('#gilt-rows .gilt-identity small').first.inner_text().startswith('GB')
        page.locator('#gilt-search').fill('TN28');assert page.locator('#gilt-rows tr').count()==1
        page.locator('#gilt-search').fill('');page.locator('#gilt-sort').select_option('net');page.locator('#gilt-type').select_option('linked');assert page.locator('#gilt-rows tr').count()==34
        page.locator('#gilt-type').select_option('all')
        assert page.evaluate('document.body.scrollWidth<=innerWidth'),width
        page.locator('#tab-equities').click();page.locator('#sub-equities-research').click();page.locator('#research-tab-0').click();page.wait_for_timeout(100)
        assert page.evaluate('document.body.scrollWidth<=innerWidth'),width
    page.set_viewport_size({'width':768,'height':1100});page.locator('#tab-bonds').click();page.wait_for_timeout(100);page.screenshot(path='/tmp/release22-gilts-ipad.png',full_page=False)
    page.locator('#tab-equities').click();page.locator('#sub-equities-research').click();page.locator('#research-tab-0').click();page.wait_for_timeout(100);page.screenshot(path='/tmp/release22-company-ipad.png',full_page=True)
    for tab in tabs.all():tab.click();page.wait_for_timeout(60)
    assert not errors,errors
    print('PASS R22: eight workspaces, six research views, legacy routes/search/saved subsections/notes, ordered unique charts, advanced technicals, real gilt names/ISINs/yields, filtering/sorting and desktop/iPad fit')
    browser.close()
