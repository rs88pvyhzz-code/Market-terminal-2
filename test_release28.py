"""Regression tests for source-backed analyst consensus and scoped Release 2.8 UI."""
import pathlib,unittest,company_data

ROOT=pathlib.Path(__file__).parent

class Release28Tests(unittest.TestCase):
    def test_consensus_known_yahoo_fields(self):
        info={'recommendationKey':'buy','recommendationMean':2.2,
              'numberOfAnalystOpinions':18,'targetMeanPrice':125.5,
              'targetLowPrice':98,'targetHighPrice':146,'currency':'GBp'}
        a=company_data.analyst_consensus(info)
        self.assertEqual(a['rating'],'buy')
        self.assertEqual(a['analysts'],18)
        self.assertEqual(a['targetMean'],125.5)
        self.assertEqual(a['quoteCurrency'],'GBp')
        self.assertEqual(a['source'],'Yahoo Finance analyst aggregation (unofficial)')
    def test_bad_aggregation_not_invented(self):
        self.assertIsNone(company_data.analyst_consensus({}))
        self.assertIsNone(company_data.analyst_consensus({'recommendationKey':'none','numberOfAnalystOpinions':10}))
        a=company_data.analyst_consensus({'recommendationMean':999,'targetLowPrice':140,'targetHighPrice':100,'targetMeanPrice':125,'currency':'USD'})
        self.assertIsNone(a['score'])
        self.assertIsNone(a['targetLow'])
        self.assertIsNone(a['targetHigh'])
        self.assertIsNone(a['rating'])
    def test_source_stays_in_research_metadata(self):
        info={'currency':'USD','targetMeanPrice':140,'recommendationKey':'hold','numberOfAnalystOpinions':8}
        result=company_data.research_metadata(info)
        self.assertEqual(result['analystConsensus']['rating'],'hold')
        self.assertIsNone(result['analystConsensus']['targetMedian'])
    def test_etf_renderer_not_modified(self):
        js=(ROOT/'terminal_release28.js').read_text('utf-8')
        self.assertNotIn('renderEtfTracker=',js)
        self.assertNotIn('etfOriginalPeers=',js)
        self.assertNotIn('ETF_FUNDS.',js)
        self.assertNotIn('ETF_HISTORY.',js)
        self.assertIn('r28NewsOverview',js)
        self.assertIn('r28MajorCalendar',js)
        self.assertIn('r28GiltPairs',js)

if __name__=='__main__':unittest.main()
