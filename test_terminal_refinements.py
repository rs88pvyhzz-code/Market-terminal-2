import datetime as dt
import unittest
from market_briefing import classify, enrich
from market_additions import market_valuation
from market_movers import clean_symbol, parse_constituents

class RefinementTests(unittest.TestCase):
    def test_ceo_departure_beats_price_alerts_but_rumour_does_not(self):
        now=dt.datetime(2026,11,12,16,tzinfo=dt.timezone.utc)
        story={'title':'NVIDIA announces CEO transition','url':'https://example.test/release','source':'NVIDIA','official':True,'published':now.isoformat(),'retrievedAt':now.isoformat()}
        quotes=[{'symbol':str(i),'name':'Test '+str(i),'changePct':10,'asOf':now.isoformat()} for i in range(8)]
        p=enrich({'generatedAt':now.isoformat(),'news':[story],'quotes':quotes,'marketHistoryMetrics':[{'symbol':q['symbol'],'volatility1YPct':20,'dailyCloses':252,'last':now.isoformat()} for q in quotes]})
        self.assertEqual(p['marketBriefing']['leadingItems'][0]['url'],story['url'])
        self.assertIn('market_moving',classify(story,now)['categories'])
        self.assertNotIn('market_moving',classify({**story,'title':'NVIDIA CEO could resign'},now)['categories'])
        self.assertTrue(any(a.get('researchUrl') for a in p['marketBriefing']['alerts']))
    def test_company_articles_join_news(self):
        now='2026-11-12T16:00:00+00:00'
        article={'title':'Dr. Martens issues profit warning','url':'https://example.test/article','source':'Publisher','published':now,'retrievedAt':now}
        p=enrich({'generatedAt':now,'company_news':[{'symbol':'DOCS.L','articles':[article]}]})
        self.assertEqual(p['news'][0]['url'],article['url'])
        self.assertEqual(p['marketBriefing']['leadingItems'][0]['classification'],'reported_development')
    def test_price_alert_links_matching_current_article_only(self):
        now='2026-11-12T16:00:00+00:00'
        article={'title':'Dr. Martens issues profit warning','url':'https://example.test/article','source':'Publisher','published':now,'retrievedAt':now}
        p=enrich({'generatedAt':now,'quotes':[{'symbol':'DOCS.L','name':'Dr. Martens','changePct':-15,'asOf':now}],
          'marketHistoryMetrics':[{'symbol':'DOCS.L','volatility1YPct':20,'dailyCloses':252,'last':now}],
          'company_news':[{'symbol':'DOCS.L','name':'Dr. Martens plc','articles':[article,{**article,'title':'Unrelated firm','url':'https://example.test/wrong'}]}]})
        alert=next(a for a in p['marketBriefing']['alerts'] if a.get('symbol')=='DOCS.L')
        self.assertEqual([a['url'] for a in alert['relatedArticles']],[article['url']])
    def test_ten_markets_do_not_borrow_uk_bond_yields(self):
        rows=market_valuation([],[],[],[{'date':'2026-11-12','DGS10':4}],[{'date':'2026-11-12','gilt10y':5}])
        self.assertEqual(len(rows),10)
        for r in rows:
            if r['region'] not in ('US','UK'):self.assertIsNone(r['benchmark10yPct'])
            self.assertIsNone(r['trailingPEProxy'])
    def test_foreign_ticker_suffixes(self):
        self.assertEqual(clean_symbol('5','.HK'),'0005.HK')
        self.assertEqual(clean_symbol('SEHK: 5','.HK'),'0005.HK')
        self.assertEqual(clean_symbol('TYO: 1332','.T'),'1332.T')
        self.assertEqual(clean_symbol('SAP.DE','.DE'),'SAP.DE')
        html='<table class="wikitable"><tr><th>Company</th><th>Stock code</th></tr><tr><td>Test</td><td>5</td></tr></table>'
        self.assertEqual(parse_constituents(html,'HSI')[0]['symbol'],'0005.HK')

if __name__=='__main__':unittest.main()
