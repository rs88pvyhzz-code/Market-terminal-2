/* Original Market Terminal presentation on the proven Market Terminal 2 data engine.
   No changes to quote, source collection, return or yield calculations. */
(function(){
'use strict';
const byId=id=>document.getElementById(id);
const val=x=>String(x==null?'':x);
const n=x=>typeof x==='number'&&Number.isFinite(x);
function metric(grid,label,value,note){
 const item=el('div','t11-metric');
 item.append(el('div','lab',label),el('strong','',value),el('small','mini',note));
 grid.append(item);
}
function shownMultiple(value){
 return n(value)&&value>0?fmt(value,1)+'×':'Unavailable';
}
// Explicit user request: remove the editable DCF, reverse DCF and all stress
// assumption panels. Financial statements, ratios and source facts remain.
renderResearchValuation=function(c){
 const host=byId('research-valuation');if(!host)return;
 host.replaceChildren();
 host.append(el('h3','','OBSERVED VALUATION RATIOS'));
 const grid=el('div','t11-ratios');host.append(grid);
 metric(grid,'Trailing P/E',shownMultiple(c.trailingPE),'Provider-reported');
 metric(grid,'Forward P/E',shownMultiple(c.forwardPE),'Analyst estimate');
 metric(grid,researchIsFinancial(c)?'Price / book':'EV / EBITDA',
   shownMultiple(researchIsFinancial(c)?c.priceToBook:c.enterpriseToEbitda),'Provider-reported');
 metric(grid,'Dividend yield',n(c.dividendYieldPct)?fmt(c.dividendYieldPct,2)+'%':'Unavailable','Quoted dividend basis');
 const sameCCY=!!c.marketCapCurrency&&c.marketCapCurrency===c.financialCurrency;
 const cashYield=sameCCY&&n(c.freeCashflow)&&n(c.marketCap)&&c.marketCap>0?c.freeCashflow/c.marketCap*100:null;
 metric(grid,'Free cash flow yield',n(cashYield)?fmt(cashYield,2)+'%':'Unavailable',
   sameCCY?'Provider trailing free cash flow':'Reporting currencies differ');
 const cs=c.analystConsensus;
 const matching=cs&&c.priceCurrency&&cs.quoteCurrency&&c.priceCurrency.replace('GBX','GBp')===cs.quoteCurrency.replace('GBX','GBp');
 const upside=matching&&n(cs.targetMean)&&n(c.price)&&c.price>0&&cs.targetMean/c.price>=.2&&cs.targetMean/c.price<=5?
 (cs.targetMean/c.price-1)*100:null;
 metric(grid,'Mean analyst target vs price',n(upside)?(upside>0?'+':'')+fmt(upside,1)+'%':'Unavailable',
   'Provider consensus, not a recommendation');
 host.append(el('p','mini','Dated share prices and company accounts can differ. Full source coverage and exceptions are in Data Quality.'));
};
function extraPanel(id,title,entries){
 const panel=el('section','panel t11-quality-section');panel.id=id;
 panel.append(el('h2','',title));
 if(!entries.length){panel.append(el('p','note','No source exceptions were reported for this category.'));return panel;}
 for(const [label,body] of entries){
  const row=el('details','t11-quality-row');
  row.append(el('summary','',label),el('p','note',val(body)));
  panel.append(row);
 }
 return panel;
}
function qualityEntries(){
 const rows=[];
 // Dated source notices are included in full here, not hidden or discarded.
 const sources=[
  ['UK gilts · retrieval & valuation', '#gilt-retrieval'],
  ['UK gilts · source warnings', '#gilts .r29-source-warning'],
  ['ETF methodology', '#etf-tracker-panel > .row .note'],
  ['Company source and coverage', '#company-dates'],
  ['Company accounts and estimates', '#research-valuation .note'],
  ['US Treasury source terms', '#us-treasuries > .note'],
  ['Market source notes', '#overview-board .pulse-warning'],
  ['Data coverage source dates', '#r29-coverage'],
 ];
 for(const [label,selector] of sources){
  const node=document.querySelector(selector);
  if(node&&node.textContent.trim())rows.push([label,node.textContent.trim().slice(0,6500)]);
 }
 return rows;
}
function renderSourceRegister(){
 const quality=byId('view-quality');if(!quality)return;
 let source=byId('terminal1-source-register');
 if(source)source.remove();
 source=el('section','panel t11-source-register');source.id='terminal1-source-register';
 source.append(el('h2','','SOURCE QUALITY & TECHNICAL DIAGNOSTICS'));
 const foot=el('p','note','Consolidated reporting of data quality checks, source dates, provider limitations and missing coverage. The data in the other sections are unchanged.');
 source.append(foot);
 const warnings=Array.isArray(D.warnings)?D.warnings:[];
 source.append(extraPanel('t11-exception-details','Collection warnings ('+warnings.length+')',
    warnings.map((item,i)=>['Issue '+(i+1),val(item)])));
 const grouped=qualityEntries();
 source.append(extraPanel('t11-source-notes','Methodology, valuation provenance and source coverage',grouped));
 const news=Array.isArray(D.newsDiagnostics)?D.newsDiagnostics:[];
 if(news.length)source.append(extraPanel('t11-news-diagnostics','News retrieval diagnostics ('+news.length+')',
   news.map((item,i)=>['Retrieval '+(i+1),typeof item==='string'?item:JSON.stringify(item)])));
 quality.append(source);
}
function dataQualityShortcut(){
 for(const key of ['overview','fx','equities','companies','bonds','analytics','etfs','economics','watchlist']){
  const view=byId('view-'+key);if(!view||view.querySelector('.t11-quality-shortcut'))continue;
  const link=el('button','btn t11-quality-shortcut','SOURCES & DATA CHECKS');
  link.type='button';link.onclick=()=>activateWorkspace('quality');
  const heading=view.querySelector(':scope > .workspace-title');
  if(heading)heading.append(link);
 }
}
function correctContent(){
 const research=byId('research-nav');
 if(research){
  const tab=byId('research-tab-2');
  if(tab)tab.textContent='MARKET RATIOS';
 }
 const name=byId('view-analytics')?.querySelector('.workspace-title h1');
 if(name)name.textContent='ANALYTICS';
 const quality=byId('view-quality')?.querySelector('.workspace-title h1');
 if(quality)quality.textContent='DATA QUALITY';
 dataQualityShortcut();
}
const previousPaint=paintWorkspace;
paintWorkspace=function(key){
 previousPaint(key);
 if(key==='quality')renderSourceRegister();
 if(key==='companies')correctContent();
};
document.addEventListener('DOMContentLoaded',()=>{document.documentElement.classList.add('terminal1-design');correctContent();});
})();