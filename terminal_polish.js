// Terminal polish — runs last, inside the application closure.
// One return figure everywhere, explanations off, flat lists, stale-data flags.
(function(){
  const $q=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
  const EMPTY=/^(unavailable|—|-|not disclosed|not verified|unverified|n\/a)$/i;
  const DATED=/\d{4}-\d{2}-\d{2}/;
  const pct=v=>(v==null||!Number.isFinite(+v))?'—':(typeof etfPct==='function'?etfPct(+v):(+v).toFixed(2)+'%');
  const fund=()=>(typeof ETF_BY_SYMBOL!=='undefined'&&typeof etfState!=='undefined')?ETF_BY_SYMBOL.get(etfState.selected):null;
  const today=()=>{const g=(typeof D!=='undefined'&&D.generatedAt)||'';return /^\d{4}-\d{2}-\d{2}/.test(g)?g.slice(0,10):new Date().toISOString().slice(0,10);};

  const PS=t=>{t=String(t||'').trim();if(/^[PS]$/.test(t))return t;if(/^S\b|synthetic|swap/i.test(t))return 'S';if(/^P\b|physical/i.test(t))return 'P';return '?';};
  // ETF detail: the 1Y/3Y/5Y shown in the detail are the same figures as the card and table.
  function etfDetail(){
    const f=fund();
    for(const host of $$('#etf-risk-stats,#etf-detail-stats')){
      for(const stat of $$('.etf-stat',host)){
        const k=$q('.k',stat),v=$q('.v',stat),d=$q('.d',stat);if(!k||!v)continue;
        const m=k.textContent.trim().match(/^([135])Y annualised$/i);
        if(m&&f){const val=pct(f['return'+m[1]+'Y']);if(v.textContent!==val)v.textContent=val;if(d)d.remove();k.textContent=m[1]+'Y total return'+(m[1]==='1'?'':' (annualised)');}
        const label=k.textContent.trim();
        if(/^fund assets \(aum\)$/i.test(label)){stat.remove();continue;}
        if(/^replication$/i.test(label)){const kind=(f&&typeof etfV5Kind==='function')?etfV5Kind(f)[0]:'';const ps=/^[PS]$/.test(kind)?kind:PS(v.textContent);if(v.textContent!==ps)v.textContent=ps;if(d)d.remove();continue;}
        if(EMPTY.test(v.textContent.trim())){stat.remove();continue;}
        if(d&&!DATED.test(d.textContent))d.remove();
      }
    }
    const risk=$q('#etf-risk-stats');
    if(risk&&f){
      let basis=$q('#polish-etf-basis');
      if(!basis){basis=document.createElement('div');basis.id='polish-etf-basis';basis.className='polish-basis';risk.before(basis);}
      const end=f.returnPeriods?.['1Y']?.end||(f.quote?.asOf||'').slice(0,10);
      const text='Returns: '+(f.returnBasis||'basis not recorded')+(end?' · to '+end:'')+(f.quote?.currency?' · '+f.quote.currency:'');
      if(basis.textContent!==text)basis.textContent=text;
    }
  }

  // ETF cards: drop filler tags; AUM is the whole fund, so say so.
  function etfCards(){
    for(const meta of $$('.etf-compare-card .etf-card-meta'))if(/^not in main table$/i.test(meta.textContent.trim()))meta.remove();
    for(const span of $$('.etf-card-facts span'))if(/^Fund AUM/.test(span.textContent))span.textContent='Fund size';
    for(const box of $$('.etf-card-facts > div')){const k=box.querySelector('span'),v=box.querySelector('strong');
      if(k&&v&&/^structure$/i.test(k.textContent.trim())){k.textContent='Replication';const ps=PS(v.textContent);if(v.textContent!==ps)v.textContent=ps;}}
    for(const th of $$('th')){const t=th.textContent.trim();if(/^Fund (AUM|assets)/.test(t)&&t!=='Fund size')th.textContent='Fund size';}
    for(const k of $$('.etf-stat .k'))if(/^Fund assets|^Fund AUM/.test(k.textContent.trim()))k.textContent='Fund size';
  }

  // Calendar: keep a release time only when it is a real time; otherwise no sub-line.
  function calendar(){
    for(const mini of $$('#calendar-items .mt-cal-row .mini')){
      const t=mini.textContent.match(/\b\d{1,2}:\d{2}(\s?(ET|CET|GMT|BST|UK))?\b/);
      if(t){if(mini.textContent!==t[0])mini.textContent=t[0];}else mini.remove();
    }
    for(const small of $$('#calendar-items small'))if(!/\d{1,2}:\d{2}/.test(small.textContent))small.remove();
  }

  // Economics actuals: drop empty forecast columns, show source once, flag stale prints.
  function periodEnd(text){
    const s=text.trim().toUpperCase(),mon={JAN:1,FEB:2,MAR:3,APR:4,MAY:5,JUN:6,JUL:7,AUG:8,SEP:9,OCT:10,NOV:11,DEC:12};
    let m=s.match(/^(\d{4}) (Q[1-4])$/);if(m){const q=+m[2][1];return {end:new Date(Date.UTC(+m[1],q*3,0)),limit:140};}
    m=s.match(/^(\d{4}) ([A-Z]{3})$/);if(m&&mon[m[2]])return {end:new Date(Date.UTC(+m[1],mon[m[2]],0)),limit:80};
    m=s.match(/^(\d{4})-(\d{2})$/);if(m)return {end:new Date(Date.UTC(+m[1],+m[2],0)),limit:80};
    return null;
  }
  function macroTable(){
    const body=$q('#macro-print-rows');if(!body||!body.rows.length)return;
    const table=body.closest('table'),heads=[...table.tHead.rows[0].cells];
    heads.forEach((th,i)=>{
      const label=th.textContent.trim();
      const cells=[...body.rows].map(r=>r.cells[i]).filter(Boolean);
      const allEmpty=cells.every(c=>/^(—|-|)$/.test(c.textContent.trim()));
      const hide=(/forecast|surprise/i.test(label)&&allEmpty)||/^source$/i.test(label);
      th.classList.toggle('polish-hidden',hide);cells.forEach(c=>c.classList.toggle('polish-hidden',hide));
      if(/^source$/i.test(label)){
        const names=[...new Set(cells.map(c=>c.textContent.trim().split(/\s*·\s*/)[0]).filter(Boolean))];
        let cap=$q('#polish-macro-source');
        if(!cap){cap=document.createElement('p');cap.id='polish-macro-source';cap.className='polish-section-source';table.parentElement.after(cap);}
        const text=names.length?'Source: '+names.join(', '):'';if(cap.textContent!==text)cap.textContent=text;
      }
    });
    const pi=heads.findIndex(th=>/observation period/i.test(th.textContent));if(pi<0)return;
    const now=Date.parse(today()+'T00:00:00Z');
    for(const row of body.rows){
      const cell=row.cells[pi];if(!cell)continue;
      const raw=(cell.firstChild&&cell.firstChild.nodeType===3?cell.firstChild.textContent:cell.textContent).replace('stale','');
      const p=periodEnd(raw);let flag=$q('.polish-stale',cell);
      const stale=p&&(now-p.end.getTime())/86400000>p.limit;
      if(stale&&!flag){flag=document.createElement('span');flag.className='polish-stale';flag.textContent='stale';
        flag.title='A newer release should exist; the feed may be serving cached data';cell.append(flag);}
      if(!stale&&flag)flag.remove();
    }
  }

  // Gilt block: keep warnings, drop the standing method explanation.
  function gilt(){for(const n of $$('#gilts .r28-gilt-single > p.note'))if(/^Gross cash figures are undiscounted/.test(n.textContent)&&!n.hidden)n.hidden=true;}

  // Long tables: first rows in page flow, the rest behind "Show all" (no nested scroll boxes).
  const LIMIT=20,expanded=new Set();
  const WRAPS='.r28-table-scroll,.etf-table-scroll,.gilt-table-scroll,.mt-table-scroll,.constituents-scroll,.screener-scroll,.watchlist-table-scroll,.scroll,#ust-securities-scroll';
  function wrapKey(w){return w.id||[...w.classList].join('.')+'@'+(w.closest('section[id],[id^=view-]')?.id||'');}
  function longTables(){
    for(const w of $$(WRAPS)){
      if(w.closest('#view-quality')||w.parentElement?.closest(WRAPS))continue;
      const body=w.querySelector('tbody');if(!body)continue;
      const rows=[...body.rows].filter(r=>!/group|geo/.test(r.className));
      const key=wrapKey(w),open=expanded.has(key),over=rows.length>LIMIT;
      let n=0;
      for(const r of body.rows){
        const isGroup=/group|geo/.test(r.className);if(!isGroup)n++;
        const keep=open||!over||n<=LIMIT||r.matches('.etf-active,.selected,.active,[aria-selected=true]');
        if(r.classList.contains('polish-cut')===keep)r.classList.toggle('polish-cut',!keep);
      }
      let btn=w.nextElementSibling?.classList.contains('polish-more')?w.nextElementSibling:null;
      if(!over){btn?.remove();continue;}
      if(!btn){btn=document.createElement('button');btn.type='button';btn.className='polish-more';w.after(btn);}
      btn.onclick=()=>{open?expanded.delete(key):expanded.add(key);longTables();if(open)w.scrollIntoView({block:'start'});};
      const label=open?'Show fewer':'Show all '+rows.length;
      if(btn.textContent!==label)btn.textContent=label;
    }
  }

  // Search: gilts and US Treasuries are searchable, and every result lands on its detail.
  function extendSearch(){
    if(typeof fullSearchList==='undefined'||typeof chooseGlobalResult!=='function')return;
    for(const g of (typeof giltList!=='undefined'?giltList:[]))
      fullSearchList.push({kind:'gilt',label:g.name+(g.shortTicker?' ('+g.shortTicker+')':''),code:g.isin||g.ticker,ticker:g.ticker,detail:'UK gilt · matures '+g.maturity});
    for(const b of (typeof ustList!=='undefined'?ustList:[]))
      fullSearchList.push({kind:'ust',label:b.name,code:b.cusip,detail:'US Treasury · '+(b.type||'')+' · matures '+b.maturity});
    const base=chooseGlobalResult;
    const land=(id)=>setTimeout(()=>{const n=document.getElementById(id);if(n)n.scrollIntoView({behavior:'smooth',block:'start'});},120);
    const bond=(i)=>{activateWorkspace('bonds',{scroll:false});if(typeof bondTab!=='undefined'){bondTab=i;renderBondTabs();}};
    chooseGlobalResult=function(item){
      if(!item)return;
      if(item.kind==='gilt'){$('global-search').value='';closeGlobalResults();bond(0);giltState.symbol=item.ticker;renderGilts();land('gilt-stats');return;}
      if(item.kind==='ust'){$('global-search').value='';closeGlobalResults();bond(1);ustState.selected=item.code;renderUST();land('ust-selected');return;}
      base(item);
      if(item.kind==='etfTracker')land('etf-selected');
    };
  }
  try{extendSearch();}catch(err){console.warn('search extension:',err);}
  try{if(typeof etfState!=='undefined'&&etfState.compared?.size){etfState.compared.clear();if(typeof renderEtfTracker==='function')renderEtfTracker();}}catch(err){}

  // No references to SEC filings, EDGAR, XBRL or form numbers outside Data Quality.
  const FILING=/\bSEC\b|EDGAR|XBRL|\b(?:10-K|10-Q|20-F|6-K|8-K)\b/;
  function scrubFilings(){
    const stage=document.getElementById('workspace-stage');if(!stage)return;
    for(const a of stage.querySelectorAll('a[href*="sec.gov"]'))if(!a.closest('#view-quality'))a.remove();
    for(const h of stage.querySelectorAll('summary,h3,h4,.r24-support-heading'))
      if(/filing dates|Field-level sources/i.test(h.textContent)&&!h.closest('#view-quality')){const box=h.closest('details,section.r24-support')||h;box.hidden=true;}
    const walk=document.createTreeWalker(stage,NodeFilter.SHOW_TEXT);const hits=[];let n;
    while(n=walk.nextNode())if(FILING.test(n.textContent)&&!n.parentElement.closest('#view-quality,script,style'))hits.push(n);
    for(const t of hits){
      const v=t.textContent.replace(/SEC issuer filings?/gi,'issuer accounts').replace(/\(?SEC XBRL\)?\s*/gi,'').replace(/SEC (?:EDGAR )?(?:filings?|companyfacts)/gi,'issuer accounts')
        .replace(/\b(?:EDGAR|XBRL)\b\s*/g,'').replace(/\b(?:10-K|10-Q|20-F|6-K|8-K)\b/g,'annual report').replace(/\bSEC\b\s*/g,'').replace(/\s{2,}/g,' ');
      if(v!==t.textContent)t.textContent=v;
    }
  }

  // Company figures carried over from the last good provider lookup carry their date.
  function retainedDates(){
    const pick=document.getElementById('company-pick');if(!pick||typeof D==='undefined')return;
    const c=(D.companies||[]).find(x=>x.symbol===pick.value);const day=c?.fundamentalsRetainedFrom;
    if(!day)return;
    for(const tile of document.querySelectorAll('#view-companies .research-stats > *, #view-companies .t11-ratios > *, #view-companies .research-dashboard > *')){
      const k=tile.firstElementChild?.textContent||'';
      if(!/P\/E|market cap|dividend yield|EV \/ EBITDA|price \/ book|margin|return on equity|free cash flow|total debt/i.test(k))continue;
      const v=tile.children[1]?.textContent.trim();if(!v||v==='—'||/unavailable/i.test(v))continue;
      let note=tile.querySelector('.polish-retained');
      if(!note){note=document.createElement('div');note.className='polish-retained';tile.append(note);}
      const t='as of '+day;if(note.textContent!==t)note.textContent=t;
    }
  }

  let busy=false,queued=false;
  function polish(){
    if(busy)return;busy=true;
    try{etfDetail();etfCards();calendar();macroTable();gilt();longTables();scrubFilings();retainedDates();}
    catch(err){console.warn('terminal polish:',err);}
    finally{busy=false;}
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;polish();});}
  polish();
  new MutationObserver(()=>{if(!busy)schedule();}).observe(document.body,{childList:true,subtree:true});
})();

// Reading headings follow page scroll even when a table has horizontal overflow.
// Keep the real header in the table for semantics and forward sorting clicks.
(function(){
 const copies=new Map();let queued=false;
 const set=(e,k,v)=>{if(e.style[k]!==v)e.style[k]=v;};
 function update(){
  queued=false;
  const stage=document.getElementById('workspace-stage');if(!stage)return;
  const nav=document.querySelector('.commandbar');
  let top=Math.max(0,nav?.getBoundingClientRect().bottom||0);
  for(const n of stage.querySelectorAll('.layout-subtabs,.mt-bond-nav,.r25-section-links')){
   const r=n.getBoundingClientRect();if(n.getClientRects().length&&getComputedStyle(n).position==='sticky'&&r.top<=top+2&&r.bottom>top)top=r.bottom;
  }
  const active=new Set();
  for(const table of stage.querySelectorAll('table')){
   const head=table.tHead;if(!head||!head.rows.length||!table.getClientRects().length)continue;
   const rect=table.getBoundingClientRect(),height=head.getBoundingClientRect().height;
   if(rect.top>=top||rect.bottom<=top+height||!height)continue;
   let left=Math.max(0,rect.left),right=Math.min(innerWidth,rect.right);
   for(let p=table.parentElement;p&&p!==stage;p=p.parentElement){
    if(/auto|scroll|hidden|clip/.test(getComputedStyle(p).overflowX)){const r=p.getBoundingClientRect();left=Math.max(left,r.left);right=Math.min(right,r.right);}
   }
   if(right<=left)continue;
   active.add(table);let copy=copies.get(table);
   const signature=head.innerHTML;
   if(!copy||copy.signature!==signature){
    copy?.box.remove();const box=document.createElement('div');box.className='table-reading-head';box.setAttribute('aria-hidden','true');
    const t=document.createElement('table'),h=head.cloneNode(true);t.append(h);box.append(t);
    for(const n of h.querySelectorAll('[id]'))n.removeAttribute('id');
    for(const n of h.querySelectorAll('button,a,input'))n.tabIndex=-1;
    const originals=[...head.querySelectorAll('th,td')],clones=[...h.querySelectorAll('th,td')];
    clones.forEach((c,i)=>{c.addEventListener('click',e=>{e.preventDefault();const button=originals[i].querySelector('button');(button||originals[i]).click();});});
    document.body.append(box);copy={box,t,originals,clones,signature};copies.set(table,copy);
   }
   set(copy.box,'top',top+'px');set(copy.box,'left',left+'px');set(copy.box,'width',(right-left)+'px');
   set(copy.t,'width',rect.width+'px');set(copy.t,'marginLeft',(rect.left-left)+'px');
   copy.clones.forEach((c,i)=>{const source=copy.originals[i],style=getComputedStyle(source),r=source.getBoundingClientRect();
    for(const key of ['display','font','color','padding','textAlign','letterSpacing','whiteSpace','borderBottom'])set(c,key,style[key]);
    set(c,'width',r.width+'px');set(c,'minWidth',r.width+'px');set(c,'maxWidth',r.width+'px');
   });
  }
  for(const [table,copy] of copies)if(!active.has(table)){copy.box.remove();copies.delete(table);}
 }
 function schedule(){if(!queued){queued=true;requestAnimationFrame(update);}}
 document.addEventListener('scroll',schedule,{capture:true,passive:true});window.addEventListener('resize',schedule,{passive:true});
 const stage=document.getElementById('workspace-stage');if(stage)new MutationObserver(schedule).observe(stage,{childList:true,subtree:true});
 schedule();
})();
