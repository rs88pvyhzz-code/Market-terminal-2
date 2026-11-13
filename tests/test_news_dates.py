"""UK calendar boundaries, DST, missing/future dates and seven-day inclusion."""
import subprocess
from pathlib import Path
import unittest
class NewsDates(unittest.TestCase):
 def test_calendar_boundaries(self):
  source=(Path(__file__).resolve().parents[1]/'news_dates.js').read_text().split('let newsSelectedCompany')[0]
  checks="""
const assert=require('node:assert/strict');
function check(published,now,range,want){assert.equal(newsDateMatches({published},Date.parse(now),range),want,JSON.stringify({published,now,range}));}
check('2026-07-01 23:30 UTC','2026-07-02T00:00:00Z','today',true);
check('2026-07-01 22:30 UTC','2026-07-02T00:00:00Z','today',false);
check('2026-07-01 22:30 UTC','2026-07-02T00:00:00Z','yesterday',true);
check('2026-10-25 00:30 UTC','2026-10-25T02:30:00Z','today',true);
check('2026-11-07 12:00 UTC','2026-11-13T14:00:00Z','week',true);
check('2026-11-06 12:00 UTC','2026-11-13T14:00:00Z','week',false);
check('2026-11-13 15:00 UTC','2026-11-13T14:00:00Z','today',false);
check('','2026-11-13T14:00:00Z','today',false);
"""
  subprocess.run(['node','-e',source+checks],check=True)
if __name__=='__main__':unittest.main()
