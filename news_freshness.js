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
let removed=0;
for(const key of ['news','company_news','watchlist_news']){
  const v=D[key];
  if(Array.isArray(v))removed+=pruneArray(v);
  else if(v&&typeof v==='object')for(const k of Object.keys(v))removed+=pruneArray(v[k]);
}
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
