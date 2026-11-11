/* Release 2.11: original Market Terminal interaction, modern data.
   No collection, price history, issuer source, ETF, gilt or return formula changes.
   Original ten-workspace shell and source-quality separation are intentional.
*/
(function(){
'use strict';
const elBy=id=>document.getElementById(id);
const canNumber=x=>typeof x==='number'&&Number.isFinite(x);
const text=x=>x===null||x===undefined?'':String(x);
function section(title){
 const box=document.createElement('section');box.className='t1-ledger-section';
 box.append(el('h3','',title));return box;
}
function ledger(){
 let root=elBy('t1-source-ledger');if(root)return root;
 root=el('section','panel t1-source-ledger');root.id='t1-source-ledger';
 root.append(el('h2','','SOURCE QUALITY BY AREA'),
   el('p','note','All technical data coverage, source freshness, retrieval exceptions, and verification details are held here. Security-level quotation dates and risk caveats remain on the relevant market screen.'));
 elBy('view-quality')?.prepend(root);
 return root;
}
function qualityMove(id,title,mode='node'){
 const node=elBy(id);if(!node)return;
 const root=ledger();
 let box=elBy('t1-source-'+id);
 if(!box){box=section(title);box.id='t1-source-'+id;root.append(box);}
 if(mode==='parent'&&node.parentElement&&!node.parentElement.closest('#view-quality')){
   const parent=node.parentElement;
   if(parent.matches('details,section')||parent.classList.contains('r29-coverage')){
    box.append(parent);return;
   }
 }
 box.append(node);
}
function qualityAnchor(host){
 if(!host||host.querySelector('.t1-quality-link'))return;
 const row=el('div','t1-quality-link');
 const link=el('button','btn','SOURCE QUALITY & DATA CHECKS');
 link.type='button';link.onclick=()=>activateWorkspace('quality');
 row.append(link);host.prepend(row);
}
function positionQuality(){
 const root=ledger();
 if(!root)return;
 qualityMove('etf-stats','ETF CATALOGUE COVERAGE');
 qualityMove('etf-coverage','ETF PUBLICATION COVERAGE');
 qualityMove('gilt-freshness','DMO QUOTATION FRESHNESS');
 qualityMove('gilt-retrieval','DMO RETRIEVAL AND DEFINITIONS','parent');
 qualityMove('r29-coverage','COMPANY RESEARCH SOURCE COVERAGE');
 qualityMove('company-coverage','COMPANY SOURCE REGISTERS');
 qualityMove('company-alert','COMPANY PROFILE RETRIEVAL WARNINGS');
 for(const warning of document.querySelectorAll('.r29-source-warning')){
   qualityMove(warning.id||assign(warning,'t1-source-warning'),'DMO SOURCE REVIEW');
 }
 const news=elBy('news');
 const feeds=news?.querySelector(':scope > details');
 if(feeds){let box=elBy('t1-publisher-feeds');if(!box){box=section('PUBLISHER FEEDS AND METHODOLOGY');box.id='t1-publisher-feeds';root.append(box);}box.append(feeds);}
 const newsMethod=news?.querySelector('details:not(.mt-quality-drilldown)');
 if(newsMethod){elBy('t1-publisher-feeds')?.append(newsMethod);}
 qualityAnchor(elBy('gilts')?.querySelector('.row'));
 qualityAnchor(elBy('etf-tracker-panel')?.querySelector(':scope > .row'));
 qualityAnchor(elBy('companies')?.querySelector('.company-toolbar'));
}
let assigned=0;
function assign(node,prefix){node.id=prefix+'-'+(++assigned);return node.id;}
const previousArrange=researchArrangeOverview;
researchArrangeOverview=function(){previousArrange();positionQuality();};
const oldOverview=researchR2Executive;
researchR2Executive=function(c){
 oldOverview(c);
 const host=elBy('research-executive');
 if(!host)return;
 for(const card of [...host.querySelectorAll('.research-executive-card')]){
  const heading=card.querySelector('h4')?.textContent||'';
  if(/valuation\s*\/\s*margin of safety|base model/i.test(heading))card.remove();
 }
 for(const warning of host.querySelectorAll('.research-warning')){
  if(/valuation requires source review/i.test(warning.textContent))warning.remove();
 }
 for(const note of host.querySelectorAll('.note')){
  if(/ROIC minus assumed WACC:/i.test(note.textContent))note.remove();
 }
};
function simpleMetric(root,label,value,context){
 const card=el('div','t1-ratio-tile');
 card.append(el('span','mini',label),el('strong','',value),el('small','note',context));
 root.append(card);
}
renderResearchValuation=function(c){
 const host=elBy('research-valuation');
 if(!host||!c)return;
 // Do not build editable DCF, reverse DCF, stress, WACC, terminal-value,
 // or user-input margin-of-safety calculations.
 host.replaceChildren();
 host.append(el('h3','','MARKET VALUATION RATIOS · PUBLISHED FACTS'));
 const grid=el('div','t1-ratio-grid');host.append(grid);
 const x=(v,n=1)=>canNumber(v)&&v>0?fmt(v,n)+'×':'Unavailable';
 simpleMetric(grid,'Trailing P/E',x(c.trailingPE),'Reported earnings');
 simpleMetric(grid,'Forward P/E',x(c.forwardPE),'Provider analyst estimates');
 simpleMetric(grid,researchIsFinancial(c)?'Price / book':'EV / EBITDA',
   x(researchIsFinancial(c)?c.priceToBook:c.enterpriseToEbitda),'Provider metric');
 simpleMetric(grid,'Dividend yield',canNumber(c.dividendYieldPct)&&c.dividendYieldPct>=0?fmt(c.dividendYieldPct,2)+'%':'Unavailable','Published distribution basis');
 const same=!!c.marketCapCurrency&&c.marketCapCurrency===c.financialCurrency;
 const cashYield=same&&canNumber(c.freeCashflow)&&canNumber(c.marketCap)&&c.marketCap>0?100*c.freeCashflow/c.marketCap:null;
 simpleMetric(grid,'Reported FCF yield',canNumber(cashYield)?fmt(cashYield,2)+'%':'Unavailable',same?'TTM cash flow divided by market cap':'Different currency bases');
 const consensus=c.analystConsensus;
 let uplift=null;
 if(consensus&&canNumber(consensus.targetMean)&&canNumber(c.price)&&c.price>0&&
    c.priceCurrency&&consensus.quoteCurrency&&c.priceCurrency.replace('GBX','GBp')===consensus.quoteCurrency.replace('GBX','GBp')&&
    consensus.targetMean/c.price>=.2&&consensus.targetMean/c.price<=5){
    uplift=100*(consensus.targetMean/c.price-1);
 }
 simpleMetric(grid,'Analyst target vs price',canNumber(uplift)?(uplift>0?'+':'')+fmt(uplift,1)+'%':'Unavailable','External analyst opinion, not an intrinsic value');
 host.append(el('p','note','These ratios are sourced observations or simple derived comparisons, not our valuation model. Dates and underlying source exceptions are in Data Quality.'));
 const holder=elBy('research-view-0');
 if(holder&&!holder.contains(host)){
  let section=elBy('t1-valuation-facts');
  if(!section){section=el('section','t1-valuation-facts');section.id='t1-valuation-facts';}
  section.append(host);
  const overview=elBy('research-overview');
  if(overview?.parentElement===holder)overview.after(section);else holder.prepend(section);
 }
};
const previousSetupResearch=setupResearchViews;
setupResearchViews=function(){
 previousSetupResearch();
 const tab=elBy('research-tab-2'),panel=elBy('research-view-2');
 if(tab){tab.hidden=true;tab.setAttribute('aria-hidden','true');tab.tabIndex=-1;}
 if(panel){panel.hidden=true;panel.setAttribute('aria-hidden','true');}
 const indices=[0,1,3,4,5];
 for(const i of indices){
  const btn=elBy('research-tab-'+i);if(!btn)continue;
  btn.onkeydown=e=>{
   if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
   e.preventDefault();
   const pos=indices.indexOf(i);
   const target=e.key==='Home'?indices[0]:e.key==='End'?indices.at(-1):
       indices[(pos+(e.key==='ArrowRight'?1:-1)+indices.length)%indices.length];
   showResearchView(target);elBy('research-tab-'+target)?.focus();
  };
 }
 if(researchView===2)showResearchView(0);
 positionQuality();
};
const originalShow=showResearchView;
showResearchView=function(i){originalShow(i===2?0:i);};
function scopeNavigation(){
 document.documentElement.classList.add('terminal1-restored');
 const keys=['overview','fx','equities','companies','bonds','analytics','etfs','economics','watchlist','quality'];
 for(const item of document.querySelectorAll('#workspace-tabs [data-workspace]')){
  const key=item.dataset.workspace;
  item.title='Original Market Terminal · '+item.textContent.trim();
  item.onclick=()=>activateWorkspace(key);
  item.onkeydown=e=>{
   if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
   e.preventDefault();
   const i=keys.indexOf(key);
   const target=e.key==='Home'?keys[0]:e.key==='End'?keys.at(-1):keys[(i+(e.key==='ArrowRight'?1:-1)+keys.length)%keys.length];
   activateWorkspace(target);elBy('tab-'+target)?.focus();
  };
 }
 // Preserve the original tab ordering and remove redundant second-level tabs.
 document.querySelectorAll('.terminal-subnav').forEach(nav=>nav.remove());
 const doc=elBy('view-companies');
 if(doc)doc.querySelector('.workspace-title h1').textContent='COMPANY RESEARCH';
 const quick=elBy('view-analytics');
 if(quick)quick.querySelector('.workspace-title h1').textContent='ANALYTICS';
 positionQuality();
}
document.addEventListener('DOMContentLoaded',scopeNavigation);
})();
