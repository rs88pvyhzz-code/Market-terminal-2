"""Corrective source and production-path regression tests."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import company_filings
import company_research
import research_intelligence
import shell_issuer_inputs
import source_archive
import source_integrity
import source_transport

ROOT=Path(__file__).resolve().parent

class SourceIntegrityTests(unittest.TestCase):
    def test_actual_archive_recovers_financials_not_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source_archive.restore_bytes((ROOT/'verified_sources'/source_archive.NAME).read_bytes(),root)
            data=json.loads((root/'.terminal_filings/SHEL.L.json').read_text())
            rows=company_filings.parse_facts(data['data'],'SHEL.L',data['retrievedAt'],asof='2026-11-10')
            self.assertEqual(rows[0]['depreciation'],25299e6)
            self.assertEqual(rows[1]['depreciation'],26872e6)
            self.assertEqual(rows[2]['depreciation'],31290e6)
            self.assertEqual(rows[0]['provenance']['depreciation']['retrievedAt'],data['retrievedAt'])
            saved=json.loads((root/'.terminal_filings/shell_supplemental.json').read_text())
            self.assertEqual(saved['balance']['debtAdjustment'],83e6)
            self.assertEqual(saved['capital']['sharesOutstanding'],5701440412)
            source=research_intelligence.PublicSources(root/'.terminal_research/documents',offline=True)
            # Exercise the real discovery/parser path against original source responses.
            with patch.object(research_intelligence,'issuer_alternatives',return_value=[]):
                evidence=research_intelligence.parse_sources({'symbol':'SHEL.L','financialCurrency':'USD'},source,asof='2026-11-10')
            c={'symbol':'SHEL.L','annual':rows,'research':company_research.analyse(rows)}
            composed=research_intelligence.compose(c,evidence,[c],asof='2026-11-10')
            self.assertTrue(composed['reportedResults']);self.assertTrue(composed['guidance']);self.assertTrue(composed['topics']['catalysts']);self.assertTrue(composed['topics']['risks'])
            cache=root/'.terminal_research'/research_intelligence.CACHE_NAME
            cache.write_text(json.dumps({'records':{'SHEL.L':{'schema':1,'documents':[],'checkedAt':'2026-11-10T00:00:00+00:00','attemptedAt':'2026-11-10T00:00:00+00:00'}}}))
            with patch('company_profiles._restore_published',return_value={}),patch.object(research_intelligence,'issuer_alternatives',return_value=[]):
                research_intelligence.collect([c],[],cache.parent,asof='2026-11-10T01:00:00+00:00',batch=0)
            self.assertTrue(c['intelligence']['sources'],'Retry backoff must not hide recoverable real documents')

    def test_archive_never_overwrites_newer_sources_or_accepts_unsafe_paths(self):
        blob=(ROOT/'verified_sources'/source_archive.NAME).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source_archive.restore_bytes(blob,root)
            path=root/'.terminal_filings/SHEL.L.json';data=json.loads(path.read_text());data['retrievedAt']='2026-11-11T00:00:00+00:00';path.write_text(json.dumps(data))
            source_archive.restore_bytes(blob,root);self.assertEqual(json.loads(path.read_text())['retrievedAt'],data['retrievedAt'])
            bad=json.loads(gzip.decompress(blob));entry=next(iter(bad['entries'].values()));bad['entries']={'.terminal_filings/../../escape.json':entry}
            with self.assertRaises(ValueError):source_archive.restore_bytes(gzip.compress(json.dumps(bad).encode()),root)
            bad['entries']={'.terminal_filings/bad.json':{**entry,'sha256':'invalid'}}
            with self.assertRaises(ValueError):source_archive.restore_bytes(gzip.compress(json.dumps(bad).encode()),root)

    def test_missing_financial_fields_reuse_exact_period_and_original_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            old=[{'fiscalEnd':'2025-12-31','workingCapitalCashChange':-12,'provenance':{'workingCapitalCashChange':{'source':'provider','retrievedAt':'2026-11-09'}}}]
            company_filings.retain_financial_history('TEST',old,directory)
            fresh=[{'fiscalEnd':'2025-12-31','depreciation':33,'provenance':{'depreciation':{'source':'SEC','retrievedAt':'2026-11-10'}}},{'fiscalEnd':'2026-12-31','depreciation':44,'provenance':{}}]
            rows=company_filings.retain_financial_history('TEST',fresh,directory)
            self.assertNotIn('workingCapitalCashChange',rows[0])
            self.assertEqual(rows[1]['workingCapitalCashChange'],-12)
            self.assertEqual(rows[1]['provenance']['workingCapitalCashChange']['retrievedAt'],'2026-11-09')
            self.assertEqual(rows[1]['depreciation'],33)
            # Retained financial amounts cannot cross reporting currencies.
            mismatch=company_filings.retain_financial_history('TEST',[{'fiscalEnd':'2025-12-31','provenance':{}}],directory,currency='GBP')
            self.assertNotIn('workingCapitalCashChange',mismatch[0])

    def test_missing_sec_identity_never_sends_fake_contact(self):
        with patch.dict('os.environ',{'SEC_USER_AGENT':''}),patch.object(source_transport,'record'),patch('urllib.request.urlopen') as request:
            with self.assertRaisesRegex(OSError,'identification unavailable'):source_transport.get('https://data.sec.gov/submissions/CIK0001306965.json')
            request.assert_not_called()

    def test_denial_stops_provider_and_missing_values_are_warned(self):
        from urllib.error import HTTPError
        with patch.dict('os.environ',{'SEC_USER_AGENT':'Market Terminal research contact@example.org'}),patch.object(source_transport,'record'),patch('urllib.request.urlopen',side_effect=HTTPError('url',403,'Forbidden',{},None)) as request:
            source_transport._BLOCKED.clear()
            with self.assertRaises(HTTPError):source_transport.get('https://data.sec.gov/test')
            with self.assertRaisesRegex(OSError,'further requests stopped'):source_transport.get('https://data.sec.gov/another')
            self.assertEqual(request.call_count,1)
            self.assertIn('www.sec.gov',source_transport._BLOCKED)
            source_transport._BLOCKED.clear()
        result=source_integrity.assess({'annual':[],'researchBalance':{}},'2026-11-10')
        self.assertEqual(result['status'],'review_required');self.assertTrue(any('adjustment' in x for x in result['issues']))

    def test_stale_document_failure_retains_actual_retrieval_date(self):
        with tempfile.TemporaryDirectory() as directory:
            source=research_intelligence.PublicSources(directory)
            import hashlib
            url='https://data.sec.gov/submissions/CIK0001306965.json'
            (Path(directory)/(hashlib.sha256(url.encode()).hexdigest()+'.json')).write_text(json.dumps({'body':'old response','retrievedAt':'2026-01-01T00:00:00+00:00'}))
            with patch.object(source_transport,'get',side_effect=OSError('denied')):
                body,stamp=source.get(url)
            self.assertEqual(body,'old response');self.assertEqual(stamp,'2026-01-01T00:00:00+00:00');self.assertTrue(source.warnings)

    def test_fresh_probe_never_reads_cached_body_as_a_download(self):
        import verify_fresh_sec
        with tempfile.TemporaryDirectory() as directory:
            source=verify_fresh_sec.FreshSources(directory)
            url='https://data.sec.gov/submissions/CIK0001306965.json'
            import hashlib
            cache=Path(directory)/'.terminal_research/documents';cache.mkdir(parents=True)
            path=cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
            path.write_text(json.dumps({'body':'cached','retrievedAt':'2026-11-09'}))
            with patch.object(source_transport,'get',side_effect=OSError('denied')) as get:
                with self.assertRaises(OSError):source.get(url)
                get.assert_called_once()
            self.assertEqual(source.downloads,{})
            self.assertEqual(json.loads(path.read_text())['body'],'cached')
            with patch.object(source_transport,'get',return_value=b'fresh') as get:
                self.assertEqual(source.get(url)[0],'fresh')
                self.assertEqual(source.get(url)[0],'fresh')
                self.assertEqual(get.call_count,1,'A URL is downloaded once per probe, not once per consumer')
            self.assertEqual(json.loads(path.read_text())['body'],'fresh')

    def test_denial_marker_applies_across_processes_but_not_new_attempts(self):
        with tempfile.TemporaryDirectory() as directory,patch('os.getcwd',return_value=directory):
            marker=Path(directory)/'sec_denial.json'
            marker.write_text(json.dumps({'runId':'123','runAttempt':'1'}))
            source_transport._BLOCKED.clear()
            original=Path.read_text
            with patch.object(Path,'read_text',lambda path,*a,**kw: original(marker,*a,**kw) if str(path).endswith('sec_denial.json') else original(path,*a,**kw)):
                with patch.dict('os.environ',{'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'}):self.assertTrue(source_transport.sec_denied())
                with patch.dict('os.environ',{'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2'}):self.assertFalse(source_transport.sec_denied())

    def test_financial_math_unchanged_and_history_thresholds(self):
        js=(ROOT/'equity_research.js').read_text()
        self.assertIn('rows.length>=12',js);self.assertIn('>=90',js)
        self.assertIn('history.length<12||span<years*365.25',js)
        workflow=(ROOT/'.github/workflows/live-source-checks.yml').read_text()
        self.assertIn('verify_live_research.py terminal.html',workflow);self.assertNotIn('--demo',workflow);self.assertNotIn('deploy-pages',workflow)

if __name__=='__main__':unittest.main()
