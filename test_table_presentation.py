"""Dated short-return endpoint checks; no network or changes to stored ETF data."""
import json,subprocess,unittest
from pathlib import Path

class ShortReturns(unittest.TestCase):
    def result(self,points,period):
        source=Path('etf_original_presentation.js').read_text()
        helper=source[source.index('function etfShortPeriod('):source.index('renderEtfTracker=function(){')]
        script='const ETF_HISTORY=new Map([["TEST",'+json.dumps(points)+']]);'+helper+';console.log(JSON.stringify(etfShortPeriod({symbol:"TEST"},'+json.dumps(period)+')));'
        return json.loads(subprocess.check_output(['node','-e',script],text=True))

    def test_daily_and_weekend(self):
        self.assertAlmostEqual(self.result([['2026-11-13',100,100],['2026-11-16',102,102]],'1D')['value'],2)
        self.assertIsNone(self.result([['2026-11-06',100,100],['2026-11-16',102,102]],'1D'))

    def test_month_end_clamps_to_february(self):
        result=self.result([['2026-02-27',100,100],['2026-03-31',104,104]],'1M')
        self.assertEqual(result['start'],'2026-02-27')
        self.assertAlmostEqual(result['value'],4)

    def test_quarter_is_cumulative_not_annualised(self):
        self.assertAlmostEqual(self.result([['2026-08-13',100,100],['2026-11-13',110,110]],'3M')['value'],10)

    def test_missing_adjusted_history_is_not_zero_or_price_return(self):
        self.assertIsNone(self.result([['2026-08-14',100,None],['2026-11-13',110,None]],'3M'))
        self.assertIsNone(self.result([['2026-08-01',100,100],['2026-11-13',110,110]],'3M'))
        self.assertIsNone(self.result([],'1D'))

if __name__=='__main__':unittest.main()
