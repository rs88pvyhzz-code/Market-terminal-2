"""Release 2.9: news, bond viewport and company hierarchy browser regression.
ETF presentation retained from Release 2.7, with its own separate tests.
"""
from pathlib import Path
import os,sys,re,json
from playwright.sync_api import sync_playwright
html=Path(sys.argv[1]).read_text(encoding="utf-8")
m=re.search(r"window\.MT_DATA\s*=\s*",html)
assert m
data=json.JSONDecoder().raw_decode(html[m.end():])[0]
assert len(data["etfTracker"]["funds"])==132
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE"),args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1024,"height":768})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.route("http://localhost:8765/**",lambda route:route.fulfill(body=html,content_type="text/html"))
    page.goto("http://localhost:8765/",wait_until="domcontentloaded",timeout=120000)
    page.wait_for_timeout(200)
    assert page.evaluate("document.documentElement.classList.contains('release29')")
    page.locator("#tab-fx").click()
    page.locator("#sub-fx-news").click()
    page.wait_for_timeout(170)
    assert page.locator("#news-list .r29-news").count()<=8
    assert page.locator(".r29-news-footer").count()==1
    count=page.locator("#news-list .r29-news").count()
    assert page.locator("#news-list .r29-news a[href^='https://']").count()==count
    if page.get_by_role("button",name=re.compile("Show next")).count():
        page.get_by_role("button",name=re.compile("Show next")).click()
        assert page.locator("#news-list .r29-news").count()>count
    page.locator("#news-pills button").first.click()
    assert page.locator(".r29-news-footer").count()==1
    assert page.locator("#news-list .r29-news").count()<=8
    if not data.get("demo"):page.screenshot(path="/tmp/release29-news-ipad.png",full_page=True)
    page.locator("#tab-equities").click()
    page.locator("#sub-equities-research").click()
    page.locator("#research-tab-0").click()
    page.wait_for_timeout(160)
    order=page.locator("#research-view-0 > [id]").evaluate_all("(els)=>els.map(x=>x.id)")
    assert order.index("research-overview")<order.index("r29-coverage")<order.index("company-price-block"),order
    assert page.locator("#research-overview .r29-market-cap").count()==1
    assert "MARKET CAPITALISATION" in page.locator("#research-overview .r29-market-cap").inner_text()
    assert page.locator("#r29-coverage .r29-coverage-cell").count()==6
    assert page.locator("#company-news-list article").count()<=3
    assert page.locator("#company-chart").is_visible()
    if not data.get("demo"):page.screenshot(path="/tmp/release29-company-ipad.png",full_page=True)
    page.locator("#research-tab-2").click()
    page.wait_for_timeout(150)
    assert page.locator("#research-valuation .r29-valuation-metric").count()==6
    assert page.locator("#research-valuation input").count()==0
    assert page.get_by_role("button",name="OPEN ADVANCED DCF & STRESS MODEL").count()==1
    if not data.get("demo"):page.screenshot(path="/tmp/release29-valuation-ipad.png",full_page=True)
    page.get_by_role("button",name="OPEN ADVANCED DCF & STRESS MODEL").click()
    page.wait_for_timeout(170)
    assert page.get_by_role("button",name="RETURN TO SIMPLE VALUATION").count()==1
    # In the source model some inputs can be unavailable, but the controls remain.
    assert page.locator("#research-valuation input").count()>0
    page.get_by_role("button",name="RETURN TO SIMPLE VALUATION").click()
    assert page.locator("#research-valuation .r29-valuation-metric").count()==6
    assert page.locator("#research-valuation input").count()==0
    page.locator("#tab-bonds").click()
    page.wait_for_timeout(100)
    for selector in ["#ust-securities-scroll","#gilts .gilt-table-scroll"]:
        height=page.locator(selector).evaluate("(x)=>parseFloat(getComputedStyle(x).maxHeight)")
        assert height<=520,(selector,height)
        assert page.locator(selector+" thead th").first.evaluate("(e)=>getComputedStyle(e).position")=="sticky",selector
    assert page.locator("#gilt-freshness").count()==1
    page.locator("#tab-etfs").click()
    assert page.locator("#etf-tracker-panel .etf-table thead th").count()==8
    assert page.locator("#etf-tracker-panel .etf-table-scroll").count()>=1
    for width,height in [(1440,900),(1024,768),(390,844)]:
        page.set_viewport_size({"width":width,"height":height})
        for tab in ["fx","equities","bonds"]:
            page.locator("#tab-"+tab).click()
            page.wait_for_timeout(50)
            assert page.evaluate("document.body.scrollWidth<=innerWidth+1"),(tab,width)
    assert not errors,errors
    browser.close()
print("PASS Release 2.9: short deduplicated news, headline market cap, early coverage, simple/advanced valuation, bounded bond tables; ETF unchanged")
