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
    for(const span of $$('.etf-card-facts span'))if(span.textContent==='Fund AUM')span.textContent='Fund AUM (all classes)';
    for(const box of $$('.etf-card-facts > div')){const k=box.querySelector('span'),v=box.querySelector('strong');
      if(k&&v&&/^structure$/i.test(k.textContent.trim())){k.textContent='Replication';const ps=PS(v.textContent);if(v.textContent!==ps)v.textContent=ps;}}
    for(const th of $$('th'))if(th.textContent.trim()==='Fund AUM')th.textContent='Fund AUM (all classes)';
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

  let busy=false,queued=false;
  function polish(){
    if(busy)return;busy=true;
    try{etfDetail();etfCards();calendar();macroTable();gilt();longTables();}
    catch(err){console.warn('terminal polish:',err);}
    finally{busy=false;}
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;polish();});}
  polish();
  new MutationObserver(()=>{if(!busy)schedule();}).observe(document.body,{childList:true,subtree:true});
})();
