/* Readability layer — runs last. Presentation only: it rewords timestamps,
   hides low-value columns and empty section rows. No market data is changed. */
(function(){
  const MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const isoShort=(y,m,d)=>`${+d} ${MONTHS[+m-1]}`;

  // "5 Nov 2026, 16:30 UTC" -> "5 Nov, 16:30";  "2026-11-05" -> "5 Nov"
  function shortTime(t){
    return t.replace(/(\d{1,2} [A-Z][a-z]{2}) \d{4},? (\d{2}:\d{2})(?: UTC)?/g,'$1, $2')
            .replace(/\b(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}))?(?: UTC)?/g,(m,y,mo,d,hm)=>isoShort(y,mo,d)+(hm?', '+hm:''))
            .replace(/ UTC\b/g,'');
  }

  function setText(el,t){if(el.textContent!==t)el.textContent=t}

  function header(){
    const s=document.getElementById('stamp');
    if(s&&/rerun Python/i.test(s.textContent))setText(s,s.textContent.replace(/\s*·\s*rerun Python to refresh/i,''));
  }

  function pulse(){
    const board=document.getElementById('market-pulse');
    if(!board)return;
    if(!document.getElementById('rd-utc-note')){
      const n=document.createElement('div');n.id='rd-utc-note';n.className='rd-utc-note';n.textContent='Quote times in UTC';
      board.parentNode.insertBefore(n,board);
    }
    board.querySelectorAll('.r24-snapshot-item .mini').forEach(m=>{
      if(m.children.length)return;
      setText(m,shortTime(m.textContent));
    });
  }

  // Tables: say "UTC" once in the column heading, not in every row.
  function tableUtc(table){
    const heads=table.tHead&&table.tHead.rows.length?[...table.tHead.rows[table.tHead.rows.length-1].cells]:[];
    if(!heads.length)return;
    const cols=new Set();
    for(const tb of table.tBodies)for(const row of tb.rows){
      if(row.cells.length!==heads.length)continue;
      [...row.cells].forEach((c,i)=>{if(!c.children.length&&/\d{2}:\d{2} UTC$/.test(c.textContent.trim()))cols.add(i)});
    }
    cols.forEach(i=>{
      const h=heads[i];
      if(h&&!/UTC/.test(h.textContent)&&!h.querySelector('button'))setText(h,h.textContent.trim()+' (UTC)');
      for(const tb of table.tBodies)for(const row of tb.rows){
        const c=row.cells[i];
        if(c&&row.cells.length===heads.length&&!c.children.length&&/ UTC$/.test(c.textContent.trim()))setText(c,c.textContent.trim().replace(/ UTC$/,''));
      }
    });
  }

  // Hide columns by heading text; keep the hidden values as a tooltip on the row.
  const HIDE={
    '#market-valuations':['P/E coverage','Financials retrieved'],
    '#equity-screener':['Financials checked','Price history']
  };
  function hideCols(){
    for(const [sel,names] of Object.entries(HIDE)){
      document.querySelectorAll(sel+' table').forEach(table=>{
        if(!table.tHead)return;
        const heads=[...table.tHead.rows[table.tHead.rows.length-1].cells];
        const idx=heads.map((h,i)=>names.includes(h.textContent.trim())?i:-1).filter(i=>i>=0);
        if(!idx.length)return;
        idx.forEach(i=>heads[i].classList.add('rd-hide-col'));
        for(const tb of table.tBodies)for(const row of tb.rows){
          if(row.cells.length!==heads.length)continue;
          const tip=idx.map(i=>heads[i].textContent.trim()+': '+row.cells[i].textContent.trim()).join(' · ');
          idx.forEach(i=>row.cells[i].classList.add('rd-hide-col'));
          if(row.cells[0]&&row.cells[0].title!==tip)row.cells[0].title=tip;
        }
      });
    }
  }

  // A section heading with no visible rows under it is hidden.
  function orphans(){
    document.querySelectorAll('#workspace-stage tbody').forEach(tb=>{
      const rows=[...tb.rows];
      rows.forEach((r,i)=>{
        if(!r.classList.contains('watch-section'))return;
        let shown=false;
        for(let j=i+1;j<rows.length&&!rows[j].classList.contains('watch-section');j++){
          if(!rows[j].classList.contains('polish-cut')&&!rows[j].classList.contains('rd-orphan')&&rows[j].style.display!=='none'){shown=true;break}
        }
        if(r.classList.contains('rd-orphan')===shown)r.classList.toggle('rd-orphan',!shown);
      });
    });
  }

  // Economic indicators: "Prior 3.10% · 2026-08" -> value in bold, readable date.
  function priors(){
    document.querySelectorAll('#macro-tiles .r28-economic-sub').forEach(el=>{
      if(el.querySelector('b'))return;
      const m=el.textContent.match(/^Prior\s+(\S+)\s*·\s*(.+)$/);
      if(!m)return;
      let when=m[2].trim().replace(/^(\d{4})-(\d{2})$/,(x,y,mo)=>MONTHS[+mo-1]+' '+y)
                         .replace(/^(\d{4}) ([A-Z]{3})$/,(x,y,mo)=>mo[0]+mo.slice(1).toLowerCase()+' '+y);
      el.textContent='Prior ';const b=document.createElement('b');b.textContent=m[1];el.append(b,' · '+when);
    });
  }

  let busy=false,queued=false;
  function apply(){
    if(busy)return;busy=true;
    try{
      header();pulse();
      document.querySelectorAll('#workspace-stage table').forEach(tableUtc);
      hideCols();orphans();priors();
    }catch(e){console.warn('readability layer',e)}
    busy=false;
  }
  function schedule(){if(queued)return;queued=true;setTimeout(()=>{queued=false;apply()},60)}

  apply();
  const stage=document.getElementById('workspace-stage')||document.body;
  new MutationObserver(()=>{if(!busy)schedule()}).observe(stage,{childList:true,subtree:true,characterData:true});
  const st=document.getElementById('stamp');if(st)new MutationObserver(()=>{if(!busy)schedule()}).observe(st,{childList:true,characterData:true,subtree:true});
})();
