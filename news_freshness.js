/* News freshness: no headline older than 3 days is shown anywhere.
 *
 * Runs before the application script, on the snapshot data itself, so every
 * news panel (Overview, company "What changed?", watchlist, briefing) sees the
 * same pruned lists. Age is measured against the viewer's clock, so a page left
 * open over a weekend keeps dropping stories as they pass 72 hours.
 * Only news is pruned. Issuer documents (results, filings, interims) are dated
 * evidence, not news, and are left untouched. A news item without a readable
 * date cannot be shown to be recent, so it is dropped.
 * build_site.py injects this file straight after the snapshot data.
 */
(function(){
'use strict';
const D=window.MT_DATA;if(!D)return;
const MAX_AGE_MS=72*3600*1000,now=Date.now();
function stamp(item){
  const raw=item&&(item.published||item.publishedAt||item.pubDate||item.date);
  if(!raw)return NaN;
  const s=String(raw).trim().replace(/ UTC$/,'Z').replace(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})/,'$1T$2');
  const t=Date.parse(/T\d{2}:\d{2}(:\d{2})?$/.test(s)?s+'Z':s);
  return t;
}
function fresh(item){const t=stamp(item);return Number.isFinite(t)&&now-t<=MAX_AGE_MS&&t-now<=6*3600*1000;}
function pruneArray(arr){if(!Array.isArray(arr))return 0;let n=0;for(let i=arr.length-1;i>=0;i--){if(!fresh(arr[i])){arr.splice(i,1);n++;}}return n;}
// One story, at most two headlines. Market headlines often carry many reports of the
// same event (e.g. a CEO resignation). A word that recurs in three or more current
// headlines and is not general market vocabulary marks a running story; once two
// headlines on it are kept (in their ranked order), further ones are dropped.
const GENERIC=new Set(('stock stocks market markets shares share ceo chief executive says said rates rate inflation '+
 'fed federal reserve bank banks bond bonds yields yield oil gold dollar sterling pound euro uk us u.s. europe european global '+
 'world week today news price prices investors wall street ftse s&p 500 nasdaq dow record high higher low lower rise rises '+
 'fall falls amid after over with from into what how why year years new first more than this that their its company '+
 'companies earnings results profit growth economy economic data report reports update live business finance financial '+
 'trade trading deal plan plans could would will may set sees seen jobs labour labor central policy cut cuts hike hikes '+
 'government china chinese american british midday morning evening close opening').split(/\s+/));
function storyWords(item){
  let t=String(item.title||'');const i=t.lastIndexOf(' - ');if(i>20)t=t.slice(0,i);
  return [...new Set((t.toLowerCase().match(/[a-z][a-z0-9&'.-]{2,}/g)||[]).map(w=>w.replace(/['.]+$/,'')).filter(w=>!GENERIC.has(w)))];
}
function capRepeatedStories(arr){
  if(!Array.isArray(arr)||arr.length<3)return 0;
  const words=arr.map(storyWords),freq=new Map();
  for(const ws of words)for(const w of ws)freq.set(w,(freq.get(w)||0)+1);
  const kept=new Map();let n=0;
  for(let i=0;i<arr.length;i++){
    const hot=words[i].filter(w=>freq.get(w)>=3);
    if(hot.some(w=>(kept.get(w)||0)>=2)){arr[i]=null;n++;continue;}
    for(const w of hot)kept.set(w,(kept.get(w)||0)+1);
  }
  for(let i=arr.length-1;i>=0;i--)if(arr[i]===null)arr.splice(i,1);
  return n;
}
let removed=0;
removed+=pruneArray(D.news);
// Company and watchlist feeds are lists of {symbol, articles:[...]}: prune the articles,
// never the company entry itself (an earlier version dropped whole feeds here).
for(const key of ['company_news','watchlist_news']){
  const v=D[key];
  const feeds=Array.isArray(v)?v:(v&&typeof v==='object'?Object.values(v):[]);
  for(const feed of feeds){
    if(feed&&Array.isArray(feed.articles))removed+=pruneArray(feed.articles);
    else if(Array.isArray(feed))removed+=pruneArray(feed);
  }
}
removed+=capRepeatedStories(D.news);
for(const c of [...(D.companies||[]),...(D.watchlist_quotes||[])]){
  if(Array.isArray(c&&c.news))removed+=pruneArray(c.news);
  const src=c&&c.intelligence&&c.intelligence.sources;
  if(Array.isArray(src))for(let i=src.length-1;i>=0;i--){if(src[i]&&src[i].kind==='news'&&!fresh(src[i])){src.splice(i,1);removed++;}}
}
const brief=D.marketBriefing;
if(brief&&Array.isArray(brief.leadingItems)){
  const live=new Set((D.news||[]).map(x=>x.id));
  brief.leadingItems=brief.leadingItems.filter(x=>x.newsId?live.has(x.newsId):(stamp(x)?fresh(x):true));
}
D.newsFreshness={maxAgeHours:72,removed,checkedAt:new Date(now).toISOString()};
})();
