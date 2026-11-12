/* Terminal layout — the single source of truth for what appears on each tab.
 *
 * Rules enforced here (and checked by tests/browser_layout.py):
 *   1. Every section sits on exactly one tab.
 *   2. Market-wide analytics (risk, volatility, correlation, breadth, spreads,
 *      valuation proxies, after-tax and ladder calculators, signals) live on the
 *      Analytics tab. Analysis of the selected company stays in Company Research.
 *   3. Duplicated or distracting panels are retired, not deleted: they are parked
 *      in a hidden container so older render code that still writes to them by id
 *      cannot throw.
 *
 * Sections are moved, never rebuilt, so every renderer keeps finding its nodes by
 * id. No figures are calculated or changed here.
 *
 * build_site.py injects this file inside the main application closure, straight
 * after init(), so it can reach paintWorkspace, activateWorkspace and the
 * renderers. It re-asserts the layout after every tab paint and after the other
 * layers' DOMContentLoaded/load handlers, because those move panels too.
 */
(function(){
'use strict';
const $L=id=>document.getElementById(id);

// Tab membership for everything except Analytics and Data Quality, in display order.
const TABS={
  // Key market news is the top-ranked stories; 'news' lists the rest without repeating them.
  overview:['r24-developments','overview-board','news','r24-upcoming'],
  fx:['monitor'],
  equities:['movers','constituents','equity-screener'],
  companies:['companies'],
  bonds:['gilts','us-treasuries','rates','real','sovereign','corporate-credit'],
  etfs:['etf-tracker-panel'],
  economics:['macro','macro-surprise','calendar'],
  watchlist:['personal-watchlist-panel']
};

// Analytics tab: grouped by the subject the analysis is about.
// `scopes` are [outer, inner] class lists standing in for the panel's original
// ancestors, so CSS written as "#gilts .x" still applies after the move
// (build_site.py adds a ".scope-gilts .x" twin to every such rule).
// `source` is the tab where the subject (company, gilt, ETF, watched security) is chosen.
const ANALYTICS=[
  {key:'markets',title:'Markets',source:null,context:null,scopes:[['scope-view-fx'],[]],
   items:['compare','mt-risk-comparison','score-panel','analytics-rolling','r23-market-conditions',
          'analytics-breadth','analytics-sectors','r212-valuation-fold','market-valuations','r23-alerts']},
  {key:'bonds',title:'Bonds & rates',source:'bonds',scopes:[['scope-view-bonds'],['scope-gilts']],
   context:()=>{const g=$L('gilt-selected')?.textContent.trim();return g?'Selected gilt: '+g:'';},
   items:['mt-gilt-tax','gilt-ladder','us-spread-panel','cross-rates']},
  {key:'etfs',title:'ETFs',source:'etfs',scopes:[['scope-view-etfs','scope-etf-tracker-panel'],['scope-etf-detail']],
   context:()=>{const h=document.querySelector('#etf-tracker-panel .etf-detail h3');return h?h.textContent.trim():'No ETF selected';},
   items:['layout-etf-performance','layout-etf-risk','etf-index-comparison','etf-cost-peers']},
  {key:'watchlist',title:'Watchlist',source:'watchlist',scopes:[[],[]],
   context:()=>{const w=$L('watchlist-selected-name')?.textContent.trim();return w||'No security selected';},
   items:['watchlist-risk']}
];

// Company Research: company-specific analysis stays with the company it describes,
// in the research view where it is read. Listed panels are placed first, in order;
// anything else in the view (e.g. the full metrics grid) follows them.
const RESEARCH={
  'research-view-0':['research-overview','company-price-block','company-benchmark-block','company-risk-panel',
                     'company-advanced','research-executive','company-news-panel'],
  'research-view-3':['peer-panel'],
  'research-view-5':['research-warning-priority','forensic-panel']
};

// Company-level source coverage belongs with the other source diagnostics.
const QUALITY=['r29-coverage','company-coverage'];

// Duplicates and distractions. Kept in the DOM (hidden) so legacy renderers are safe.
const RETIRED_IDS=['r24-conditions','r24-watch','r23-moves','r23-watch','headline','subview-fx-news'];
const RETIRED_SELECTORS=[
  '.terminal-subnav','.r25-section-links','#mt-bond-nav','.r210-research-jump',
  '.t11-quality-shortcut','.mt-quality-link'
];
// Methodology notes inside Company Research that add nothing to the figures shown.
const RETIRED_HEADINGS=['Dashboard rules'];

// Renderers to run when Analytics becomes visible: charts need a visible
// container to measure. Each is optional; a failure in one does not stop the rest.
const ANALYTICS_PAINT=[
  ()=>renderGilts(),()=>usSpread(),()=>renderRates(),
  ()=>renderEtfTracker(),()=>renderWatchlist(),()=>renderMarketBriefing()
];

const TAB_NAMES={companies:'Company Research',bonds:'Bonds & Rates',etfs:'ETF Trackers',watchlist:'My Watchlist'};

function parking(){
  let p=$L('layout-retired');
  if(!p){p=document.createElement('div');p.id='layout-retired';p.hidden=true;p.setAttribute('aria-hidden','true');document.body.append(p);}
  return p;
}

// Give id-less panels stable ids so they can be placed like everything else.
function tagAnonymous(){
  const wr=document.querySelector('#personal-watchlist-panel .watchlist-risk:not([id])');
  if(wr)wr.id='watchlist-risk';
  const detail=document.querySelector('#etf-tracker-panel .etf-detail');
  wrapEtf('layout-etf-performance',detail,()=>{
    const chartEl=$L('etf-chart');if(!chartEl)return [];
    const head=$L('etf-chart-stamp')?.closest('div');
    return [head,chartEl,$L('etf-chart-note')].filter(Boolean);
  });
  wrapEtf('layout-etf-risk',detail,()=>{
    const stats=$L('etf-risk-stats');if(!stats)return [];
    const head=stats.previousElementSibling&&/RISK/i.test(stats.previousElementSibling.textContent)?stats.previousElementSibling:null;
    return [head,stats].filter(Boolean);
  });
}
// Wrapper sections are rebuilt from the live nodes each time, so a renderer that
// recreates the ETF detail can never leave a stale copy behind.
function wrapEtf(id,detail,collect){
  const nodes=collect();if(!nodes.length)return;
  let w=$L(id);
  if(!w){w=document.createElement('section');w.id=id;w.className='layout-subpanel';}
  if(nodes.some((n,i)=>w.children[i]!==n)||w.children.length!==nodes.length)w.replaceChildren(...nodes);
  if(!w.parentElement&&detail)detail.append(w);
}

function place(container,ids){
  let prev=null;
  for(const id of ids){
    const node=$L(id);if(!node||node===container)continue;
    // Leave a node where it is if it sits inside another listed item (e.g. a fold).
    if(ids.some(x=>{const o=$L(x);return o&&o!==node&&o.contains(node);}))continue;
    const want=prev?prev.nextElementSibling:firstContentSlot(container);
    if(node.parentElement!==container||node!==want){
      if(prev)prev.after(node);else{const slot=firstContentSlot(container);slot?container.insertBefore(node,slot):container.append(node);}
    }
    prev=node;
  }
}
function firstContentSlot(container){
  for(const c of container.children)if(!c.classList.contains('workspace-title')&&!c.classList.contains('layout-group-head'))return c;
  return null;
}

function analyticsGroup(view,g){
  let box=$L('layout-analytics-'+g.key);
  if(!box){
    box=document.createElement('div');box.id='layout-analytics-'+g.key;
    box.className=['layout-group',...g.scopes[0]].join(' ');
    const head=document.createElement('div');head.className='layout-group-head';
    const h=document.createElement('h2');h.textContent=g.title;head.append(h);
    if(g.context){const p=document.createElement('p');p.className='layout-context';p.id='layout-context-'+g.key;head.append(p);}
    if(g.source){const b=document.createElement('button');b.type='button';b.className='btn layout-source';
      b.textContent='Change in '+TAB_NAMES[g.source];b.onclick=()=>activateWorkspace(g.source);head.append(b);}
    const body=document.createElement('div');body.id='layout-body-'+g.key;
    body.className=['layout-group-body',...g.scopes[1]].join(' ');
    box.append(head,body);
  }
  if(box.parentElement!==view)view.append(box);
  return $L('layout-body-'+g.key);
}

// Company Research: the reported snapshot figures join the overview tiles as one
// block, instead of a separate "All reported snapshot metrics" section further down.
// Figures already shown in the overview tiles (day move, market capitalisation) are
// hidden from the merged grid, not deleted. Re-run after every company render,
// because that render rebuilds the overview and its snapshot section.
const SNAPSHOT_DUPLICATES=/^(day move|market capitali[sz]ation)$/i;
// One grid read in a fixed order: price & valuation, size & growth, profitability,
// then cash & balance sheet. Tiles stay inside their own grids (renderers rebuild
// them); the shared wrapper orders them with CSS order, so nothing is copied.
const METRIC_GROUPS=[
  ['Price & valuation',[/^price$/,/^market capitali[sz]ation$/,/^valuation$/,/^trailing p\/e/,/^forward p\/e/,/^price \/ book/,/^ev \/ ebitda/,/^eps/,/^dividend yield/]],
  ['Size & growth',[/^revenue · ttm/,/^revenue · fy/,/^revenue growth/,/^ebitda/,/^operating profit/,/^net profit · ttm/,/^net profit · fy/]],
  ['Profitability',[/^profit margin/,/^profitability/,/^return on equity/,/^return on/]],
  ['Cash & balance sheet',[/^cash generation/,/^free cash flow/,/^total debt/,/^financial strength/,/^net debt/]]
];
function metricOrder(label){
  const l=label.trim().toLowerCase();let n=0;
  for(let g=0;g<METRIC_GROUPS.length;g++){
    for(let i=0;i<METRIC_GROUPS[g][1].length;i++)if(METRIC_GROUPS[g][1][i].test(l))return (g+1)*100+i+1;
  }
  return 900;
}
function mergeSnapshot(park){
  const kpis=$L('company-kpis'),dash=document.querySelector('#research-overview .research-dashboard');
  if(!kpis||!dash)return;
  const holder=kpis.closest('.research-detail');
  let wrap=dash.parentElement.classList.contains('layout-metrics')?dash.parentElement:null;
  if(!wrap){
    wrap=document.createElement('div');wrap.className='layout-metrics';
    METRIC_GROUPS.forEach(([title],g)=>{const h=document.createElement('div');h.className='layout-metrics-head';h.textContent=title;h.style.order=String((g+1)*100);wrap.append(h);});
    dash.before(wrap);wrap.append(dash);
  }
  if(kpis.parentElement!==wrap)wrap.append(kpis);
  kpis.classList.add('layout-merged-kpis');
  for(const tile of kpis.children){const label=(tile.firstElementChild&&tile.firstElementChild.textContent||'').trim();tile.hidden=SNAPSHOT_DUPLICATES.test(label);}
  for(const tile of [...dash.children,...kpis.children]){const label=tile.firstElementChild&&tile.firstElementChild.textContent||'';tile.style.order=String(metricOrder(label));}
  if(holder&&!holder.contains(kpis)&&!park.contains(holder)){
    const rest=[...holder.children].filter(c=>!c.matches('h3,h4,summary,.r24-support-heading'));
    if(!rest.length)park.append(holder);
  }
}

function refreshContexts(){
  for(const g of ANALYTICS){
    const box=$L('layout-analytics-'+g.key);if(!box)continue;
    const filled=g.items.some(id=>{const n=$L(id);return n&&box.contains(n);});
    box.hidden=!filled;
    if(g.context){const p=$L('layout-context-'+g.key);if(p){const t=g.context();if(p.textContent!==t)p.textContent=t;}}
  }
}

let applying=false;
function applyLayout(){
  if(applying)return;applying=true;
  try{
    tagAnonymous();
    const park=parking();
    for(const id of RETIRED_IDS){const n=$L(id);if(n&&n.parentElement!==park)park.append(n);}
    for(const sel of RETIRED_SELECTORS)document.querySelectorAll(sel).forEach(n=>{if(!park.contains(n))park.append(n);});
    document.querySelectorAll('#companies .research-detail').forEach(sec=>{
      const h=sec.querySelector('.r24-support-heading,h3,summary');
      if(h&&RETIRED_HEADINGS.includes(h.textContent.trim())&&!park.contains(sec))park.append(sec);
    });
    for(const [key,ids] of Object.entries(TABS)){const view=$L('view-'+key);if(view)place(view,ids);}
    for(const [id,ids] of Object.entries(RESEARCH)){const view=$L(id);if(view)place(view,ids);}
    mergeSnapshot(park);
    const av=$L('view-analytics');
    if(av){for(const g of ANALYTICS)place(analyticsGroup(av,g),g.items);}
    const qv=$L('mt-other-audits')||$L('view-quality');
    if(qv)for(const id of QUALITY){const n=$L(id);if(n&&!qv.contains(n))qv.append(n);}
    // The Markets sub-view wrapper is redundant once its sub-navigation is gone.
    const sub=$L('subview-fx-prices');if(sub&&!sub.children.length&&sub.parentElement!==park)park.append(sub);
    refreshContexts();
  }finally{applying=false;}
}

function runAnalyticsPaint(){
  for(const fn of ANALYTICS_PAINT){try{fn();}catch(e){console.warn('Layout repaint skipped:',e&&e.message);}}
}

// Company Research re-arranges its overview after every company render, outside
// the tab paint cycle; re-assert the layout straight after it.
const baseArrange=researchArrangeOverview;
researchArrangeOverview=function(){baseArrange();applyLayout();};

const basePaint=paintWorkspace;
paintWorkspace=function(key){
  applyLayout();
  try{basePaint(key);if(key==='analytics')runAnalyticsPaint();}
  finally{applyLayout();}
};

// UK government bond yields in Global prices, next to the US Treasury yields:
// Bank of England nominal zero-coupon spot yields (5/10/20Y) and the DMO-quoted
// 0 1/8% Treasury Gilt 2028 (TN28), whose yield uses the same model as Bonds & Rates.
// Rows are added to the snapshot once; their history feeds the price chart.
function ukYieldQuote(symbol,name,points,source,note){
  const pts=points.filter(p=>Number.isFinite(p.v)).sort((a,b)=>a.date.localeCompare(b.date));if(!pts.length)return null;
  const last=pts.at(-1),prev=pts.at(-2),lastDate=new Date(last.date+'T00:00:00Z');
  const yearStart=last.date.slice(0,4)+'-01-01';const ytdBase=[...pts].reverse().find(p=>p.date<yearStart);
  const yearAgo=new Date(lastDate.getTime()-365*864e5).toISOString().slice(0,10);
  const yearBase=[...pts].reverse().find(p=>p.date<=yearAgo);
  const window=pts.filter(p=>p.date>yearAgo).map(p=>p.v);
  const bpChange=base=>base?Math.round((last.v-base.v)*1000)/10:null;
  return {group:'Rates',symbol,name,kind:'yield',currency:'GBP',price:Math.round(last.v*1000)/1000,changePct:null,
    changeBp:bpChange(prev),ytdPct:null,yearPct:null,ytdBp:bpChange(ytdBase),yearBp:bpChange(yearBase),
    low52:window.length>20?Math.min(...window):null,high52:window.length>20?Math.max(...window):null,
    asOf:last.date,delayedMin:null,cached:false,cacheDetail:note,source,history:pts};
}
function addUkYieldQuotes(){
  if(!Array.isArray(D.quotes)||D.quotes.some(q=>q.symbol==='UK10Y.BOE'))return;
  const added=[];
  for(const [field,label] of [['gilt5y','5Y'],['gilt10y','10Y'],['gilt20y','20Y']]){
    const pts=(D.uk_rates||[]).map(r=>({date:r.date,v:Number(r[field])}));
    const q=ukYieldQuote('UK'+label+'.BOE','UK '+label+' gilt yield (BoE spot)',pts,'Bank of England','BoE nominal zero-coupon spot curve');
    if(q)added.push(q);
  }
  try{
    const b=(D.gilts||[]).find(g=>g.shortTicker==='TN28'&&g.quoted&&!g.indexLinked);
    if(b&&typeof giltValuation==='function'){
      const pts=(D.gilt_history||[]).filter(p=>p.ticker===b.ticker).map(p=>({date:p.date,v:giltValuation(b,p.close,p.date)?.ytm}));
      // Changes compare like with like (every point valued the same way, clean + modelled
      // accrued); the level shown uses the DMO's own dirty price, as Bonds & Rates does.
      const modelLatest=giltValuation(b,b.askClean,b.asOf)?.ytm;
      if(Number.isFinite(modelLatest)&&!pts.some(p=>p.date===b.asOf))pts.push({date:b.asOf,v:modelLatest});
      const q=ukYieldQuote('TN28.DMO','0 1/8% Treasury Gilt 2028 (TN28) gross YTM',pts,'UK DMO','Model yield from DMO dated offer price');
      const official=giltValuation(b,b.askClean,b.asOf,b.askDirty)?.ytm;
      if(q&&Number.isFinite(official))q.price=Math.round(official*1000)/1000;
      if(q)added.push(q);
    }
  }catch(e){console.warn('TN28 yield skipped:',e&&e.message);}
  if(!added.length)return;
  const at=D.quotes.findIndex(q=>q.group==='Rates');
  D.quotes.splice(at<0?D.quotes.length:at,0,...added.map(({history,...q})=>q));
  if(Array.isArray(D.history))for(const q of added)for(const p of q.history)D.history.push({symbol:q.symbol,date:p.date,close:Math.round(p.v*1000)/1000});
  // The page indexed quotes and histories at start-up; register the new rows there too.
  const pick=$L('main-pick');
  for(const q of added){
    const {history,...row}=q;
    try{qMap.set(q.symbol,D.quotes.find(x=>x.symbol===q.symbol)||row);}catch(e){}
    try{histMap.set(q.symbol,history.map(p=>({date:p.date,v:Math.round(p.v*1000)/1000,adj:null})));}catch(e){}
    if(pick&&![...pick.options].some(o=>o.value===q.symbol)){const o=document.createElement('option');o.value=q.symbol;o.textContent=q.name+' ['+q.symbol+']';pick.append(o);}
  }
  try{if(typeof renderWatch==='function')renderWatch();}catch(e){}
}
addUkYieldQuotes();

window.terminalLayout={TABS,RESEARCH,ANALYTICS,QUALITY,RETIRED_IDS,apply:applyLayout};
applyLayout();
// Other layers rearrange panels in their own DOMContentLoaded handlers and on short
// timers; a zero-delay task queued from ours runs after all of them.
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(applyLayout,0));
window.addEventListener('load',()=>{applyLayout();setTimeout(applyLayout,150);});
setTimeout(applyLayout,150);
})();
