/* Release 2.6 non-ETF presentation retained unchanged by Release 2.7. */
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
