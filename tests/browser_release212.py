"""Release 2.12: original Terminal 1 style, structural hierarchy and gross gilt redemption.
Runs against the exact demo or production HTML, without substituting market sources.
"""
import os,sys,re,json,math
from pathlib import Path
from playwright.sync_api import sync_playwright

html=Path(sys.argv[1]).read_text(encoding='utf-8')
m=re.search(r'window\\.MT_DATA\\s*=\\s*',html)
assert m
data=json.JSONDecoder().raw_decode(html[m.end():])[0]
assert 'terminal12-styles' in html
assert 'release212' in html
assert len(data['etfTracker']['funds'])==132
with sync_playwright() as p:
    browser=p.chromium.launch(**({'executable_path':os.environ['CHROMIUM_EXECUTABLE']} if os.environ.get('CHROMIUM_EXECUTABLE') else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':390,'height':844})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://localhost:8765/**',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
    page.wait_for_timeout(160)
    assert page.evaluate("document.documentElement.classList.contains('release212')")
    assert page.locator('#market-pulse .r24-snapshot-item').count()==14
    assert 'GBP/EUR' in ' '.join(page.locator('#market-pulse .r24-snapshot-item').all_text_contents())
    blocks=page.locator('#view-overview > section').evaluate_all('(els)=>els.map(e=>e.id)')
    assert blocks[:2]==['r24-developments','overview-board'],blocks
    assert page.locator('#r24-watch').is_hidden()
    assert page.locator('#view-overview #r24-developments').is_visible()

    page.locator('#tab-economics').click()
    major=page.locator('#calendar-items tbody tr').count()
    assert major<=5,major
    page.get_by_role('button',name='All verified releases').click()
    assert page.locator('#calendar-items tbody tr').count()>=major
    page.get_by_role('button',name='Major releases').click()

    page.locator('#tab-analytics').click()
    assert page.locator('#analytics-rolling .r212-filter-group').count()==4
    assert page.locator('#analytics-sectors .r212-filter-group').count()==2
    assert page.locator('#analytics-rolling .r212-filter-group').first.locator('label').inner_text()=='INSTRUMENT'
    heads=page.locator('#analytics-sectors thead th').all_text_contents()
    assert heads[:2]==['Sector','Relative (pp)'],heads
    assert page.locator('#r212-valuation-fold').count()==1
    if page.locator('#sector-rows tr').count()>0:
        row=page.locator('#sector-rows tr').first
        assert row.locator('td').count()==6
        assert row.locator('td').nth(1).is_visible(),'Relative outperformance must be visible'
        assert row.locator('.r212-sector-context').is_visible(),'Underlying sector/index returns must be readable on mobile'

    page.locator('#tab-companies').click()
    page.locator('#research-tab-0').click()
    ids=page.locator('#research-view-0 > [id]').evaluate_all('(xs)=>xs.map(x=>x.id)')
    assert ids.index('company-risk-panel') < ids.index('company-news-panel'),ids
    page.locator('#peer-panel').scroll_into_view_if_needed()
    assert page.locator('#r212-peer-bar').count()==1
    if page.locator('#r212-peer-pick option').count():
        assert page.locator('#r212-peer-bar').is_visible()
        assert page.locator('#peer-table table').count()==1
        assert page.locator('#peer-table table tr').first.locator('th:visible').count()<=3

    page.locator('#tab-bonds').click()
    assert page.locator('#gilts .gilt-table thead th').count()==6
    assert page.locator('#gilt-ladder').is_hidden()
    assert not page.locator('#gilt-sort option[value="net"]').count()
    assert page.locator('#gilt-nominal-input').count()==1
    gilt=page.evaluate("""() => {
        const b=giltList.find(x=>x.shortTicker==='TN28') || giltList.find(x=>!x.indexLinked&&x.quoted&&!giltYieldReviewReason(x));
        if(!b)return null;
        const flow=giltCashflows(b,b.asOf,true),v=giltValuation(b,b.askClean,b.asOf,b.askDirty);
        if(!flow||!v)return null;
        const coupons=flow.flows.reduce((a,x)=>a+x.coupon,0);
        return {isin:b.isin, profitPer100:100+coupons-v.dirty,
           ytm:v.ytm, cumulative:(100+coupons-v.dirty)/v.dirty*100,
           coupons,dirty:v.dirty};
    }""")
    if gilt:
        page.locator('#gilt-rows tr[data-isin="'+gilt['isin']+'"]').click()
        page.locator('#gilt-nominal-input').fill('20000')
        page.locator('#gilt-nominal-input').press('Tab')
        page.wait_for_timeout(70)
        assert page.locator('#gilt-stats .r28-gilt-yield').count()==3
        displayed=page.locator('#gilt-stats .r28-gilt-yield').all_text_contents()
        assert 'Annualised gross YTM' in displayed[0]
        assert 'Cumulative cash return' in displayed[1]
        assert 'Total profit for holding' in displayed[2]
        for actual,expected in [(displayed[0],gilt['ytm']),(displayed[1],gilt['cumulative'])]:
            value=float(re.search(r'-?[0-9,]+(?:\\.[0-9]+)?(?=%)',actual).group(0).replace(',',''))
            assert abs(value-expected)<0.025,(actual,expected)
        value=float(re.search(r'£(-?[0-9,]+(?:\\.[0-9]+)?)',displayed[2]).group(1).replace(',',''))
        assert abs(value-gilt['profitPer100']*200)<0.03,(value,gilt)
        assert not page.locator('#gilt-stats').get_by_text('After-tax YTM').count()

    page.locator('#tab-quality').click()
    assert page.locator('#r212-technical-notes').count()==1
    assert page.locator('#sector-note').count()==1
    for width,height in [(390,844),(768,1024),(1024,768),(1440,900)]:
        page.set_viewport_size({'width':width,'height':height})
        for key in ['overview','fx','equities','companies','bonds','analytics','etfs','economics','watchlist','quality']:
            page.locator('#tab-'+key).click()
            page.wait_for_timeout(30)
            assert page.evaluate('document.body.scrollWidth<=innerWidth+1'),(width,key,page.evaluate('document.body.scrollWidth'))
        if not data.get('demo') and width in [390,768,1024]:
            for key in ['overview','fx','analytics','bonds']:
                page.locator('#tab-'+key).click()
                page.screenshot(path=f'/tmp/release212-{key}-{width}.png',full_page=True)
    assert not errors,errors
    browser.close()
print('PASS R2.12: news-first Overview, GBP/EUR, five macro releases, mobile sector results, peers, gross gilt cash returns and all ten workspace widths')
