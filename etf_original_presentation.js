/* Original Market Terminal ETF presentation, source ced3f6a, terminal_template.html
   and etf_consolidation.py. Adaptations: exact peers capped at three, no repeated
   cards, full-current-catalogue search. No return/risk/FX calculations changed. */
function etfOriginalKey(f){
  const explicit=[f.name,f.benchmark,f.market].join(' ').match(/\b(?:GBP|USD|EUR|JPY|CHF)\s*[- ]?hedged\b/i)?.[0]||'';
  return etfV5Key(f)+'|'+explicit.toLowerCase().replace(/[- ]+/g,' ');
}
function etfOriginalPeers(f){
  if(!f?.benchmark)return [];
  const seen=new Set([f.isin||f.symbol]);
  return ETF_FUNDS.filter(p=>p.symbol!==f.symbol&&etfOriginalKey(p)===etfOriginalKey(f)).sort((a,b)=>(a.terPct??Infinity)-(b.terPct??Infinity)||a.symbol.localeCompare(b.symbol)).filter(p=>{const id=p.isin||p.symbol;if(seen.has(id))return false;seen.add(id);return true;}).slice(0,3);
}
etfV5Choose=function(symbol){
 const f=ETF_BY_SYMBOL.get(symbol);if(!f)return;
 etfState.selected=symbol;etfCompareBenchmark=f.benchmark||'';
 const allowed=new Set(etfOriginalPeers(f).map(p=>p.symbol));etfState.compared=new Set([...etfState.compared].filter(s=>allowed.has(s)).slice(0,3));renderEtfTracker();
};
etfV5ChangeCompare=function(symbol,yes){
 const f=ETF_BY_SYMBOL.get(etfState.selected);
 if(!etfOriginalPeers(f).some(p=>p.symbol===symbol)||yes&&etfState.compared.size>=3&&!etfState.compared.has(symbol))return false;
 if(yes)etfState.compared.add(symbol);else etfState.compared.delete(symbol);
 renderEtfTracker();return true;
};
renderSameIndexETFs=function(){
 const target=$('etf-same-index'),selector=$('etf-same-index-benchmark'),f=ETF_BY_SYMBOL.get(etfState.selected);if(!target||!selector||!f)return;
 const names=[...new Set(ETF_FUNDS.map(p=>p.benchmark).filter(Boolean))].sort();selector.replaceChildren(...names.map(s=>new Option(s,s)));selector.value=f.benchmark;
 const peers=etfOriginalPeers(f);target.replaceChildren();
 if(!peers.length){target.append(el('p','note','No other exact-benchmark and hedge-label alternatives are available.'));}
 else{
  const table=el('table','watch etf-index-table'),head=el('thead'),line=el('tr');
  for(const label of ['ETF','TER','P/S','Fund AUM','1Y','3Y','5Y','Cmp'])line.append(el('th','',label));head.append(line);table.append(head);const body=el('tbody');
  for(const p of peers){const row=el('tr');row.dataset.etfAlternative=p.symbol;const first=etfCell(row,'');const button=el('button','btn',p.symbol+' · '+p.name);button.onclick=()=>etfV5Choose(p.symbol);first.append(button,el('span','secondary',(p.hedged?'Hedged '+p.hedged:'Hedge label unspecified')+' · '+(p.quote?.currency||'Quote currency unavailable')+' · '+(p.distribution||'Income unspecified')));
   etfCell(row,etfFee(p),'n');const method=etfCell(row,etfV5Kind(p)[0]);method.title=etfV5Kind(p)[1];etfCell(row,etfFundSize(p),'n');for(const y of ['1Y','3Y','5Y'])etfCell(row,etfPct(etfPerformance(p,y)),'n');
   const cell=etfCell(row,'');const check=el('input');check.type='checkbox';check.checked=etfState.compared.has(p.symbol);check.setAttribute('aria-label','Compare alternative '+p.symbol);check.onchange=()=>{if(!etfV5ChangeCompare(p.symbol,check.checked))check.checked=false;};cell.append(check);body.append(row);
  }table.append(body);target.append(table);
 }
 $('etf-same-index-note').textContent='Exact catalogue benchmark and hedge labels; unspecified issuer return variants require verification. Up to three alternatives. Returns use the selected chart basis; local currencies can differ. Main-table returns retain their recorded basis.';
 etfV5PeerLabels();
};
initEtfSameIndex=function(){const selector=$('etf-same-index-benchmark');if(selector)selector.onchange=()=>{const f=ETF_FUNDS.find(f=>f.benchmark===selector.value);if(f)etfV5Choose(f.symbol);};};
const etfOriginalDetails=etfDetails;
etfDetails=function(){
 etfOriginalDetails();renderEtfStructure();renderEtfIssuerVerified();renderSameIndexETFs();
 const f=ETF_BY_SYMBOL.get(etfState.selected);if(!f)return;
 // Keep the newer unique quote/source information inside the original text areas.
 const q=f.quote;if(q?.price!=null)$('etf-selected-meta').append(document.createTextNode(' · Last quote '+fmt(q.price,Math.abs(q.price)<2?4:2)+' '+(q.currency||'')+' · '+(q.asOf||'Quote date unavailable')+' · '+(q.source||'Source unavailable')));
 const host=$('etf-issuer-snapshot');if(host){const sources=el('p','note'),seen=new Set([$('etf-facts-link')?.href,$('etf-quote-link')?.href]);
  for(const [label,url] of [['Issuer',f.issuerVerifiedUrl||f.officialFactsUrl],['TER source',f.terUrl],['Structure',f.structureSource],['Lending policy',f.lendingPolicySource]])if(url?.startsWith('https://')&&!seen.has(url)){seen.add(url);const a=el('a','',label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';sources.append(a,document.createTextNode(' · '));}
  sources.append(document.createTextNode('Issuer checked '+(f.issuerCheckedAt||'not recorded')+' · snapshot '+(f.snapshotCapturedAt||'not recorded')));host.append(sources);
 }
};
function etfV5PickMain(){
  const all=etfFiltered();
  const groups=new Map();
  for(const f of all){const key=etfOriginalKey(f);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(f);}
  const keep=new Set();
  for(const funds of groups.values()){
    funds.sort((a,b)=> (a.terPct??Infinity)-(b.terPct??Infinity) ||
       (etfAumUSD(b)??0)-(etfAumUSD(a)??0) || a.symbol.localeCompare(b.symbol));
    // The selected ETF is always visible after choosing it in the comparison area.
    const selected=funds.find(f=>f.symbol===etfState.selected);
    const first=funds.slice(0,2);
    if(selected && !first.includes(selected))first[1]=selected;
    for(const f of first)keep.add(f.symbol);
  }
  return {all,shown:all.filter(f=>keep.has(f.symbol)),suppressed:all.length-keep.size};
}
renderEtfTracker=function(){
  const etfViewport=$('etf-rows')?.closest('.etf-table-scroll'),savedTop=etfViewport?.scrollTop||0;
  _etfV5PriorRender(); // existing risk, issuer facts, chart, data-quality links preserved
  const tbody=$('etf-rows'),table=tbody?.closest('table'),thead=table?.querySelector('thead');
  if(!tbody||!table||!thead)return;
  const labels=['Fund / ticker','TER','P/S','Fund AUM','1Y','3Y','5Y','Cmp'];
  const head=el('tr');
  for(const label of labels){const th=el('th','',label);th.scope='col';
    if(label==='TER')th.title='Annual ongoing charge. Not tracking error.';
    if(label==='Cmp')th.title='Tick to add this fund to the detailed comparison and display its expanded facts.';
    if(label==='P/S')th.title='P: physical; S: synthetic; ?: unknown. Click a fund for the exact replication detail.';
    if(['1Y','3Y','5Y'].includes(label))th.title='Annualised adjusted-close price proxy. Not certified NAV total return.';
    head.append(th);
  }
  thead.replaceChildren(head);
  const {all,shown,suppressed}=etfV5PickMain();
  const frag=document.createDocumentFragment();let lastGroup='';
  for(const f of shown){
    const region=typeof etfRegion==='function'?etfRegion(f)[2]:f.market;
    if($('etf-sort')?.value==='market'&&region!==lastGroup){
      const gr=el('tr','etf-geo-group'),th=el('th','',region||f.market);th.colSpan=8;th.scope='rowgroup';gr.append(th);frag.append(gr);lastGroup=region;
    }
    const row=el('tr',f.symbol===etfState.selected?'etf-active':'');row.dataset.etfSymbol=f.symbol;
    row.setAttribute('aria-label','View details of '+f.name);
    const name=etfCell(row,'');name.append(el('span','etf-compact-fund',f.name),el('span','etf-compact-sub',f.symbol+' · '+f.market));
    const fee=etfCell(row,etfFee(f),'n');fee.title=(f.terSource||f.terStatus||'Unverified')+(f.terCheckedAt?' · '+f.terCheckedAt:'');
    const [code,label]=etfV5Kind(f);const codecell=etfCell(row,code,'etf-compact-code');codecell.title=label+' · '+(f.replicationStatus||'unverified');
    const aum=etfCell(row,etfFundSize(f),'n');aum.title=(f.fundSizeSource||'Fund AUM unverified')+(f.fundSizeAsOf?' · '+f.fundSizeAsOf:'');
    etfCell(row,etfPct(f.return1Y),'n');etfCell(row,etfPct(f.return3Y),'n');etfCell(row,etfPct(f.return5Y),'n');
    const cell=etfCell(row,'','etf-compact-compare');
    const check=el('input');check.type='checkbox';check.checked=f.symbol===etfState.selected||etfState.compared.has(f.symbol);check.disabled=f.symbol===etfState.selected||!etfOriginalPeers(ETF_BY_SYMBOL.get(etfState.selected)).some(p=>p.symbol===f.symbol);
    check.setAttribute('aria-label','Compare '+f.symbol);check.onchange=()=>{if(!etfV5ChangeCompare(f.symbol,check.checked))check.checked=false;};cell.append(check);
    row.onclick=(e)=>{if(e.target.closest('input,button,a'))return;etfV5Choose(f.symbol);};
    frag.append(row);
  }
  tbody.replaceChildren(frag);etfViewport.scrollTop=savedTop;
  const label=$('etf-result-count');if(label)label.textContent=shown.length+' funds · '+suppressed+' same-index alternatives · 1Y/3Y/5Y annualised';
  // Older wrappers used a seven-column layout; these eight match the headers.
  // Duplicate checked-fund cards are deliberately not restored.
  renderSameIndexETFs();
  etfV5PeerLabels();
};

function etfOriginalSetup(){
 const heading=$('view-etfs')?.querySelector('.workspace-title h1'),subtitle=$('view-etfs')?.querySelector('.workspace-title span');if(heading)heading.textContent='ETF RESEARCH';if(subtitle)subtitle.textContent='TER · tracking error · country funds · equities · bonds';
 $('etf-selected-comparisons')?.remove();
 const stylesheet=$('etf-original-styles');if(stylesheet)document.head.append(stylesheet);
}
document.addEventListener('DOMContentLoaded',etfOriginalSetup);
