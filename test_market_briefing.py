"""Synthetic RSS/market scenarios; none of these records enter production caches."""
import copy
import datetime as dt
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import market_intelligence as news
from market_briefing import classify,deduplicate,enrich,timestamp,THRESHOLDS
from market_intelligence import rss_articles

NOW=dt.datetime(2026,11,10,12,tzinfo=dt.timezone.utc)
def story(title,**kw):
    return dict(title=title,url='https://example.test/'+title.replace(' ','-'),source='Synthetic test publisher',published='2026-11-10 10:00 UTC',retrievedAt='2026-11-10T11:00:00+00:00',**kw)
class BriefingTests(unittest.TestCase):
    def test_topic_scores_do_not_grant_market_moving(self):
        titles=['Microsoft earnings preview: what to expect','UK CPI inflation falls to 2.5%',
                'Fed interest rates and inflation commentary','Global stocks rally as oil slumps',
                'Euro ministers await leaders guidance','Fed official calls for interest rate cuts',
                'Company announces earnings results','Microsoft earnings beat expectations',
                'Company considers $2 billion acquisition','Could stocks jump 8% next week?']
        for title in titles:
            with self.subTest(title=title):
                item=classify(story(title,categories=['market_moving']),NOW,['Microsoft'])
                self.assertNotIn('market_moving',item['categories'])
                self.assertEqual(item['significanceEvidence'],[])
        self.assertIn('economic',classify(story(titles[1]),NOW)['categories'])
        self.assertIn('rates',classify(story(titles[2]),NOW)['categories'])
        self.assertIn('corporate',classify(story(titles[0]),NOW)['categories'])
    def test_documented_material_announcements(self):
        for title in ['Federal Reserve cuts interest rates by 25 basis points',
                      'ECB holds interest rates unchanged','Shell issues profit warning',
                      'Microsoft cuts annual revenue guidance',
                      'Company announces $2 billion acquisition']:
            with self.subTest(title=title):
                item=classify(story(title),NOW)
                self.assertIn('market_moving',item['categories'])
                self.assertTrue(item['significanceEvidence'])
        small=classify(story('Company announces $20 million acquisition'),NOW)
        self.assertNotIn('market_moving',small['categories'])
    def test_reported_move_thresholds_and_no_forecast_promotion(self):
        for title in ['Shell shares jump 5% after earnings','Stocks plunge 4% ahead of Fed decision','Treasury yields rise 15 basis points']:
            item=classify(story(title),NOW)
            self.assertIn('market_moving',item['categories']);self.assertTrue(item['significanceEvidence'])
        for title in ['Shell shares jump 2% after earnings','Treasury yields rise 5 basis points','Stocks could jump 5%','Stocks jump nearly 3%']:
            self.assertNotIn('market_moving',classify(story(title),NOW)['categories'])
    def test_significance_priority_and_dedup_evidence(self):
        routine=classify(story('Inflation earnings and interest rates commentary'),NOW)
        material=classify(story('Shell shares jump 5%'),NOW)
        self.assertGreater(routine['rank'],material['rank'])
        ranked=deduplicate([routine,material])
        self.assertEqual(ranked[0]['title'],material['title'])
        for item in ranked:
            if 'market_moving' in item['categories']:self.assertTrue(item['significanceEvidence'])
    def test_archived_evidence_cannot_silently_promote_current_duplicate(self):
        current=classify(story('Federal Reserve issues FOMC statement'),NOW)
        old=classify(dict(story('Federal Reserve issues FOMC statement'),source='Federal Reserve',official=True,archived=True),NOW)
        self.assertTrue(old['significanceEvidence'])
        combined=deduplicate([old,current])
        self.assertEqual(len(combined),1)
        self.assertNotIn('market_moving',combined[0]['categories'])
    def test_uk_release_and_fed(self):
        uk=classify(story('UK CPI inflation falls to 2.5%'),NOW)
        fed=classify(story('Federal Reserve cuts interest rates by 25 basis points'),NOW)
        self.assertIn('economic',uk['categories']);self.assertIn('UK',uk['regions'])
        self.assertIn('rates',fed['categories']);self.assertIn('US',fed['regions'])
    def test_punctuated_countries_and_eurozone(self):
        for title,region in [('U.S. inflation released','U'+'S'),('U.K. GDP rises','UK'),('Eurozone bond yields rise','Europe'),('Germany GDP falls','Europe')]:
            self.assertIn(region,classify(story(title),NOW)['regions'])
    def test_official_bank_source_provides_jurisdiction(self):
        item=classify(dict(story('Bank rate increased to 4%'),source='Bank of England',official=True),NOW)
        self.assertIn('UK',item['regions']);self.assertIn('rates',item['categories'])
    def test_publisher_location_is_not_story_geography(self):
        item=classify(story('Canadian bond yields decline - Yahoo Finance UK'),NOW)
        self.assertNotIn('UK',item['regions'])
    def test_unverified_search_match_not_featured_as_watchlist_evidence(self):
        p=enrich({'generatedAt':NOW.isoformat(),'personalWatchlist':[{'name':'Shell plc','symbol':'SHEL.L'}],'watchlist_news':[{'symbol':'SHEL.L','articles':[story('UK earnings calendar for next week')]}]})
        self.assertNotIn('watchlist',p['news'][0]['categories'])
    def test_company_watchlist(self):
        for name in ['Shell','Microsoft']:
            item=classify(story(name+' earnings and buyback announced'),NOW,[name])
            self.assertIn('watchlist',item['categories']);self.assertIn('corporate',item['categories'])
    def test_duplicate_across_categories(self):
        a=classify(story('Federal Reserve cuts interest rates by 25 basis points - Publisher A'),NOW)
        b=classify(story('Fed cuts interest rates by 25 basis points - Publisher B'),NOW)
        self.assertEqual(len(deduplicate([a,b])),1)
        c=classify(story('Fed cuts interest rates by 50 basis points - Publisher C'),NOW)
        self.assertEqual(len(deduplicate([copy.deepcopy(a),c])),2)
    def test_realistic_syndication_and_edition_labels(self):
        titles=['Euro zone ministers to discuss ECB appointments - Euronext Markets: Real-time Data','Euro zone ministers to discuss ECB appointments - Reuters','Bond yields rise ahead of inflation -- 2nd Update - marketscreener.com','Bond yields rise ahead of inflation - WSJ']
        records=[classify(story(t),NOW) for t in titles]
        self.assertEqual(len(deduplicate(records)),2)
    def test_opposite_reported_movements_remain_distinct(self):
        a=classify(story('European bond yields rise ahead of inflation and central bank decisions'),NOW)
        b=classify(story('European bond yields fall ahead of inflation and central bank decisions'),NOW)
        self.assertEqual(len(deduplicate([a,b])),2)
    def test_archives_missing_future(self):
        for item in [story('Shell earnings',restored=True),dict(story('Shell earnings'),published='2026-11-01 10:00 UTC'),dict(story('Shell earnings'),published=None),dict(story('Shell earnings'),published='2026-11-11 10:00 UTC')]:
            self.assertTrue(classify(item,NOW)['archived'])
        self.assertEqual(enrich({'generatedAt':NOW.isoformat()})['marketBriefing']['currentCount'],0)
    def test_rss_exact_headline_and_dates(self):
        xml=b'<rss><channel><item><title>UK CPI inflation falls</title><link>https://example.test/cpi</link><pubDate>Tue, 10 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(rss_articles(xml,'UK',generated=NOW)[0]['title'],'UK CPI inflation falls')
        self.assertEqual(rss_articles(xml.replace(b'https:',b'http:'),'UK',generated=NOW),[])
    def test_volatility_yields_credit_and_preservation(self):
        p={'generatedAt':NOW.isoformat(),'quotes':[{'symbol':'TEST','name':'Fixture','price':106,'changePct':6,'asOf':'2026-11-10 10:00 UTC'}], 'marketHistoryMetrics':[{'symbol':'TEST','volatility1YPct':20,'dailyCloses':252,'last':'2026-11-10'}], 'us_rates':[{'date':'2026-11-09','DGS10':4},{'date':'2026-11-10','DGS10':4.2}], 'credit_spreads':[{'name':'Synthetic credit','history':[{'date':'2026-11-09','bp':100},{'date':'2026-11-10','bp':120}]}]}
        original=copy.deepcopy(p);out=enrich(p);alerts=out['marketBriefing']['alerts']
        self.assertTrue(any('volatility' in x['detail'] for x in alerts));self.assertTrue(any('US 10Y' in x['title'] for x in alerts));self.assertTrue(any('Synthetic credit' in x['title'] for x in alerts))
        for key,value in original.items():self.assertEqual(out[key],value)
        p=copy.deepcopy(original);p['marketHistoryMetrics'][0]['priceDiscontinuityFlag']=True
        self.assertFalse(any('volatility' in x['detail'] for x in enrich(p)['marketBriefing']['alerts']))
    def test_scheduled_cpi_uses_full_official_release_title(self):
        p=enrich({'generatedAt':NOW.isoformat(),'calendar':[{'title':'Consumer Price Index','date':'2026-11-10','url':'https://example.test/synthetic-calendar'}]})
        self.assertTrue(any(x['kind']=='Scheduled' for x in p['marketBriefing']['alerts']))
    def test_routine_rate_commentary_does_not_dominate_alerts(self):
        p=enrich({'generatedAt':NOW.isoformat(),'news':[story(t) for t in ['Bond yields rise ahead of inflation rates outlook','UK earnings calendar for next 7 days','Weekly recap of share buybacks','Euro ministers await leaders guidance']]})
        self.assertFalse(any(x['kind']=='Reported' for x in p['marketBriefing']['alerts']))
    def test_no_recovered_news_alert(self):
        p=enrich({'generatedAt':NOW.isoformat(),'news':[story('Shell profit warning',archived=True)]})
        self.assertFalse(any(x['kind']=='Reported' for x in p['marketBriefing']['alerts']))
    def test_first_build_without_public_directory(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.object(news,'__file__',str(Path(root)/'market_intelligence.py')),patch.object(news,'_collect_legacy_news',return_value=([],[],0)),patch.object(news,'_published_news_archive',return_value=[]),patch.object(news,'PRIMARY_NEWS_FEEDS',[]):
                news.collect_news(None,SimpleNamespace(offline=False))
                self.assertTrue((Path(root)/'public'/'news_cache.json').exists())
                duplicate=story('Synthetic duplicate')
                with patch.object(news,'_collect_legacy_news',return_value=([duplicate,dict(duplicate,archived=True)],[],0)):
                    records,_,_=news.collect_news(None,SimpleNamespace(offline=False))
                    self.assertEqual(len(records),1)
                    self.assertFalse(records[0].get('archived',False))
                with patch.object(Path,'write_text',side_effect=OSError('synthetic unavailable disk')):
                    _,warnings,_=news.collect_news(None,SimpleNamespace(offline=False))
                    self.assertIn('could not be saved',warnings[-1])
    def test_timezones(self):self.assertEqual(timestamp('2026-11-10T13:00:00+01:00'),NOW)
if __name__=='__main__':unittest.main()
