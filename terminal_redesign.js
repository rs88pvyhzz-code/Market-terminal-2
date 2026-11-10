/* Release 2.4: presentation only. MT_DATA and all calculation functions stay intact. */
function r24Table(host, headings, rows, cls='') {
  const table=el('table','watch r24-table '+cls),head=el('thead'),line=el('tr');
  headings.forEach((text,i)=>line.append(el('th',i?'':'r24-name',text)));head.append(line);table.append(head);
  const body=el('tbody');for(const cells of rows){const tr=el('tr');for(const value of cells){const td=el('td');if(value instanceof Node)td.append(value);else td.textContent=String(value??'Unavailable');tr.append(td);}body.append(tr);}table.append(body);host.append(table);return table;
}
function r24Section(id,title,parent) {
  let node=$(id);if(!node){node=el('section','panel r24-section');node.id=id;node.append(el('h2','',title),el('div','r24-content'));parent.append(node);}
  node.lastElementChild.replaceChildren();return node.lastElementChild;
}
function r24Link(title,url){const a=el('a','',title);if(String(url||'').startsWith('https://')){a.href=url;a.target='_blank';a.rel='noopener noreferrer';}return a;}
function r24VisibleSection(detail) {
  // Used only for named decision content/basic controls or inner support headings.
  const section=el('section',detail.className+' r24-support');
  for(const a of detail.attributes)if(!['class','open','data-r24-policy'].includes(a.name))section.setAttribute(a.name,a.value);
  for(const child of [...detail.childNodes]){
    if(child.nodeName==='SUMMARY'){const h=el('h3','r24-support-heading');h.append(...child.childNodes);section.append(h);}
    else section.append(child);
  }
  detail.replaceWith(section);return section;
}
function r24SelectivePresentation(root=document) {
  // Only exceptions and technical audits are disclosures. Facts, sources and models stay direct.
  for(const detail of [...root.querySelectorAll('details')]){
    const title=detail.querySelector(':scope > summary')?.textContent||'';
    const diagnostic=detail.closest('#view-quality')||/^(Source status|Failed requests|Technical diagnostics|Retrieval diagnostics)/i.test(title);
    if(diagnostic){
      detail.dataset.r25Disclosure='diagnostic';
      if(!detail.dataset.r24Policy){detail.open=false;detail.dataset.r24Policy='diagnostic';}
    }else r24VisibleSection(detail);
  }
  for(const inner of [...root.querySelectorAll('details details')].reverse())r24VisibleSection(inner);
  for(const warning of root.querySelectorAll('.research-warning,.phase-warning,.err')){
    const disclosure=warning.closest('details');if(disclosure)disclosure.before(warning);
  }
  for(const view of root.querySelectorAll('.research-view')){
    const seen=new Set();for(const note of view.querySelectorAll('p.note')){
      const key=note.textContent.trim()+'|'+[...note.querySelectorAll('a')].map(a=>a.href).join('|');
      if(key&&seen.has(key))note.remove();else seen.add(key);
    }
  }
  const overview=$('research-overview'),view=$('research-view-0');
  if(overview&&view){const support=[...overview.children].filter(n=>n.matches('section.r24-support'));
    if(support.length){view.querySelectorAll(':scope > [data-r25-owner]').forEach(n=>n.remove());for(const node of support){node.dataset.r25Owner='overview';view.append(node);}}
  }
  // Workings stay direct, below the decision results and basic controls.
  const valuation=$('research-valuation');if(valuation){
    const bridge=[...valuation.children].find(n=>/Normalised FCFF calculation/.test(n.querySelector(':scope > h3')?.textContent||''));
    if(bridge&&valuation.lastElementChild!==bridge)valuation.append(bridge);
    for(const projected of valuation.querySelectorAll('section.r24-support')){
      if(/^Projected FCFF/.test(projected.querySelector(':scope > h3')?.textContent||'')){
        const parent=projected.parentElement;if(parent.lastElementChild!==projected)parent.append(projected);
      }
    }
  }
  r25SectionLinks();
}
function r25SectionLinks(){
  for(const host of document.querySelectorAll('.research-view,#subview-fx-prices,#view-economics')){
    const all=[...host.querySelectorAll('h2,h3')].filter(h=>!h.closest('details')&&!h.closest('[hidden]')&&!/rules|methodology|coverage|source register|snapshot metrics|evidence that would/i.test(h.textContent));
    const headings=all.slice(0,7),source=all.find(h=>/Field-level sources|Source documents|Valuation sources/i.test(h.textContent));if(source&&!headings.includes(source))headings.splice(6,1,source);
    let nav=host.querySelector(':scope > .r25-section-links');
    const signature=headings.map(h=>h.textContent).join('|');
    if(nav?.dataset.signature===signature)continue;
    if(!nav){nav=el('nav','r25-section-links');nav.setAttribute('aria-label','Jump to section');host.prepend(nav);}
    nav.dataset.signature=signature;nav.replaceChildren();nav.hidden=headings.length<3;
    headings.forEach((h,i)=>{if(!h.id)h.id=host.id+'-section-'+i;const text=h.textContent.trim().split(' · ')[0];const a=el('a','',text.length>38?text.slice(0,35)+'…':text);a.title=h.textContent;a.href='#'+h.id;a.onclick=e=>{e.preventDefault();h.scrollIntoView({block:'start'});};nav.append(a);});
  }
}
function r24Fresh(item){return !intelligenceArchived(item);}
function r24Item(host,item,label){
  const row=el('article','r24-item');row.append(item.url?r24Link(item.title,item.url):el('strong','',item.title));
  row.append(el('div','mini',[label,item.published,item.source].filter(Boolean).join(' · ')));host.append(row);return row;
}
function r24CalendarEvents(){
  const today=D.generatedAt.slice(0,10),seen=new Set();
  return (D.calendar||[]).filter(e=>{const key=[e.date,e.region,e.title,e.time].join('|');if(!e.date||e.date<today||seen.has(key))return false;seen.add(key);return true;}).slice().sort((a,b)=>a.date.localeCompare(b.date)||String(a.time||'zz').localeCompare(String(b.time||'zz'))||a.region.localeCompare(b.region));
}
function r24MajorEvent(e){return /inflation|consumer price|\bcpi\b|\bgdp\b|gross domestic|employment|payroll|wages|retail sales|monetary policy|bank rate|interest rate|fomc|policy decision/i.test(e.title||'');}
function r24Value(x){return x===null||x===undefined||x===''?'Unavailable':typeof x==='number'?fmt(x,2):String(x);}
function r24CalendarTable(host,events,overview=false){
  const rows=events.map(e=>{
    const source=r24Link(e.source||'Official calendar',e.url);
    const forecast=e.forecastSource||e.forecastSourceUrl?r24Value(e.forecast):'Unavailable';
    return overview?[e.date+' · '+(e.time||'Time unavailable'),e.region==='EU'?'Euro area':e.region,r24Link(e.title,e.url),r24Value(e.previous),forecast]:[e.date,e.time||'Unavailable',e.region==='EU'?'Euro area':e.region,r24Link(e.title,e.url),r24Value(e.previous),forecast,r24Value(e.actual),source];
  });
  const table=r24Table(host,overview?['Date / time','Country','Indicator','Previous','Forecast']:['Date','Time','Country','Indicator','Previous','Forecast','Actual','Source'],rows,'r24-calendar-table');
  events.forEach((e,i)=>{if(r24MajorEvent(e))table.tBodies[0].rows[i].classList.add('r24-major-event');});
  if(!events.length)host.append(el('p','note','No verified scheduled releases are available for this selection.'));
}
function r24Conditions(host){
  const vix=qMap.get('^VIX'),breadth=D.marketAnalytics?.breadth||[],credit=(D.credit_spreads||[]).filter(x=>['US_IG','US_HY'].includes(x.key));
  const list=values=>{const box=el('div');if(!values.length)box.textContent='Unavailable';values.forEach(value=>box.append(el('div','r24-line',value)));return box;};
  const uk=(D.uk_rates||[]).filter(x=>Number.isFinite(x.gilt10y)),us=(D.us_rates||[]).filter(x=>Number.isFinite(x.DGS10)),u=uk.at(-1),p=uk.at(-2),s=us.at(-1),t=us.at(-2),two=latestField(D.us_rates,'DGS2');
  const curve=s&&two&&s.date===two.date?((s.DGS10-two.DGS2)*100).toFixed(1)+' bp':'Unavailable';
  r24Table(host,['Indicator','Latest observation','Change / context','Observation date'],[
    ['Volatility',vix?'VIX '+fmt(vix.price,2):'Unavailable',vix?pc(vix.changePct):'Unavailable',vix?.asOf||'Unavailable'],
    ['Market breadth',list(breadth.map(b=>b.name+': '+b.advancers+' advancing / '+b.decliners+' declining')),list(breadth.map(b=>b.quoted+'/'+b.members+' quoted; above 200D '+b.above200+'/'+b.eligible200)),list(breadth.map(b=>b.name+' '+b.date))],
    ['Sovereign yields / curve',list([u?'UK 10Y '+fmt(u.gilt10y,2)+'%':'UK unavailable',s?'US 10Y '+fmt(s.DGS10,2)+'%':'US unavailable']),list([u&&p?'UK '+fmt((u.gilt10y-p.gilt10y)*100,1)+' bp since '+p.date:'UK change unavailable',s&&t?'US '+fmt((s.DGS10-t.DGS10)*100,1)+' bp since '+t.date:'US change unavailable','US 10Y−2Y '+curve]),list([u?'UK '+u.date:'UK date unavailable',s?'US '+s.date:'US date unavailable'])],
    ['Credit spreads',list(credit.map(c=>c.name+' '+fmt(c.latestBp,0)+' bp')),list(credit.map(c=>c.name+' 1M '+fmt(c.change30Bp,0)+' bp')),list(credit.map(c=>c.name+' '+c.date))]
  ],'r24-conditions-table');
}
function r24Snapshot(){
  const host=$('market-pulse');if(!host)return;host.replaceChildren();
  for(const [symbol,label] of [['^FTSE','FTSE 100'],['^GSPC','S&P 500'],['^IXIC','Nasdaq Composite'],['UK10','UK 10Y gilt yield'],['GBPUSD=X','GBP/USD'],['BZ=F','Brent crude'],['^VIX','VIX']]){
    const tile=el('button','r24-snapshot-item'),q=qMap.get(symbol),rows=(D.uk_rates||[]).filter(x=>Number.isFinite(x.gilt10y)),last=rows.at(-1),prior=rows.at(-2);
    tile.type='button';tile.setAttribute('aria-label','Open '+(symbol==='^VIX'?'VIX':label));tile.onclick=()=>symbol==='UK10'?activateWorkspace('bonds'):marketInstrument(symbol);
    tile.append(el('div','lab',label+(symbol==='BZ=F'&&q?.currency?' · '+q.currency:'')));
    if(symbol==='UK10')tile.append(el('strong','',last?fmt(last.gilt10y,2)+'%':'Unavailable'),el('div','mini',last&&prior?fmt((last.gilt10y-prior.gilt10y)*100,1)+' bp since '+prior.date:'Change unavailable'),el('div','mini',last?.date||'Date unavailable'));
    else tile.append(el('strong','',q?fmt(q.price,symbol==='GBPUSD=X'?4:2):'Unavailable'),el('div',q?.changePct>0?'pos':q?.changePct<0?'neg':'mini',q?pc(q.changePct):'Change unavailable'),el('div','mini',(symbol==='^VIX'?'Index points · ':'')+(q?.asOf||'Date unavailable')));
    host.append(tile);
  }
  let sources=$('r24-snapshot-sources');if(!sources){sources=el('div','mini');sources.id='r24-snapshot-sources';$('overview-board').append(sources);}sources.replaceChildren(r24Link('Market quotes: Yahoo Finance','https://finance.yahoo.com/'),document.createTextNode(' · '),r24Link('UK yield: Bank of England','https://www.bankofengland.co.uk/boeapps/database/'));
  let warning=$('r24-snapshot-warning');if(!warning){warning=el('p','research-warning');warning.id='r24-snapshot-warning';$('overview-board').append(warning);}const issues=(D.marketBriefing?.alerts||[]).filter(x=>x.kind==='Coverage').map(x=>x.title+' · '+x.date);
  const age=Date.now()-Date.parse(D.generatedAt.replace(' UTC','Z').replace(' ','T'));if(age>(D.marketBriefing?.thresholds?.criticalMaxAgeDays||5)*86400000)issues.unshift('Scheduled snapshot is stale; source dates below are historical.');warning.textContent=issues.join(' · ');warning.hidden=!issues.length;
  $('overview-board').querySelector('h2').textContent='GLOBAL MARKET SNAPSHOT';
  $('overview-board').querySelector('.row .mini')?.remove();$('overview-board').querySelector('.r23-shortcuts')?.remove();$('overview-board').querySelector('.pulse-warning')?.remove();
}
function r24Overview(){
  const parent=$('view-overview');if(!parent)return;r24Snapshot();
  let host=r24Section('r24-developments','KEY MARKET DEVELOPMENTS',parent);const choices=[],seen=new Set(),briefing=D.marketBriefing||{};
  const recent=Date.now()-Date.parse(D.generatedAt.replace(' UTC','Z').replace(' ','T'))<=(briefing.thresholds?.criticalMaxAgeDays||5)*86400000;
  for(const item of recent?(briefing.leadingItems||[]):[]){
    const q=(D.quotes||[]).find(q=>item.title.startsWith((q.name||q.symbol)+':'));
    const majorMove=item.classification==='observed_market_movement'&&q&&['index','fx','future','volatility'].includes(q.kind);
    const primaryEvent=item.classification==='confirmed_event'&&item.marketMoving;
    if(majorMove||primaryEvent){choices.push(item);seen.add(item.id);}
  }
  for(const alert of recent?(briefing.alerts||[]):[]){const q=(D.quotes||[]).find(q=>alert.title.startsWith((q.name||q.symbol)+':'));
    if(alert.kind==='Calculated'&&!seen.has(alert.id)&&(['Bonds','Credit','FX','Commodities','Volatility'].includes(alert.assetClass)||q?.kind==='index')){choices.push({...alert,published:alert.date,classification:'observed_market_movement'});seen.add(alert.id);}}
  for(const story of D.news||[]){if(!r24Fresh(story)||seen.has(story.id)||!story.significanceEvidence?.length)continue;
    if(story.official||story.significanceEvidence.some(s=>s.includes('>=1 billion'))){choices.push(story);seen.add(story.id);}}
  choices.slice(0,3).forEach(x=>r24Item(host,x,x.classification==='observed_market_movement'?'Observed major-market movement':(x.official||x.classification==='confirmed_event')?'Official announcement':'Reported material development'));
  if(!choices.length)host.append(el('p','note','No material macro or major-market development is verified by this snapshot. Individual share moves remain in Markets.'));
  host=r24Section('r24-conditions','MARKET CONDITIONS',parent);r24Conditions(host);
  host=r24Section('r24-watch','MY WATCHLIST',parent);
  const names=(D.personalWatchlist||[]).map(w=>w.name.replace(/\b(plc|inc|corporation|corp|limited|ltd|holdings|ag|se)\b.*$/i,'').trim().toLowerCase());
  const watch=[];for(const item of recent?(briefing.leadingItems||[]):[]){if(item.classification==='observed_market_movement'&&names.some(n=>n.length>2&&item.title.toLowerCase().startsWith(n)))watch.push(item);}
  for(const item of D.news||[]){if(r24Fresh(item)&&item.categories?.includes('watchlist')&&['confirmed_event','reported_development'].includes(item.developmentStatus)&&!seen.has(item.id))watch.push(item);}
  const watchSeen=new Set();watch.filter(x=>!watchSeen.has(x.id)&&watchSeen.add(x.id)).slice(0,2).forEach(x=>r24Item(host,x,x.classification==='observed_market_movement'?'Exceptional observed movement':x.official?'Official announcement':'Reported company development'));
  if(!watch.length)host.append(el('p','note','No current important watchlist development is verified. Detailed news and individual risk statistics remain in My Watchlist.'));
  host=r24Section('r24-upcoming','UPCOMING ECONOMIC EVENTS',parent);r24CalendarTable(host,r24CalendarEvents().filter(r24MajorEvent).slice(0,3),true);
  for(const id of ['overview-board','r24-developments','r24-conditions','r24-watch','r24-upcoming'])if($(id))parent.append($(id));
  const markets=$('subview-fx-prices');if(markets){for(const id of ['monitor','r23-moves','movers','r23-market-conditions','r23-alerts','r23-watch','headline'])if($(id))markets.append($(id));}
  const newsView=$('subview-fx-news');if(newsView&&$('news'))newsView.append($('news'));
  // The duplicate tile snapshot contains exactly the quote values in Markets' price table.
  if($('headline'))$('headline').replaceChildren();
  $('r23-snapshot-detail')?.remove();$('r23-conditions')?.remove();$('r23-calendar')?.remove();
  for(const id of ['r23-alerts','r23-watch'])if($(id))$(id).querySelector('h2').textContent=id==='r23-alerts'?'FULL DAILY BRIEFING & RESEARCH ALERTS':'WATCHLIST NEWS REFERENCES';
  const cal=$('calendar');if(cal&&$('r23-calendar'))cal.append($('r23-calendar'));
}
const r24OldBriefing=renderMarketBriefing;
renderMarketBriefing=function(){r24OldBriefing();r24Overview();};
renderPulse=r24Snapshot;
renderIntelligenceNews=function(){
  const host=$('news-list'),pills=$('news-pills');if(!host||!pills)return;host.replaceChildren();pills.replaceChildren();
  for(const [key,label] of [['all','All subjects'],...Object.entries(intelligenceCategories)]){const b=el('button','btn'+(key===intelligenceCategory?' active':''),label);b.onclick=()=>{intelligenceCategory=key;renderIntelligenceNews();};pills.append(b);}
  const regions=el('div','r23-regions');for(const region of ['All','UK','US','Europe','Global']){const b=el('button','btn'+(region===intelligenceRegion?' active':''),region==='All'?'All regions':region);b.onclick=()=>{intelligenceRegion=region;renderIntelligenceNews();};regions.append(b);}pills.append(regions);
  const rows=(D.news||[]).filter(x=>(intelligenceCategory==='all'||x.categories?.includes(intelligenceCategory))&&(intelligenceRegion==='All'||x.regions?.includes(intelligenceRegion)));
  for(const item of rows){const row=r24Item(host,item,(item.official?'Official announcement':'Third-party reporting')+(r24Fresh(item)?'':' · ARCHIVED'));
    row.dataset.eventId=item.id;row.append(el('div','mini','Retrieved '+(item.retrievedAt||'date not recorded')));
    if(item.significanceEvidence?.length)row.append(el('div','mini',item.significanceEvidence.join(' · ')));
    const links=new Set([item.url]);for(const other of item.coverage||[])if(!links.has(other.url)){links.add(other.url);row.append(r24Link('Also reported by '+other.source+' · '+other.published+' · retrieved '+(other.retrievedAt||'date not recorded'),other.url));}
  }
  if(!rows.length)host.append(el('p','note',intelligenceCategory==='market_moving'?'No sourced headline meets the strict Market Moving criteria. Observed movement alerts remain above.':'No current coverage for this subject and region.'));
  $('news-stamp').textContent='Scheduled snapshot '+D.generatedAt+' · publication and retrieval dates shown separately';
  $('news').querySelector('h2').textContent='NEWS BY SUBJECT & REGION';
};
renderCalendar=function(){
  const host=$('calendar-items'),filters=$('calendar-filters');if(!host||!filters)return;host.replaceChildren();filters.replaceChildren();
  for(const [key,label] of [['ALL','All regions'],['UK','UK'],['EU','Euro area'],['US','US']]){const b=el('button','btn'+(state.calendarRegion===key?' active':''),label);b.onclick=()=>{state.calendarRegion=key;renderCalendar();};filters.append(b);}
  r24CalendarTable(host,r24CalendarEvents().filter(e=>state.calendarRegion==='ALL'||e.region===state.calendarRegion));
  $('mt-calendar-tip')?.remove();
};
const r24OldPaint=paintWorkspace;
paintWorkspace=function(key){if(key==='fx'&&terminalSubSelection.fx==='news'){renderMarketBriefing();renderNews();}else r24OldPaint(key);if(key==='fx'){renderNews();if(terminalSubSelection.fx==='analytics'){renderBreadth();renderSectors();}}r24SelectivePresentation();};
intelligenceCategory='all';
function r24Setup(){
  document.documentElement.classList.add('release24');const sheet=$('release24-styles');if(sheet)document.head.append(sheet);r24Overview();renderNews();renderCalendar();r24SelectivePresentation();
  // Apply the same selective policy to later company, ETF and diagnostic renders.
  new MutationObserver(records=>{if(records.some(r=>[...r.addedNodes].some(n=>n.nodeType===1&&(n.matches('details')||n.querySelector('details')))))r24SelectivePresentation();}).observe(document.body,{childList:true,subtree:true});
  const bar=document.querySelector('.commandbar');if(bar)new ResizeObserver(()=>document.documentElement.style.setProperty('--r24-nav-height',Math.ceil(bar.getBoundingClientRect().height)+'px')).observe(bar);
}
document.addEventListener('DOMContentLoaded',r24Setup);
