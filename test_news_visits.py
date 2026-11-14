"""New markers use publication time, previous visit, and the current 24h window."""
import subprocess
from pathlib import Path
source=(Path(__file__).parent/'news_visits.js').read_text().split('(function(){')[0]
subprocess.run(['node','-e',source+'''
const a=require('node:assert/strict'),now=Date.parse('2026-11-14T12:00:00Z'),before=now-12*3600000;
a.equal(newsVisitIsNew('2026-11-14 01:00 UTC',before,now),true);
a.equal(newsVisitIsNew('2026-11-14 00:00 UTC',before,now),false);
a.equal(newsVisitIsNew('2026-11-14 13:00 UTC',before,now),false);
a.equal(newsVisitIsNew('2026-11-12 23:00 UTC',now-3*86400000,now),false);
a.equal(newsVisitIsNew('2026-11-14',before,now),false);
a.equal(newsVisitIsNew('2026-11-14 01:00 UTC',null,now),false);
a.equal(newsVisitIsNew('2026-11-14 01:00 UTC',now,now),false);
'''],check=True)
