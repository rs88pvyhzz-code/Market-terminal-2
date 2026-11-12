/* Terminal layout — the single source of truth for what appears on each tab.
 *
 * Rules enforced here (and checked by tests/browser_layout.py):
 *   1. Every section sits on exactly one tab.
 *   2. All analytics (risk, volatility, correlation, momentum, benchmarks,
 *      spreads, peer comparisons, valuation proxies, after-tax and ladder
 *      calculators, signals) live only on the Analytics tab.
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
  {key:'company',title:'Company',source:'companies',scopes:[['scope-view-companies','scope-panel'],['scope-research-view','scope-research-view-0']],
   context:()=>{const n=$L('company-name')?.textContent.trim(),s=$L('company-symbol')?.textContent.trim();
     return n?(n+(s?' ['+s+']':'')):'No company selected';},
   items:['company-benchmark-block','company-risk-panel','company-advanced','research-executive',
          'peer-panel','research-warning-priority','forensic-panel']},
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
  ()=>renderCompany(),()=>renderPeers(),()=>renderGilts(),()=>usSpread(),()=>renderRates(),
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

window.terminalLayout={TABS,ANALYTICS,QUALITY,RETIRED_IDS,apply:applyLayout};
applyLayout();
// Other layers rearrange panels in their own DOMContentLoaded handlers and on short
// timers; a zero-delay task queued from ours runs after all of them.
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(applyLayout,0));
window.addEventListener('load',()=>{applyLayout();setTimeout(applyLayout,150);});
setTimeout(applyLayout,150);
})();
