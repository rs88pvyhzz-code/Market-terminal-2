"""Release 2.6 UI verification on the supplied payload; no replacement fixtures."""
import json,os,re,sys,math
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text();m=re.search(r'window\.MT_DATA\s*=\s*',html);data=json.JSONDecoder().raw_decode(html[m.end():])[0]
html=html.replace('function etfR26Key(f){','window.__etf={funds:ETF_FUNDS,state:etfState,key:etfR26Key,peers:etfR26Alternatives,choose:etfR26Choose,performance:etfPerformance,rows:etfRows,priority:etfR26Priority,size:etfR26Size};\nfunction etfR26Key(f){')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1024,'height':768});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000);page.locator('#tab-etfs').click();page.wait_for_timeout(100)
    # Pure formatter edge cases; these objects never enter the live dataset.
    assert page.evaluate('__etf.size({fundSize:null,fundSizeCurrency:"USD"})')=='Unavailable'
    assert page.evaluate('__etf.size({fundSize:0,fundSizeCurrency:"USD"})')=='USD 0'
    assert page.locator('#etf-r26-pick option').count()==len(data['etfTracker']['funds'])
    assert page.locator('#etf-rows tr[data-etf-symbol]').count()>0
    assert page.locator('#etf-rows').evaluate('''e=>{const rows=[...e.querySelectorAll('[data-etf-symbol]')],counts={};for(const r of rows)counts[r.dataset.benchmarkKey]=(counts[r.dataset.benchmarkKey]||0)+1;return Object.values(counts).every(n=>n<=2)&&new Set(rows.map(r=>r.dataset.etfSymbol)).size===rows.length&&rows.every((r,i)=>!i||+r.dataset.regionOrder>=+rows[i-1].dataset.regionOrder);}''')
    assert page.locator('#etf-rows').evaluate('''e=>[...e.querySelectorAll('[data-etf-symbol]')].every(r=>{const f=__etf.funds.find(f=>f.symbol===r.dataset.etfSymbol);const eligible=__etf.funds.filter(p=>__etf.key(p)===__etf.key(f)).sort(__etf.priority).slice(0,2);return eligible.includes(f);})''')
    headers=page.locator('#etf-rows').evaluate('(e)=>[...e.closest("table").tHead.querySelectorAll("th")].map(t=>t.textContent)')
    assert headers==['Fund / ticker','TER','P/S','Fund size','1Y ann.','3Y ann.','5Y ann.'],headers
    assert page.locator('#etf-index-comparison,#etf-selected-comparisons,.etf-compare-card').count()==0
    assert page.locator('#etf-cost-peers').inner_text()==''
    # Every catalogue line remains selectable, with selected details and evidence refreshed.
    funds=data['etfTracker']['funds']
    sample=[funds[0],funds[-1]]+[f for f in funds if f['symbol'] in ['VUAG.L','EQQQ.L','VAGP.L','VAGS.L','SMH.L','FRIN.L']]
    max_peers=page.evaluate('''()=>__etf.funds.slice().sort((a,b)=>__etf.peers(b).length-__etf.peers(a).length)[0].symbol''')
    sample+=[next(f for f in funds if f['symbol']==max_peers)]
    for f in sample:
        page.locator('#etf-r26-pick').select_option(f['symbol']);page.wait_for_timeout(50)
        assert f['name'] in page.locator('#etf-selected').inner_text()
        assert f['symbol'] in page.locator('#etf-quote-link').get_attribute('href')
        assert page.locator('#etf-r26-alternatives [data-etf-alternative]').count()<=3
        assert page.evaluate('''()=>{const f=__etf.funds.find(f=>f.symbol===__etf.state.selected),peers=__etf.peers(f);return peers.every(p=>p.symbol!==f.symbol&&__etf.key(p)===__etf.key(f))&&new Set(peers.map(p=>p.isin||p.symbol)).size===peers.length;}''')
        assert page.locator('#etf-detail-stats .k').all_text_contents().count('Fund size')==1
        assert 'Fund assets (AUM)' not in page.locator('#etf-detail-stats .k').all_text_contents()
        actual_size=page.locator('#etf-detail-stats .etf-stat').filter(has=page.locator('.k',has_text=re.compile('^Fund size$'))).locator('.v').inner_text()
        assert actual_size==page.evaluate('(s)=>__etf.size(__etf.funds.find(f=>f.symbol===s))',f['symbol'])
        for check in page.locator('#etf-r26-alternatives input').all():check.check()
        assert page.evaluate('__etf.state.selected')==f['symbol']
        assert page.evaluate('__etf.state.compared.size')<=3
    if page.locator('#etf-chart svg').count():
        expected=page.evaluate('()=>[__etf.state.selected,...__etf.state.compared].filter(s=>__etf.rows(__etf.funds.find(f=>f.symbol===s)).length>1).length')
        assert page.locator('#etf-chart svg path[fill=none]').count()==expected
    selected=page.evaluate('__etf.state.selected')
    for basis in ['adjusted_gbp','price_gbp','adjusted_local','price_local']:
        page.locator('#etf-basis').select_option(basis)
        for years in ['1Y','3Y','5Y']:
            page.locator('#etf-period').select_option(years)
            # Independently reconcile the existing CAGR from the existing converted observations.
            result=page.evaluate('''([s,y])=>{const f=__etf.funds.find(f=>f.symbol===s);return {rows:__etf.rows(f,y),value:__etf.performance(f,y)};}''',[selected,years])
            rows=result['rows'];value=result['value']
            if value is not None:
                import datetime as dt
                elapsed=(dt.date.fromisoformat(rows[-1]['date'])-dt.date.fromisoformat(rows[0]['date'])).days/365.25
                expected=100*((rows[-1]['v']/rows[0]['v'])**(1/max(elapsed,1/365.25))-1)
                assert math.isclose(value,expected,abs_tol=1e-9)
        assert page.locator('#etf-r26-alternatives').locator('table').count()<=1
    # Search accesses a fund even when omitted from the initial shortlist.
    hidden=page.evaluate('''()=>__etf.funds.find(f=>!document.querySelector('[data-etf-symbol="'+f.symbol+'"]'))?.symbol''')
    if hidden:
        page.locator('#etf-search').fill(hidden);assert page.locator('#etf-r26-pick option').count()>=1
        page.locator('#etf-r26-pick').select_option(hidden);assert hidden in page.locator('#etf-selected').inner_text()
        page.locator('#etf-search').fill('')
    page.locator('#etf-basis').select_option('adjusted_gbp');page.locator('#etf-r26-pick').select_option(max_peers)
    for check in page.locator('#etf-r26-alternatives input').all():check.check()
    for width,height in [(1440,1000),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        for tab,name in [('etfs','etfs-complete'),('fx','markets'),('equities','research'),('economics','economics'),('bonds','bonds'),('watchlist','watchlist'),('quality','quality'),('overview','overview')]:
            page.locator('#tab-'+tab).click();page.wait_for_timeout(80)
            if tab=='fx':page.locator('#sub-fx-prices').click();assert page.locator('#r23-market-conditions table').count()==1
            if tab=='equities':page.locator('#sub-equities-research').click();page.locator('#research-tab-0').click();page.wait_for_timeout(100)
            assert page.evaluate('document.body.scrollWidth<=innerWidth'),(tab,width)
            assert page.locator('details details').count()==0
            if tab=='etfs':
                assert page.locator('.etf-table-scroll').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),width
                assert page.locator('#etf-r26-alternatives').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),width
            if width>=1024 and tab in ['etfs','fx','equities']:
                page.evaluate('scrollTo(0,0)');page.screenshot(path=f'/tmp/release26-{name}-{width}.png',full_page=True)
                if tab=='etfs':
                    page.locator('.etf-detail').screenshot(path=f'/tmp/release26-etfs-detail-{width}.png')
                    page.locator('#etf-r26-alternatives').screenshot(path=f'/tmp/release26-etfs-comparison-{width}.png')
    assert not errors,errors
    browser.close()
print('PASS Release 2.6: '+('ACTUAL PRODUCTION' if not data.get('demo') else 'DEMO')+'; shortlist, geography, exact peers, selection, four return bases/CAGR, no duplicated ETF panels, all workspaces, desktop/iPad/mobile; screenshots saved')
