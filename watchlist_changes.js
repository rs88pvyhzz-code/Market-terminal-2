/* Dated evidence, not an inference from a price move or an empty news feed. */
function watchChangesData(company,articles=[],now=Date.now()){
 const intel=company?.intelligence||{},sources=new Map((intel.sources||[]).filter(s=>/^https:\/\//.test(s.url||'')&&Number.isFinite(Date.parse(s.published))&&Date.parse(s.published)<=now).map(s=>[s.id,s]));
 const groups={Results:[],Guidance:[],Dividends:[],Announcements:[]};
 const add=(group,text,source,note)=>{if(!source||!text)return;groups[group].push({text,date:source.published,url:source.url,note});};
 const latest=[...sources.values()].filter(s=>s.kind==='results').sort((a,b)=>String(b.published).localeCompare(String(a.published)))[0];
 if(latest){
  const facts=(intel.reportedResults||[]).filter(r=>r.sourceId===latest.id).slice(0,3);
  add('Results',facts.map(r=>r.metric+': '+companyAmount(r.value,r.currency)).join(' · ')||'Results document available',latest,'Latest reported results · period '+(latest.period||'see source')+'; not a claim of a new release today.');
 }
 for(const g of intel.guidance||[]){
  if(!g.previous||!sources.has(g.previous.sourceId)||!g.comparison||g.previous.amountText===g.amountText||g.horizon!==g.previous.horizon||g.basis!==g.previous.basis)continue;
  const category=/dividend|payout/i.test(g.metric||'')?'Dividends':'Guidance';
  add(category,g.metric+': '+g.previous.amountText+' → '+g.amountText,sources.get(g.sourceId),'Management expectation · '+g.comparison+' · '+(g.horizon||'horizon unspecified'));
 }
 for(const items of Object.values(intel.topics||{}))for(const item of items||[]){
  if(/dividend|distribution per share/i.test(item.excerpt||''))add('Dividends',item.excerpt,sources.get(item.sourceId),'Issuer statement; payment terms and dates require the linked document.');
 }
 for(const article of articles){
  if(!/^https:\/\//.test(article.url||'')||!newsDateMatches(article,now))continue;
  const title=article.title||'';
  if(!/results|earnings|guidance|dividend|merger|acquisition|takeover|chief executive|\bCEO\b|profit warning|capital rais|rights issue|disposal|regulator|litigation/i.test(title))continue;
  if(/transaction in own shares|executes buyback/i.test(title))continue;
  add('Announcements',title,article,'Publisher report · '+(article.source||'Source')+'; headline is not issuer confirmation.');
 }
 for(const key of Object.keys(groups)){
  const seen=new Set();groups[key]=groups[key].sort((a,b)=>String(b.date).localeCompare(String(a.date))).filter(x=>{const id=x.text+'|'+x.url;if(seen.has(id))return false;seen.add(id);return true;}).slice(0,2);
 }
 return groups;
}
function renderWatchChanges(w){
 const parent=document.getElementById('personal-watchlist-panel');if(!parent)return;
 let host=document.getElementById('watchlist-changes');
 if(!host){host=el('section','watchlist-changes');host.id='watchlist-changes';const anchor=parent.querySelector('.watchlist-selected-header');if(anchor)anchor.after(host);else parent.prepend(host);}
 host.replaceChildren(el('h3','','WHAT CHANGED? · '+w.name));
 host.append(el('p','mini','Latest available issuer evidence; publisher announcements follow the selected news date. Missing evidence does not mean nothing changed.'));
 const c=watchProfile(w.symbol),stored=(D.company_news||[]).find(x=>x.symbol===w.symbol);
 const articles=watchNewsMap.get(w.symbol)?.articles||stored?.articles||[];
 const groups=watchChangesData(c,articles);
 for(const [name,rows] of Object.entries(groups)){
  const group=el('div','watch-change-group');group.append(el('strong','',name));
  if(!rows.length)group.append(el('p','mini',name==='Announcements'?'No matching material report in the selected news period.':'No sourced '+name.toLowerCase()+' evidence or comparable change available.'));
  for(const row of rows){const item=el('div','watch-change-row');item.append(el('div','',row.text),el('small','mini',row.note+' · '+row.date));const a=el('a','','Source');a.href=row.url;a.target='_blank';a.rel='noopener noreferrer';item.append(a);group.append(item);}
  host.append(group);
 }
}
const previousWatchChangesNews=watchlistNews;
watchlistNews=function(w,q){previousWatchChangesNews(w,q);renderWatchChanges(w);};
