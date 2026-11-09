"""Frozen live-source verification: Shell Q3 2026 and 9 November 2026 valuation."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
import tempfile
from unittest.mock import patch
import shell_issuer_inputs as issuer
import company_research

ROOT=Path(__file__).parent
F=ROOT/'tests/fixtures'
V=json.loads((F/'shell_live_validation_2026_11_09.json').read_text())

class ShellValidationTests(unittest.TestCase):
    def debt(self,body=None):
        return issuer.parse_quarterly(body or (F/'shell_q3_2026_debt.html').read_text(),V['balance']['url'],V['retrievedAt'],'2026-10-29',asof='2026-11-09')
    def capital(self,body=None):
        return issuer.parse_capital(body or (F/'shell_capital_2026_10_30.html').read_text(),V['balance']['sharesUrl'],V['retrievedAt'],'2026-11-02',asof='2026-11-09')

    def test_q3_debt_cash_and_reported_net_debt(self):
        b=self.debt()
        self.assertEqual(b['period'],'2026-09-30')
        self.assertEqual(b['totalDebt'],76075e6);self.assertEqual(b['cash'],36425e6)
        self.assertEqual(b['debtDerivatives'],963e6);self.assertEqual(b['debtCollateral'],-880e6)
        self.assertEqual(b['debtAdjustment'],83e6)
        self.assertEqual(b['leaseLiabilities'],34147e6)
        self.assertEqual(b['reportedNetDebt'],39733e6)
        self.assertEqual(b['totalDebt']-b['cash']+b['debtAdjustment'],b['reportedNetDebt'])

    def test_issued_shares_own_date_not_yahoo_or_eps(self):
        c=self.capital()
        self.assertEqual(c['sharesOutstanding'],5701440412)
        self.assertEqual(c['sharesPeriod'],'2026-10-30')
        for other in (V['yahooQuarterEndCount'],V['yahooUndatedCount'],V['shareQuarterEndIssued'],5663.8e6):
            self.assertNotEqual(c['sharesOutstanding'],other)
        y={'period':'2026-09-30','currency':'USD','sharesOutstanding':V['yahooQuarterEndCount'],'retrievedAt':'2026-11-09','source':'Yahoo'}
        b=issuer.apply(y,self.debt(),c)
        self.assertEqual(b['sharesOutstanding'],5701440412)
        self.assertEqual(b['period'],'2026-09-30');self.assertEqual(b['sharesPeriod'],'2026-10-30')
        # If no fresh capital statement is available, do not relabel old shares with a new balance date.
        old={**y,'period':'2026-06-30'}
        b=issuer.apply(old,self.debt(),None)
        self.assertEqual(b['period'],'2026-09-30');self.assertEqual(b['sharesPeriod'],'2026-06-30')
        newer={**y,'period':'2026-12-31','totalDebt':99,'cash':88,'sharesOutstanding':55}
        b=issuer.apply(newer,self.debt(),c)
        self.assertEqual(b['totalDebt'],99);self.assertEqual(b['sharesOutstanding'],55)
        self.assertNotIn('debtAdjustment',b)

    def test_failed_source_refresh_keeps_original_dates(self):
        with tempfile.TemporaryDirectory() as root:
            balance=self.debt();capital=self.capital()
            (Path(root)/'shell_supplemental.json').write_text(json.dumps({'balance':balance,'capital':capital}))
            with patch('urllib.request.urlopen',side_effect=OSError('Source unavailable')):
                b,c,warnings=issuer.collect(root)
            self.assertEqual(b['retrievedAt'],balance['retrievedAt'])
            self.assertEqual(c['sharesRetrievedAt'],capital['sharesRetrievedAt'])
            self.assertEqual(len(warnings),2)
        self.assertIsNone(issuer.apply(None,None,None))

    def test_changed_or_future_disclosures_fail_closed(self):
        body=(F/'shell_q3_2026_debt.html').read_text()
        with self.assertRaises(ValueError):self.debt(body.replace('39,733','39,999'))
        with self.assertRaises(ValueError):self.debt(body.replace('September 30, 2026','September 30, 2030'))
        with self.assertRaises(ValueError):self.debt('<table>Unavailable</table>')
        capital=(F/'shell_capital_2026_10_30.html').read_text()
        with self.assertRaises(ValueError):self.capital(capital.replace('held no shares','held some shares'))
        with self.assertRaises(ValueError):self.capital(capital.replace('30 October 2026','30 October 2030'))

    def test_fcff_cashflow_reconciliation_and_normalised_median(self):
        a=company_research.analyse(V['historical'])
        self.assertAlmostEqual(a['normalisedFCFF'],25892.649488670548e6,places=3)
        for r in a['annual']:
            self.assertAlmostEqual(r['fcf']+r['ocfToFcffBridge'],r['fcffProxy'],places=3)
            self.assertEqual(r['fcf'],r['operatingCashFlow']-abs(r['capex']))
        self.assertAlmostEqual(a['annual'][0]['fcffProxy'],21344.209638392258e6,places=3)
        self.assertAlmostEqual(a['annual'][2]['fcffProxy'],33940.535936494314e6,places=3)

    def test_live_snapshot_dcf_fx_claims_and_scenarios(self):
        source=(ROOT/'equity_research.js').read_text().split('function setupResearchViews(){')[0]
        js=source+'\nconst V='+json.dumps(V)+r''';
const assert=require('node:assert/strict');
const fx=researchFXValue('USD','GBP',V.fxObservation.close,null);
assert(Math.abs(fx-0.7441472816299802)<1e-12);
assert.equal(researchQuoteMajor(V.equityQuote.price,'GBp'),37.01);
for(const expected of V.scenarios){
 const r=researchDCF({...V.assumptions,growth:expected.growth});
 assert(Math.abs(r.price-expected.price)<1e-10);
 assert(Math.abs(r.enterprise-r.equity-39733)<1e-8);
 assert(Math.abs(researchReverse(V.assumptions,r.price)-expected.growth)<1e-10);
 const unadjusted=researchDCF({...V.assumptions,growth:expected.growth,debtAdjustment:0});
 assert(Math.abs(unadjusted.price-r.price-83e6/V.balance.sharesOutstanding*fx)<1e-10);
}
assert.equal(researchDCF({...V.assumptions,growth:0,debtAdjustment:null}),null);
assert(researchBalanceStale({...V.balance,sharesPeriod:'2025-01-01'},'2026-11-09'));
console.log('Shell: £34.38 / £43.69 / £54.80, correct GBP/USD, ordinary shares and $39,733m financing deduction');
'''
        subprocess.run(['node','-e',js],check=True)

if __name__=='__main__':unittest.main()
