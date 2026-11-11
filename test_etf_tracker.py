import datetime as dt
import pathlib
import sys
import types
import unittest

ROOT=pathlib.Path(__file__).parent
sys.path.insert(0,str(ROOT))
import etf_tracker

class CatalogTests(unittest.TestCase):
    def test_catalog(self):
        rows,warnings=etf_tracker.read_catalog(ROOT/'etf_catalog.csv')
        self.assertFalse(warnings)
        self.assertEqual(len(rows),132)
        self.assertGreaterEqual(len(set(x['market'] for x in rows)),45)
        self.assertEqual(len(rows),len(set(x['symbol'] for x in rows)))
        records={x['symbol']:x for x in rows}
        self.assertEqual(records['EMXN.L']['replication'],'Synthetic swap')
        self.assertEqual(records['SPOL.L']['replication'],'Physical full')
        self.assertEqual(records['FRIN.L']['market'],'India')
        self.assertEqual(records['HMCX.L']['market'],'UK FTSE 250')
        self.assertEqual(records['VAGP.L']['hedged'],'GBP')
        self.assertEqual(records['LTAM.L']['market'],'Latin America')
    def test_demo_does_not_invent_quotes(self):
        result=etf_tracker.demo(ROOT/'etf_catalog.csv')
        self.assertEqual(result['coverage']['quoted'],0)
        self.assertTrue(all(x['quote'] is None for x in result['funds']))
    def test_performance_uses_real_span(self):
        first=dt.date(2020,1,1)
        pts=[]
        for i in range(6*365):
            date=(first+dt.timedelta(days=i)).isoformat()
            price=100*1.05**(i/365.25)
            pts.append({'date':date,'close':price,'adjClose':price})
        compact=etf_tracker.compact_history(pts)
        self.assertGreater(len(compact),1800)
        for year in (1,3,5):
            ret,basis=etf_tracker.annualised_performance(compact,year)
            self.assertAlmostEqual(ret,5,delta=0.15)
            self.assertEqual(basis,'Adjusted close proxy')
    def test_november_anniversary_uses_closest_trading_day(self):
        # Nov 9 2025 was a Sunday: use Monday Nov 10, not Friday Nov 7.
        history=[['2025-11-07',124.6,124.6],
                 ['2025-11-10',126.84,126.84],
                 ['2026-11-09',139.80,139.80]]
        # Before the chart has today's bar, 1Y is calculated to Nov 9.
        ret,basis=etf_tracker.annualised_performance(history,1)
        expected=100*((139.80/126.84)**(365.25/364)-1)
        self.assertAlmostEqual(ret,round(expected,2),places=2)
        self.assertEqual(basis,'Adjusted close proxy')

    def test_quote_only_completed_session_with_dates(self):
        history=[['2021-11-10',95,None],['2023-11-10',105,105],
                 ['2025-11-07',124.6,124.6],
                 ['2025-11-10',126.84,126.84],
                 ['2026-11-09',139.80,139.80]]
        q={'symbol':'VWRP.L','source':'Yahoo Finance',
           'price':140.36,'currency':'GBP','tradingDay':'2026-11-10',
           'asOf':'2026-11-10 16:35 UTC','quoteAfterRegularClose':True}
        points,appended=etf_tracker.include_completed_quote(history,q)
        self.assertTrue(appended)
        self.assertEqual(points[-1],['2026-11-10',140.36,None])
        value,basis=etf_tracker.annualised_performance(points,1)
        self.assertEqual(value,10.66)
        self.assertEqual(basis,'Price only')
        fund={}
        etf_tracker.attach(fund,q,points,quote_as_history=appended)
        self.assertEqual(fund['return1Y'],10.66)
        self.assertEqual(fund['returnPeriods']['1Y']['start'],'2025-11-10')
        self.assertEqual(fund['returnPeriods']['1Y']['end'],'2026-11-10')
        self.assertEqual(fund['returnEndSource'],'Yahoo after-close quote, price only')
        self.assertEqual(fund['returnBasis'],'Price only')

    def test_never_append_intraday_old_or_wrong_source(self):
        history=[['2026-11-09',139.80,139.80]]
        template={'symbol':'VWRP.L','source':'Yahoo Finance','price':140.36,
                  'tradingDay':'2026-11-10','quoteAfterRegularClose':False}
        for changes in ({},{'tradingDay':'2026-11-20','quoteAfterRegularClose':True},
                        {'source':'Unknown','quoteAfterRegularClose':True}):
            q=dict(template,**changes)
            p,used=etf_tracker.include_completed_quote(history,q)
            self.assertFalse(used)
            self.assertEqual(p,history)

    def test_missing_anniversary_is_not_imputed(self):
        points=[['2024-10-01',80,80],['2026-11-10',140,140]]
        self.assertEqual(etf_tracker.annualised_performance(points,1),(None,''))

    def test_missing_data_not_fabricated(self):
        record={'symbol':'FOO','quoteStatus':'Not downloaded','return1Y':None,'return3Y':None,'return5Y':None,'returnBasis':''}
        etf_tracker.attach(record,None,[])
        self.assertEqual(record['quoteStatus'],'Unavailable')
        self.assertIsNone(record['return1Y'])
    def test_collect_graceful_failures(self):
        class Core:
            @staticmethod
            def fetch_quote(info,opts):
                return (None,[],None,'not available')
        opts=types.SimpleNamespace(workers=3,years=5)
        payload,warnings,cached=etf_tracker.collect(Core(),opts,ROOT/'etf_catalog.csv',[],[],[],[])
        self.assertEqual(payload["coverage"]["catalogued"],132)
        self.assertEqual(payload['coverage']['unavailable'],132)
        self.assertTrue(warnings)
        self.assertEqual(cached,0)

if __name__=='__main__':unittest.main()
