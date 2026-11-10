"""Original-ETF restoration: actual supplied payload, no financial fixtures."""
import base64,json,math,os,re,sys,urllib.request,hashlib,datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text();m=re.search(r'window\.MT_DATA\s*=\s*',html);data=json.JSONDecoder().raw_decode(html[m.end():])[0]
# Closure access only for reconciliation; the market-data JSON is never changed.
html=html.replace('function etfOriginalKey(f){','window.__etf={funds:ETF_FUNDS,state:etfState,key:etfOriginalKey,peers:etfOriginalPeers,performance:etfPerformance,rows:etfRows};\nfunction etfOriginalKey(f){')
def choose(page,symbol):
    page.locator('#etf-search').fill(symbol);page.locator('#etf-rows [data-etf-symbol="'+symbol+'"]').click();page.locator('#etf-search').fill('');page.wait_for_timeout(70)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1024,'height':768});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000);page.locator('#tab-etfs').click();page.wait_for_timeout(100)
    assert page.locator('#workspace-tabs [role=tab]').count()==8
    assert len(data['etfTracker']['funds'])==132
    assert page.locator('.etf-table thead th').all_text_contents()==['Fund / ticker','TER','P/S','Fund AUM','1Y','3Y','5Y','Cmp']
    assert page.locator('#etf-r26-pick,#etf-selected-comparisons,.etf-compare-card').count()==0
    reference_disclosure=page.locator('#etf-tracker-panel [aria-label="US domiciled bond ETF references"] details')
    assert reference_disclosure.count()==1 and reference_disclosure.get_attribute('open') is None
    assert page.locator('.etf-table-scroll').evaluate('(e)=>e.clientHeight<=600&&e.scrollHeight>e.clientHeight&&getComputedStyle(e).overflowY==="auto"')
    assert page.locator('#etf-rows [data-etf-symbol]').evaluate_all('''rows=>{const counts={};for(const r of rows){const f=__etf.funds.find(f=>f.symbol===r.dataset.etfSymbol),key=__etf.key(f);counts[key]=(counts[key]||0)+1;}return Object.values(counts).every(n=>n<=2)&&new Set(rows.map(r=>r.dataset.etfSymbol)).size===rows.length;}''')
    # All original region headers remain, in the existing geographic order.
    groups=page.locator('#etf-rows .etf-geo-group').all_text_contents();assert groups[0]=='Global' and 'United States' in groups and 'United Kingdom' in groups,groups
    omitted=page.evaluate('''()=>__etf.funds.find(f=>!document.querySelector('[data-etf-symbol="'+f.symbol+'"]'))?.symbol''')
    if omitted:choose(page,omitted);assert omitted in page.locator('#etf-selected').inner_text()
    sample=['VWRP.L','VUAG.L','EQQQ.L','VAGP.L','FRIN.L']
    for symbol in sample:
        if not any(f['symbol']==symbol for f in data['etfTracker']['funds']):continue
        choose(page,symbol);assert symbol in page.locator('#etf-selected').inner_text()
        assert symbol in page.locator('#etf-quote-link').get_attribute('href')
        fund=next(f for f in data['etfTracker']['funds'] if f['symbol']==symbol)
        if fund.get('quote',{}):assert fund['quote'].get('asOf','') in page.locator('#etf-selected-meta').inner_text()
        assert page.locator('#etf-same-index [data-etf-alternative]').count()<=3
        assert page.evaluate('''()=>{const f=__etf.funds.find(f=>f.symbol===__etf.state.selected),p=__etf.peers(f);return p.every(x=>x.symbol!==f.symbol&&__etf.key(x)===__etf.key(f))&&new Set(p.map(x=>x.isin||x.symbol)).size===p.length;}''')
    # A benchmark with at least three valid alternatives must genuinely display three.
    primary=page.evaluate('''()=>__etf.funds.find(f=>__etf.peers(f).length===3)?.symbol''')
    assert primary
    choose(page,primary);assert page.locator('#etf-same-index [data-etf-alternative]').count()==3
    for index in range(3):page.locator('#etf-same-index input').nth(index).check()
    assert page.evaluate('__etf.state.selected')==primary and page.evaluate('__etf.state.compared.size')==3
    if page.locator('#etf-chart svg').count():assert page.locator('#etf-chart svg path[fill=none]').count()<=4
    for basis in ['adjusted_gbp','price_gbp','adjusted_local','price_local']:
        page.locator('#etf-basis').select_option(basis)
        for period in ['1Y','3Y','5Y']:
            page.locator('#etf-period').select_option(period)
            actual=page.evaluate('''([s,y])=>{const f=__etf.funds.find(f=>f.symbol===s);return {rows:__etf.rows(f,y),value:__etf.performance(f,y)};}''',[primary,period])
            if actual['value'] is not None:
                a,b=actual['rows'][0],actual['rows'][-1];years=(datetime.date.fromisoformat(b['date'])-datetime.date.fromisoformat(a['date'])).days/365.25
                expected=100*((b['v']/a['v'])**(1/max(years,1/365.25))-1);assert math.isclose(actual['value'],expected,abs_tol=1e-9)
    page.locator('#etf-basis').select_option('adjusted_gbp');page.locator('#etf-period').select_option('5Y')
    for width,height in [(1440,1000),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.locator('#tab-etfs').click();page.wait_for_timeout(80)
        assert page.evaluate('document.body.scrollWidth<=innerWidth'),width
        if width>=1024:assert page.locator('.etf-table-scroll').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),width
        assert page.locator('#etf-rows').evaluate('(e)=>e.children.length<145')
        assert page.locator('#etf-same-index table').count()<=1
    assert not errors,errors
    # Same representative funds and viewport for visual reference comparison.
    if not data.get('demo'):
        original_path=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/tmp/release27-original.html')
        if not original_path.exists():original_path.write_bytes(urllib.request.urlopen('https://rs88pvyhzz-code.github.io/market-terminal/',timeout=60).read())
        original=original_path.read_text();om=re.search(r'window\.MT_DATA\s*=\s*',original);od=json.JSONDecoder().raw_decode(original[om.end():])[0];assert not od.get('demo')
        reference=browser.new_page(viewport={'width':1024,'height':768});reference.route('http://localhost:8766/**',lambda r:r.fulfill(body=original,content_type='text/html'));reference.goto('http://localhost:8766/',wait_until='domcontentloaded',timeout=120000);reference.locator('#tab-etfs').click();reference.wait_for_timeout(100)
        assert set(page.locator('#etf-tracker-panel details > summary').all_text_contents()).issubset(set(reference.locator('#etf-tracker-panel details > summary').all_text_contents()))
        page.set_viewport_size({'width':1024,'height':768});choose(reference,'VUAG.L');choose(page,'VUAG.L');reference.locator('#etf-clear-comparisons').click();page.locator('#etf-clear-comparisons').click();reference.locator('#etf-search').blur();page.locator('#etf-search').blur()
        properties={'#view-etfs>.workspace-title h1':['fontFamily','fontSize','color'],'#etf-tracker-panel':['fontFamily','fontSize','padding','borderRadius'],'#etf-tracker-panel h2':['fontFamily','fontSize','color'],'#etf-tracker-panel .etf-detail .etf-stat-grid':['gridTemplateColumns','gap'],'#etf-tracker-panel .etf-detail .etf-stat .v':['fontFamily','fontSize'],'#etf-stats':['gap'],'#etf-tracker-panel .etf-table':['width','tableLayout'],'#etf-tracker-panel .etf-table th:first-child':['width'],'#etf-tracker-panel .etf-controls':['gridTemplateColumns'],'#etf-tracker-panel .etf-table td':['fontFamily','fontSize','padding','lineHeight']}
        comparisons={}
        for selector,props in properties.items():
            read='(e,props)=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]]))'
            expected=reference.locator(selector).first.evaluate(read,props);actual=page.locator(selector).first.evaluate(read,props);comparisons[selector]={'original':expected,'restored':actual};assert actual==expected,(selector,expected,actual)
        for label,target in [('original',reference),('restored',page)]:
            target.evaluate('scrollTo(0,0)');target.screenshot(path=f'/tmp/release27-{label}-ipad.png')
            target.locator('.etf-table-scroll').screenshot(path=f'/tmp/release27-{label}-table-ipad.png')
            target.locator('.etf-detail').screenshot(path=f'/tmp/release27-{label}-detail-ipad.png',style='.commandbar{visibility:hidden!important}')
        gallery=browser.new_page(viewport={'width':2080,'height':850})
        for kind in ['','table-','detail-']:
            files=[Path('/tmp/release27-'+label+'-'+kind+'ipad.png') for label in ['original','restored']]
            images=['data:image/png;base64,'+base64.b64encode(f.read_bytes()).decode() for f in files]
            gallery.set_content('<body style="margin:0;background:#08090c;color:#dce1e7;font:16px Arial"><div style="display:grid;grid-template-columns:1024px 1024px;gap:16px;padding:8px"><div><p>Original Market Terminal · '+od['generatedAt']+'</p><img src="'+images[0]+'" style="width:100%"></div><div><p>Restored Market Terminal 2 · '+data['generatedAt']+'</p><img src="'+images[1]+'" style="width:100%"></div></div></body>');gallery.screenshot(path='/tmp/release27-side-by-side-'+(kind or 'page-')+'ipad.png',full_page=True)
        Path('/tmp/release27-visual-verification.json').write_text(json.dumps({'originalSnapshot':od['generatedAt'],'currentSnapshot':data['generatedAt'],'originalHTMLSha256':hashlib.sha256(original.encode()).hexdigest(),'currentDataSha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'styles':comparisons},indent=2))
    browser.close()
print('PASS Release 2.7: '+('ACTUAL PRODUCTION' if not data.get('demo') else 'DEMO')+'; original eight-column table/scrolling/fonts, complete 132-fund search, two-per-benchmark, three exact alternatives, selection, currency bases/CAGR, iPad/desktop/mobile. Actual original/restored visual comparison produced when not demo.')
