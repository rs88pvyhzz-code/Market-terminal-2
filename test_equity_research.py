"""Research data-integrity and valuation regression checks (no network)."""
import pathlib
import subprocess
import unittest
from types import SimpleNamespace
import company_data

ROOT = pathlib.Path(__file__).resolve().parent

class Frame:
    def __init__(self, data):
        self.data = data
        self.columns = list(data)
        self.index = {k for v in data.values() for k in v}
        self.empty = not data
        self.loc = self
    def __getitem__(self, key):
        name, date = key
        return self.data[date].get(name)

class ResearchTests(unittest.TestCase):
    def test_exact_period_join_and_missing_values(self):
        t = SimpleNamespace(income_stmt=Frame({'2025-12-31': {'Total Revenue': 100},
                                               '2025-06-30': {'Total Revenue': 40}}),
                            balance_sheet=Frame({'2025-06-30': {'Total Debt': 20}}),
                            cashflow=Frame({'2024-12-31': {'Operating Cash Flow': 12}}))
        rows = company_data.annual_income_rows(t)
        self.assertEqual(len(rows), 3)
        self.assertNotIn('totalDebt', rows[0])
        self.assertEqual(rows[1]['totalDebt'], 20)
        self.assertNotIn('revenue', rows[2])
        self.assertEqual(rows[2]['operatingCashFlow'], 12)

    def test_partial_statement_failure(self):
        class T:
            @property
            def income_stmt(self): raise RuntimeError('Unavailable')
            balance_sheet = Frame({f'{y}-12-31': {'Total Assets': y} for y in range(2019, 2026)})
            cashflow = None
        rows = company_data.annual_income_rows(T())
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[-1]['fiscalYear'], '2021')
        self.assertNotIn('netProfit', rows[0])

    def test_models(self):
        source = (ROOT/'equity_research.js').read_text().split('function setupResearchViews(){')[0]
        js = source + r'''
const assert=require('node:assert/strict');
const m={fcf:100,growth:0,discount:.1,terminal:0,years:5,debt:200,cash:50,shares:100e6,fx:1};
const r=researchDCF(m);
// Constant perpetual FCFF of 100 at 10% gives EV 1,000; equity = 850.
assert(Math.abs(r.enterprise-1000)<1e-8);assert(Math.abs(r.price-8.5)<1e-8);
assert(Math.abs(researchReverse(m,8.5))<1e-10);
assert(Math.abs(researchReverse(m,researchDCF({...m,growth:.2}).price)-.2)<1e-10);
assert.equal(researchReverse(m,1e20),null);
for(const changed of [{fcf:null},{debt:null},{shares:0},{fx:0},{discount:0},{terminal:.1},{years:1.5},{growth:-1},{fcf:1e308}])assert.equal(researchDCF({...m,...changed}),null);
assert.equal(researchQuoteMajor(850,'GBp'),8.5);assert.equal(researchQuoteMajor(850,'GBX'),8.5);
assert.equal(researchQuoteMajor(850,'GBP'),850);assert.equal(researchQuoteMajor(null,'USD'),null);
assert(Math.abs(researchDCF({...m,fx:2}).price-17)<1e-8);
assert.equal(researchFCF({operatingCashFlow:100,capex:-30}),70);
assert.equal(researchFCF({operatingCashFlow:100,capex:30}),70);
assert.equal(researchFCF({operatingCashFlow:100}),null);
assert.equal(researchRatio(null,10),null);
assert.equal(researchROIC({operatingProfit:30,taxExpense:5,pretaxProfit:20,equity:80,totalDebt:30,cash:10},{equity:80,totalDebt:30,cash:10}),22.5);
console.log('DCF, reverse DCF, FX, GBp, missing inputs, cash flow and ROIC OK');
'''
        subprocess.run(['node','-e',js],check=True)

if __name__ == '__main__': unittest.main()
