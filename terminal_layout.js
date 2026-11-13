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
  overview:['overview-board','r24-conditions','r24-developments','news','r24-upcoming'],
  fx:['monitor'],
  equities:['equity-screener','constituents','movers'],
  companies:['companies'],
  bonds:['gilts','us-treasuries','rates','real','sovereign','corporate-credit'],
  etfs:['etf-tracker-panel'],
  economics:['macro','calendar','macro-surprise'],
  watchlist:['personal-watchlist-panel']
};

// Analytics tab: grouped by the subject the analysis is about.
// `scopes` are [outer, inner] class lists standing in for the panel's original
// ancestors, so CSS written as "#gilts .x" still applies after the move
// (build_site.py adds a ".scope-gilts .x" twin to every such rule).
// `source` is the tab where the subject (company, gilt, ETF, watched security) is chosen.
const ANALYTICS=[
  {key:'markets',title:'Markets',source:null,context:null,scopes:[['scope-view-fx'],[]],
   items:['score-panel','mt-risk-comparison','analytics-rolling','market-valuations','compare',
          'analytics-breadth','analytics-sectors','r23-market-conditions','r23-alerts']},
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
  'research-view-0':['research-overview','company-news-panel','company-advanced','company-price-block',
                     'company-benchmark-block','company-risk-panel','research-executive'],
  'research-view-3':['peer-panel'],
  'research-view-5':['research-warning-priority','forensic-panel']
};

// Company-level source coverage belongs with the other source diagnostics.
const QUALITY=['r29-coverage','company-coverage'];

// Duplicates and distractions. Kept in the DOM (hidden) so legacy renderers are safe.
const RETIRED_IDS=['r24-watch','r23-moves','r23-watch','headline','subview-fx-news'];
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

// Match visual navigation to keyboard navigation; stable IDs preserve deep links.
function orderNavigation(){
 const nav=$L('workspace-tabs');if(!nav)return;
 WORKSPACES.forEach((key,i)=>{const tab=$L('tab-'+key);if(tab&&nav.children[i]!==tab)nav.insertBefore(tab,nav.children[i]||null);});
}
function unwrapValuations(){
 const fold=$L('r212-valuation-fold'),panel=$L('market-valuations');
 if(fold&&panel){fold.before(panel);fold.remove();}
}
function sectionLinks(){
 for(const key of ['overview','equities','companies','analytics','economics','watchlist']){
  const view=$L('view-'+key),title=view?.querySelector(':scope > .workspace-title');if(!title)continue;
  const ids=key==='analytics'?ANALYTICS[0].items:key==='companies'?RESEARCH['research-view-0']:TABS[key];
  let nav=title.querySelector('.layout-jumps');if(!nav){nav=document.createElement('nav');nav.className='layout-jumps';nav.setAttribute('aria-label','Jump within '+key);title.append(nav);}
  const targets=(ids||[]).map(id=>$L(id)).filter(n=>n&&n.querySelector('h2,h3'));
  const sig=targets.map(n=>n.id).join('|');if(nav.dataset.targets===sig)continue;nav.dataset.targets=sig;nav.replaceChildren();
  for(const node of targets){const b=document.createElement('button');b.type='button';b.textContent=node.querySelector('h2,h3').textContent.replace(/ · .*/,'');
   b.onclick=()=>node.scrollIntoView({behavior:'smooth',block:'start'});nav.append(b);}
 }
}

function renderYieldSnapshot(){
 // Curve strip at the top of Yield curves only: level and day change by tenor, plus 2s10s.
 const rates=$L('rates');if(!rates)return;
 $L('layout-yield-snapshot')?.remove();
 let host=$L('layout-curve-strip');if(host&&host.dataset.ready)return;
 if(!host){host=document.createElement('div');host.id='layout-curve-strip';const head=rates.querySelector(':scope > .row');head?head.after(host):rates.prepend(host);}
 host.dataset.ready='yes';
 const TENORS=['2Y','5Y','10Y','20Y','30Y'];
 const MARKETS=[['UK · BoE spot',D.uk_rates,{'5Y':'gilt5y','10Y':'gilt10y','20Y':'gilt20y'}],
  ['US · Treasury',D.us_rates,{'2Y':'DGS2','5Y':'DGS5','10Y':'DGS10','20Y':'DGS20','30Y':'DGS30'}],
  ['Euro area · ECB',D.eu_rates,{'2Y':'eur2y','5Y':'eur5y','10Y':'eur10y','20Y':'eur20y','30Y':'eur30y'}]];
 const table=document.createElement('table');table.className='watch layout-curve-table';
 const head=document.createElement('tr');for(const t of ['',...TENORS,'2s10s','As of']){const th=document.createElement('th');th.textContent=t;if(t&&t!=='As of')th.className='n';head.append(th);}
 const thead=document.createElement('thead');thead.append(head);table.append(thead);
 const body=document.createElement('tbody');
 const bp=x=>{const r=Math.round(x);return (r>0?'+':r<0?'−':'')+Math.abs(r)+' bp';};
 for(const [name,rows,fields] of MARKETS){
  const tr=document.createElement('tr');const label=document.createElement('td');const [mk,src]=name.split(' · ');label.append(mk);if(src){const sp=document.createElement('span');sp.className='layout-curve-src';sp.textContent=' · '+src;label.append(sp);}tr.append(label);
  const valid=(rows||[]).filter(r=>Object.values(fields).some(f=>Number.isFinite(r[f])));
  const last=valid.at(-1),prev=valid.at(-2);
  const cell=(level,change)=>{const td=document.createElement('td');td.className='n';
   if(!Number.isFinite(level)){td.textContent='—';return td;}
   const v=document.createElement('div');v.textContent=level.toFixed(2)+'%';td.append(v);
   if(Number.isFinite(change)){const c=document.createElement('div');c.className='layout-curve-chg '+(change>0?'up':change<0?'down':'');c.textContent=bp(change);td.append(c);}
   return td;};
  for(const t of TENORS){const f=fields[t];tr.append(cell(f&&last?last[f]:NaN,f&&last&&prev&&Number.isFinite(prev[f])?(last[f]-prev[f])*100:NaN));}
  const s2=fields['2Y'],s10=fields['10Y'];
  const slope=r=>r&&s2&&Number.isFinite(r[s2])&&Number.isFinite(r[s10])?(r[s10]-r[s2])*100:NaN;
  const sl=slope(last),sp=slope(prev);
  const td=document.createElement('td');td.className='n';
  if(Number.isFinite(sl)){const v=document.createElement('div');v.textContent=bp(sl);td.append(v);
   if(Number.isFinite(sp)){const c=document.createElement('div');const d=sl-sp;c.className='layout-curve-chg '+(d>0?'up':d<0?'down':'');c.textContent=bp(d);td.append(c);}}
  else td.textContent='—';
  tr.append(td);
  const date=document.createElement('td');date.textContent=last?.date||'—';tr.append(date);
  body.append(tr);
 }
 table.append(body);host.append(table);
}

function orderDetailContent(){
 // The price table answers the first Markets question; history follows selection.
 const monitor=$L('monitor'),table=$L('watch-rows')?.closest('.scroll');
 if(monitor&&table&&!$L('layout-market-prices')){
  const group=$L('group-pills')?.closest('.inputs'),head=group?.previousElementSibling;
  const prices=document.createElement('section');prices.id='layout-market-prices';
  if(head&&group){prices.append(head,group,table);monitor.prepend(prices);}
 }
 const watch=$L('personal-watchlist-panel'),news=watch?.querySelector('.watchlist-bottom'),selected=watch?.querySelector('.watchlist-selected-header');
 if(news&&selected&&selected.nextElementSibling!==news)selected.after(news);
 // Selected bond cash returns precede the history chart, retaining all controls.
 const stats=$L('gilt-stats'),chart=$L('gilt-chart');
 if(stats&&chart&&stats.parentElement===chart.parentElement&&stats.compareDocumentPosition(chart)&Node.DOCUMENT_POSITION_PRECEDING)chart.before(stats);
}

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

// Repeated caveats the reader already knows (causation, methodology) are removed
// wherever a renderer writes them. Whole notes that are only a caveat are hidden;
// a caveat sentence inside a longer plain-text note is cut out.
const CAVEAT_SENTENCES=[
  /[^.]*\bnot (?:proof|evidence) (?:of|that)[^.]*causa[^.]*\.?/gi,
  /[^.]*\bno (?:price |event-to-price )?caus(?:ation|e)[^.]*inferred[^.]*\.?/gi,
  /[^.]*\bRelated (?:headlines|articles) are[^.]*\.?/gi,
  /[^.]*\bnot verified causes[^.]*\.?/gi,
  /[^.]*\bCheck company announcements, dividends, splits[^.]*\.?/gi,
  /[^.]*\bVerify company announcements and corporate actions[^.]*\.?/gi,
  /\s*·\s*Existing alert threshold crossed[^·]*/gi
];
function stripCaveats(root){
  const scope=root||$L('workspace-stage');if(!scope)return;
  scope.querySelectorAll('.note,.mini,p,.r23-observation>div,.watchlist-kpis>*>:nth-child(3)').forEach(n=>{
    if(n.dataset.caveatChecked===n.textContent)return;
    if(n.children.length===0){
      let t=n.textContent;const orig=t;
      for(const re of CAVEAT_SENTENCES)t=t.replace(re,'');
      t=t.replace(/\s{2,}/g,' ').trim();
      if(t!==orig.trim()){if(!t||/^[·.,;:\s]*$/.test(t))n.hidden=true;else n.textContent=t;}
    }
    n.dataset.caveatChecked=n.textContent;
  });
  scope.querySelectorAll('details').forEach(d=>{const s=d.querySelector('summary');if(s&&/^News methodology$/i.test(s.textContent.trim()))d.hidden=true;});
}

// ---------------------------------------------------------------- Release 3.3
// Overview pulse: equity indices, then currencies, bond yields, VIX, gold, Brent, bitcoin.
const PULSE_ORDER=[/^FTSE 100/,/^S&P 500/,/^Nasdaq/,/STOXX 600/,/Nikkei/,/Emerging/,/^GBP\/USD/,/^GBP\/EUR/,/^EUR\/USD/,
  /UK 10Y/,/US 10Y/,/^VIX/,/^Gold/,/^Brent/,/^Bitcoin/];
function orderPulse(){
  document.querySelectorAll('#overview-board .r24-snapshot-item').forEach(item=>{
    const label=(item.firstElementChild&&item.firstElementChild.textContent||'').trim();
    const i=PULSE_ORDER.findIndex(re=>re.test(label));item.style.order=String(i<0?50:i);
  });
}

// ETF Trackers: catalogue counts belong in Data Quality; tidy duplicated or hedged labels.
function tidyEtf(){
  const panel=$L('etf-tracker-panel');if(!panel)return;
  const stats=$L('etf-stats'),quality=$L('mt-other-audits')||$L('view-quality');
  if(stats&&quality&&!quality.contains(stats)){
    const box=$L('layout-etf-coverage')||document.createElement('section');
    if(!box.id){box.id='layout-etf-coverage';box.className='panel';const h=document.createElement('h2');h.textContent='ETF CATALOGUE COVERAGE';box.append(h);}
    const head=panel.querySelector(':scope > .row');
    if(head)head.querySelectorAll('.note,.mini,p,span').forEach(n=>{if(!n.closest('h2')){box.append(n);} });
    box.append(stats);quality.append(box);
  }
  panel.querySelectorAll('*').forEach(n=>{
    if(n.children.length===0&&/\(submethod not confirmed\)/.test(n.textContent))n.textContent=n.textContent.replace(/\s*\(submethod not confirmed\)/g,'');
  });
  panel.querySelectorAll('.etf-stat-grid').forEach(grid=>{
    const tiles=[...grid.children],label=t=>(t.firstElementChild&&t.firstElementChild.textContent||'').trim().toLowerCase();
    if(tiles.some(t=>/^fund assets/.test(label(t))))tiles.forEach(t=>{if(label(t)==='fund size')t.classList.add('layout-hidden');});
  });
}

// ETF alternatives: the selected fund beside up to three funds tracking the same
// market (then closely related markets), largest first, on cost, size and returns.
const ETF_RELATED={'Global':['Developed world'],'Developed world':['Global'],'Europe':['Eurozone'],'Eurozone':['Europe'],
  'UK FTSE 100':['UK FTSE All Share','UK FTSE 250'],'UK FTSE 250':['UK FTSE 100','UK FTSE All Share'],'UK FTSE All Share':['UK FTSE 100','UK FTSE 250'],
  'Emerging markets':['EM ex China'],'EM ex China':['Emerging markets'],'United States':['US equal weight','US small cap','US technology'],
  'US technology':['United States'],'UK gilts':['UK short gilts'],'UK short gilts':['UK gilts'],
  'US Treasury 7-10y':['US Treasury 3-7y','US Treasury long dated'],'US Treasury 1-3y':['US Treasury 0-1y','US Treasury 3-7y'],
  'Global aggregate bond':['Global aggregate GBP hedged'],'Global aggregate GBP hedged':['Global aggregate bond'],
  'USD investment grade':['EUR investment grade','UK investment grade'],'China':['Asia Pacific ex Japan'],'Latin America':['Brazil','Mexico']};
function etfAlternatives(fund){
  const same=ETF_FUNDS.filter(f=>f.symbol!==fund.symbol&&f.market===fund.market&&f.category===fund.category);
  const related=(ETF_RELATED[fund.market]||[]).flatMap(m=>ETF_FUNDS.filter(f=>f.market===m&&f.category===fund.category));
  const bySize=a=>a.sort((x,y)=>(y.fundSize||0)-(x.fundSize||0));
  return [...bySize(same),...bySize(related)].slice(0,3);
}
function etfMoney(f){
  if(!Number.isFinite(f.fundSize)||!f.fundSize)return '—';
  const v=f.fundSize,c=f.fundSizeCurrency||'';return c+' '+(v>=1e9?fmt(v/1e9,2)+'bn':fmt(v/1e6,1)+'m');
}
function etfPct(v){return Number.isFinite(v)?(v>0?'+':'')+fmt(v,2)+'%':'—';}
function renderEtfAlternatives(){
  const detail=document.querySelector('#etf-tracker-panel .etf-detail');if(!detail||typeof ETF_BY_SYMBOL==='undefined')return;
  const fund=ETF_BY_SYMBOL.get(etfState.selected);if(!fund)return;
  let box=$L('layout-etf-alternatives');
  if(!box){box=document.createElement('section');box.id='layout-etf-alternatives';box.className='layout-subpanel';}
  if(box.dataset.fund===fund.symbol&&box.isConnected)return;
  box.dataset.fund=fund.symbol;box.replaceChildren();
  const h=document.createElement('h3');h.textContent='ALTERNATIVES — '+String(fund.market||'').toUpperCase();box.append(h);
  const alts=etfAlternatives(fund);
  if(!alts.length){const p=document.createElement('p');p.className='note';p.textContent='No other catalogued fund tracks this market.';box.append(p);}
  else{
    const wrap=document.createElement('div');wrap.className='mt-table-scroll';
    const t=document.createElement('table');t.className='watch layout-alt-table';
    t.innerHTML='<thead><tr><th>Fund / ticker</th><th>Index</th><th>TER</th><th>Fund size</th><th>1Y</th><th>3Y</th><th>5Y</th><th>Replication</th><th>Income</th></tr></thead>';
    const tb=document.createElement('tbody');
    for(const f of [fund,...alts]){
      const tr=document.createElement('tr');if(f===fund)tr.className='selected';
      const cells=[null,f.benchmark||'—',Number.isFinite(f.terPct)?fmt(f.terPct,2)+'%':'—',etfMoney(f),etfPct(f.return1Y),etfPct(f.return3Y),etfPct(f.return5Y),
        String(f.replication||'—').replace(/\s*\(submethod not confirmed\)/,''),f.distribution||'—'];
      const name=document.createElement('td');const b=document.createElement('button');b.type='button';b.className='layout-alt-pick';
      b.textContent=f.name+' · '+f.symbol;b.disabled=f===fund;b.onclick=()=>{etfState.selected=f.symbol;try{renderEtfTracker();}catch(e){}renderEtfAlternatives();};
      name.append(b);tr.append(name);
      cells.slice(1).forEach((c,i)=>{const td=document.createElement('td');td.textContent=c;if(i>=3&&i<=5&&/^[+-]/.test(c))td.className=c.startsWith('-')?'down':'up';tr.append(td);});
      tb.append(tr);
    }
    t.append(tb);wrap.append(t);box.append(wrap);
    const p=document.createElement('p');p.className='note';p.textContent='Returns are annualised for 3Y and 5Y, in each fund\u2019s quoted currency. Same market first, then closely related markets; largest funds first.';box.append(p);
  }
  const anchor=detail.querySelector('.etf-stat-grid');
  if(anchor)anchor.after(box);else detail.prepend(box);
}

// Data Quality: collection warnings grouped by source in plain language.
function plainWarning(w){
  const s=String(w);
  if(/429|Too Many Requests/i.test(s))return 'Source limited request rate; retried, then skipped';
  if(/404|Not Found|delisted/i.test(s))return 'No longer available from source';
  if(/Under two historical closes|insufficient|too short/i.test(s))return 'Too little price history to use';
  if(/stale cache/i.test(s))return 'Download failed; last saved copy used';
  if(/timed? ?out|timeout/i.test(s))return 'Source did not respond in time';
  return s.replace(/^[^:]+:\s*/,'');
}
function renderWarnings(){
  const old=$L('t11-exception-details');if(!old)return;
  const list=Array.isArray(D.warnings)?D.warnings:[];
  let box=$L('layout-warnings');
  if(!box){box=document.createElement('section');box.id='layout-warnings';box.className='panel';old.before(box);}
  if(box.dataset.count===String(list.length))return;box.dataset.count=String(list.length);box.replaceChildren();
  const h=document.createElement('h2');h.textContent='COLLECTION ISSUES THIS BUILD ('+list.length+')';box.append(h);
  const groups=new Map();
  for(const w of list){const s=String(w);const m=s.match(/^([A-Za-z][A-Za-z/& ]{1,20}?)\s+([^:]{1,40}):/);const src=m?m[1]:'Other';const item=m?m[2]:'';
    const key=src+'|'+plainWarning(s);if(!groups.has(key))groups.set(key,{src,issue:plainWarning(s),items:[]});if(item)groups.get(key).items.push(item);}
  const t=document.createElement('table');t.className='watch';t.innerHTML='<thead><tr><th>Source</th><th>What happened</th><th>Affected</th></tr></thead>';
  const tb=document.createElement('tbody');
  for(const g of groups.values()){const tr=document.createElement('tr');for(const c of [g.src,g.issue,g.items.length?g.items.join(', '):'—']){const td=document.createElement('td');td.textContent=c;tr.append(td);}tb.append(tr);}
  t.append(tb);const wrap=document.createElement('div');wrap.className='mt-table-scroll';wrap.append(t);box.append(wrap);
  old.hidden=true;
}

// Sovereign yields: one table of 10-year yields for the major economies, no chart.
function lastTwo(arr,field){const v=(arr||[]).filter(r=>Number.isFinite(Number(r[field])));return v;}
function changeBp(pts,days){
  const last=pts.at(-1);if(!last)return null;const cutoff=new Date(new Date(last.date).getTime()-days*864e5).toISOString().slice(0,10);
  const base=[...pts].reverse().find(p=>p.date<=cutoff);return base?Math.round((last.v-base.v)*100):null;
}
function renderSovereignTable(){
  const host=$L('sovereign');if(!host)return;
  const series=[];
  const add=(name,rows,field,source)=>{const pts=(rows||[]).filter(r=>Number.isFinite(Number(r[field]))).map(r=>({date:r.date,v:Number(r[field])}));if(pts.length)series.push({name,pts,source});};
  add('United Kingdom',D.uk_rates,'gilt10y','BoE spot');add('United States',D.us_rates,'DGS10','US Treasury');
  for(const [code,name] of [['DE','Germany'],['FR','France'],['IT','Italy'],['ES','Spain'],['NL','Netherlands']])add(name,D.sovereign_yields,code,'Eurostat monthly');
  if(!series.length)return;
  let box=$L('layout-sovereign-table');
  const sig=series.map(s=>s.name+s.pts.at(-1).date).join();if(box&&box.dataset.sig===sig)return;
  if(!box){box=document.createElement('div');box.id='layout-sovereign-table';const head=host.querySelector('.row');(head||host.firstElementChild).after(box);}
  box.dataset.sig=sig;box.replaceChildren();
  const de=series.find(s=>s.name==='Germany');
  const t=document.createElement('table');t.className='watch';t.innerHTML='<thead><tr><th>Country</th><th>10Y yield</th><th>As of</th><th>vs Germany</th><th>1M change</th><th>1Y change</th><th>Source</th></tr></thead>';
  const tb=document.createElement('tbody');
  for(const s of series){const last=s.pts.at(-1),spread=de&&s!==de?Math.round((last.v-de.pts.at(-1).v)*100):null;
    const c1=changeBp(s.pts,31),c12=changeBp(s.pts,365);
    const vals=[s.name,fmt(last.v,2)+'%',last.date,spread==null?'—':(spread>0?'+':'')+spread+'bp',c1==null?'—':(c1>0?'+':'')+c1+'bp',c12==null?'—':(c12>0?'+':'')+c12+'bp',s.source];
    const tr=document.createElement('tr');vals.forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});tb.append(tr);}
  t.append(tb);const wrap=document.createElement('div');wrap.className='mt-table-scroll';wrap.append(t);box.append(wrap);
  const h2=host.querySelector('h2');if(h2)h2.textContent='SOVEREIGN 10-YEAR YIELDS';
  const intro=host.querySelector('.row .note');if(intro)intro.textContent='Latest 10-year government bond yields. UK uses the Bank of England spot curve; euro-area countries use Eurostat monthly benchmarks, so their dates lag.';
  for(const id of ['sovereign-chart','sovereign-latest','sovereign-meta'])$L(id)?.classList.add('layout-hidden');
  host.querySelectorAll('select').forEach(sel=>{(sel.closest('label')||sel).classList.add('layout-hidden');const l=host.querySelector('label[for="'+sel.id+'"]');if(l)l.classList.add('layout-hidden');});
  host.querySelectorAll('details').forEach(d=>d.classList.add('layout-hidden'));
}

// Bonds & Rates: five sub-tabs instead of one long page.
const BOND_TABS=[['UK gilts',['gilts']],['US Treasuries',['us-treasuries']],['Yield curves',['rates','real']],['Credit spreads',['corporate-credit']],['Sovereign',['sovereign']]];
let bondTab=0;
function bondTabFor(id){return BOND_TABS.findIndex(([,ids])=>ids.some(x=>x===id||$L(x)?.querySelector('#'+CSS.escape(id))));}
function renderBondTabs(){
  const view=$L('view-bonds');if(!view)return;
  let nav=$L('layout-bond-tabs');
  if(!nav){nav=document.createElement('nav');nav.id='layout-bond-tabs';nav.className='layout-subtabs';
    BOND_TABS.forEach(([label],i)=>{const b=document.createElement('button');b.type='button';b.className='btn';b.textContent=label;b.onclick=()=>{bondTab=i;renderBondTabs();try{paintWorkspace('bonds');}catch(e){}window.scrollTo({top:Math.max(0,view.offsetTop-80)});};nav.append(b);});}
  const title=view.querySelector(':scope > .workspace-title');
  if(nav.parentElement!==view||nav.previousElementSibling!==title){title?title.after(nav):view.prepend(nav);}
  [...nav.children].forEach((b,i)=>b.classList.toggle('active',i===bondTab));
  BOND_TABS.forEach(([,ids],i)=>ids.forEach(id=>$L(id)?.classList.toggle('layout-subtab-hidden',i!==bondTab)));
}
window.addEventListener('hashchange',()=>{const id=location.hash.slice(1);if(!id)return;const i=bondTabFor(id);if(i>=0&&i!==bondTab){bondTab=i;renderBondTabs();}});
{const id=location.hash.slice(1);const i=id?bondTabFor(id):-1;if(i>=0)bondTab=i;}

// Clean reading (Release 3.4): this terminal has one expert reader, so explanatory
// notes, caveats, source boilerplate, coverage counts and footers are removed from
// every tab except Data Quality. Kept: figures, tables, tiles with data, headlines
// and their dates, chart summaries, empty-state messages and controls.
const KEEP_NOTE=[/^(1D|1W|1M|3M|6M|YTD|1Y|3Y|5Y|10Y|MAX)\s*·/,/\bprice (?:move|change)[: ]/i,/^\d{4}-\d{2}-\d{2} to \d{4}/,/^No /,/^Showing \d+ of \d+/];
const DROP_SECTIONS=['etf-issuer-snapshot'];
const TILE_GRIDS='.etf-stat-grid,.research-stats,.watchlist-kpis,.etf-stat-grid,.analytic-cards,.research-dashboard,.company-kpis,.credit-kpis,.r28-gilt-yields,.r28-gilt-facts,.t11-ratios,.macro,.pulse-board,.layout-metrics,.r29-coverage-grid';
function cleanReading(){
  const stage=$L('workspace-stage');if(!stage)return;
  document.querySelectorAll('footer.foot').forEach(f=>f.hidden=true);
  for(const id of DROP_SECTIONS){const n=$L(id);if(n)n.classList.add('layout-hidden');}
  stage.querySelectorAll('.r24-calendar-key,.r28-gilt-advanced,.r28-more').forEach(n=>{if(!n.closest('#view-quality'))n.classList.add('layout-hidden');});
  stage.querySelectorAll('p,.note,.mini,small').forEach(n=>{
    if(n.dataset.cleanChecked===n.textContent)return;n.dataset.cleanChecked=n.textContent;
    if(n.closest('#view-quality,table,label,button,select,summary,h1,h2,h3,h4,.news-item,.r24-item,.r23-observation,.layout-group-head,#layout-bond-tabs,.mt-reading-note,.r213-company-evidence,.company-story,.research-warning,.mt-inline-notice'))return;
    const text=n.textContent.trim();if(!text)return;
    // Research write-ups (outlook, statements, issuer evidence) are content: there only
    // purely explanatory lines (no figure or date) are removed.
    if(n.closest('.research-view:not(#research-view-0),.r23-company-changes')){if(!/\d/.test(text))n.classList.add('layout-hidden');return;}
    const tile=n.closest(TILE_GRIDS);
    if(tile){ // inside a data tile: keep captions that carry figures or dates
      if(n.parentElement&&n.parentElement.firstElementChild===n)return;   // tile label
      if(!/\d/.test(text))n.classList.add('layout-hidden');
      return;
    }
    if(KEEP_NOTE.some(re=>re.test(text)))return;
    n.classList.add('layout-hidden');
  });
  // Tile captions that only explain (no figure or date) go; captions with data stay.
  stage.querySelectorAll(TILE_GRIDS.split(',').map(g=>g+' > * > :nth-child(n+3)').join(',')).forEach(n=>{
    if(n.closest('#view-quality'))return;
    if(n.children.length===0&&!/\d/.test(n.textContent))n.classList.add('layout-hidden');
  });
  $L('company-dates')?.classList.add('layout-hidden');
  // Methodology fold-outs belong in Data Quality only.
  stage.querySelectorAll('details').forEach(d=>{
    if(d.closest('#view-quality'))return;
    const sum=d.querySelector(':scope > summary');if(sum&&/methodolog|source tables|how this is calculated/i.test(sum.textContent))d.classList.add('layout-hidden');
  });
  // Retrieval timestamps on article cards add nothing to the publisher date.
  stage.querySelectorAll('.news-item .meta,.r24-item .mini,.mini').forEach(n=>{
    if(n.children.length===0&&/ · retrieved \d{4}-\d{2}-\d{2}T[\d:.+]+/.test(n.textContent))n.textContent=n.textContent.replace(/\s*·\s*retrieved \d{4}-\d{2}-\d{2}T[\d:.+-]+(?::\d{2})?/g,'');
  });
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
    const sheet=$L('terminal-layout-styles');if(sheet&&document.head.lastElementChild!==sheet)document.head.append(sheet);
    tagAnonymous();
    orderNavigation();
    unwrapValuations();
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
    for(const step of [orderPulse,orderDetailContent,renderYieldSnapshot,tidyEtf,renderEtfAlternatives,renderWarnings,renderSovereignTable,renderBondTabs])
      {try{step();}catch(e){console.warn('Layout step skipped:',step.name,e&&e.message);}}
    const ws=$L('watchlist-summary');if(ws&&ws.parentElement!==park)park.append(ws);
    stripCaveats();
    try{cleanReading();}catch(e){console.warn('Clean reading skipped:',e&&e.message);}
    const av=$L('view-analytics');
    if(av){for(const g of ANALYTICS)place(analyticsGroup(av,g),g.items);}
    const qv=$L('mt-other-audits')||$L('view-quality');
    if(qv)for(const id of QUALITY){const n=$L(id);if(n&&!qv.contains(n))qv.append(n);}
    // The Markets sub-view wrapper is redundant once its sub-navigation is gone.
    const sub=$L('subview-fx-prices');if(sub&&!sub.children.length&&sub.parentElement!==park)park.append(sub);
    refreshContexts();
    sectionLinks();
  }finally{applying=false;}
}

function runAnalyticsPaint(){
  for(const fn of ANALYTICS_PAINT){try{fn();}catch(e){console.warn('Layout repaint skipped:',e&&e.message);}}
}

// Company Research re-arranges its overview after every company render, outside
// the tab paint cycle; re-assert the layout straight after it.
const baseArrange=researchArrangeOverview;
researchArrangeOverview=function(){baseArrange();applyLayout();};

// Re-draw the alternatives table whenever the ETF tracker re-renders a selection.
try{const baseEtf=renderEtfTracker;renderEtfTracker=function(){const r=baseEtf.apply(this,arguments);try{renderEtfAlternatives();tidyEtf();}catch(e){}return r;};}catch(e){}

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
