"""R2.5 UI regressions against the supplied snapshot; no replacement financial fixtures."""
import csv,io,json,os,re,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text()
# Test-only access to closure state; the supplied financial payload remains unchanged.
html=html.replace('function screenNumber(id){','window.__screenState=screenState;window.__screenNumber=(id)=>screenNumber(id);\nfunction screenNumber(id){')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1024,'height':768});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000);page.locator('#tab-equities').click();page.locator('#sub-equities-screen').click()
    assert page.locator('#screen-mom').input_value()==''
    # Reproduce restored/injected FCFF in DOM, including a plausible in-range model value.
    for value in ['25892.649488670548','43.69']:
        page.locator('#screen-mom').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',value)
        assert page.locator('#screen-mom').input_value()==''
        assert page.evaluate('__screenNumber("mom")') is None
    prop={'pe':'pe','div':'div','roe':'roe','growth':'growth','debt':'leverage','vol':'vol','mom':'momentum'}
    limits={'pe':'15','div':'3','roe':'15','growth':'5','debt':'2','vol':'30','mom':'0'}
    for field,value in limits.items():
        page.locator('#screen-clear').click();page.locator('#screen-'+field).fill(value)
        assert page.evaluate('(k)=>__screenNumber(k)',field)==float(value)
        assert page.evaluate('([k,v])=>__screenState.matches.every(x=>x[k]!=null&&'+('x[k]<=v' if field in ['pe','debt','vol'] else 'x[k]>=v')+')',[prop[field],float(value)])
    page.locator('#screen-mom').fill('25892.649488670548')
    assert page.locator('#screen-export').is_disabled() and 'invalid filter' in page.locator('#screen-results').inner_text()
    page.locator('#screen-clear').click();assert not page.locator('#screen-export').is_disabled()
    for market in ['FTSE100','FTSE250','SP500','NASDAQ100','all']:
        page.locator('#screen-market').select_option(market)
        assert page.evaluate('(m)=>__screenState.matches.every(x=>m==="all"||x.markets.includes(m))',market)
    sectors=page.locator('#screen-sector option').evaluate_all('(els)=>els.map(e=>e.value)')
    for sector in sectors:
        page.locator('#screen-sector').select_option(sector)
        assert page.evaluate('(s)=>__screenState.matches.every(x=>s==="all"||x.sector===s)',sector)
    page.locator('#screen-clear').click()
    for sort in ['cap','pe','div','roe','growth','vol','momentum','name']:
        page.locator('#screen-sort').select_option(sort)
        assert page.evaluate('''(sort)=>{const a=__screenState.matches;const direction=['pe','vol'].includes(sort)?1:-1;return a.every((x,i)=>{if(!i)return true;const prev=a[i-1];if(sort==='name')return prev.name.localeCompare(x.name)<=0;if(prev[sort]==null)return x[sort]==null;if(x[sort]==null)return true;return direction*(prev[sort]-x[sort])<=0;});}''',sort)
    with page.expect_download() as download:page.locator('#screen-export').click()
    rows=list(csv.reader(io.StringIO(Path(download.value.path()).read_text())))
    assert len(rows)-1==page.evaluate('__screenState.matches.length')
    assert [r[1] for r in rows[1:]]==page.evaluate('__screenState.matches.map(x=>x.symbol)')
    page.locator('#screen-mom').fill('5');page.locator('#sub-equities-research').click();page.locator('#research-tab-2').click()
    model=page.get_by_label('Normalised FCFF (reporting currency, millions)',exact=True)
    if model.count():
        assert model.get_attribute('name').startswith('research_')
        assert model.get_attribute('form')=='mt-research-form'
    page.locator('#sub-equities-screen').click();assert page.locator('#screen-mom').input_value()=='5'
    page.reload(wait_until='domcontentloaded',timeout=120000);page.locator('#tab-equities').click();page.locator('#sub-equities-screen').click()
    assert page.locator('#screen-mom').input_value()==''
    for width,height in [(1440,1000),(1024,768),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.locator('#tab-equities').click();page.locator('#sub-equities-research').click()
        for view in [0,1,2,3,4,5]:
            page.locator('#research-tab-'+str(view)).click();page.wait_for_timeout(70)
            assert page.locator('.research-view details:not([data-r25-disclosure])').count()==0
            assert page.evaluate('document.body.scrollWidth<=innerWidth')
        page.locator('#research-tab-1').click();page.wait_for_timeout(100)
        for id in ['research-financial-chart','research-cash-chart','research-margin-chart','research-return-chart']:
            assert page.locator('#'+id).is_visible()
            assert page.locator('#'+id).evaluate('(e)=>{const r=e.getBoundingClientRect();return r.height>0&&r.height<=260;}')
        page.locator('#tab-bonds').click();page.wait_for_timeout(80)
        assert page.locator('#gilts thead th').first.evaluate('(e)=>getComputedStyle(e).position')=='sticky'
        assert page.locator('details details').count()==0
        page.evaluate('scrollTo(0,0)');page.screenshot(path=f'/tmp/release25-bonds-{width}.png',full_page=True)
    assert not errors,errors
    browser.close()
print('Release 2.5: isolated filter state, reset, ranges, all filters/sorts/index/sector/CSV, direct analysis, chart scales, sticky gilt headers; desktop/iPad/mobile passed')
