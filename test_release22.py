"""Reliability tests; existing valuation tests remain the numerical authority."""
import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import gilt_market as g
import gilt_freshness as freshness
ROOT=Path(__file__).resolve().parent

class ReliabilityTests(unittest.TestCase):
    def test_actual_official_xls_quotation_not_generation_date(self):
        raw=(ROOT/'dmo_prices/DMO_D10B_2026-11-09.xls').read_bytes()
        rows,date=g.parse_dmo_xlsx(raw)
        self.assertEqual(date.isoformat(),'2026-11-09')
        self.assertEqual(len(rows),103);self.assertEqual(sum(r['indexLinked'] for r in rows),34)
        self.assertTrue(all(r['bidClean']<=r['askClean']+.011 for r in rows))
        self.assertTrue(g._accept_snapshot({'asOf':date.isoformat(),'bonds':rows}))
        self.assertIsNone(g._accept_snapshot({'asOf':'2026-11-10','bonds':rows}))
        # Original XLSX recovery and the original model reconciliation remain supported.
        self.assertEqual(g.parse_dmo_xlsx((ROOT/'dmo_gilt_prices.xlsx').read_bytes())[1].isoformat(),'2026-11-06')

    def test_weekend_holidays_cutoff_and_uncovered_calendar(self):
        calendar=freshness.load_calendar(offline=True)
        def expect(now,quote):return freshness.assess(quote,dt.datetime.fromisoformat(now),calendar)
        self.assertEqual(expect('2026-11-10T08:00:00+00:00','2026-11-09')['expectedQuotationDate'],'2026-11-09')
        self.assertFalse(expect('2026-11-08T20:00:00+00:00','2026-11-06')['stale'])
        self.assertFalse(expect('2026-11-09T13:59:00+00:00','2026-11-06')['stale'])
        self.assertTrue(expect('2026-11-09T14:31:00+00:00','2026-11-06')['stale'])
        self.assertEqual(expect('2026-12-28T20:00:00+00:00','2026-12-24')['expectedQuotationDate'],'2026-12-24')
        self.assertFalse(expect('2026-12-28T20:00:00+00:00','2026-12-24')['stale'])
        self.assertEqual(expect('2026-04-06T20:00:00+00:00','2026-04-02')['expectedQuotationDate'],'2026-04-02')
        unknown={**calendar,'holidays':[]}
        self.assertTrue(freshness.assess('2026-11-09',dt.datetime.fromisoformat('2026-11-10T08:00:00+00:00'),unknown)['stale'])

    def test_export_exact_request_and_fail_closed_on_wrong_date(self):
        raw=(ROOT/'dmo_prices/DMO_D10B_2026-11-09.xls').read_bytes()
        class Reply:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return raw
        with patch('urllib.request.urlopen',return_value=Reply()) as call:
            events=[];result=g._download_dmo_for(dt.date(2026,11,9),events)
            self.assertEqual(result['asOf'],'2026-11-09');self.assertTrue(events[0]['success'])
            self.assertIn('Trade%20Date',call.call_args.args[0].full_url)
            events=[];self.assertIsNone(g._download_dmo_for(dt.date(2026,11,10),events));self.assertIn('does not match',events[0]['error'])

    def test_failed_retrieval_preserves_verified_prices_and_dates(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dmo_prices').mkdir()
            raw=(ROOT/'dmo_prices/DMO_D10B_2026-11-09.xls').read_bytes();(root/'dmo_prices/latest.xls').write_bytes(raw)
            with patch.object(g,'ROOT',root),patch.object(g,'LATEST',root/'latest.json'),patch.object(g,'HISTORY',root/'history.json'),patch.object(g,'_get_json',side_effect=OSError('blocked')),patch.object(g,'_download_dmo_for',return_value=None):
                rows,_,warnings,fresh=g.collect(None,SimpleNamespace(offline=False))
                self.assertFalse(fresh);self.assertEqual(len(rows),103);self.assertEqual(rows[0]['asOf'],'2026-11-09')
                self.assertTrue(any('retained verified quotation' in w for w in warnings))
                saved=json.loads((root/'latest.json').read_text());self.assertEqual(saved['asOf'],'2026-11-09')

    def test_navigation_and_calculators_have_one_copy(self):
        html=(ROOT/'terminal_template.html').read_text();js=(ROOT/'equity_research.js').read_text()
        self.assertEqual(html.count('data-workspace="'),8)
        self.assertEqual(html.count('id="company-chart"'),1);self.assertEqual(html.count('id="company-benchmark-chart"'),1)
        self.assertNotIn("'Performance & Risk'",js)
        self.assertIn('terminalResolveRoute',html)
        self.assertIn("'10Y':{label:'10 years'",html)

if __name__=='__main__':unittest.main()
