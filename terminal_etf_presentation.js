/* Release 2.6: presentation only; existing return/risk/FX and issuer renderers are reused. */
function etfR26Key(f){const text=[f.name,f.benchmark,f.market].join(' ');const explicit=text.match(/\b(?:GBP|USD|EUR|JPY|CHF)\s*[- ]?hedged\b/i)?.[0]||(/\bunhedged\b/i.test(text)?'unhedged':'');return etfV5Key(f)+'|'+explicit.toLowerCase().replace(/[- ]+/g,' ');}
function etfR26Region(f){
  if(f.category==='Bonds'){const order=['UK short gilts','UK gilts','UK index linked','US Treasury 0-1y','US Treasury 1-3y','US Treasury 3-7y','US Treasury 7-10y','US Treasury 20y+','US Treasury long dated','US inflation linked','EUR government 0-6m','Global government','Global inflation-linked','Global aggregate bond','Global aggregate GBP hedged','UK investment grade','USD investment grade','EUR investment grade','EUR high yield','USD high yield','EM sovereign debt','EM local currency debt','USD floating rate','Global green bonds','Global green bonds GBP hedged'];return [7,order.includes(f.market)?order.indexOf(f.market):99,'Bonds'];}
  if(f.category==='Thematic')return [8,0,'Specialist funds'];
  if(f.category==='Commodity ETC')return [9,0,'Commodities'];
  const geo=ETF_GEO[f.market];
  if(geo?.[0]===0)return [0,geo[1],'Global'];
  if(geo?.[0]===1)return [1,geo[1],'North America'];
  if(geo?.[0]===2)return [2,geo[1],'UK'];
  if(geo?.[0]===3)return [3,geo[1],'Europe'];
  if(geo?.[0]===4)return [4,geo[1],'Asia-Pacific'];
  if(geo||['South Korea','Saudi Arabia'].includes(f.market))return [5,geo?.[1]??99,'Emerging Markets'];
  return [6,0,'Other markets'];
}
function etfR26VerifiedAum(f){return Number.isFinite(f.fundSize)&&f.fundSize>=0&&!!f.fundSizeCurrency&&/issuer|audited/i.test(f.fundSizeSource||'')&&!f.identifierWarning&&!f.auditIsinConflict&&!/fallback|unverified|not independently/i.test(f.fundSizeStatus||'');}
function etfR26Size(f){return f.fundSize===0&&f.fundSizeCurrency?f.fundSizeCurrency+' 0':etfFundSize(f)==='—'?'Unavailable':etfFundSize(f);}
function etfR26Priority(a,b){
  const verified=Number(etfR26VerifiedAum(b))-Number(etfR26VerifiedAum(a));if(verified)return verified;
  const x=etfR26VerifiedAum(a)?etfAumUSD(a):null,y=etfR26VerifiedAum(b)?etfAumUSD(b):null;
  if((x!=null)!==(y!=null))return x!=null?-1:1;
  if(x!=null&&y!=null&&x!==y)return y-x;
  const fee=(a.terPct??Infinity)-(b.terPct??Infinity);if(!Number.isNaN(fee)&&fee)return fee;
  const coverage=f=>['return1Y','return3Y','return5Y'].filter(k=>Number.isFinite(f[k])).length+Number((ETF_HISTORY.get(f.symbol)||[]).length>1);
  return coverage(b)-coverage(a)||a.symbol.localeCompare(b.symbol);
}
function etfR26Alternatives(f){
  if(!f.benchmark)return [];
  const seen=new Set([f.isin||f.symbol]);
  return ETF_FUNDS.filter(p=>p.symbol!==f.symbol&&etfR26Key(p)===etfR26Key(f)).sort(etfR26Priority).filter(p=>{const id=p.isin||p.symbol;if(seen.has(id))return false;seen.add(id);return true;}).slice(0,3);
}
function etfR26Choose(symbol){
  const f=ETF_BY_SYMBOL.get(symbol);if(!f)return;
  etfState.selected=symbol;const allowed=new Set(etfR26Alternatives(f).map(p=>p.symbol));
  etfState.compared=new Set([...etfState.compared].filter(s=>allowed.has(s)).slice(0,3));
  renderEtfTracker();
}
etfV5Choose=etfR26Choose;
function etfR26Compare(symbol,checked){
  const f=ETF_BY_SYMBOL.get(etfState.selected),allowed=etfR26Alternatives(f).some(p=>p.symbol===symbol);
  if(!allowed||checked&&!etfState.compared.has(symbol)&&etfState.compared.size>=3)return false;
  if(checked)etfState.compared.add(symbol);else etfState.compared.delete(symbol);
  etfDrawChart();return true;
}
renderSameIndexETFs=function(){
  const f=ETF_BY_SYMBOL.get(etfState.selected),host=$('etf-r26-alternatives');if(!f||!host)return;
  host.replaceChildren(el('h3','','EXACT-BENCHMARK ALTERNATIVES'));
  host.append(el('p','mini',(f.benchmark||'Benchmark unavailable')+' · '+(f.hedged?'Hedged: '+f.hedged:'Hedge not specified in catalogue')+' · '+$('etf-basis').selectedOptions[0].textContent));
  host.append(el('p','mini','Exact catalogue labels only; where the issuer return variant or hedge is unspecified, verify it before treating funds as equivalent.'));
  const peers=etfR26Alternatives(f);
  if(!peers.length){host.append(el('p','note','No other exact-benchmark and matching hedge-label funds are available. Different benchmark variants are excluded.'));return;}
  const table=el('table','watch etf-r26-comparison'),head=el('thead'),tr=el('tr');
  ['Alternative fund / ticker','TER','P/S','Fund size','1Y ann.','3Y ann.','5Y ann.','Chart'].forEach((t,i)=>tr.append(el('th',i?'n':'',t)));head.append(tr);table.append(head);
  const body=el('tbody');for(const p of peers){const row=el('tr');row.dataset.etfAlternative=p.symbol;
    const name=etfCell(row,'');const select=el('button','etf-fund-link',p.name+' · '+p.symbol);select.type='button';select.onclick=()=>etfR26Choose(p.symbol);name.append(select,el('div','mini',(p.distribution||'Income unverified')+' · quote '+(p.quote?.currency||'unavailable')));
    etfCell(row,etfFee(p),'n');const method=etfCell(row,etfV5Kind(p)[0]);method.title=etfV5Kind(p)[1];method.append(el('div','mini',etfV5Kind(p)[1]));
    const size=etfCell(row,etfR26Size(p),'n');size.append(el('div','mini',p.fundSizeAsOf||'AUM date unavailable'));
    for(const period of ['1Y','3Y','5Y'])etfCell(row,etfPct(etfPerformance(p,period)),'n');
    const cell=etfCell(row,'');const check=el('input');check.type='checkbox';check.checked=etfState.compared.has(p.symbol);check.setAttribute('aria-label','Compare '+p.symbol);check.onchange=()=>{if(!etfR26Compare(p.symbol,check.checked))check.checked=false;};cell.append(check);body.append(row);
  }table.append(body);host.append(table);
};
const etfR26OriginalChart=etfDrawChart;
etfDrawChart=function(){const f=ETF_BY_SYMBOL.get(etfState.selected);if(f){const allowed=new Set(etfR26Alternatives(f).map(p=>p.symbol));etfState.compared=new Set([...etfState.compared].filter(s=>allowed.has(s)).slice(0,3));}etfR26OriginalChart();let legend=$('etf-r26-legend');if(!legend){legend=el('div','r25-chart-legend');legend.id='etf-r26-legend';$('etf-chart').after(legend);}legend.replaceChildren();
  const shown=[etfState.selected,...etfState.compared].filter(s=>{const p=ETF_BY_SYMBOL.get(s);return p&&etfRows(p).length>1;});if($('etf-chart').querySelector('svg'))shown.forEach((symbol,i)=>{const label=el('span','',symbol);label.style.borderLeft='3px solid '+['#ffa028','#5caeff','#60d5ce','#c6a0ff'][i];legend.append(label);});if($('etf-reference').checked&&$('etf-chart').querySelector('svg')){const reference=etfReference(f);if(reference?.points.length>1){const label=el('span','',reference.name);label.style.borderLeft='3px solid '+['#ffa028','#5caeff','#60d5ce','#c6a0ff','#ff6f91'][shown.length];legend.append(label);}}
};
const etfR26OriginalDetails=etfDetails;
etfDetails=function(){
  etfR26OriginalDetails();renderEtfStructure();renderEtfIssuerVerified();
  const f=ETF_BY_SYMBOL.get(etfState.selected);if(!f)return;
  // One authoritative current AUM/replication/spread tile; keep distinct dated audit facts.
  for(const [host,labels] of [[$('etf-detail-stats'),['Fund assets (AUM)','Bid-offer spread']],[$('etf-structure-stats'),['Replication type']]]){
    for(const tile of host?.querySelectorAll('.etf-stat')||[])if(labels.includes(tile.querySelector('.k')?.textContent))tile.remove();
  }
  if(f.quote?.price!=null)etfStatistic($('etf-detail-stats'),'Last quotation',fmt(f.quote.price,Math.abs(f.quote.price)<2?4:2)+' '+(f.quote.currency||''),(f.quote.asOf||'Date unavailable')+' · '+(f.quote.source||'Source unavailable'));
  for(const tile of $('etf-risk-stats').querySelectorAll('.etf-stat'))if(tile.querySelector('.k')?.textContent==='Tracking difference')tile.remove();
  const size=[...$('etf-detail-stats').querySelectorAll('.etf-stat')].find(t=>t.querySelector('.k')?.textContent==='Fund size');
  if(size){size.querySelector('.v').textContent=etfR26Size(f);size.querySelector('.d').textContent=(f.fundSizeSource||'Source unavailable')+' · '+(f.fundSizeAsOf||'AUM observation date unavailable')+' · checked '+(f.fundSizeCheckedAt||'not recorded');}
  const snapshot=$('etf-issuer-snapshot');const repeated=snapshot?.querySelector(':scope > p.note');if(repeated){repeated.textContent=(f.snapshotIssuer||'Issuer not supplied')+' · snapshot '+(f.snapshotCapturedAt||'not recorded')+(f.fundSize!=null&&!f.fundSizeAsOf?' · AUM observation date unconfirmed':'');}
  // Preserve source links together, including fields formerly repeated in issuer paragraphs.
  let sources=$('etf-r26-sources');if(!sources){sources=el('p','note');sources.id='etf-r26-sources';snapshot?.append(sources);}sources.replaceChildren();
  const seen=new Set();for(const [label,url] of [['Issuer facts',f.issuerVerifiedUrl||f.officialFactsUrl||f.issuerFactsUrl],['TER source',f.terUrl],['Structure',f.structureSource],['Lending policy',f.lendingPolicySource]])if(url?.startsWith('https://')&&!seen.has(url)){seen.add(url);sources.append(r24Link(label,url),document.createTextNode(' · '));}
  sources.append(document.createTextNode('Issuer checked '+(f.issuerCheckedAt||f.snapshotCapturedAt||'not recorded')+' · '+(f.replicationStatus||'Replication unverified')+' · snapshot '+(f.snapshotCapturedAt||'not recorded')+' · '+(f.snapshotIssuer||f.issuerProvider||'Issuer not recorded')));
  renderSameIndexETFs();
};
renderEtfTracker=function(){
  if(!$('etf-rows'))return;
  for(const id of ['etf-index-comparison','etf-selected-comparisons'])$(id)?.remove();
  if(!$('etf-r26-alternatives')){const section=el('section','etf-peer-box');section.id='etf-r26-alternatives';$('etf-risk-stats').before(section);}
  const coverage=ETF_DATA.coverage||{};$('etf-coverage').textContent=ETF_FUNDS.length+' catalogue funds · '+(coverage.quoted||0)+' quoted · '+(coverage.withHistory||0)+' histories';
  $('etf-stats').replaceChildren();
  let picker=$('etf-r26-pick');if(!picker){const label=el('label','mini','SELECT FROM COMPLETE CATALOGUE ');picker=el('select','field');picker.id='etf-r26-pick';picker.setAttribute('aria-label','Select ETF from complete catalogue');label.append(picker);$('etf-result-count').parentElement.before(label);picker.onchange=()=>etfR26Choose(picker.value);}
  const filtered=etfFiltered();picker.replaceChildren(...filtered.map(f=>new Option(f.name+' · '+f.symbol,f.symbol)));picker.value=etfState.selected;
  const groups=new Map();for(const f of filtered){const key=etfR26Key(f);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(f);}
  const ordered=[...groups.values()].sort((a,b)=>{const x=etfR26Region(a[0]),y=etfR26Region(b[0]);return x[0]-y[0]||x[1]-y[1]||a[0].market.localeCompare(b[0].market)||etfR26Key(a[0]).localeCompare(etfR26Key(b[0]));});
  const body=$('etf-rows');body.replaceChildren();const head=el('tr');['Fund / ticker','TER','P/S','Fund size','1Y ann.','3Y ann.','5Y ann.'].forEach((t,i)=>head.append(el('th',i?'n':'',t)));body.closest('table').tHead.replaceChildren(head);
  let region='',shown=0;
  for(const funds of ordered){const f=funds[0],geo=etfR26Region(f);if(geo[2]!==region){region=geo[2];const row=el('tr','etf-geo-group'),th=el('th','',region);th.colSpan=7;th.scope='rowgroup';row.append(th);body.append(row);}
    const group=el('tr','etf-benchmark-group'),title=el('th','',f.market+' · '+(f.benchmark||'Benchmark unverified')+(f.hedged?' · '+f.hedged+' hedged':''));title.colSpan=7;title.scope='rowgroup';group.append(title);body.append(group);
    const selected=funds.slice().sort(etfR26Priority).slice(0,2),order=new Map(filtered.map((f,i)=>[f.symbol,i]));selected.sort((a,b)=>order.get(a.symbol)-order.get(b.symbol));
    for(const fund of selected){const row=el('tr',fund.symbol===etfState.selected?'etf-active':'');row.dataset.etfSymbol=fund.symbol;row.dataset.benchmarkKey=etfR26Key(fund);row.dataset.regionOrder=geo[0];
      const name=etfCell(row,'');const select=el('button','etf-fund-link',fund.name);select.type='button';select.onclick=()=>etfR26Choose(fund.symbol);name.append(select,el('div','mini',fund.symbol));
      const fee=etfCell(row,etfFee(fund),'n');fee.title=(fund.terSource||'Unverified')+' · '+(fund.terCheckedAt||'Date unavailable');
      const kind=etfCell(row,etfV5Kind(fund)[0]);kind.title=etfV5Kind(fund)[1];
      const size=etfCell(row,etfR26Size(fund),'n');size.title=(fund.fundSizeSource||'Source unavailable')+' · '+(fund.fundSizeAsOf||'AUM date unavailable');
      for(const key of ['return1Y','return3Y','return5Y'])etfCell(row,etfPct(fund[key]),'n');body.append(row);shown++;
    }
  }
  $('etf-result-count').textContent=shown+' main-table funds / '+filtered.length+' catalogue matches · at most two per exact benchmark and hedge label';
  etfDetails();
};
// Cross-market values reuse the existing observations and definitions; only their layout changes.
intelligenceConditions=function(host){
  const rows=[];
  for(const [label,series,key] of [['UK 10Y',D.uk_rates,'gilt10y'],['US 10Y',D.us_rates,'DGS10'],['Euro-area 10Y',D.eu_rates,'eur10y']]){
    const valid=(series||[]).filter(x=>Number.isFinite(x[key])),last=valid.at(-1),prev=valid.at(-2);
    if(last)rows.push([label,fmt(last[key],2)+'%',prev?fmt((last[key]-prev[key])*100,1)+' bp since '+prev.date:'Unavailable',last.date]);
  }
  const us=latestField(D.us_rates,'DGS10'),two=latestField(D.us_rates,'DGS2');if(us&&two&&us.date===two.date)rows.push(['US 10Y − 2Y',fmt((us.DGS10-two.DGS2)*100,1)+' bp','Yield-curve slope',us.date]);
  for(const [symbol,label] of [['^GSPC','S&P 500'],['^VIX','VIX']]){const q=qMap.get(symbol);if(q)rows.push([label,fmt(q.price,2),pc(q.changePct),q.asOf||'Unavailable']);}
  for(const b of (D.marketAnalytics?.breadth||[]).slice(0,2))rows.push([b.name+' breadth',b.advancers+' advancing / '+b.decliners+' declining',b.quoted+'/'+b.members+' quoted',b.date]);
  for(const c of (D.credit_spreads||[]).filter(c=>['US_IG','US_HY'].includes(c.key)))rows.push([c.name,fmt(c.latestBp,0)+' bp','1M '+fmt(c.change30Bp,0)+' bp',c.date]);
  r24Table(host,['Indicator','Observation','Change / context','Date'],rows,'r26-conditions');
  host.append(el('p','note','Observed comparisons; no causal inference. Verified point-in-time concentration weights are unavailable. Full breadth, credit and curve analysis remains in Markets Analytics and Bonds & Rates.'));
};
const r26PriorOverview=r24Overview;
r24Overview=function(){
  r26PriorOverview();
  const universe=new Set((D.movers||[]).flatMap(m=>(m.constituents||[]).map(x=>x.symbol))),leading=new Set((D.marketBriefing?.leadingItems||[]).filter(x=>x.classification==='observed_market_movement').map(x=>x.title));
  const panel=$('r23-moves'),body=panel?.querySelector('.r23-body');if(body){body.replaceChildren();const unique=(D.marketBriefing?.movements||[]).filter(q=>!universe.has(q.symbol)&&![...leading].some(title=>title.startsWith((q.name||q.symbol)+':')));
    unique.forEach(q=>body.append(el('div','r23-observation',(q.name||q.symbol)+' '+pc(q.changePct)+' · '+q.asOf)));panel.hidden=!unique.length;
  }
  // Only verified material watchlist developments appear in the short Overview.
  const watch=$('r24-watch')?.querySelector('.r24-content')||$('r24-watch')?.lastElementChild;
  if(watch){for(const article of [...watch.querySelectorAll('article')]){const link=article.querySelector('a'),item=(D.news||[]).find(n=>n.url===link?.href);
    if(item&&!(item.significanceEvidence?.length||item.official&&item.developmentStatus==='confirmed_event'))article.remove();}
    if(!watch.querySelector('article')){watch.replaceChildren(el('p','note','No material current watchlist development is verified. Full company news and risk statistics remain in My Watchlist and Markets.'));}
  }
};
const r26PriorPolicy=r24SelectivePresentation;
r24SelectivePresentation=function(root=document){
  r26PriorPolicy(root);
  // Charts with no plotted observations become compact coverage notices, not blank graphics.
  for(const chart of root.querySelectorAll('.research-view .chart')){
    const empty=!chart.querySelector('svg');chart.classList.toggle('r26-empty-chart',empty);
  }
  const c=ensureCompany(state.companySymbol),kpis=$('company-kpis');
  if(c&&kpis){const raw={};for(const [key,value] of [['SHARE PRICE',c.price],['TRAILING P/E',c.trailingPE>0?c.trailingPE:null],['EV / EBITDA',!researchIsFinancial(c)&&c.enterpriseToEbitda>0?c.enterpriseToEbitda:null]])raw[key]=value;
    for(const tile of kpis.querySelectorAll('.company-kpi')){const title=tile.querySelector('.k,.lab')?.textContent?.trim();if(Object.hasOwn(raw,title)&&Number.isFinite(raw[title]))tile.remove();}
  }
};
