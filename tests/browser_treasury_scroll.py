"""Treasury-only viewport regression using the supplied build, without data fixtures."""
import json,os,re,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text();m=re.search(r'window\.MT_DATA\s*=\s*',html);data=json.JSONDecoder().raw_decode(html[m.end():])[0]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
    for width,height in [(1440,1000),(1024,768)]:
        page.set_viewport_size({'width':width,'height':height});page.locator('#tab-bonds').click();page.wait_for_timeout(100)
        viewport=page.locator('#ust-securities-scroll');rows=page.locator('#ust-rows tr')
        securities=data.get('us_treasuries',[])
        assert rows.count()==(len(securities) or 1)
        assert viewport.evaluate('(e)=>Math.abs(parseFloat(getComputedStyle(e).maxHeight)-Math.min(innerHeight*.6,600))<1')
        assert viewport.evaluate('(e)=>getComputedStyle(e).overflowY')=='auto'
        assert page.locator('#ust-securities-scroll thead th').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).position==="sticky"&&getComputedStyle(e).top==="0px")')
        for id in ['ust-selected','ust-clean-input','ust-stats','ust-chart','ust-selected-date']:
            assert page.locator('#'+id).evaluate('(e)=>!e.closest("#ust-securities-scroll")')
        # The shared wrappers retain their existing policies.
        assert page.locator('#gilts .gilt-table-scroll').evaluate('(e)=>parseFloat(getComputedStyle(e).maxHeight)>.6*innerHeight')
        assert page.locator('#const-rows').evaluate('(e)=>getComputedStyle(e.closest(".constituents-scroll")).maxHeight')=='none'
        if securities:
            viewport.scroll_into_view_if_needed();viewport.evaluate('(e)=>e.scrollTop=Math.min(3000,(e.scrollHeight-e.clientHeight)/2)');page.wait_for_timeout(80)
            before=viewport.evaluate('(e)=>e.scrollTop')
            if before>0:
                assert viewport.evaluate('(e)=>{const box=e.getBoundingClientRect(),h=e.querySelector("thead th").getBoundingClientRect();return Math.abs(h.top-box.top)<3;}')
                index=rows.evaluate_all('''els=>{const box=els[0].closest('#ust-securities-scroll').getBoundingClientRect();let best=0,d=Infinity;els.forEach((e,i)=>{const r=e.getBoundingClientRect(),delta=Math.abs((r.top+r.bottom)/2-(box.top+box.bottom)/2);if(r.top>box.top+40&&r.bottom<box.bottom&&delta<d){best=i;d=delta;}});return best;}''')
                cusip=rows.nth(index).locator('td').nth(1).inner_text();rows.nth(index).click();page.wait_for_timeout(80)
                assert abs(viewport.evaluate('(e)=>e.scrollTop')-before)<2,'selection reset table scroll'
                assert cusip in page.locator('#ust-selected').inner_text()
                source=next(s for s in securities if s['cusip']==cusip)
                assert source['asOf'] in page.locator('#ust-selected-date').inner_text()
                # Detail updates and period selectors also rebuild rows: retain position.
                page.locator('#ust-clean-input').fill('99.5');assert abs(viewport.evaluate('(e)=>e.scrollTop')-before)<2
                page.locator('[data-ust-range="1Y"]').click();assert abs(viewport.evaluate('(e)=>e.scrollTop')-before)<2
                page.locator('#ust-clean-input').fill('')
            page.locator('#ust-search').fill(securities[0]['cusip']);assert rows.count()==1
            page.locator('#ust-search').fill('');assert rows.count()==len(securities)
            for kind in ['Bill','Note','Bond','TIPS','FRN','all']:
                page.locator('#ust-kind').select_option(kind)
                expected=sum(kind=='all' or s['type']==kind for s in securities)
                assert rows.count()==(expected or 1),(kind,rows.count(),expected)
            viewport.scroll_into_view_if_needed();viewport.evaluate('(e)=>e.scrollTop=Math.min(2000,e.scrollHeight-e.clientHeight)');page.wait_for_timeout(60)
            page.locator('#us-treasuries').screenshot(path=f'/tmp/release26-treasury-scroll-{width}.png')
        assert page.evaluate('document.body.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('PASS Treasury viewport: '+('ACTUAL PRODUCTION' if not data.get('demo') else 'DEMO')+'; bounded/sticky, full list, selection/detail scroll retention, filters, dates and isolated styles; desktop/iPad')
