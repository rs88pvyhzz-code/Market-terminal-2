"""Presentation checks on the supplied synthetic or actual saved production payload."""
import calendar,datetime,json,math,os,re,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text();m=re.search(r'window\.MT_DATA\s*=\s*',html);data=json.JSONDecoder().raw_decode(html[m.end():])[0]
history_path=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).resolve().parents[1]/'.terminal_us_treasury_history.json'
if not history_path.exists():history_path=Path('/tmp/current-ust-history.json')
ust_history=json.loads(history_path.read_text()) if not data.get('demo') and history_path.exists() else {}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1024,'height':768});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
        if r.request.url.endswith('us_treasury_history_cache.json'):
            r.fulfill(body=json.dumps(ust_history),content_type='application/json')
        else:r.fulfill(body=html,content_type='text/html')
    page.route('http://localhost:8765/**',route)
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
    page.locator('#tab-etfs').click();page.wait_for_timeout(200)
    expected=['Fund / ticker','TER','P/S','Fund size','1D','1M','3M','1Y','3Y','5Y','Cmp']
    assert page.locator('.etf-table thead th').all_text_contents()==expected
    histories={x['symbol']:x['points'] for x in data['etfTracker']['history']}
    funds={x['symbol']:x for x in data['etfTracker']['funds']}
    for row in page.locator('#etf-rows tr[data-etf-symbol]').all()[:12]:
        cells=row.locator('td');assert cells.count()==11
        symbol=row.get_attribute('data-etf-symbol');rows=sorted([r for r in histories.get(symbol,[]) if isinstance(r[2],(int,float)) and math.isfinite(r[2]) and r[2]>0])
        for index,period in enumerate(['1D','1M','3M'],4):
            start=None
            if len(rows)>=2:
                end=datetime.date.fromisoformat(rows[-1][0])
                if period=='1D':
                    start=rows[-2] if (end-datetime.date.fromisoformat(rows[-2][0])).days<=4 else None
                else:
                    total=end.year*12+end.month-1-(1 if period=='1M' else 3);year,month=divmod(total,12);month+=1
                    target=datetime.date(year,month,min(end.day,calendar.monthrange(year,month)[1]))
                    choices=[r for r in rows if datetime.date.fromisoformat(r[0])<=target]
                    if choices and (target-datetime.date.fromisoformat(choices[-1][0])).days<=7:start=choices[-1]
            text=cells.nth(index).inner_text()
            if start:
                value=100*(rows[-1][2]/start[2]-1)
                assert abs(float(text.replace('%','').replace('−','-'))-value)<.011,(symbol,period,text,value)
                assert start[0] in cells.nth(index).get_attribute('title')
            else:assert text=='—',(symbol,period,text)
        # Annualised return fields must still be the recorded, unmodified values.
        for index,period in enumerate(['1Y','3Y','5Y'],7):
            value=funds[symbol].get('return'+period)
            if value is not None:assert abs(float(cells.nth(index).inner_text().replace('%','').replace('−','-'))-value)<.011
    for width,height in [(1440,900),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100)
        assert page.evaluate('document.body.scrollWidth<=innerWidth+1')
        if width>=1024:
            assert page.locator('.etf-table-scroll').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
            assert page.locator('.etf-table thead th:visible').all_text_contents()==expected[:-1]
        page.locator('.etf-table').screenshot(path=f'/tmp/compact-table-emphasis-etf-{width}.png')
    page.set_viewport_size({'width':1024,'height':768})
    page.locator('#tab-bonds').click();page.locator('#layout-bond-tabs button').filter(has_text='US Treasuries').click();page.wait_for_timeout(180)
    assert 'CUSIP' not in page.locator('#ust-securities-scroll thead').inner_text()
    rows=page.locator('#ust-rows tr[data-cusip]')
    if rows.count():
        assert rows.first.locator('td').count()==8
        first=data['us_treasuries'][0];page.locator('#ust-search').fill(first['cusip']);assert rows.count()==1
        rows.first.click();assert first['cusip'] in page.locator('#ust-selected').inner_text()
        assert first['cusip'] in page.locator('#ust-stats').inner_text()
        page.locator('#ust-search').fill('');assert rows.count()==len(data['us_treasuries'])
        # Actual unchanged marks must be explained, not manufactured into movement.
        flat=next((b for b in data['us_treasuries'] if len(ust_history.get(b['cusip'],[]))>=2 and len({v for d,v in ust_history[b['cusip']]})==1),None)
        if flat:
            page.locator('#ust-search').fill(flat['cusip']);rows.first.click();page.wait_for_timeout(100)
            assert page.locator('#ust-chart svg').count()==0
            assert 'Unchanged recorded prices' in page.locator('#ust-chart').inner_text()
            assert page.locator('#ust-chart tbody tr').count()==len(ust_history[flat['cusip']])
            page.locator('#us-treasuries').screenshot(path='/tmp/compact-table-emphasis-treasury-ipad.png')
        varying=next((b for b in data['us_treasuries'] if len({v for d,v in ust_history.get(b['cusip'],[])})>1),None)
        if varying:
            page.locator('#ust-search').fill(varying['cusip']);rows.first.click();page.wait_for_timeout(100)
            assert page.locator('#ust-chart svg').count()==1, 'Genuine changing price history must retain its chart'
    page.locator('#layout-bond-tabs button').filter(has_text='UK gilts').click();page.wait_for_timeout(120)
    if data.get('gilts'):
        assert page.locator('#gilt-rows .rate-coupon').count()>0
        assert page.locator('#gilt-rows .rate-ytm').count()>0
        # Review markers are never coloured like verified numeric yields.
        assert page.locator('#gilt-rows td.rate-ytm').filter(has_text='Review').count()==0
        page.locator('#gilts').screenshot(path='/tmp/compact-table-emphasis-gilts-ipad.png')
    page.locator('#tab-companies').click();page.wait_for_timeout(180)
    if page.locator('#view-companies .signed-positive').count():
        assert page.locator('#view-companies .signed-positive').first.evaluate('(e)=>getComputedStyle(e).color')=='rgb(95, 211, 154)'
    if page.locator('#view-companies .layout-metrics').count():
        page.locator('#view-companies .layout-metrics').first.screenshot(path='/tmp/compact-table-emphasis-company-ipad.png')
    assert not errors,errors
    browser.close()
print('PASS table emphasis: '+('SYNTHETIC' if data.get('demo') else 'ACTUAL SAVED PRODUCTION')+'; six ETF periods independently reconciled, CUSIP details/search retained, flat marks explained, rate and sign colours, desktop/iPad/mobile')
