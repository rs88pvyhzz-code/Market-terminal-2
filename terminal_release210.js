/* Release 2.10: 14 sourced market indicators, concise distinct headlines,
   short analysis tables, usable research headings and UK/US bond layout parity.
   No changes to historic returns, quote ingestion or valuation calculations. */
(function(){
'use strict';
const $r=id=>document.getElementById(id);
const str=x=>String(x==null?'':x).trim();
const isReal=x=>typeof x==='number'&&Number.isFinite(x);
const r210Extra=[
 ['GBPEUR=X','GBP/EUR','fx'],
 ['US10','US 10Y yield','us10'],
 ['GC=F','Gold · USD','quote'],
 ['BTC-USD','Bitcoin · USD','quote'],
 ['^STOXX','Europe · STOXX 600','quote'],
 ['^N225','Japan · Nikkei 225','quote'],
 ['EEM','Emerging Mkts · ETF','quote']
];
const previousSnapshot=r24Snapshot;
r24Snapshot=function(){
 previousSnapshot();
 const host=$r('market-pulse');if(!host)return;
 for(const [symbol,label,kind] of r210Extra){
  const tile=el('button','r24-snapshot-item');
  tile.type='button';tile.setAttribute('aria-label','Open '+label);
  tile.onclick=()=>kind==='us10'?activateWorkspace('bonds',{scroll:false}):marketInstrument(symbol);
  const q=qMap.get(symbol);
  tile.append(el('div','lab',label));
  if(kind==='us10'){
   const rows=(D.us_rates||[]).filter(x=>isReal(x.DGS10));
   const cur=rows.at(-1),prior=rows.at(-2);
   tile.append(el('strong','',cur?fmt(cur.DGS10,2)+'%':'Unavailable'),
     el('div','mini',cur&&prior?fmt((cur.DGS10-prior.DGS10)*100,1)+' bp since '+prior.date:'Change unavailable'),
     el('div','mini',cur?.date||'Date unavailable'));
  }else{
   tile.append(el('strong','',q?fmt(q.price,kind==='fx'?4:q.price<100?2:1):'Unavailable'),
     el('div',q?.changePct>0?'pos':q?.changePct<0?'neg':'mini',q?pc(q.changePct):'Change unavailable'),
     el('div','mini',q?.asOf||'Date unavailable'));
  }
  host.append(tile);
 }
 host.dataset.count=String(host.children.length);
 const existing=$r('r210-snapshot-note');
 if(!existing){
  const note=el('p','mini r210-market-note','14 dated indicators · quoted units shown in labels · EEM is an ETF proxy for emerging equities, not an official emerging-markets index · US 10Y is the official Treasury yield series.');
  note.id='r210-snapshot-note';host.after(note);
 }
};
function newsTokens(item){
 let title=str(item.title).toLowerCase()
  .replace(/\s*[-–—]\s*(yahoo finance.*|reuters.*|investing\.com.*|financial times.*|bbc.*)$/,'');
 title=title.replace(/\b(reel|fall|fell|slide|slump|decline|drop|dip|sink|tumble|plunge)\b/g,'fall')
  .replace(/\b(jolt|stoke|spark|revive|raise|heighten|intensify)\b/g,'raise')
  .replace(/\b(usa|u\.s\.|us|american)\b/g,'us')
  .replace(/\b(share|stock|equity|equities)\b/g,'stocks');
 return [...new Set(title.replace(/[^a-z0-9]+/g,' ').split(' ').filter(w=>w.length>2&&!['the','and','with','for','over','after','amid','are','from','into','its','says','said','could','would','more','than','this','that','these','shares'].includes(w)))];
}
function sameNews(a,b){
 const ta=new Set(newsTokens(a)),tb=new Set(newsTokens(b)),overlap=[...ta].filter(t=>tb.has(t)).length;
 return !!(a.id&&a.id===b.id)||!!(a.url&&a.url===b.url)||
 (ta.size>0&&tb.size>0&&overlap>=4&&overlap/Math.min(ta.size,tb.size)>=.62);
}
function eventWeight(x){
 const title=str(x.title).toLowerCase();
 const text=[title,...(x.categories||[])].join(' ');
 let n=0;
 if(x.developmentStatus==='confirmed_event')n+=46;
 if(x.developmentStatus==='reported_development')n+=30;
 if(x.official)n+=24;
 if(/interest rates|policy rate|central bank decision|inflation|cpi|gdp|payrolls|unemployment|federal reserve|bank of england/.test(text))n+=35;
 if(/bond|yield|market|global|stocks|oil|energy|geopolit|recession/.test(text))n+=23;
 if(/results|merger|acquisition|takeover|earnings|guidance/.test(text))n+=18;
 if(x.significanceEvidence?.length)n+=15;
 if(/speech|lecture|communication|digital euro|working paper|research note|science and practice|forecast chart|market outlook/.test(title))n-=65;
 if(/quote|price history|seasonal returns chart|shares surge.*gf score/.test(title))n-=55;
 if(x.developmentStatus==='commentary_preview')n-=25;
 const age=(Date.parse(D.generatedAt?.replace(' UTC','Z').replace(' ','T')||'')-Date.parse(x.published?.replace(' UTC','Z').replace(' ','T')||''))/3600000;
 if(Number.isFinite(age))n+=Math.max(0,16-age/6);
 return n;
}
function validNews(x){
 return x&&x.title&&x.source&&x.published&&/^https:\/\//.test(str(x.url))&&r24Fresh(x)&&
 !/stock price, news, quote|quote & history|seasonal returns chart|historical data|price forecast:|stock price & news/i.test(x.title);
}
function sortedNews(){
 return (D.news||[]).filter(validNews).slice().sort((a,b)=>eventWeight(b)-eventWeight(a)||str(b.published).localeCompare(str(a.published)));
}
function distinctNews(rows,avoid=[]){
 const unique=[];
 for(const row of rows){
  if(avoid.some(x=>sameNews(row,x))||unique.some(x=>sameNews(row,x)))continue;
  unique.push(row);
 }
 return unique;
}
let overviewHeadlines=[];
r28NewsOverview=function(){
 const host=$r('r24-developments')?.querySelector('.r24-content');if(!host)return;
 host.replaceChildren();overviewHeadlines=distinctNews(sortedNews()).filter(x=>eventWeight(x)>=23).slice(0,5);
 if(!overviewHeadlines.length){
  host.append(el('p','note','No major sourced market development in this snapshot. Full dated market news remains available in Markets.'));
  return;
 }
 for(const x of overviewHeadlines){
  r24Item(host,x,x.official?'Official source':x.developmentStatus==='confirmed_event'?'Confirmed development':'Publisher report');
 }
 const link=el('a','','Additional distinct market news in Markets');
 link.href='#news';link.onclick=e=>{e.preventDefault();activateWorkspace('fx',{subview:'news',scroll:false});};
 const foot=el('p','mini r28-more');foot.append(link,document.createTextNode(' · Top '+overviewHeadlines.length+' sourced material developments, de-duplicated by event.'));host.append(foot);
};
let newsLimit=6;
renderIntelligenceNews=function(){
 const host=$r('news-list'),pills=$r('news-pills');if(!host||!pills)return;
 host.replaceChildren();pills.replaceChildren();
 for(const [key,label] of [['all','All subjects'],...Object.entries(intelligenceCategories)]){
  const b=el('button','btn'+(key===intelligenceCategory?' active':''),label);
  b.type='button';b.onclick=()=>{intelligenceCategory=key;newsLimit=6;renderIntelligenceNews();};pills.append(b);
 }
 const regions=el('div','r23-regions');
 for(const region of ['All','UK','US','Europe','Global']){
  const b=el('button','btn'+(region===intelligenceRegion?' active':''),region==='All'?'All regions':region);
  b.type='button';b.onclick=()=>{intelligenceRegion=region;newsLimit=6;renderIntelligenceNews();};regions.append(b);
 }
 pills.append(regions);
 const relevant=sortedNews().filter(x=>
   (intelligenceCategory==='all'||x.categories?.includes(intelligenceCategory))&&
   (intelligenceRegion==='All'||x.regions?.includes(intelligenceRegion)));
 const distinct=distinctNews(relevant,overviewHeadlines);
 for(const x of distinct.slice(0,newsLimit)){
  const article=el('article','r29-news');
  article.dataset.eventId=str(x.id||x.url);
  const title=el('a','r29-news-title',x.title);
  title.href=x.url;title.target='_blank';title.rel='noopener noreferrer';
  article.append(title,el('div','r29-news-meta',x.source+' · '+x.published+(x.official?' · official':'')));
  host.append(article);
 }
 if(!distinct.length)host.append(el('p','note','No additional distinct publisher stories for the selected filters. The most important sourced events appear in Overview.'));
 for(const old of host.parentElement.querySelectorAll('.r29-news-footer'))old.remove();
 const foot=el('div','r29-news-footer','Showing '+Math.min(newsLimit,distinct.length)+' of '+distinct.length+' additional distinct headlines');
 if(distinct.length>newsLimit){
  const more=el('button','btn','Show 6 more');more.type='button';more.onclick=()=>{newsLimit+=6;renderIntelligenceNews();};foot.append(more);
 }
 host.after(foot);
 const stamp=$r('news-stamp');if(stamp)stamp.textContent='Publisher dates retained · priority stories are in Overview';
 const heading=$r('news')?.querySelector('h2');if(heading)heading.textContent='ADDITIONAL MARKET NEWS';
};
function reframeGilts(){
 const panel=$r('gilts'),ladder=$r('gilt-ladder');
 if(!panel||!ladder)return;
 // As with US Treasuries: search / short table / selected security / chart.
 // The ladder is a separate optional analysis after the price history.
 panel.append(ladder);
 const selected=$r('gilt-selected');
 if(selected)selected.textContent=selected.textContent.replace(/^SELECT A GILT$/,'SELECT A UK GILT');
 const table=$r('gilt-rows')?.closest('.gilt-table-scroll');
 if(table){table.setAttribute('role','region');table.setAttribute('aria-label','UK gilt securities');table.tabIndex=0;}
 const us=$r('ust-securities-scroll');if(us)us.setAttribute('aria-label','US Treasury securities');
}
function conciseCompanyEvents(){
 const root=$r('company-events-panel');if(!root)return;
 const table=root.querySelector('table');
 if(table){
  const parent=table.closest('.constituents-scroll')||table.parentElement;
  parent.classList.add('r210-company-events-scroll');
  parent.setAttribute('role','region');
  parent.setAttribute('aria-label','Company earnings and corporate events');
  parent.tabIndex=0;
 }
}
function simplifyManagement(host){
 // Keep reported guidance and the primary sources, but limit repeated excerpts
 // in the reading path. All original passages remain accessible via Show all.
 for(const sec of host.querySelectorAll('details')){
  const heading=str(sec.querySelector(':scope > summary')?.textContent).toLowerCase();
  if(heading.includes('recent company news')){sec.remove();continue;} // Company News is already on the Overview research tab.
  if(!/management expectations|potential 1–3 year|downside risks|indicators to monitor/.test(heading))continue;
  const entries=[...sec.children].filter(x=>x.matches('article.research-evidence')||
   (heading.includes('indicators')&&x.matches('p.note')));
  if(entries.length<=2)continue;
  let expanded=false;
  for(const node of entries.slice(2))node.hidden=true;
  const button=el('button','btn r210-more-evidence','Show all '+entries.length+' source-backed items');
  button.type='button';
  button.onclick=()=>{expanded=!expanded;
    for(const node of entries.slice(2))node.hidden=!expanded;
    button.textContent=expanded?'Show fewer':'Show all '+entries.length+' source-backed items';
  };
  sec.append(button);
 }
 const notice=el('p','note r210-management-note','Material guidance and the first two source excerpts are shown by default. Full issuer evidence is retained via Show all. Duplicate media headlines are in Company News, not repeated here.');
 host.prepend(notice);
}
const previousOutlook=researchR2Outlook;
researchR2Outlook=function(c,host){previousOutlook(c,host);simplifyManagement(host);};
const previousSectionLinks=r25SectionLinks;
r25SectionLinks=function(){
 previousSectionLinks();
 const host=$r('research-view-4');if(!host)return;
 const nav=host.querySelector(':scope > .r25-section-links');if(!nav)return;
 const headings=[...host.querySelectorAll('h3.r24-support-heading')].filter(h=>h.getClientRects().length);
 if(!headings.length)return;
 nav.replaceChildren();nav.hidden=false;
 nav.setAttribute('aria-label','Company research sections');
 headings.forEach((heading,i)=>{
  const label=heading.textContent.replace(/ \u00b7 .*$/,'').trim();
  const button=el('button','btn r210-research-jump',label.length>38?label.slice(0,35)+'…':label);
  button.type='button';button.title=label;
  button.onclick=()=>{
   const current=[...host.querySelectorAll('h3.r24-support-heading')].find(h=>h.textContent.trim()===heading.textContent.trim());
   if(!current)return;
   const delta=current.getBoundingClientRect().top;
   const top=Math.max(0,window.scrollY+delta-(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--r24-nav-height'))||90)-65);
   window.scrollTo({top,behavior:'instant'});
   nav.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
   button.classList.add('active');
   current.classList.add('r210-focused-heading');
   setTimeout(()=>current.classList.remove('r210-focused-heading'),1800);
  };
  nav.append(button);
 });
};
function markRelease(){
 document.documentElement.classList.add('release210');
 reframeGilts();conciseCompanyEvents();
 const host=$r('market-pulse');if(host&&host.children.length!==14)r24Snapshot();
}
document.addEventListener('DOMContentLoaded',markRelease);
})();