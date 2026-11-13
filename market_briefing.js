/* Snapshot intelligence uses existing market observations; never invokes email alerts. */
const intelligenceCategories={market_moving:'Market Moving',rates:'Central Banks & Rates',economic:'Economic Releases',corporate:'Corporate',watchlist:'My Watchlist',policy:'Regulation & Policy'};
let intelligenceCategory='market_moving',intelligenceRegion='All';
// A price move found in market data has no article of its own. Offer a dated news
// search for the company instead of an unlinked headline; it is labelled as a search,
// not presented as the cause of the move.
function intelligenceTitle(item){
 if(item.url)return intelligenceLink(item);
 const wrap=el('span','r23-title');wrap.append(el('strong','',item.title));
 const name=String(item.title||'').split(':')[0].trim();
 if(name&&/[%]|bp\b/.test(String(item.title))){
  const a=el('a','r23-news-search','Find news →');a.target='_blank';a.rel='noopener noreferrer';
  a.href='https://news.google.com/search?'+new URLSearchParams({q:'"'+name+'" when:3d',hl:'en-GB',gl:'GB',ceid:'GB:en'}).toString();
  a.title='Google News search for '+name+' in the last 3 days; not a sourced cause of the move';
  wrap.append(' ',a);
 }
 return wrap;
}
function intelligenceLink(item){const a=el('a','',item.title);a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function intelligenceArchived(item){const date=Date.parse(String(item.published||'').replace(' UTC','Z').replace(' ','T'));return !!item.archived||!Number.isFinite(date)||Date.now()-date>(D.marketBriefing?.thresholds?.maxNewsAgeHours||48)*3600000||date>Date.now()+300000;}
function intelligenceRelatedMoves(item){
 const text=String(item.title).toLowerCase(),seen=new Set(),rows=[];
 const quotes=[...(D.watchlist_quotes||[]),...(D.companies||[]).map(c=>({symbol:c.symbol,name:c.name,changePct:c.changePct,asOf:c.priceAsOf,source:'Yahoo Finance'}))];
 for(const q of quotes){const name=String(q.name||'').replace(/\b(plc|inc|corporation|corp|limited|ltd|holdings|ag|se)\b.*$/i,'').trim().toLowerCase();const when=Date.parse(String(q.asOf||'').replace(' UTC','Z').replace(' ','T'));if(name.length<3||seen.has(q.symbol)||!Number.isFinite(q.changePct)||!Number.isFinite(when)||Math.abs(Date.now()-when)>4*86400000)continue;
  const safe=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');if(!new RegExp('\\b'+safe+'\\b','i').test(text))continue;seen.add(q.symbol);rows.push('Observed separately: '+q.name+' '+(q.changePct>=0?'+':'')+q.changePct.toFixed(2)+'% · '+q.asOf+' · '+(q.source||'Yahoo Finance'));if(rows.length===2)break;
 }return rows;
}
function intelligenceCard(item){const card=el('article','news-item');card.dataset.eventId=item.id||'';card.append(intelligenceLink(item));card.append(el('div','meta',(item.official?'Official · ':'Publisher headline · ')+(item.source||'Unknown source')+' · '+item.published+(intelligenceArchived(item)?' · ARCHIVED':'')));const details=document.createElement('details');details.append(el('summary','','Sources & context'));details.append(el('div','mini','Retrieved '+(item.retrievedAt||'date not recorded')+' · '+(item.regions||[]).join(', ')));for(const move of intelligenceRelatedMoves(item))details.append(el('div','mini',move));details.append(el('div','mini','Ranking: '+(item.rankReasons?.join(', ')||'General market headline')+'. Headline evidence only; no causal market attribution.'));for(const other of item.coverage||[]){details.append(intelligenceLink(other),el('div','mini',(other.source||'Publisher')+' · '+other.published+' · retrieved '+(other.retrievedAt||'date not recorded')+(intelligenceArchived(other)?' · ARCHIVED':'')));}card.append(details);return card;}
function renderIntelligenceNews(){
 const host=$('news-list'),pills=$('news-pills');if(!host||!pills)return;host.replaceChildren();pills.replaceChildren();
 Object.entries(intelligenceCategories).forEach(([key,label])=>{const b=el('button','btn'+(key===intelligenceCategory?' active':''),label);b.onclick=()=>{intelligenceCategory=key;renderIntelligenceNews();};pills.append(b);});
 const regions=el('div','r23-regions');for(const region of ['All','UK','US','Europe','Global']){const b=el('button','btn'+(region===intelligenceRegion?' active':''),region==='All'?'All regions':region);b.onclick=()=>{intelligenceRegion=region;renderIntelligenceNews();};regions.append(b);}pills.append(regions);
 const leadingNewsIds=new Set((D.marketBriefing?.leadingItems||[]).map(x=>x.newsId).filter(Boolean));
 const all=(D.news||[]).filter(x=>!leadingNewsIds.has(x.id)&&(x.categories||[]).includes(intelligenceCategory)&&(intelligenceRegion==='All'||(x.regions||[]).includes(intelligenceRegion)));
 const current=all.filter(x=>!intelligenceArchived(x)&&(typeof newsDateMatches!=='function'||newsDateMatches(x))),archived=[];current.slice(0,7).forEach(x=>host.append(intelligenceCard(x)));
 if(!current.length)host.append(el('div','empty',intelligenceCategory==='market_moving'?'No additional story meets the strict Market Moving evidence criteria. Browse subject categories for general coverage.':'No additional current headlines in this selection. Leading briefing items and archived coverage are separate.'));
 if(archived.length){const more=document.createElement('details');more.append(el('summary','',`Archived coverage (${archived.length}) · not current`));archived.slice(0,15).forEach(x=>more.append(intelligenceCard(x)));host.append(more);}
 const successful=(D.newsDiagnostics||[]).filter(x=>x.retrievedAt&&!x.archived).map(x=>x.retrievedAt).sort().pop();$('news-stamp').textContent='Scheduled snapshot '+D.generatedAt+' · latest recorded feed retrieval '+(successful||'see article dates');
 const title=$('news').querySelector('h2');if(title)title.textContent='NEWS BY SUBJECT';
}
function intelligencePanel(id,title,parent){let panel=$(id);if(!panel){panel=el('section','panel r23-panel');panel.id=id;panel.append(el('h2','',title));const body=el('div','r23-body');panel.append(body);parent.append(panel);}panel.lastElementChild.replaceChildren();return panel.lastElementChild;}
function intelligenceConditions(host){
 const rows=[['UK 10Y',D.uk_rates,'gilt10y'],['US 10Y',D.us_rates,'DGS10'],['Euro-area 10Y',D.eu_rates,'eur10y']];
 for(const [label,series,key] of rows){const valid=(series||[]).filter(x=>Number.isFinite(x[key]));const last=valid.at(-1),prev=valid.at(-2);if(last)host.append(el('div','r23-observation',label+' '+last[key].toFixed(2)+'%'+(prev?' · '+((last[key]-prev[key])*100).toFixed(0)+' bp since '+prev.date:'')+' · '+last.date));}
 const uk=latestField(D.uk_rates,'gilt10y'),us=latestField(D.us_rates,'DGS10'),us2=latestField(D.us_rates,'DGS2');if(us&&us2&&us.date===us2.date)host.append(el('div','r23-observation','US 10Y − 2Y curve '+((us.DGS10-us2.DGS2)*100).toFixed(0)+' bp · '+us.date));
 const equity=qMap.get('^GSPC');if(equity)host.append(el('div','r23-observation','S&P 500 '+fmt(equity.changePct,2)+'% · '+equity.asOf+'; compare dated sovereign observations below.'));
 const vix=qMap.get('^VIX');if(vix)host.append(el('div','r23-observation','VIX '+fmt(vix.price,2)+' · '+(vix.asOf||'date unavailable')));
 for(const b of (D.marketAnalytics?.breadth||[]).slice(0,2))host.append(el('div','r23-observation',b.name+' breadth: '+b.advancers+' advancing / '+b.decliners+' declining · '+b.quoted+'/'+b.members+' quoted · '+b.date));
 for(const c of (D.credit_spreads||[]).filter(x=>['US_IG','US_HY'].includes(x.key)))host.append(el('div','r23-observation',c.name+' OAS '+fmt(c.latestBp,0)+' bp · 1M '+fmt(c.change30Bp,0)+' bp · '+c.date));
 host.append(el('div','mini','Concentration: current free snapshots do not provide verified point-in-time index weights. No concentration rating inferred.'));
 host.append(el('div','mini','Observed comparisons, not causal explanations. Breadth and sector detail are on this tab; credit spreads and full yield curves are in Bonds & Rates.'));
 const b=el('button','btn','Open market analytics');b.onclick=()=>activateWorkspace('analytics');host.append(b);
}
function renderMarketBriefing(){
 const parent=$('view-overview');if(!parent)return;const briefing=D.marketBriefing||{};
 let body=intelligencePanel('r23-alerts','DAILY MARKET BRIEFING',parent);$('r23-alerts').firstElementChild.textContent='DAILY MARKET BRIEFING';
 const buildAge=Date.now()-Date.parse(String(D.generatedAt).replace(' UTC','Z').replace(' ','T')),recent=buildAge<=(briefing.thresholds?.criticalMaxAgeDays||5)*86400000;
 const leading=recent?(briefing.leadingItems||[]):[],leadingAlertIds=new Set(leading.map(x=>x.alertId).filter(Boolean));
 // One tidy list: title, then date · source. Duplicates (same subject) and anything past seven are dropped.
 const items=[...leading.map(x=>({item:x,date:x.published,source:x.source})),
   ...(recent?(briefing.alerts||[]).filter(a=>!leadingAlertIds.has(a.id)):[]).map(a=>({item:a,date:a.date,source:a.source}))];
 const seen=new Set(),subject=t=>String(t||'').toLowerCase().split(':')[0].replace(/[^a-z0-9]+/g,' ').trim();
 const words=t=>new Set(String(t||'').toLowerCase().replace(/[^a-z0-9£$.]+/g,' ').split(' ').filter(w=>w.length>3));
 const kept=[];
 for(const x of items){
  const key=subject(x.item.title);if(seen.has(key))continue;
  const w=words(x.item.title);if(kept.some(k=>{const o=words(k.item.title);let n=0;for(const v of w)if(o.has(v))n++;return n>=3&&n>=Math.min(w.size,o.size)*.5;}))continue;
  seen.add(key);kept.push(x);if(kept.length>=7)break;
 }
 for(const x of kept){const row=el('div','r23-observation');row.dataset.briefingId=x.item.id||'';if(x.item.alertId||x.item.id)row.dataset.alertId=x.item.alertId||x.item.id;
  row.append(intelligenceTitle(x.item),el('div','mini',[String(x.date||'').replace(' UTC',''),x.source].filter(Boolean).join(' · ')));body.append(row);}
 if(!recent)body.append(el('div','mini','Market snapshot is stale.'));
 else if(!kept.length)body.append(el('div','mini','Nothing material today.'));
 body=intelligencePanel('r23-moves','TODAY’S MAJOR OBSERVED MOVEMENTS',parent);for(const q of briefing.movements||[])body.append(el('div','r23-observation',(q.name||q.symbol)+' '+(q.changePct>=0?'+':'')+q.changePct.toFixed(2)+'% · '+q.asOf));if(!(briefing.movements||[]).length)body.append(el('div','mini','No sufficiently recent comparable quote timestamps.'));
 body=intelligencePanel('r23-calendar','ECONOMIC ANNOUNCEMENTS · TODAY & TOMORROW',parent);const today=D.generatedAt.slice(0,10),tomorrow=new Date(Date.parse(today)+86400000).toISOString().slice(0,10);const events=(D.calendar||[]).filter(x=>x.date===today||x.date===tomorrow);for(const x of events.slice(0,8)){const row=el('div','r23-observation');row.append(intelligenceLink({...x,title:x.title+' · '+x.date+' · '+x.region}),el('div','mini','Scheduled · '+x.source+' · '+(x.time||'See official source for time')));body.append(row);}if(!events.length)body.append(el('div','mini','No verified announcements retrieved for today or tomorrow. Official calendars remain in Economics.'));
 body=intelligencePanel('r23-conditions','MARKET CONDITIONS',parent);intelligenceConditions(body);
 body=intelligencePanel('r23-watch','MY WATCHLIST · MATERIAL DEVELOPMENTS',parent);for(const q of briefing.watchMovements||[])body.append(el('div','r23-observation',(q.name||q.symbol)+' '+q.changePct.toFixed(2)+'% · '+q.asOf+' · observed price move'));const leadingIds=new Set((D.news||[]).filter(x=>!intelligenceArchived(x)&&x.categories?.includes('market_moving')).slice(0,5).map(x=>x.id));const watch=(D.news||[]).filter(x=>!intelligenceArchived(x)&&x.categories?.includes('watchlist')&&!leadingIds.has(x.id));for(const x of watch.slice(0,4))body.append(intelligenceCard(x));if(!watch.length)body.append(el('div','mini','No additional current watchlist headlines beyond Market Moving. Company news and individual risk statistics remain in My Watchlist.'));
 for(const id of ['overview-board','r23-alerts','news','r23-moves','r23-calendar','r23-conditions','r23-watch']){const node=$(id);if(node)parent.append(node);}const tiles=$('headline');if(tiles){let advanced=$('r23-snapshot-detail');if(!advanced){advanced=document.createElement('details');advanced.id='r23-snapshot-detail';advanced.append(el('summary','','Detailed market snapshot'));}advanced.append(tiles);parent.append(advanced);}
 const markets=$('subview-fx-prices');if(markets){const h=intelligencePanel('r23-market-conditions','CROSS-MARKET CONDITIONS',markets);intelligenceConditions(h);markets.prepend($('r23-market-conditions'));}
 const quality=$('view-quality');if(quality){const h=intelligencePanel('r23-news-quality','NEWS SOURCE DIAGNOSTICS',quality);const d=document.createElement('details');d.append(el('summary','','Feed requests, source dates & coverage'));const pre=el('pre','',JSON.stringify(D.newsDiagnostics||[],null,2));d.append(pre);h.append(d);}
}
function renderCompanyChanges(c){
 const panel=$('company-news-list');if(!panel)return;
 const intel=c.intelligence||{},sources=new Map((intel.sources||[]).filter(s=>String(s.url).startsWith('https://')).map(s=>[s.id,s]));
 const wrap=el('div','r23-company-changes r213-company-evidence');
 const latest=[...sources.values()].filter(s=>s.kind==='results').sort((a,b)=>String(b.published).localeCompare(String(a.published)))[0];
 const changes=(intel.guidance||[]).filter(g=>g.previous&&g.comparison&&g.previous.amountText!==g.amountText&&g.horizon===g.previous.horizon&&g.basis===g.previous.basis&&sources.has(g.sourceId)).slice(0,3);
 const changeBox=el('section','r213-changes');changeBox.append(el('h4','','WHAT CHANGED'));
 for(const g of changes){
  const source=sources.get(g.sourceId),old=sources.get(g.previous.sourceId),row=el('div','r23-observation');
  row.append(el('strong','',g.metric+' · management expectation'),el('div','',g.previous.amountText+' → '+g.amountText),
    el('div','mini',g.comparison+' · horizon '+(g.horizon||'not specified')));
  const links=el('div','r213-source-links');links.append(intelligenceLink({title:'Current · '+source.published,url:source.url}));
  if(old)links.append(intelligenceLink({title:'Previous · '+old.published,url:old.url}));row.append(links);changeBox.append(row);
 }
 if(!changes.length)changeBox.append(el('p','mt-reading-note','No comparable sourced guidance change identified. This does not establish unchanged guidance.'));
 wrap.append(changeBox);
 const results=el('section','r213-results');results.append(el('h4','','LATEST REPORTED RESULTS'));
 if(latest)results.append(intelligenceLink({title:'Period '+(latest.period||'see source')+' · published '+latest.published,url:latest.url}));
 const rows=(intel.reportedResults||[]).filter(r=>sources.has(r.sourceId)&&(!latest||r.sourceId===latest.id)).slice(0,3);
 const table=el('table','r213-results-table');const body=el('tbody');const bases=[...new Set(rows.map(r=>r.basis||'See issuer document for reporting basis'))];
 for(const r of rows){
  const tr=el('tr'),label=el('th','',r.metric);label.scope='row';
  // Repeat only exceptions: differing periods/bases must never be lost in compression.
  if(!latest||r.period!==latest.period)label.append(el('small','','Period '+r.period));
  if(bases.length>1)label.append(el('small','',r.basis||'See issuer document for reporting basis'));
  tr.append(label,el('td','',companyAmount(r.value,r.currency)));body.append(tr);
 }
 if(rows.length){table.append(body);results.append(table);if(bases.length===1)results.append(el('p','mt-reading-note',bases[0]));}
 else results.append(el('p','mt-reading-note','No reported results available in this snapshot.'));
 // Guidance changes and latest-results block retired (v3.9): headlines only.
 const heading=el('h4','r213-headlines-title','COMPANY HEADLINES');panel.prepend(heading);
 const supporting=el('section','r213-supporting r213-company-evidence');supporting.append(el('h4','','SUPPORTING EVIDENCE'));
 const topics=intel.topics||{},developments=[...(topics.acquisitions||[]),...(topics.capitalAllocation||[]),...(topics.catalysts||[])].filter(x=>sources.has(x.sourceId)&&(!latest||x.sourceId===latest.id)).slice(0,2);
 for(const x of developments){const source=sources.get(x.sourceId),row=el('div','r23-observation');
  row.append(el('div','',(x.classification==='management_expectation'?'Management expectation: ':'Issuer statement: ')+x.excerpt),intelligenceLink({title:'Source · '+source.published,url:source.url}));supporting.append(row);
 }
 supporting.append(el('p','mt-reading-note','Issuer evidence and publisher headlines are separate. A matching headline is not a verified change.'));
 // Supporting issuer evidence retired from this panel (v3.9).
 // Full retrieval details remain available in Data Quality, scoped to this company.
 let audit=$('company-evidence-audit');if(!audit){audit=el('section','panel');audit.id='company-evidence-audit';$('view-quality')?.append(audit);}
 audit.replaceChildren(el('h2','','COMPANY EVIDENCE · '+c.name));
 for(const source of sources.values())audit.append(el('p','note',(source.kind||'Document')+' · '+source.published+' · retrieved '+(source.retrievedAt||'not recorded')));
 const snapshot=(D.company_news||[]).find(x=>x.symbol===c.symbol);
 for(const article of snapshot?.articles||watchNewsMap.get(c.symbol)?.articles||[])audit.append(el('p','note',article.title+' · '+article.source+' · published '+article.published+' · retrieved '+(article.retrievedAt||'not recorded')));
}
