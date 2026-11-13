"""Desktop/iPad checks on the supplied build, without replacing its data."""
import json,os,re,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text();m=re.search(r'window\.MT_DATA\s*=\s*',html);data=json.JSONDecoder().raw_decode(html[m.end():])[0]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded')
    page.locator('#tab-overview').dispatch_event('click');assert page.locator('#workspace-tabs [role=tab]').count()==10
    if any(q.get('symbol')=='^VIX' for q in data['quotes']):assert 'Index points' in page.get_by_role('button',name='Open VIX',exact=True).inner_text()
    page.locator('#tab-overview').dispatch_event('click')  # headlines live on Overview (terminal_layout.js)
    assert page.locator('#news-pills > button').count()==7
    assert page.locator('.r23-regions button').count()==5
    ids=page.locator('#r23-alerts [data-alert-id]').evaluate_all('(els)=>els.map(e=>e.dataset.alertId)');assert len(ids)==len(set(ids))
    assert page.locator('#r23-alerts [data-briefing-id]').count()<=5
    expected=['overview-board','r24-conditions','r24-developments','news','r24-upcoming']
    order=page.locator('#view-overview > [id]').evaluate_all('(els)=>els.map(e=>e.id)')
    assert [order.index(x) for x in expected]==sorted(order.index(x) for x in expected)
    for width in [1440,1024,768]:
        page.set_viewport_size({'width':width,'height':1100})
        for b in page.locator('#news-pills > button').all():
            b.click();ids=page.locator('#news-list [data-event-id]').evaluate_all('(els)=>els.map(e=>e.dataset.eventId)');assert len(ids)==len(set(ids))
            assert page.evaluate('document.body.scrollWidth<=innerWidth'),width
        page.locator('.r23-regions button').filter(has_text='UK').click();assert page.evaluate('document.body.scrollWidth<=innerWidth')
        page.locator('#news-pills > button').first.click();page.screenshot(path=f'/tmp/release24-news-{width}.png',full_page=True)
    page.locator('#tab-companies').dispatch_event('click')
    for symbol in ['SHEL.L','MSFT','HSBA.L']:
        if not any(c['symbol']==symbol for c in data['companies']):continue
        page.locator('#company-pick').select_option(symbol);page.locator('#research-tab-0').click();assert page.locator('.r23-company-changes').count()==1
        assert page.locator('#research-nav [role=tab]').count()==6
    page.locator('#tab-quality').dispatch_event('click');page.wait_for_timeout(120)
    assert page.locator('#mt-quality-focus').is_visible()
    if not page.locator('#r23-news-quality').is_visible():page.locator('#mt-other-audits > summary').click()
    assert page.locator('#r23-news-quality').is_visible()
    page.locator('#tab-analytics').dispatch_event('click');assert page.locator('#r23-market-conditions').is_visible()
    assert not errors,errors
    print('PASS R23 browser: '+('SYNTHETIC DEMO' if data['demo'] else 'ACTUAL COLLECTED DATA')+'; categories, regions, event uniqueness, overview order, issuer evidence, diagnostics, desktop/iPad')
    browser.close()
