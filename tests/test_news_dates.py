"""Rolling news window: exact cutoff, midnight, DST, future and missing times."""
import subprocess
from pathlib import Path
import unittest
class NewsDates(unittest.TestCase):
 def test_rolling_window(self):
  source=(Path(__file__).resolve().parents[1]/'news_dates.js').read_text().split('let newsSelectedCompany')[0]
  checks="""
const assert=require('node:assert/strict');
const now=Date.parse('2026-11-14T00:30:00Z');
for(const [published,want] of [
 ['2026-11-13 23:30 UTC',true],['2026-11-13 00:30 UTC',true],
 ['2026-11-13T00:29:59Z',false],['2026-11-14T00:30:01Z',false],
 ['',false],['bad date',false],['2026-11-14',false]])
 assert.equal(newsDateMatches({published},now),want,published);
assert.equal(newsDateMatches({published:'2026-10-24T02:00:00+01:00'},Date.parse('2026-10-25T01:00:00Z')),true);
assert.equal(newsDateMatches({published:'2026-10-24T01:59:59+01:00'},Date.parse('2026-10-25T01:00:00Z')),false);
assert.match(newsEmptyText(),/last 24 hours/);
"""
  subprocess.run(['node','-e',source+checks],check=True)
if __name__=='__main__':unittest.main()
