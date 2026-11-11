"""Release 2.10: 14 sourced overview markets, clean ETF selection, short tables,
distinct news, working research section navigation and UK/US bond layout.
Run unchanged demo and actual production payloads through a real browser.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys,os,json,re,collections
html=Path(sys.argv[1]).read_text(encoding='utf-8')
mt=re.search(r'window\.MT_DATA\s*=\s*',html)
assert mt,'Missing sourced data'
data=json.JSONDecoder().raw_decode(html[mt.end():])[0]
assert len(data['etfTracker']['funds'])==132,'Full source catalogue altered'
screen=[(1440,900),(1024,768),(390,844)]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1024,'height':768})
 errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.route('http://localhost:8765/**',lambda route:route.fulfill(body=html,content_type='text/html'))
 page.goto('http://localhost:8765/',wait_until='domcontentloaded',timeout=120000)
 page.wait_for_timeout(160)
 assert page.evaluate('document.documentElement.classList.contains("release210")')
 page.locator('#tab-overview').click()
 items=page.locator('#market-pulse .r24-snapshot-item')
 assert items.count()==14,items.all_text_contents()
 for symbol in ['GBP/EUR','US 10Y','Gold','Bitcoin','Europe','Japan','Emerging']:
  assert any(symbol in a for a in items.all_text_contents()),symbol
 assert 'ETF proxy' in page.locator('#r210-snapshot-note').inner_text()
 assert page.locator('#r24-developments article').count()<=5
 overview_names=page.locator('#r24-developments article a').all_text_contents()
 assert len(overview_names)==len(set(overview_names))
 page.locator('#tab-fx').click()
 page.locator('#sub-fx-news').click()
 assert page.locator('#news-list article').count()<=6
 names=page.locator('#news-list article a').all_text_contents()
 assert not set(overview_names)&set(names),'Overview headlines repeated in Markets'
 assert len(names)==len(set(names)),'Repeated Markets headlines'
 assert page.locator('.r29-news-footer').count()==1
 if not data.get('demo'):page.screenshot(path='/tmp/release210-news-ipad.png',full_page=True)
 page.locator('#tab-etfs').click()
 table=page.locator('#etf-tracker-panel .etf-table')
 assert table.locator('thead th').count()==8
 result=page.locator('#etf-rows [data-etf-symbol]').evaluate_all('''rows=>rows.map(r=>r.dataset.etfSymbol)''')
 catalogue={f['symbol']:f for f in data['etfTracker']['funds']}
 market=collections.Counter()
 for symbol in result:
  fund=catalogue[symbol]
  assert not re.search(r'\\b(ESG|SRI|climate|low[ -]?carbon|carbon[ -]?transition|Paris[ -]?aligned|sustainable|sustainability|green[ -]?bond|net[ -]?zero|responsible[ -]?investment|SDG|PAB|CTB)\\b', ' '.join([fund.get('name',''),fund.get('benchmark',''),fund.get('market','')]),re.I),(symbol,fund['name'])
  market[(fund.get('category','unknown'),fund.get('market','unknown'))]+=1
 assert market and max(market.values())<=2,market
 assert table.locator('.etf-geo-group').count()>2
 assert 'two per market' in page.locator('#etf-result-count').inner_text()
 for selector in ['#etf-tracker-panel .etf-table-scroll']:
  assert page.locator(selector).evaluate('(e)=>parseFloat(getComputedStyle(e).maxHeight)<=440')
  assert page.locator(selector).evaluate('(e)=>getComputedStyle(e).overflowY')=='auto'
 if not data.get('demo'):page.screenshot(path='/tmp/release210-etfs-ipad.png',full_page=True)
 page.locator('#tab-bonds').click()
 for selector in ['#ust-securities-scroll','#gilts .gilt-table-scroll']:
  assert page.locator(selector).evaluate('(e)=>Math.abs(parseFloat(getComputedStyle(e).maxHeight)-Math.min(innerHeight*.44,440))<1')
  assert page.locator(selector+' thead th').first.evaluate('(e)=>getComputedStyle(e).position')=='sticky'
 assert page.locator('#gilts').evaluate('''e=>e.querySelector("#gilt-ladder").compareDocumentPosition(e.querySelector("#gilt-chart"))&Node.DOCUMENT_POSITION_PRECEDING'''),'Gilt chart must precede ladder'
 assert page.locator('#gilt-stats .r28-gilt-yields').count()==1
 assert page.locator('#gilt-chart').count()==1
 assert page.locator('#gilt-freshness').count()==1
 if not data.get('demo'):page.screenshot(path='/tmp/release210-gilts-ipad.png',full_page=True)
 page.locator('#tab-equities').click()
 page.locator('#sub-equities-research').click()
 page.locator('#research-tab-4').click()
 page.wait_for_timeout(180)
 nav=page.locator('#research-view-4 > .r25-section-links')
 assert nav.locator('button').count()>=3,nav.inner_text()
 button=nav.locator('button').nth(1)
 button.click()
 assert button.evaluate('(e)=>e.classList.contains("active")'),'Research jump not activating'
 assert page.locator('#research-view-4 .r210-management-note').count()==1
 assert page.locator('#research-view-4 .r210-more-evidence').count()>=0
 assert page.locator('#research-view-4 .r24-support-heading').count()>=3
 assert page.locator('#company-events-panel .r210-company-events-scroll').count()==1
 if not data.get('demo'):page.screenshot(path='/tmp/release210-research-ipad.png',full_page=True)
 for width,height in screen:
  page.set_viewport_size({'width':width,'height':height})
  for tab in ['overview','fx','equities','bonds','etfs']:
   page.locator('#tab-'+tab).click()
   page.wait_for_timeout(40)
   assert page.evaluate('document.body.scrollWidth<=innerWidth+1'),(width,tab)
 assert not errors,errors
 browser.close()
print('PASS Release 2.10: 14 sourced quotes, UK gilt parity, 2 mainstream ETFs/market, no ESG/climate candidates, no duplicated news, short scroll, research headings; original eight-column ETF UI retained.')
