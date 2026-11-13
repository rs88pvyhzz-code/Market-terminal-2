"""Compact layout: order, honest returns, sorting, retained evidence, all viewport sizes.
Demo-only news strings are labelled fixtures. Production payloads are never replaced.
"""
import json, os, re, sys, datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
html=Path(sys.argv[1]).read_text()
a=re.search(r'window.MT_DATA\s*=\s*',html).end()
data,end=json.JSONDecoder().raw_decode(html[a:])
if data.get('demo'):
    sys.path.insert(0,str(root))
    import company_research, research_intelligence
    companies=json.loads((root/'tests/fixtures/release2_companies.json').read_text())['companies']
    records=json.loads((root/'tests/fixtures/release2_evidence.json').read_text())['records']
    for c in companies:
        c['research']=company_research.analyse(c['annual'],company_research.financial_sector(c))
        c['intelligence']=research_intelligence.compose(c,records[c['symbol']],companies,asof='2026-11-09')
    by_symbol={c['symbol']:c for c in companies}
    data['companies']=[by_symbol.get(c['symbol'],c) for c in data['companies']]
    fixture_date=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M UTC')
    data['company_news']=[{'symbol':'SHEL.L','retrievedAt':'2026-11-09T23:00:00Z','articles':[
        {'title':'UI fixture: Transaction in Own Shares','url':'https://example.org/buyback','source':'UI fixture','published':fixture_date},
        {'title':'UI fixture: Quarterly results and management outlook','url':'https://example.org/results','source':'UI fixture','published':fixture_date}]}]
    html=html[:a]+json.dumps(data).replace('</','<\\/')+html[a+end:]
keys=['overview','watchlist','fx','analytics','equities','companies','etfs','bonds','economics','quality']
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),headless=True,args=['--no-sandbox'])
    for width,height in [(1440,1000),(1024,768),(768,1024),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
        page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
        page.wait_for_timeout(200)
        assert page.locator('#workspace-tabs [role=tab]').evaluate_all('(xs)=>xs.map(x=>x.dataset.workspace)')==keys
        page.locator('#tab-overview').focus();page.keyboard.press('ArrowRight')
        assert page.locator('#tab-watchlist').get_attribute('aria-selected')=='true'
        for key in keys:
            page.locator('#tab-'+key).dispatch_event('click')
            assert page.evaluate('document.body.scrollWidth<=innerWidth+1'),(width,key,'page overflow',page.evaluate('Array.from(document.querySelectorAll("body *")).filter(e=>e.getBoundingClientRect().right>innerWidth+1&&e.clientWidth>0).slice(0,20).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().width])'))
        page.locator('#tab-watchlist').dispatch_event('click')
        groups=page.locator('#watchlist-changes .watch-change-group > strong').all_text_contents()
        assert all(g in ['Results','Guidance','Dividends','Announcements'] for g in groups),groups
        assert groups or page.locator('#watchlist-changes p.mini').count()==1
        assert page.locator('#personal-watchlist-panel > :last-child').get_attribute('id')=='watchlist-changes'
        assert page.locator('#watchlist-changes').evaluate('(e)=>e.getBoundingClientRect().right<=innerWidth+1')
        page.screenshot(path=f'/tmp/compact-watchlist-changes-{width}.png')
        page.locator('#tab-overview').dispatch_event('click')
        assert page.locator('#view-overview > section').evaluate_all('(xs)=>xs.map(x=>x.id)')[:3]==['overview-board','r24-conditions','r24-developments']
        page.screenshot(path=f'/tmp/compact-overview-{width}.png')
        page.locator('#tab-analytics').dispatch_event('click')
        assert page.locator('#layout-body-markets > *').first.get_attribute('id')=='score-panel'
        assert page.locator('#mt-movers-table').count()==1
        assert page.locator('#mt-movers-table th button').count()==7
        assert page.locator('#score .mt-mover-row').count()==0
        assert page.locator('#score-panel .mt-reading-note').first.is_visible()
        rows=page.locator('#mt-movers-matrix tr[data-symbol]')
        assert rows.count()>0
        # Independently compare the displayed 1M result with the stored closing prices.
        symbol=rows.first.get_attribute('data-symbol')
        points=sorted([x for x in data['history'] if x['symbol']==symbol and x.get('close',0)>0],key=lambda x:x['date'])
        if len(points)>1:
            target=(datetime.date.fromisoformat(points[-1]['date'])-datetime.timedelta(days=30)).isoformat()
            prior=[x for x in points if x['date']<=target]
            if prior:
                expected=(points[-1]['close']/prior[-1]['close']-1)*100
                actual=float(rows.first.locator('td').nth(1).inner_text().replace('%',''))
                assert abs(expected-actual)<.051,(expected,actual)
        page.locator('[data-mt-period="YTD"]').click()
        assert page.locator('#mt-movers-view').input_value()=='ranked'
        values=[float(x.replace('%','')) for x in page.locator('#mt-movers-matrix tr[data-symbol] td:nth-child(5)').all_text_contents() if x!='—']
        assert values==sorted(values,reverse=True)
        page.locator('[data-mt-period="YTD"]').click()
        values=[float(x.replace('%','')) for x in page.locator('#mt-movers-matrix tr[data-symbol] td:nth-child(5)').all_text_contents() if x!='—']
        assert values==sorted(values)
        page.locator('#mt-movers-view').select_option('regions')
        assert page.locator('#mt-movers-matrix tr.watch-section').first.text_content()=='UK equity indices'
        row_height=rows.first.bounding_box()['height'];assert row_height<=36,(width,row_height)
        assert page.locator('#mt-movers-table thead th').first.evaluate('(e)=>getComputedStyle(e).position')=='sticky'
        page.locator('#score-panel').scroll_into_view_if_needed()
        page.screenshot(path=f'/tmp/compact-performance-{width}.png')
        page.locator('#tab-companies').dispatch_event('click');page.locator('#company-pick').select_option('SHEL.L');page.locator('#research-tab-0').click()
        ids=page.locator('#research-view-0 > [id]').evaluate_all('(xs)=>xs.map(x=>x.id)')
        assert ids.index('company-news-panel')<ids.index('company-price-block')<ids.index('company-risk-panel')
        if data.get('demo'):
            assert 'Quarterly results' in page.locator('#company-news-list article').first.inner_text()
            assert page.locator('.r213-results-table tr').count()==3
            assert page.locator('.r213-changes').is_visible()
            assert 'different stated terms' in page.locator('.r213-changes').inner_text()
            for row in page.locator('#company-news-list article').all():
                assert row.bounding_box()['height']<180,(width,row.inner_text())
                assert row.locator('a').get_attribute('href').startswith('https://')
            assert 'retrieved' not in page.locator('#company-news-list article').first.inner_text()
            assert page.locator('#company-evidence-audit').count()==1
        page.locator('#company-news-panel').scroll_into_view_if_needed()
        page.screenshot(path=f'/tmp/compact-company-{width}.png')
        assert not errors,(width,errors)
        page.close()
    browser.close()
print('PASS compact layout: four viewports, keyboard order, numeric returns, sorting, row density and company evidence')
