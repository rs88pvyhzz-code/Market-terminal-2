/* Release 2.12 — structural presentation on the original Terminal 1 design.
   Retains Terminal 2 source data, chart calculations, cash-flow maths and ETF engine.
   No fabricated values; important results cannot be hidden behind clipped columns. */
(function(){
'use strict';
const get=id=>document.getElementById(id);
function overviewOrder(){
 const host=get('view-overview'),news=get('r24-developments'),snapshot=get('overview-board');
 if(!host||!news||!snapshot)return;
 const title=host.querySelector(':scope > .workspace-title');
 if(title)title.after(snapshot);else host.prepend(snapshot);
 const conditions=get('r24-conditions');
 if(conditions){snapshot.after(conditions);conditions.after(news);}else snapshot.after(news);
 const h=news.querySelector('h2');if(h)h.textContent='KEY MARKET NEWS';
 const label=snapshot.querySelector('h2');if(label)label.textContent='GLOBAL MARKET PULSE';
 // The watchlist has its own complete workspace; no repeated headlines in Overview.
 const repeat=get('r24-watch');if(repeat)repeat.hidden=true;
 const emptyMove=get('r23-moves');
 if(emptyMove&&!emptyMove.querySelector('.r23-observation,.r23-item,.r24-item,.movers-tbl tbody tr'))emptyMove.hidden=true;
}
const oldOverview=r24Overview;
r24Overview=function(){oldOverview();overviewOrder();};
function companyOrder(){
 const host=get('research-view-0');if(!host)return;
 const risk=get('company-risk-panel'),news=get('company-news-panel');
 if(risk&&news&&risk.parentElement===host&&news.parentElement===host)host.insertBefore(news,risk);
}
const oldResearchOrder=researchArrangeOverview;
researchArrangeOverview=function(){oldResearchOrder();companyOrder();};
function analyticsControls(id){
 const host=get(id)?.querySelector('.research-controls');if(!host||host.dataset.r212Grouped)return;
 const nodes=[...host.children];if(!nodes.length)return;
 const groups=[];
 for(let i=0;i<nodes.length;i+=2){
  const label=nodes[i],input=nodes[i+1];
  if(!label||!input||label.tagName!=='LABEL'||!['SELECT','INPUT'].includes(input.tagName))return;
  const group=document.createElement('div');group.className='r212-filter-group';
  group.append(label,input);groups.push(group);
 }
 host.replaceChildren(...groups);host.dataset.r212Grouped='yes';host.classList.add('r212-control-grid');
}
function peerMobileView(){
 const host=get('peer-table'),table=host?.querySelector('table');
 if(!host||!table||!table.rows.length)return;
 const head=table.rows[0],size=head.cells.length;
 let bar=get('r212-peer-bar'),pick=get('r212-peer-pick');
 if(!bar){
  bar=document.createElement('div');bar.id='r212-peer-bar';bar.className='r212-peer-bar';
  const label=document.createElement('label');label.setAttribute('for','r212-peer-pick');label.textContent='MOBILE PEER';
  pick=document.createElement('select');pick.id='r212-peer-pick';pick.className='field';label.append(pick);bar.append(label);
  host.before(bar);
 }
 const prior=pick.value;
 pick.replaceChildren();
 for(let i=2;i<size;i++){
  const option=document.createElement('option');option.value=String(i);option.textContent=head.cells[i].textContent.trim();
  pick.append(option);
 }
 if(size<=2){bar.hidden=true;}else{
  bar.hidden=false;pick.value=[...pick.options].some(o=>o.value===prior)?prior:'2';
 }
 function selectPeer(){
  const selected=Number(pick.value)||2;
  for(const row of table.rows){
   [...row.cells].forEach((cell,i)=>{cell.classList.toggle('r212-mobile-extra-peer',i>1&&i!==selected);});
  }
 }
 pick.onchange=selectPeer;selectPeer();
}
const origPeers=renderPeers;
renderPeers=function(){origPeers();peerMobileView();};
function moveMethodNotes(){
 const quality=get('view-quality');if(!quality||get('r212-technical-notes'))return;
 const panel=document.createElement('section');panel.id='r212-technical-notes';panel.className='panel r212-technical-notes';
 const head=document.createElement('h2');head.textContent='DETAILED METHODOLOGY BY WORKSPACE';panel.append(head);
 let any=false;
 for(const [id,title] of [
   ['gilt-quality','Bonds · Gilt yield methodology'],
   ['gilt-calc-note','Bonds · Settlement and accrued interest'],
   ['breadth-note','Analytics · Breadth coverage'],
   ['sector-note','Analytics · Sector methodology'],
   ['valuation-method','Analytics · Valuation proxy limitations'],
   ['screen-note','Equities · Source and period definitions']]){
   const node=get(id);if(!node)continue;
   const line=document.createElement('details');const label=document.createElement('summary');
   label.textContent=title;line.append(label,node);panel.append(line);any=true;
   const parent=node.closest('details.research-detail');
   // Keep the original node live: update functions still write the source text here.
   if(parent&&parent.querySelectorAll('p').length===0)parent.hidden=true;
 }
 if(any)quality.append(panel);
}
function shortMarketNav(){
 const bar=get('sub-fx-prices');
 if(bar)bar.textContent='PRICES & CHARTS';
 const nav=get('view-fx')?.querySelector('.terminal-subnav');
 if(nav&&!get('r212-market-movers')){
  const button=document.createElement('button');button.id='r212-market-movers';button.type='button';
  button.className='btn';button.textContent='MARKET MOVERS';
  button.onclick=()=>{
   if(typeof activateWorkspace==='function')activateWorkspace('fx',{subview:'prices',scroll:false});
   get('movers')?.scrollIntoView({behavior:'smooth',block:'start'});
  };
  nav.append(button);
 }
}
function cleanGiltUI(){
 const sort=get('gilt-sort');
 if(sort&&sort.value==='net')sort.value='maturity';
 const amount=get('gilt-nominal-input');
 if(amount&&!amount.dataset.r212Bound){
  amount.dataset.r212Bound='yes';
  amount.addEventListener('change',()=>renderGilts());
 }
}
function scrollToActiveTab(){
 const nav=get('workspace-tabs');if(!nav)return;
 for(const tab of nav.querySelectorAll('[role=tab]')){
  tab.addEventListener('click',()=>{
   if(window.matchMedia('(max-width: 720px)').matches)
    tab.scrollIntoView({block:'nearest',inline:'center',behavior:'smooth'});
  });
 }
}
document.addEventListener('DOMContentLoaded',()=>{
 document.documentElement.classList.add('release212','terminal1-design');
 // Older releases relocate their styles; make this final layout stylesheet last.
 const sheet=get('terminal12-styles');if(sheet)document.head.append(sheet);
 overviewOrder();companyOrder();
 analyticsControls('analytics-rolling');analyticsControls('analytics-sectors');
 peerMobileView();moveMethodNotes();shortMarketNav();cleanGiltUI();scrollToActiveTab();
});
})();