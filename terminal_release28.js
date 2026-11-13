/* Release 2.8 — scoped terminal clarity, no ETF modification and no fabricated data.
   Uses existing sourced MT_DATA; no changes to constituent, ETF, or gilt cashflows. */
(function(){
'use strict';
const R28_MAX_NEWS=5, R28_MAX_OBSERVED_MOVES=2, R28_MAX_MARKET_MOVERS=6;
const r28Text=(x)=>String(x??'').trim();
const r28Finite=x=>typeof x==='number'&&Number.isFinite(x);
const r28Date=x=>String(x||'').slice(0,10);
const r28Url=x=>/^https:\/\//.test(String(x||''));
const r28SnapshotDate=()=>r28Date(D.generatedAt);
const r28EventKey=e=>[e.region,e.date,e.time,r28Text(e.title).toLowerCase()].join('|');
function r28MarketInstrument(item){
 const t=r28Text(item.title),q=(D.quotes||[]).find(q=>t.startsWith((q.name||q.symbol)+':')||t.startsWith(q.symbol+':'));
 return q&&['index','fx','future','volatility'].includes(q.kind)?q:null;
}
function r28NewspaperRank(item){
 const status=item.developmentStatus||item.classification||'';
 let score=item.official?110:status==='confirmed_event'?95:status==='reported_development'?72:50;
 if(item.categories?.includes('economic'))score+=20;
 if(item.categories?.includes('rates'))score+=18;
 if(item.categories?.includes('market_moving'))score+=12;
 if(item.significanceEvidence?.length)score+=12;
 if(item.retrievedAt&&r28Date(item.retrievedAt)===r28SnapshotDate())score+=5;
 return score;
}
function r28ObservedScore(q){
 if(!r28Finite(q?.changePct))return 0;
 const threshold={index:1,fx:0.8,future:2,volatility:6};
 if(!(q.kind in threshold))return 0;
 const move=Math.abs(q.changePct);
 if(move<threshold[q.kind])return 0;
 const priority={index:22,fx:18,future:15,volatility:12}[q.kind];
 return priority+Math.min(30,move/threshold[q.kind]*9);
}
function r28NewsOverview(){
 const node=document.querySelector('#r24-developments .r24-content');
 if(!node)return;
 node.replaceChildren();
 const headlineSeen=new Set(),news=[];
 // Use the same archival test as Markets News, with a date, publisher and URL.
 for(const n of D.news||[]){
  if(!n||!r24Fresh(n)||!r28Url(n.url)||!n.published||!n.source)continue;
  const id=r28Text(n.id||n.url).toLowerCase();
  if(headlineSeen.has(id))continue;
  headlineSeen.add(id);news.push(n);
 }
 news.sort((a,b)=>r28NewspaperRank(b)-r28NewspaperRank(a)||r28Text(b.published).localeCompare(r28Text(a.published)));
 const used=new Set(),items=[];
 for(const n of news){
  const key=r28Text(n.title).toLowerCase();
  if(used.has(key))continue;
  used.add(key);items.push({kind:'news',score:r28NewspaperRank(n),item:n});
  if(items.length>=R28_MAX_NEWS)break;
 }
 const movers=(D.quotes||[]).filter(q=>r28ObservedScore(q)>0&&q.asOf)
  .sort((a,b)=>r28ObservedScore(b)-r28ObservedScore(a)).slice(0,R28_MAX_OBSERVED_MOVES);
 // Max two major-market moves; don't crowd out real company/economic headlines.
 for(const q of movers){if(items.length>=R28_MAX_NEWS)break;
  if(items.some(x=>x.kind==='news'&&r28Text(x.item.title).startsWith(q.name+':')))continue;
  items.push({kind:'move',score:r28ObservedScore(q),item:q});
 }
 if(!items.length){
  node.append(el('p','note','No current verified headlines were returned in this snapshot. Open Markets → News for the full dated feed and source status.'));
  return;
 }
 const ordered=items.sort((a,b)=>b.score-a.score).slice(0,R28_MAX_NEWS);
 for(const x of ordered){
  if(x.kind==='news'){
   const n=x.item,label=n.official?'Official announcement':n.developmentStatus==='commentary_preview'?'Commentary / preview':'Verified publisher headline';
   r24Item(node,n,label);
  }else{
   const q=x.item;
   const row=el('article','r24-item');row.append(el('strong','',q.name+' · '+pc(q.changePct)),el('div','mini','Observed market move · Yahoo Finance · '+q.asOf+' · not an explanation of the cause'));node.append(row);
  }
 }
 const note=el('p','mini r28-more');
 const link=el('a','', 'Full dated news and market movements');
 link.href='#news';link.onclick=e=>{e.preventDefault();activateWorkspace('fx',{scroll:false,subview:'news'});};
 note.append(link,document.createTextNode(' · Top '+ordered.length+' selected by event significance, category and observed market move.'));node.append(note);
}
function r28UpdateMoverList(){
 const panel=$('r23-moves'),body=panel?.querySelector('.r23-body');
 if(!body)return;
 const all=(D.marketBriefing?.movements||[]).filter(q=>r28ObservedScore(q)>0&&q.asOf);
 const ranked=all.sort((a,b)=>r28ObservedScore(b)-r28ObservedScore(a)||Math.abs(b.changePct)-Math.abs(a.changePct));
 const unique=new Set(),best=ranked.filter(q=>{const key=q.symbol||q.name;if(unique.has(key))return false;unique.add(key);return true;}).slice(0,R28_MAX_MARKET_MOVERS);
 body.replaceChildren();
 for(const q of best){
  const row=el('div','r23-observation');
  row.append(el('strong','',q.name+' '+pc(q.changePct)),el('div','mini',(q.kind||'Market')+' · '+q.asOf));
  body.append(row);
 }
 panel.hidden=!best.length;
 if(best.length){
  const foot=el('p','mini r28-more','Top '+best.length+' major-market observations ranked by move versus asset-class threshold. Full constituent risers/fallers are in Equities.');
  body.append(foot);
 }
}
function r28EventCategory(e){
 const s=r28Text(e.title).toLowerCase();
 if(/construction|production|trade:|trade in|business investment|productivity|rti|real time information|time series|regional labour|regions of the uk|index of services/.test(s))return null;
 if(/monetary policy|bank rate|interest rate decision|fomc|federal reserve decision|ecb.*rate|deposit facility decision/.test(s))return 'policy';
 if(/consumer price|inflation|\bcpi\b|\bhicp\b/.test(s))return 'inflation';
 if(/gdp|gross domestic product/.test(s))return 'gdp';
 if(/labour market|labor market|unemployment|employment situation|nonfarm payroll|payrolls|average weekly earnings/.test(s))return 'labour';
 if(/retail sales/.test(s))return 'retail';
 return null;
}
function r28MajorCalendar(){
 const list=r24CalendarEvents().filter(e=>r28EventCategory(e));
 const selected=new Map();
 for(const e of list){
  const cat=r28EventCategory(e),key=[e.region,e.date,cat].join('|');
  const old=selected.get(key);
  // Prefer the headline GDP quarter and consolidated labour release.
  const rank=x=>/first quarterly estimate|advance estimate|labour market:|labor market:|employment situation/i.test(x.title||'')?3:/monthly estimate|gdp monthly|unemployment/i.test(x.title||'')?2:1;
  if(!old||rank(e)>rank(old))selected.set(key,e);
 }
 return [...selected.values()].sort((a,b)=>a.date.localeCompare(b.date)||r28Text(a.time).localeCompare(r28Text(b.time)));
}
let r28CalendarMajorOnly=true;
function r28CalendarTable(host,arr,overview){
 r24CalendarTable(host,arr,overview);
 const label=host.querySelector('.r24-calendar-table');
 if(label)label.setAttribute('aria-label',overview?'Major upcoming economic releases':'Scheduled economic releases');
 r28StickyTables(host);
}
const r28PrevOverview=r24Overview;
r24Overview=function(){
 r28PrevOverview();
 r28NewsOverview();
 r28UpdateMoverList();
 const host=document.querySelector('#r24-upcoming .r24-content');
 if(host){host.replaceChildren();r28CalendarTable(host,r28MajorCalendar().slice(0,3),true);}
 r28StickyTables($('view-overview'));
};
renderCalendar=function(){
 const host=$('calendar-items'),filters=$('calendar-filters');if(!host||!filters)return;
 host.replaceChildren();filters.replaceChildren();
 for(const [key,label] of [['ALL','All regions'],['UK','UK'],['EU','Euro area'],['US','US']]){
  const b=el('button','btn'+(key===state.calendarRegion?' active':''),label);
  b.onclick=()=>{state.calendarRegion=key;renderCalendar();};filters.append(b);
 }
 const sep=el('span','r28-calendar-separator','|');filters.append(sep);
 for(const [major,label] of [[true,'Major releases'],[false,'All verified releases']]){
  const b=el('button','btn'+(r28CalendarMajorOnly===major?' active':'')+' r28-calendar-view',label);
  b.onclick=()=>{r28CalendarMajorOnly=major;renderCalendar();};filters.append(b);
 }
 const pool=r28CalendarMajorOnly?r28MajorCalendar():r24CalendarEvents();
 const items=pool.filter(e=>state.calendarRegion==='ALL'||e.region===state.calendarRegion).slice(0,r28CalendarMajorOnly?5:70);
 r28CalendarTable(host,items,false);
};
const r28PrevRenderMacro=renderMacro;
renderMacro=function(){
 r28PrevRenderMacro();
 const rows=(D.macro||[]).filter(m=>(m.region||'US')===state.macroRegion);
 const index=new Map((D.economicPrints||[]).map(p=>[p.key,p]));
 const tiles=[...($('macro-tiles')?.children||[])];
 rows.forEach((m,i)=>{
  const tile=tiles[i];if(!tile||!tile.matches('button'))return;
  tile.querySelectorAll('.r28-economic-sub').forEach(n=>n.remove());
  const p=index.get(m.key);const text=el('div','r28-economic-sub');
  if(p?.previous!=null){
   text.textContent='Prior '+fmt(p.previous,2)+(p.unit||m.unit||'')+' · '+(p.previousPeriod||'previous period');
  }else text.textContent='Prior unavailable';
  tile.append(text);
  if(p?.forecast!=null&&p?.sourceUrl&&p?.source&&p?.recordedAt){
   const forecast=el('div','r28-economic-sub r28-consensus','Sourced pre-release forecast '+fmt(p.forecast,2)+(p.unit||m.unit||''));
   forecast.title=p.source+' · recorded '+p.recordedAt;tile.append(forecast);
  }
 });
 const repeated=$('macro-surprise');if(repeated){repeated.hidden=true;repeated.setAttribute('aria-label','Economic actual vs prior data moved to indicator cards');}
};
function r28StickyTables(root=document){
 if(!root)return;
 const candidate=root.querySelectorAll('table.watch,table.r24-table');
 for(const table of candidate){
  if(table.closest('#etf-tracker-panel')||table.closest('#ust-securities-scroll'))continue;
  if(table.closest('#gilt-ladder')||table.closest('#gilts .gilt-table-scroll'))continue;
  const count=table.tBodies?.[0]?.rows?.length||0;
  let wrapper=table.closest('.r28-table-scroll');
  if(count<9){
   if(wrapper)wrapper.classList.remove('r28-table-scroll');
   continue;
  }
  if(wrapper){wrapper.classList.add('r28-table-scroll');continue;}
  const host=table.parentElement;
  if(host?.matches('.constituents-scroll,.small-scroll,.scroll,.events-scroll,.analytic-scroll,.screener-scroll,.watchlist-table-scroll,.valuation-scroll,.gilt-table-scroll')){
   host.classList.add('r28-table-scroll');continue;
  }
  const scroll=el('div','r28-table-scroll');table.before(scroll);scroll.append(table);
 }
}
function r28GiltPairs(host,statRows,b,v,clean,manual){
 // Gross hold-to-maturity cash flows: dirty cost is paid once, all remaining
 // coupons are received, and £100 per £100 nominal is repaid at redemption.
 // Net/tax-equivalent calculations deliberately do not appear in this view.
 host.replaceChildren();
 const when=manual?r28SnapshotDate():b.asOf;
 const review=giltYieldReviewReason(b);
 const usable=!!(v&&!b.indexLinked&&!review&&r28Finite(v.dirty)&&v.dirty>0);
 const flows=usable?giltCashflows(b,when,!manual&&b.askDirty!=null):null;
 const couponPer100=flows?flows.flows.reduce((sum,f)=>sum+f.coupon,0):null;
 const nominalInput=$('gilt-nominal-input');
 const nominal=Number(nominalInput?.value);
 const validNominal=Number.isFinite(nominal)&&nominal>=100&&nominal<=100000000;
 const scale=validNominal?nominal/100:null;
 const dirty=usable?v.dirty:null;
 const grossYtm=usable&&r28Finite(v.ytm)?v.ytm:null;
 const grossProfitPer100=usable&&couponPer100!=null?100+couponPer100-dirty:null;
 const holdingReturn=grossProfitPer100!=null?grossProfitPer100/dirty*100:null;
 const gbp=x=>x==null?'—':'£'+fmt(x,2);
 const value=x=>x==null?'Unavailable':fmt(x,2)+'%';
 const group=el('div','r28-gilt-single r212-gilt-income');
 const heading=el('div','r28-gilt-caption','BUY AND HOLD TO MATURITY · '+(manual?'entered price as of '+when:'DMO offer dated '+when));
 group.append(heading);
 const yields=el('div','r28-gilt-yields');
 for(const [name,number,kind] of [
   ['Annualised gross YTM',grossYtm,'percent'],
   ['Cumulative cash return',holdingReturn,'percent'],
   ['Total profit for holding',grossProfitPer100!=null&&scale!=null?grossProfitPer100*scale:null,'money']]){
   const cell=el('div','r28-gilt-yield');
   cell.append(el('div','mini',name),el('strong','',kind==='money'?gbp(number):value(number)));
   yields.append(cell);
 }
 group.append(yields);
 const facts=el('div','r28-gilt-facts');
 const metrics=[
  ['Nominal redeemed at maturity',validNominal?gbp(nominal):'Enter a valid holding'],
  ['Initial dirty purchase cost',dirty!=null&&scale!=null?gbp(dirty*scale):'—'],
  ['All remaining coupon receipts',couponPer100!=null&&scale!=null?gbp(couponPer100*scale):'—'],
  ['Total cash received to maturity',couponPer100!=null&&scale!=null?gbp((100+couponPer100)*scale):'—'],
  ['Clean purchase price / £100',clean!=null?fmt(clean,2):'—'],
  ['Dirty purchase price / £100',dirty!=null?fmt(dirty,2):'—'],
  ['Coupon rate',fmt(b.coupon,3)+'%'],
  ['Maturity date',b.maturity],
 ];
 for(const [name,text] of metrics){
  const cell=el('div','r28-gilt-fact');cell.append(el('span','mini',name),el('strong','',text));facts.append(cell);
 }
 group.append(facts);
 const advanced=el('div','r28-gilt-advanced');
 for(const [label,metric] of statRows){
  if(['Modified duration','Running yield','DV01 per £100 nominal','Quoted bid / offer spread'].includes(label))
    advanced.append(el('span','',label+': '+metric));
 }
 group.append(advanced);
 const text=review?'Review required — gross yield and cash profit withheld until the bond cash-flow schedule is independently validated.':
  b.indexLinked?'No fixed nominal hold-to-maturity return is shown for index-linked gilts.':
  !usable?'Not enough validated purchase/cash-flow data to calculate redemption return.':
  'Gross cash figures are undiscounted and include redemption plus scheduled coupons, less initial dirty cost. Annualised YTM is the cash-flow internal rate of return. Tax, broker fees and reinvestment of coupons are excluded. DMO reference quotes are not executable broker prices.';
 group.append(el('p','note',text));
 host.append(group);
 const taxBox=$('mt-gilt-tax-panel');
 if(taxBox)taxBox.hidden=true;
}
mtRenderGiltSummary=r28GiltPairs;
function r28AnalystPanel(c){
 const host=$('research-overview');if(!host)return;
 host.querySelector('#r28-analyst-consensus')?.remove();
 const box=el('section','r28-analyst-panel');box.id='r28-analyst-consensus';
 box.append(el('h3','', 'ANALYST CONSENSUS'));
 const a=c?.analystConsensus;
 if(!a){
  box.append(el('p','note','No sourced analyst aggregation is available for this company in the saved provider snapshot. Missing ratings and price targets are not estimated.'));
  host.append(box);return;
 }
 const label={strong_buy:'Strong buy',buy:'Buy',hold:'Hold',underperform:'Underperform',sell:'Sell',strong_sell:'Strong sell'}[a.rating]||'Not available';
 const facts=el('div','r28-analyst-grid');
 const fmtValue=(x,d=2)=>r28Finite(x)?fmt(x,d):'—';
 const targetCurrency=a.quoteCurrency||'currency unverified';
 const target=v=>r28Finite(v)?fmt(v,2)+' '+targetCurrency:'—';
 for(const [key,val] of [['Provider consensus',label],['Analyst count',a.analysts!=null?String(a.analysts):'—'],
   ['Mean 12-month target',target(a.targetMean)],['Target low / high',target(a.targetLow)+' / '+target(a.targetHigh)],
   ['Median target',target(a.targetMedian)]]){
  const t=el('div','r28-analyst-kpi');t.append(el('span','mini',key),el('strong','',val));facts.append(t);
 }
 // Target upside is only valid when the source's quoted units match today's quote.
 const q=(c.priceCurrency||'').replace('GBX','GBp'),u=(a.quoteCurrency||'').replace('GBX','GBp');
 if(r28Finite(a.targetMean)&&r28Finite(c.price)&&c.price>0&&q&&q===u&&a.targetMean/c.price>=0.2&&a.targetMean/c.price<=5){
  const upside=100*(a.targetMean/c.price-1);
  const t=el('div','r28-analyst-kpi');t.append(el('span','mini','Implied price-only upside'),el('strong',upside>=0?'r28-positive':'r28-negative',(upside>=0?'+':'')+fmt(upside,1)+'%'));facts.append(t);
 }else{
  const t=el('div','r28-analyst-kpi');t.append(el('span','mini','Implied price-only upside'),el('strong','','Unavailable — quote/target units or scale not verified'));facts.append(t);
 }
 box.append(facts);
 const source=el('a','', 'Yahoo Finance analyst data');source.href='https://finance.yahoo.com/quote/'+encodeURIComponent(c.symbol)+'/analysis/';source.target='_blank';source.rel='noopener noreferrer';
 const date=r28Text(c.asOf||c.financialAsOf||'');
 box.append(el('p','mini','Provider-reported aggregation, not our rating · retrieved '+(date||'date unavailable')+' · '),source);
 box.append(el('p','note','Analyst target periods and coverage may differ. Targets are not certified or guaranteed, and historical price targets may be stale. Unavailable observations stay blank.'));
 host.append(box);
}
const r28OriginalResearchOverview=renderResearchOverview;
renderResearchOverview=function(c){r28OriginalResearchOverview(c);r28AnalystPanel(c);};
document.addEventListener('DOMContentLoaded',()=>{
 document.documentElement.classList.add('release28');
 // The original ETF panel and its styles are excluded from all selectors.
 r28StickyTables(document);
 const observed=['view-overview','view-fx','view-bonds','view-economics','view-equities'];
 for(const id of observed){
  const host=$(id);if(!host)continue;
  let queued=false;
  new MutationObserver(()=>{if(queued)return;queued=true;
   requestAnimationFrame(()=>{queued=false;r28StickyTables(host);});
  }).observe(host,{childList:true,subtree:true});
 }
});
})();