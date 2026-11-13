import subprocess,unittest
from pathlib import Path
class Coverage(unittest.TestCase):
 def test_gaps(self):
  source=(Path(__file__).resolve().parents[1]/'company_coverage.js').read_text().split('function renderCompanyCoverage')[0]
  subprocess.run(['node','-e',source+"""
const assert=require('node:assert/strict'),now=Date.parse('2026-11-13');
assert(companyCoverageFacts({},now).gaps.includes('No dated results document'));
const c={annual:[{fiscalEnd:'2025-12-31',revenue:0,netIncome:-1,operatingCashFlow:0},{fiscalEnd:'2023-12-31',revenue:1,netIncome:null,operatingCashFlow:1}]};
const x=companyCoverageFacts(c,now);assert.equal(x.usable,1);assert.equal(x.total,2);assert(x.gaps.includes('Gaps in annual history'));
c.annual.push(c.annual[0]);assert.equal(companyCoverageFacts(c,now).total,2);
c.intelligence={sources:[{kind:'results',url:'https://example.org',published:'2026-01-01',period:'2025-12-31'}]};
assert(companyCoverageFacts(c,now).gaps.some(s=>s.includes('7 months')));
"""],check=True)
if __name__=='__main__':unittest.main()
