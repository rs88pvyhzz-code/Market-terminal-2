"""Release 1 financial integrity, issuer reconciliation and cache regression tests."""
import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import company_data
import company_filings as filings
import company_research as research
from test_equity_research import Frame

ROOT=Path(__file__).parent
FIX=json.loads((ROOT/'tests/fixtures/research_filings.json').read_text())

def primary(sym):
    return filings.parse_facts(FIX['issuers'][sym],sym,'2026-11-09T21:43:00+00:00',asof='2026-11-09')

class ReleaseOneTests(unittest.TestCase):
    def test_shell_published_report_reconciliation(self):
        report=json.loads((ROOT/'tests/fixtures/shell_report_reconciliation.json').read_text())
        rows={r['fiscalEnd']:r for r in primary('SHEL.L')}
        for date,fields in report['reported'].items():
            for key,millions in fields.items():
                if key in report.get('secondaryFields',[]): continue
                self.assertEqual(rows[date][key],millions*1e6,(date,key))
                self.assertEqual(rows[date]['provenance'][key]['source'],'SEC issuer filing')
                self.assertTrue(rows[date]['provenance'][key]['url'].startswith('https://www.sec.gov/'))
        self.assertEqual(len(rows),5)
        # Neither total income (including minorities) nor total revenue plus other income.
        self.assertEqual(rows['2025-12-31']['netProfit'],17837e6)
        self.assertEqual(rows['2025-12-31']['revenue'],266886e6)

    def test_secondary_shell_capex_reconciles_with_issuer_report(self):
        report=json.loads((ROOT/'tests/fixtures/shell_report_reconciliation.json').read_text())
        companies=json.loads((ROOT/'tests/fixtures/release1_companies.json').read_text())['companies']
        shell=next(c for c in companies if c['symbol']=='SHEL.L')
        rows={r['fiscalEnd']:r for r in shell['annual']}
        for date,fields in report['reported'].items():
            self.assertEqual(rows[date]['capex'],fields['capex']*1e6)
            self.assertEqual(rows[date]['provenance']['capex']['source'],'Yahoo Finance')
        calculated=research.analyse(shell['annual'])['annual'][0]
        self.assertEqual(calculated['fcf'],23916e6)
        self.assertNotEqual(calculated['fcf'],report['issuerSpecific']['2025']['freeCashFlow']*1e6)

    def test_msft_and_hsbc_primary_coverage_and_sector(self):
        msft=primary('MSFT');hsbc=primary('HSBA.L')
        self.assertEqual(len(msft),5);self.assertEqual(len(hsbc),5)
        self.assertEqual(msft[0]['sharesOutstanding'],7427e6)  # absolute quoted shares, not millions
        self.assertEqual(msft[0]['revenue'],331839e6)
        self.assertEqual(hsbc[0]['revenue'],68274e6)
        self.assertTrue(research.financial_sector({'symbol':'HSBA.L'}))
        bank=research.analyse(hsbc,True)
        for r in bank['annual']:
            for k in ('fcffProxy','roic','debtToEquity','cashConversion','fcf'):self.assertIsNone(r[k],k)
        self.assertIsNone(bank['normalisedFCFF'])

    def test_filing_priority_currency_and_periods(self):
        p=primary('SHEL.L')
        y=[{'fiscalEnd':'2025-12-31','fiscalYear':'2025','revenue':1,'operatingProfit':2},
           {'fiscalEnd':'2025-06-30','fiscalYear':'2025','revenue':3}]
        merged=filings.merge_rows(y,p,'USD')
        self.assertEqual(merged[0]['revenue'],266886e6)
        self.assertEqual(merged[0]['operatingProfit'],2)  # exact field fallback, not a manufactured EBIT
        self.assertEqual(merged[1]['revenue'],3)  # no cross-period overwrite
        mismatch=filings.merge_rows(y,p,'GBP')
        self.assertEqual(mismatch[0]['revenue'],1)  # do not mix currencies

    def test_quarterly_flows_future_filings_and_restatements(self):
        raw=copy.deepcopy(FIX['issuers']['MSFT']);facts=raw['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']['units']['USD']
        facts.extend([
            {'start':'2025-07-01','end':'2026-06-30','filed':'2026-08-01','form':'10-K','val':400e9,'accn':'test'},
            {'start':'2026-04-01','end':'2026-06-30','filed':'2026-08-02','form':'10-K','val':1,'accn':'test'},
            {'start':'2025-07-01','end':'2026-06-30','filed':'2030-08-03','form':'10-K','val':2,'accn':'test'}])
        rows=filings.parse_facts(raw,'MSFT','2026-11-09',asof='2026-11-09')
        self.assertEqual(rows[0]['revenue'],400e9)
        self.assertEqual(rows[0]['provenance']['revenue']['filed'],'2026-08-01')

    def test_growth_cagr_fcff_and_missing_data(self):
        rows=[]
        for y,revenue in [(2025,121),(2024,110),(2023,100)]:
            rows.append({'fiscalEnd':f'{y}-12-31','revenue':revenue,'operatingProfit':30,'pretaxProfit':20,'taxExpense':5,
                'depreciation':10,'capex':-15,'workingCapitalCashChange':-2,'operatingCashFlow':40,'netProfit':20,'totalDebt':30,'cash':10,'equity':80})
        a=research.analyse(rows);r=a['annual'][0]
        self.assertAlmostEqual(r['growth']['revenue'],10)
        self.assertAlmostEqual(a['cagr']['revenue'],10,delta=.02)
        self.assertEqual(r['cashConversion'],2)
        self.assertEqual(r['fcf'],25)
        self.assertEqual(r['ebitda'],40)
        self.assertEqual(r['roic'],22.5)
        self.assertEqual(r['nopat'],22.5)
        self.assertEqual(r['fcffProxy'],15.5)  # 22.5 + 10 − 15 − 2
        self.assertEqual(a['normalisedFCFF'],15.5)
        del rows[0]['workingCapitalCashChange'];rows[1]['revenue']=0
        a=research.analyse(rows)
        self.assertIsNone(a['annual'][0]['fcffProxy'])
        self.assertIsNone(a['annual'][0]['growth']['revenue'])
        self.assertNotIn('2025-12-31',a['normalisationPeriods'])
        self.assertIsNone(research.analyse([])['normalisedFCFF'])
        rows[0]['taxExpense']=50
        self.assertIsNone(research.analyse(rows)['annual'][0]['roic'])

    def test_provider_failures_are_independent(self):
        with patch('company_filings.collect',return_value=(primary('MSFT'),None)), patch.dict('sys.modules',{'yfinance':None}):
            info,rows,status,_=company_data.financials_for('MSFT')
        self.assertEqual(len(rows),5)
        self.assertEqual(info['financialCurrency'],'USD')
        self.assertIn('Issuer filings',status)
        ticker=SimpleNamespace(get_info=lambda:{'financialCurrency':'USD','longName':'Microsoft'},
            income_stmt=Frame({'2026-06-30':{'Total Revenue':100}}),balance_sheet=None,
            quarterly_balance_sheet=None,cashflow=None,calendar={})
        with patch('company_filings.collect',side_effect=ValueError('malformed response')), patch.dict('sys.modules',{'yfinance':SimpleNamespace(Ticker=lambda s:ticker)}):
            _,rows,status,_=company_data.financials_for('MSFT')
        self.assertEqual(rows[0]['revenue'],100)
        self.assertIn('SEC parsing unavailable',status)

    def test_latest_balance_is_dated_and_does_not_use_weighted_shares(self):
        t=type('T',(),{'quarterly_balance_sheet':Frame({'2026-09-30':{'Total Debt':30,'Cash And Cash Equivalents':10,'Ordinary Shares Number':7427e6}}),
                      'balance_sheet':Frame({'2025-06-30':{'Total Debt':50,'Cash And Cash Equivalents':5,'Ordinary Shares Number':7500e6}})})()
        r=company_data.latest_balance(t,'MSFT','USD','2026-11-09T00:00:00+00:00')
        self.assertEqual(r['period'],'2026-09-30');self.assertEqual(r['totalDebt'],30)
        self.assertEqual(r['sharesOutstanding'],7427e6)
        self.assertNotIn('sharesOutstanding',company_data.latest_balance(t,'UNKNOWN','USD','2026-11-09'))

    def test_observed_multiples_never_backfilled_or_saved_offline(self):
        with tempfile.TemporaryDirectory() as d:
            c={'symbol':'MSFT','annual':[],'financialAsOf':'2026-11-09','trailingPE':30,'priceToBook':8}
            with patch('company_profiles._restore_published',return_value={}):
                research.enrich([c],[],d,asof='2026-11-09T00:00:00+00:00')
            self.assertEqual(len(c['valuationHistory']),1)
            self.assertEqual(c['valuationHistory'][0]['date'],'2026-11-09')
            research.enrich([c],[],d,offline=True,asof='2026-11-10T00:00:00+00:00')
            self.assertEqual(len(c['valuationHistory']),1)
            c['financialAsOf']='2026-11-10'
            research.enrich([c],[],d,asof='2026-11-10T00:00:00+00:00')
            self.assertEqual(len(c['valuationHistory']),2)

    def test_fx_staleness_and_bank_exclusions_in_javascript(self):
        source=(ROOT/'equity_research.js').read_text().split('function setupResearchViews(){')[0]
        js=source+'''
const assert=require('node:assert/strict');
function forensicIsFinancial(c){return /bank|insurance/i.test(c.industry||'');}
assert.equal(researchFXValue('GBP','GBP',null,null),1);
assert.equal(researchFXValue('USD','GBP',1.25,null),.8);
assert.equal(researchFXValue('GBP','USD',1.25,null),1.25);
assert.equal(researchFXValue('USD','GBP',null,null),null);
assert.equal(researchFXValue('USD','GBP',0,null),null);
assert.equal(researchFXValue('UNKNOWN','GBP',1.25,null),null);
assert(researchIsFinancial({symbol:'HSBA.L'}));
assert(researchIsFinancial({symbol:'INSURER',industry:'Life insurance'}));
assert(!researchIsFinancial({symbol:'MSFT',industry:'Software'}));
assert(researchBalanceStale({period:'2025-12-31',retrievedAt:'2026-11-09'},'2026-11-09'));
assert(!researchBalanceStale({period:'2026-09-30',retrievedAt:'2026-11-09'},'2026-11-09'));
assert(researchBalanceStale({period:'2026-09-30',retrievedAt:'2026-10-01'},'2026-11-09'));
assert(researchBalanceStale({period:null,retrievedAt:null},'2026-11-09'));
console.log('FX direction, missing rates, stale balance review and sector exclusions OK');
'''
        subprocess.run(['node','-e',js],check=True)

if __name__=='__main__':unittest.main()
