import subprocess,unittest
from pathlib import Path
class WatchChanges(unittest.TestCase):
 def test_evidence_and_missing_data(self):
  root=Path(__file__).resolve().parents[1]
  source=(root/'news_dates.js').read_text().split('let newsSelectedCompany')[0]+(root/'watchlist_changes.js').read_text().split('function renderWatchChanges')[0]
  checks="""
const assert=require('node:assert/strict');
function companyAmount(v,c){return c+' '+v;}
const now=Date.parse('2026-11-13T15:00:00Z');
assert.deepEqual(watchChangesData(null,[],now),{Results:[],Guidance:[],Dividends:[],Announcements:[]});
const c={intelligence:{sources:[{id:'new',kind:'results',published:'2026-10-29',period:'2026-09-30',url:'https://example.org/new'},{id:'old',published:'2026-07-01',url:'https://example.org/old'}],reportedResults:[{sourceId:'new',metric:'Revenue',value:10,currency:'USD'},{sourceId:'missing',metric:'Invented',value:999}],guidance:[{sourceId:'new',metric:'Capital spending',amountText:'23–25',horizon:'2026',basis:'cash',comparison:'different stated terms',previous:{sourceId:'old',amountText:'24–26',horizon:'2026',basis:'cash'}}]}};
let rows=watchChangesData(c,[{title:'CEO departure',published:'2026-11-13 12:00 UTC',url:'https://example.org/news',source:'Publisher'},{title:'Old acquisition',published:'2026-11-12 12:00 UTC',url:'https://example.org/old-news'}],now);
assert.equal(rows.Results.length,1);assert(!rows.Results[0].text.includes('Invented'));
assert.equal(rows.Guidance.length,1);assert(rows.Guidance[0].note.includes('different stated terms'));
assert.equal(rows.Announcements.length,1);assert(rows.Announcements[0].note.includes('not issuer confirmation'));
c.intelligence.guidance[0].previous.horizon='2025';
assert.equal(watchChangesData(c,[],now).Guidance.length,0);
"""
  subprocess.run(['node','-e',source+checks],check=True)
if __name__=='__main__':unittest.main()
