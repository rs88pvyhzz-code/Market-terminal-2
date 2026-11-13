// Terminal polish — runs last, inside the application closure.
// One return figure everywhere, explanations off, flat lists, stale-data flags.
(function(){
  const $q=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
  const EMPTY=/^(unavailable|—|-|not disclosed|not verified|unverified|n\/a)$/i;
  const DATED=/\d{4}-\d{2}-\d{2}/;
  const pct=v=>(v==null||!Number.isFinite(+v))?'—':(typeof etfPct==='function'?etfPct(+v):(+v).toFixed(2)+'%');
  const fund=()=>(typeof ETF_BY_SYMBOL!=='undefined'&&typeof etfState!=='undefined')?ETF_BY_SYMBOL.get(etfState.selected):null;
  const today=()=>{const g=(typeof D!=='undefined'&&D.generatedAt)||'';return /^\d{4}-\d{2}-\d{2}/.test(g)?g.slice(0,10):new Date().toISOString().slice(0,10);};

  // ETF detail: the 1Y/3Y/5Y shown in the detail are the same figures as the card and table.
  function etfDetail(){
    const f=fund();
    for(const host of $$('#etf-risk-stats,#etf-detail-stats')){
      for(const stat of $$('.etf-stat',host)){
        const k=$q('.k',stat),v=$q('.v',stat),d=$q('.d',stat);if(!k||!v)continue;
        const m=k.textContent.trim().match(/^([135])Y annualised$/i);
        if(m&&f){const val=pct(f['return'+m[1]+'Y']);if(v.textContent!==val)v.textContent=val;if(d)d.remove();k.textContent=m[1]+'Y return'+(m[1]==='1'?'':' (annualised)');}
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

  // Data Quality: off the tab bar, one quiet link at the foot of the page.
  function qualityLink(){
    const tab=$q('#tab-quality');if(!tab||$q('.polish-quality-link'))return;
    const a=document.createElement('a');a.href='#quality';a.className='polish-quality-link';a.textContent='DATA QUALITY →';
    a.onclick=e=>{e.preventDefault();tab.click();window.scrollTo(0,0);};
    (document.querySelector('main')||document.body).append(a);
  }

  let busy=false,queued=false;
  function polish(){
    if(busy)return;busy=true;
    try{etfDetail();etfCards();calendar();macroTable();qualityLink();}
    catch(err){console.warn('terminal polish:',err);}
    finally{busy=false;}
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;polish();});}
  polish();
  new MutationObserver(()=>{if(!busy)schedule();}).observe(document.body,{childList:true,subtree:true});
})();
