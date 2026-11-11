/* Release 2.9: concise news and company research hierarchy.
 * Presentation only. ETF markup, stylesheet, selection, pricing and maths unchanged.
 * Reuses the existing sourced MT_DATA; no external feed or invented figures.
 */
(function(){
'use strict';
const MAX_NEWS=8, MAX_COMPANY_NEWS=3;
let visibleNews=MAX_NEWS;
const val=x=>typeof x==='string'?x.trim():'';
const validUrl=x=>/^https:\/\//.test(val(x));
const lc=x=>val(x).toLowerCase();
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const $id=id=>document.getElementById(id);
function itemRank(x){
 let n=x.official?85:0;
 const cats=x.categories||[];
 if(cats.includes('economic'))n+=32;
 if(cats.includes('rates'))n+=31;
 if(cats.includes('market_moving'))n+=23;
 if(cats.includes('policy'))n+=18;
 if(x.developmentStatus==='confirmed_event')n+=27;
 if(x.developmentStatus==='reported_development')n+=16;
 if(x.significanceEvidence?.length)n+=10;
 if(x.developmentStatus==='commentary_preview')n-=18;
 const last=Date.parse(x.published||'');
 if(Number.isFinite(last))n+=Math.max(0,16-(Date.now()-last)/3600000/6);
 return n;
}
function disposableHeadline(x){
 const title=lc(x.title),url=lc(x.url);
 return /stock price, news, quote|news, quote & history|seasonal returns chart|historical data|price forecast:|stock price & news|ftse 100 ucits etf.*chart/.test(title)||
 /\/quote\/[^/]+\/?$/.test(url)||/\/historical\/?$/.test(url);
}
function newsEventKey(x){
 const raw=lc(x.title).replace(/\s*[-–|]\s*(reuters|yahoo finance.*|bbc.*|financial times|marketwatch).*$/,'');
 return raw.replace(/\b(shareholders|shares|stock|says|said|reportedly|amid|and|the|a|of|to|in|for|on|by|at|from)\b/g,' ')
   .replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');
}
function clusteredNews(rows){
 const chosen=[],keys=[];
 for(const x of rows){
  const tokens=new Set(newsEventKey(x).split(' ').filter(k=>k.length>2));
  const key=newsEventKey(x);
  if(!key||keys.some(y=>{
   if(y.key===key)return true;
   const common=[...tokens].filter(t=>y.tokens.has(t)).length;
   return common>=4&&common/Math.max(tokens.size,y.tokens.size)>=.72;
  }))continue;
  chosen.push(x);keys.push({key,tokens});
 }
 return chosen;
}
renderIntelligenceNews=function(){
 const host=$id('news-list'),pills=$id('news-pills');if(!host||!pills)return;
 host.replaceChildren();pills.replaceChildren();
 for(const [key,label] of [['all','All subjects'],...Object.entries(intelligenceCategories)]){
  const b=el('button','btn'+(key===intelligenceCategory?' active':''),label);
  b.type='button';b.onclick=()=>{intelligenceCategory=key;visibleNews=MAX_NEWS;renderIntelligenceNews();};pills.append(b);
 }
 const regions=el('div','r23-regions');
 for(const region of ['All','UK','US','Europe','Global']){
  const b=el('button','btn'+(region===intelligenceRegion?' active':''),region==='All'?'All regions':region);
  b.type='button';b.onclick=()=>{intelligenceRegion=region;visibleNews=MAX_NEWS;renderIntelligenceNews();};regions.append(b);
 }
 pills.append(regions);
 const relevant=(D.news||[]).filter(x=>
  x&&r24Fresh(x)&&validUrl(x.url)&&val(x.title)&&val(x.source)&&val(x.published)&&
  !disposableHeadline(x)&&
  (intelligenceCategory==='all'||x.categories?.includes(intelligenceCategory))&&
  (intelligenceRegion==='All'||x.regions?.includes(intelligenceRegion))
 ).sort((a,b)=>itemRank(b)-itemRank(a)||lc(b.published).localeCompare(lc(a.published)));
 const distinct=clusteredNews(relevant);
 for(const x of distinct.slice(0,visibleNews)){
  const a=el('article','r29-news');a.dataset.eventId=val(x.id||x.url);
  const heading=el('a','r29-news-title',val(x.title));heading.href=x.url;heading.target='_blank';heading.rel='noopener noreferrer';
  a.append(heading,el('div','r29-news-meta',val(x.source)+' · '+val(x.published)+
   (x.official?' · official':'')+(x.developmentStatus==='commentary_preview'?' · commentary':'') ));
  host.append(a);
 }
 if(!distinct.length)host.append(el('p','note','No current verified publisher developments for these filters. The full source coverage and retrieval diagnostics are in Data Quality.'));
 const count=el('div','r29-news-footer','Showing '+Math.min(visibleNews,distinct.length)+' of '+distinct.length+' distinct current headlines');
 if(distinct.length>visibleNews){
  const button=el('button','btn','Show next '+Math.min(MAX_NEWS,distinct.length-visibleNews));
  button.type='button';button.onclick=()=>{visibleNews+=MAX_NEWS;renderIntelligenceNews();};count.append(button);
 }
 for(const old of host.parentElement.querySelectorAll('.r29-news-footer'))old.remove();
 host.after(count);
 const stamp=$id('news-stamp');if(stamp)stamp.textContent='Snapshot '+(D.generatedAt||'unavailable')+' · published date shown for each story';
 const title=$id('news')?.querySelector('h2');if(title)title.textContent='MARKET NEWS · RANKED HEADLINES';
};
const previousInsight=renderCompanyInsight;
renderCompanyInsight=function(c){
 previousInsight(c);
 const host=$id('company-news-list');
 if(host){const list=host.querySelectorAll('article');for(let i=MAX_COMPANY_NEWS;i<list.length;i++)list[i].remove();}
};
const previousResearchOverview=renderResearchOverview;
renderResearchOverview=function(c){
 previousResearchOverview(c);
 const grid=$id('research-overview')?.querySelector('.research-dashboard');
 if(grid){
  const box=el('div','research-card r29-market-cap');
  box.append(el('span','mini','MARKET CAPITALISATION'),
    el('strong','',finite(c.marketCap)&&c.marketCap>0?companyAmount(c.marketCap,c.marketCapCurrency||''):'Unavailable'),
    el('small','note','Provider observation · '+(c.financialAsOf||'date unavailable')));
  grid.insertBefore(box,grid.children[1]||null);
 }
};
function coverage(c){
 const host=$id('research-view-0');if(!host)return;
 let box=$id('r29-coverage');if(!box){box=el('section','r29-coverage');box.id='r29-coverage';host.append(box);}
 box.replaceChildren(el('h3','','DATA COVERAGE & SOURCE DATES'));
 const grid=el('div','r29-coverage-grid');
 const annual=researchData(c)?.annual||[];
 const history=companyHistory.get(c.symbol)||[];
 const vals=[
  ['Share price',c.priceAsOf||'Unavailable'],
  ['Financial accounts',annual[0]?.fiscalEnd||c.fiscalEnd||'Unavailable'],
  ['Annual statements',annual.length?annual.length+' dated period'+(annual.length===1?'':'s'):'Unavailable'],
  ['Chart observations',history.length?history.length+' dated closes':'Not saved'],
  ['Fundamental source',c.fundamentalSource||'Unavailable'],
  ['Analyst coverage',c.analystConsensus?.analysts!=null?c.analystConsensus.analysts+' analysts':'Not available']
 ];
 for(const [label,value] of vals){const tile=el('div','r29-coverage-cell');tile.append(el('div','mini',label),el('strong','',String(value)));grid.append(tile);}
 box.append(grid,el('p','note','Coverage varies by company. Dated reports and share prices are separate feeds; missing observations are not assumed to be zero.'));
}
researchArrangeOverview=function(){
 const view=$id('research-view-0');if(!view)return;
 const c=ensureCompany(state.companySymbol);if(c)coverage(c);
 for(const id of ['research-overview','r29-coverage','company-price-block','company-benchmark-block','company-risk-panel','research-executive','company-news-panel','company-advanced','company-coverage']){
  const node=$id(id);if(node)view.append(node);
 }
};
let detailedSymbol=null;
const previousValuation=renderResearchValuation;
function ratioTile(grid,title,value,note){
 const t=el('div','r29-valuation-metric');t.append(el('span','mini',title),el('strong','',value),el('small','note',note));grid.append(t);
}
renderResearchValuation=function(c){
 const host=$id('research-valuation');if(!host)return;
 if(detailedSymbol===c.symbol){
  previousValuation(c);
  const button=el('button','btn r29-return','RETURN TO SIMPLE VALUATION');
  button.type='button';button.onclick=()=>{detailedSymbol=null;renderResearchValuation(c);r24SelectivePresentation(host);};
  host.prepend(button);
  return;
 }
 host.replaceChildren();
 host.append(el('h3','','VALUATION · SOURCED MARKET MULTIPLES'));
 host.append(el('p','note','Observed provider ratios, not a calculated intrinsic value. Compare with sector peers; ratios can reflect different accounting dates and definitions.'));
 const grid=el('div','r29-valuation-grid');host.append(grid);
 const multiple=(x,d=1)=>finite(x)&&x>0?fmt(x,d)+'×':'Unavailable';
 ratioTile(grid,'Trailing P/E',multiple(c.trailingPE),'Reported earnings');
 ratioTile(grid,'Forward P/E',multiple(c.forwardPE),'Provider earnings estimate');
 ratioTile(grid,researchIsFinancial(c)?'Price / book':'EV / EBITDA',
  multiple(researchIsFinancial(c)?c.priceToBook:c.enterpriseToEbitda),'Provider calculation');
 ratioTile(grid,'Dividend yield',finite(c.dividendYieldPct)&&c.dividendYieldPct>=0?fmt(c.dividendYieldPct,2)+'%':'Unavailable','Quoted dividend basis');
 const sameCurrency=!!c.marketCapCurrency&&c.marketCapCurrency===c.financialCurrency;
 const yieldValue=sameCurrency&&finite(c.freeCashflow)&&finite(c.marketCap)&&c.marketCap>0?
  100*c.freeCashflow/c.marketCap:null;
 ratioTile(grid,'FCF / market capitalisation',finite(yieldValue)?fmt(yieldValue,2)+'%':'Unavailable',
  sameCurrency?'Provider TTM FCF; not normalised':'Reporting and market currencies differ');
 const consensus=c.analystConsensus;
 const matching=consensus&&c.priceCurrency&&consensus.quoteCurrency&&
   c.priceCurrency.replace('GBX','GBp')===consensus.quoteCurrency.replace('GBX','GBp');
 const target=matching&&finite(consensus.targetMean)&&finite(c.price)&&c.price>0&&
   consensus.targetMean/c.price>=.2&&consensus.targetMean/c.price<=5?
   100*(consensus.targetMean/c.price-1):null;
 ratioTile(grid,'Analyst target vs price',finite(target)?(target>0?'+':'')+fmt(target,1)+'%':'Unavailable',
  'Aggregated provider opinion · not a recommendation');
 host.append(el('p','note','Financial data checked '+(c.financialAsOf||'unknown')+' · share price '+(c.priceAsOf||'unknown')+
  '. Forward ratios and analyst targets are third-party estimates; these are not certified fair values.'));
 const button=el('button','btn r29-full-model','OPEN ADVANCED DCF & STRESS MODEL');
 button.type='button';button.onclick=()=>{detailedSymbol=c.symbol;renderResearchValuation(c);r24SelectivePresentation(host);};
 host.append(button);
 host.append(el('p','mini','Optional: detailed discounted cash-flow inputs are assumption-driven and remain available, but are not suitable as a default valuation score.'));
};
function compactBonds(){
 const source=$id('gilt-retrieval');
 const panel=source?.closest('section.r24-support,details');
 if(panel){
  panel.classList.add('r29-bond-diagnostics');
  // Freshness warning remains visible above the securities table.
  panel.hidden=true;
 }
 const gilt=$id('gilts'),treasury=$id('us-treasuries');
 for(const root of [gilt,treasury]){
  const row=root?.querySelector(':scope > .inputs');
  if(row)row.classList.add('r29-bond-toolbar');
 }
}
document.addEventListener('DOMContentLoaded',()=>{
 document.documentElement.classList.add('release29');
 compactBonds();
 // No ETF selectors or styles are changed in this release.
});
})();