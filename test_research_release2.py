"""Release 2 evidence, cache and stress regressions. No live network required."""
import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import company_research
import research_documents as documents
import research_intelligence as intelligence

ROOT=Path(__file__).parent
FIX=ROOT/'tests/fixtures'
COMPANIES=json.loads((FIX/'release2_companies.json').read_text())['companies']
RECORDS=json.loads((FIX/'release2_evidence.json').read_text())['records']


def prepared():
    companies=copy.deepcopy(COMPANIES)
    for c in companies:c['research']=company_research.analyse(c['annual'],company_research.financial_sector(c))
    return companies


class EvidenceTests(unittest.TestCase):
    def test_real_shell_source_mix_and_guidance(self):
        c=prepared()[0];r=intelligence.compose(c,RECORDS[c['symbol']],prepared(),asof='2026-11-09')
        self.assertEqual(c['symbol'],'SHEL.L')
        self.assertEqual(r['revenueBreakdown']['segments']['period'],'2025-12-31')
        self.assertEqual(next(x for x in r['revenueBreakdown']['segments']['rows'] if x['label']=='Integrated Gas')['value'],38457e6)
        self.assertIn('overlap',r['revenueBreakdown']['geography']['basis'])
        capex=next(g for g in r['guidance'] if g['metric']=='capital expenditure' and g['horizon']=='2026')
        self.assertEqual(capex['amountText'],'$23-$25 billion')
        self.assertEqual(capex['previous']['amountText'],'$24-$26 billion')
        self.assertNotIn('upgrade',capex['comparison'])
        self.assertEqual(r['commoditySensitivities'][0]['downShockPct'],-10)
        self.assertEqual(r['commoditySensitivities'][0]['impairmentLow'],7e9)
        self.assertIn('not an FCFF',r['commoditySensitivities'][0]['basis'])
        result={x['metric']:x['value'] for x in r['reportedResults']}
        self.assertEqual(result['Cash flow from operating activities'],21043e6)

    def test_real_technology_and_financial_sector_evidence(self):
        cs=prepared()
        msft=next(c for c in cs if c['symbol']=='MSFT');bank=next(c for c in cs if c['symbol']=='HSBA.L')
        r=intelligence.compose(msft,RECORDS['MSFT'],cs,asof='2026-11-09')
        self.assertEqual(r['revenueBreakdown']['segments']['period'],'2026-09-30')
        self.assertEqual({x['metric']:x['value'] for x in r['reportedResults']}['Revenue'],92279e6)
        self.assertTrue(any('RPO' in g['metric'] for g in r['guidance']))
        r=intelligence.compose(bank,RECORDS['HSBA.L'],cs,asof='2026-11-09')
        self.assertTrue(any(g['metric']=='RoTE' for g in r['guidance']))
        self.assertTrue(any(g['metric']=='banking NII' for g in r['guidance']))
        self.assertTrue(all(w['status']=='not_assessed' for w in r['financialWarnings'] if w['key'] in ('cash','debt','margin','distributions')))
        self.assertIsNone(bank['research']['normalisedFCFF'])

    def test_no_fabricated_moats_competitors_or_missing_risk(self):
        c={'symbol':'UNKNOWN','name':'Unknown','annual':[],'research':company_research.analyse([])}
        r=intelligence.compose(c,{},[c],asof='2026-11-09')
        self.assertFalse(r['sources']);self.assertFalse(r['reportedCompetitors']);self.assertFalse(r['guidance'])
        self.assertEqual(len(r['financialWarnings']),5)
        self.assertTrue(all(x['status']=='not_assessed' for x in r['financialWarnings']))
        self.assertTrue(any('not evidence of low risk' in x for x in r['gaps']))
        peer={'symbol':'PEER','name':'Peer','industry':'Widgets','sector':'Industrials'}
        c.update(industry='Widgets',sector='Industrials')
        r=intelligence.compose(c,{},[c,peer],asof='2026-11-09')
        self.assertEqual(r['peerCandidates'][0]['symbol'],'PEER')
        self.assertFalse(r['reportedCompetitors'])

    def test_guidance_requires_same_period_unit_definition_and_qualifier(self):
        def doc(id,date,metric,period,amount,unit='USD',basis='cash capex',qualifier='range'):
            return {'id':id,'published':date,'guidance':[{'metric':metric,'horizon':period,'amountText':amount,'unit':unit,'basis':basis,'qualifier':qualifier}]}
        old=doc('old','2026-07-30','capital expenditure','2026','$24-$26 billion')
        new=doc('new','2026-10-29','capital expenditure','2026','$23-$25 billion')
        rows=documents.compare_guidance([old,new]);self.assertEqual(rows[0]['previous']['sourceId'],'old')
        for key,value in [('horizon','2027'),('unit','%'),('basis','gross capex')]:
            altered=copy.deepcopy(new);altered['guidance'][0][key]=value
            rows=documents.compare_guidance([old,altered]);self.assertIsNone(rows[0]['previous'])
        uncertain=doc('ambiguous','2026-10-29','capital expenditure','2026','$3 billion')
        uncertain['guidance'].append({**uncertain['guidance'][0],'amountText':'$6 billion'})
        rows=documents.compare_guidance([old,uncertain]);self.assertFalse(any(x['sourceId']=='ambiguous' for x in rows))

    def test_historical_rpo_is_not_a_forecast_and_no_transcript_invention(self):
        sentences=['Revenue allocated to remaining performance obligations was $684 billion as of June 30, 2026.',
                   'We expect to recognize approximately 30% of remaining performance obligation revenue over the next 12 months.']
        g=documents.guidance_rows(sentences,'2026-07-29')
        self.assertEqual(len(g),1);self.assertEqual(g[0]['amountText'],'30%');self.assertIsNone(g[0]['horizon'])
        self.assertEqual(g[0]['relativeHorizon'],'next 12 months')
        r=intelligence.compose(prepared()[0],RECORDS['SHEL.L'],prepared(),asof='2026-11-09')
        self.assertFalse(r['transcriptLinks'])
        self.assertTrue(any('No earnings-call transcript' in x for x in r['gaps']))

    def test_inline_dimensions_keep_period_currency_and_single_axis(self):
        html='''<xbrli:unit id="u"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
<xbrli:context id="a"><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">co:AlphaMember</xbrldi:explicitMember></xbrli:context>
<xbrli:context id="b"><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">co:BetaMember</xbrldi:explicitMember></xbrli:context>
<ix:nonFraction name="us-gaap:Revenues" contextRef="a" unitRef="u" scale="6">100</ix:nonFraction>
<ix:nonFraction name="us-gaap:Revenues" contextRef="b" unitRef="u" scale="6">50</ix:nonFraction>'''
        doc=documents.FilingHTML(html)
        b=documents.dimensional_revenue(doc,'USD')['segments']
        self.assertEqual(b['period'],'2025-12-31');self.assertEqual([r['value'] for r in b['rows']],[100e6,50e6])
        self.assertIsNone(documents.dimensional_revenue(doc,'GBP')['segments'])
        self.assertIsNone(documents.dimensional_revenue(documents.FilingHTML(html.replace('2025-01-01','2025-10-01')),'USD')['segments'])

    def test_capital_allocation_does_not_fill_missing_distributions(self):
        c={'research':{'annual':[{'fiscalEnd':'2025-12-31','capex':-20,'netBusinessAcquisitions':10,'dividendsPaid':-3,'fcf':10,'roic':8}]}}
        r=intelligence.capital_allocation(c)[0]
        self.assertEqual(r['acquisitions'],10)  # net proceeds stay positive, not invented spending
        self.assertIsNone(r['buybacks']);self.assertIsNone(r['coverage'])
        self.assertEqual(r['capex'],20)

    def test_losses_and_zero_payouts_are_not_missing_or_safe_by_default(self):
        c={'symbol':'LOSS','research':{'annual':[{'fiscalEnd':'2025-12-31','operatingCashFlow':-10,'netProfit':-20,'totalDebt':50,'cash':5,'operatingProfit':-2,'dividendsPaid':0,'buybacks':0}]}}
        w={x['key']:x for x in intelligence.financial_warnings(c)}
        self.assertEqual(w['cash']['status'],'flag')
        self.assertEqual(w['debt']['status'],'flag')
        self.assertEqual(w['distributions']['status'],'not_applicable')
        self.assertIsNone(w['debt']['value'])

    def test_future_cached_evidence_is_not_displayed(self):
        record=copy.deepcopy(RECORDS['SHEL.L'])
        for d in record['documents']:d['published']='2030-01-01'
        r=intelligence.compose(prepared()[0],record,prepared(),asof='2026-11-09')
        self.assertFalse(r['sources'])
        self.assertFalse(r['guidance'])

    def test_primary_links_dates_and_issuer_claim_classification(self):
        for record in RECORDS.values():
            for doc in record['documents']:
                self.assertTrue(intelligence.valid_source(doc['url']))
                self.assertLessEqual(doc['published'],'2026-11-09')
                self.assertTrue(doc.get('retrievedAt'))
                for items in doc['topics'].values():
                    for item in items:
                        self.assertIn(item['classification'],('reported_statement','management_expectation','possible_scenario'))
                        self.assertNotIn('evidenceText',item)
        self.assertFalse(intelligence.valid_source('http://www.sec.gov/test'))
        self.assertFalse(intelligence.valid_source('https://www.sec.gov.attacker.test/test'))

    def test_source_discovery_filters_future_and_irrelevant_filings(self):
        rows={'form':['8-K','8-K','10-K'],'filingDate':['2030-01-01','2026-10-01','2026-07-29'],
            'primaryDocument':['future.htm','director.htm','annual.htm'],'items':['2.02','5.02',''],
            'accessionNumber':['a','b','c'],'reportDate':['2030-01-01','2026-10-01','2026-06-30']}
        source=type('S',(),{'get':lambda self,url:(json.dumps({'filings':{'recent':rows}}),'2026-11-09')})()
        found=intelligence.discover_documents('MSFT','0000789019',source,'2026-11-09')
        self.assertEqual(len(found),1);self.assertEqual(found[0]['kind'],'annual')

    def test_cache_offline_refresh_retry_and_preservation_of_release1(self):
        with tempfile.TemporaryDirectory() as directory:
            cs=prepared();before=[copy.deepcopy((c['annual'],c['research'])) for c in cs]
            with patch('research_intelligence.parse_sources',side_effect=lambda c,*args,**kw:copy.deepcopy(RECORDS[c['symbol']])), patch('company_profiles._restore_published',return_value={}):
                cov,w=intelligence.collect(cs,[],directory,batch=3,asof='2026-11-09T23:00:00+00:00')
            self.assertEqual(cov['refreshed'],3)
            for c,old in zip(cs,before):self.assertEqual((c['annual'],c['research']),old)
            with patch('research_intelligence.parse_sources') as parse:
                intelligence.collect(cs,[],directory,asof='2026-11-10T01:00:00+00:00');parse.assert_not_called()
                intelligence.collect(cs,[],directory,offline=True,asof='2026-12-01T00:00:00+00:00');parse.assert_not_called()
            old_dates=[s['retrievedAt'] for s in cs[0]['intelligence']['sources']]
            with patch('research_intelligence.parse_sources',side_effect=OSError('network failure')):
                intelligence.collect(cs,[],directory,asof='2026-11-11T00:00:00+00:00')
            self.assertEqual(old_dates,[s['retrievedAt'] for s in cs[0]['intelligence']['sources']])
            self.assertTrue(any('Refresh failed' in text for text in cs[0]['intelligence']['gaps']))
            with patch('research_intelligence.parse_sources') as parse:
                intelligence.collect(cs,[],directory,asof='2026-11-11T02:00:00+00:00');parse.assert_not_called()
            public=Path(directory)/'public';intelligence.publish(directory,public)
            self.assertTrue((public/intelligence.CACHE_NAME).exists())

    def test_stress_preserves_r1_and_models_a_real_operating_contraction(self):
        r1=(ROOT/'equity_research.js').read_text().split('function setupResearchViews(){')[0]
        r2=(ROOT/'equity_research_r2.js').read_text().split('function researchR2Data(')[0]
        js=r1+'\n'+r2+r'''
const assert=require('node:assert/strict');
const m={fcf:100,growth:.05,discount:.1,terminal:.02,years:5,debt:200,cash:50,shares:100e6,fx:.8,debtAdjustment:3};
const inputs={revenue:1000,operatingProfit:200,taxRate:.25,revenueShockPct:0,marginShockPp:0,waccShockBp:0,recoveryYears:3,extraReinvestment:0};
const base=researchDCF(m),flat=researchDownturn(m,false,inputs);
assert(Math.abs(base.price-flat.price)<1e-10);
const stress=researchDownturn(m,false,{...inputs,revenueShockPct:-20,marginShockPp:-5,waccShockBp:200});
assert(stress.price<base.price);assert(stress.projection[0].fcff<base.flows[0].flow);
assert.equal(stress.projection[3].delta,0);
assert.equal(researchDownturn(m,true,inputs),null);
assert.equal(researchDownturn(m,false,{...inputs,taxRate:null}),null);
assert.equal(researchDownturn(m,false,{...inputs,recoveryYears:0}),null);
assert(researchPathDCF(m,[-100,-50,30,50,100])); // actual negative interim flows allowed
assert.equal(researchPathDCF(m,[100,-1]),null); // no invented perpetuity from negative terminal CF
assert.equal(researchMOS(100,80),20);
assert.equal(researchMOS(null,80),null);
assert.equal(researchMOS(-1,80),null);
assert.equal(researchPathDCF({...m,fx:null},[100,100]),null);
assert.equal(researchDownturn(m,false,{...inputs,financingShockBp:500}).price,flat.price); // interest cost is liquidity-only, not double counted in FCFF
console.log('Stress: R1 parity, real revenue/margin contraction, recovery, negative cash flow, bank exclusion, missing inputs, FX and margin of safety OK');
'''
        subprocess.run(['node','-e',js],check=True)

if __name__=='__main__':unittest.main()
