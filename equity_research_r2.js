// Release 2 evidence and stress models. Release 1 accounting/DCF functions stay unchanged.
const researchStressModels=new Map();
function researchPathDCF(params,flows){
  const {discount,terminal,debt,cash,shares,fx,debtAdjustment=0}=params;
  if(![discount,terminal,debt,cash,shares,fx,debtAdjustment].every(Number.isFinite)||discount<=0||terminal<=-1||discount<=terminal||debt<0||cash<0||shares<=0||fx<=0||!Array.isArray(flows)||!flows.length||!flows.every(Number.isFinite)||flows.at(-1)<=0)return null;
  const explicitPV=flows.reduce((sum,flow,i)=>sum+flow/(1+discount)**(i+1),0);
  const terminalPV=flows.at(-1)*(1+terminal)/(discount-terminal)/(1+discount)**flows.length;
  const enterprise=explicitPV+terminalPV,equity=enterprise-debt+cash-debtAdjustment,price=equity*1e6/shares*fx;
  return [enterprise,equity,price,terminalPV].every(Number.isFinite)?{enterprise,equity,price,terminalPV,flows}:null;
}
function researchDownturn(params,financial,inputs){
  if(financial)return null;
  const {revenue,operatingProfit,taxRate,revenueShockPct,marginShockPp,waccShockBp,recoveryYears,extraReinvestment=0}=inputs;
  if(![revenue,operatingProfit,taxRate,revenueShockPct,marginShockPp,waccShockBp,recoveryYears,extraReinvestment,params.fcf,params.growth,params.years].every(Number.isFinite)||revenue<=0||taxRate<0||taxRate>1||revenueShockPct<=-100||params.growth<=-1||!Number.isInteger(params.years)||params.years<1||params.years>20||!Number.isInteger(recoveryYears)||recoveryYears<1||recoveryYears>10||extraReinvestment<0)return null;
  const margin=operatingProfit/revenue,projection=[];
  for(let y=1;y<=params.years;y++){
    const weight=Math.max(0,1-(y-1)/recoveryYears);
    const stressedRevenue=revenue*(1+revenueShockPct/100*weight);
    const stressedEbit=stressedRevenue*(margin+marginShockPp/100*weight);
    const delta=(stressedEbit-operatingProfit)*(1-taxRate)-extraReinvestment*weight;
    projection.push({year:y,weight,revenue:stressedRevenue,ebit:stressedEbit,delta,fcff:params.fcf*(1+params.growth)**y+delta});
  }
  const valuation=researchPathDCF({...params,discount:params.discount+waccShockBp/10000},projection.map(p=>p.fcff));
  return valuation?{...valuation,projection}:null;
}
function researchMOS(value,price){return Number.isFinite(value)&&value>0&&Number.isFinite(price)&&price>0?(value-price)/value*100:null;}
function researchR2Data(c){return c.intelligence||{sources:[],topics:{},guidance:[],financialWarnings:[],capitalAllocation:[],peerCandidates:[],reportedCompetitors:[],revenueBreakdown:{},gaps:['Primary research evidence has not been collected for this company. Missing information is not evidence of low risk.']};}
function researchSourceLink(c,id){const source=researchR2Data(c).sources.find(s=>s.id===id);const a=el('a','research-source',source?`${source.kind} · ${source.published}`:'Source unavailable');if(source?.url?.startsWith('https://')){a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';a.title=`${source.title} · period ${source.period||'not extracted'} · retrieved ${source.retrievedAt||'unknown'}`;}return a;}
function researchFinancialSource(c,period,field='operatingCashFlow'){
  const row=(c.annual||[]).find(r=>r.fiscalEnd===period)||(c.annual||[])[0]||{},p=row.provenance?.[field]||{};
  const a=el('a','research-source',`${p.source||c.fundamentalSource||'financial source'} · ${period||'period unknown'}`);a.href=p.url?.startsWith('https://')?p.url:'https://finance.yahoo.com/quote/'+encodeURIComponent(c.symbol)+'/financials/';a.target='_blank';a.rel='noopener noreferrer';a.title='Retrieved '+(p.retrievedAt||c.financialAsOf||'unknown');return a;
}
function researchEvidence(host,c,items,empty,max=4){
  if(!items?.length){host.append(el('p','research-gap',empty));return;}
  const list=el('div','research-evidence-list');
  for(const item of items.slice(0,max)){const row=el('article','research-evidence');const cls=item.classification||'calculated';row.append(el('span','research-kind',cls.replaceAll('_',' ')),el('p','',item.excerpt||item.text||''));if(item.sourceId)row.append(researchSourceLink(c,item.sourceId));if(item.horizon)row.append(el('small','note','Period / horizon: '+item.horizon));list.append(row);}host.append(list);
}
function researchR2Setup(){
  if($('research-executive'))return;
  for(const [view,id] of [[0,'research-executive'],[6,'research-warning-priority']]){const host=el('section','research-r2');host.id=id;$('research-view-'+view)?.prepend(host);}
}
function researchModelSnapshot(c){
  const m=researchModels.get(c.symbol);if(!m||researchIsFinancial(c))return null;
  const balance=researchBalance(c);if(researchBalanceStale(balance,(D.generatedAt||'').slice(0,10))&&!m.acceptDated)return null;
  const params={...m,fcf:m.fcf+m.adjustment,growth:m.base/100,discount:m.discount/100,terminal:m.terminal/100};
  return researchDCF(params)?params:null;
}
function researchR2Executive(c){
  const host=$('research-executive');if(!host)return;host.replaceChildren();const d=researchR2Data(c),annual=researchData(c).annual||[],r=annual[0]||{},fin=researchIsFinancial(c),params=researchModelSnapshot(c),value=params?researchDCF(params):null;
  host.append(el('h3','','EXECUTIVE RESEARCH SUMMARY'));
  if(!fin&&c.valuationIntegrity?.issues?.length)host.append(el('p','research-warning','VALUATION REQUIRES SOURCE REVIEW · Dated or unverified inputs are in use. Open Valuation for source status.'));
  const grid=el('div','research-executive-grid');host.append(grid);
  const add=(title,text,kind='calculated')=>{const card=el('article','research-executive-card');card.append(el('span','research-kind',kind),el('h4','',title),el('p','',text));grid.append(card);return card;};
  add('Business quality',fin?`ROE ${pc(r.roe)}. Regulatory capital, RoTE and credit quality need issuer evidence.`:`ROIC ${pc(r.roic)}; OCF / profit ${Number.isFinite(r.cashConversion)?fmt(r.cashConversion,2)+'×':'unavailable'}. Financial returns do not establish a competitive moat.`);
  const flags=(d.financialWarnings||[]).filter(w=>['flag','watch'].includes(w.status)),missing=(d.financialWarnings||[]).filter(w=>w.status==='not_assessed');
  add('Financial strength',d.financialWarnings?.length?`${flags.length} financial rule(s) outside threshold; ${missing.length} unassessed. ${flags[0]?.title||'Review debt, cash conversion and source coverage.'} Screening only, not a low-risk conclusion.`:'Financial indicators are unassessed. Missing source coverage is not evidence of low risk.');
  const market=researchQuoteMajor(c.price,c.priceCurrency),mos=value?researchMOS(value.price,market):null;
  add('Valuation / margin of safety',value?`Base model ${fmt(value.price,2)} ${['GBp','GBX'].includes(c.priceCurrency)?'GBP':c.priceCurrency} vs market ${fmt(market,2)}. Margin of safety ${pc(mos)} = (model − price) / model. WACC ${pc(params.discount*100)} is assumed.`:fin?'Standard FCFF valuation excluded for this sector. Compare sourced P/E/P/B and issuer capital disclosures.':'Complete and review the Valuation inputs to calculate a model comparison. No investment rating.','assumption-based calculation');
  const latest=d.guidance?.find(g=>['revenue growth','revenue','operating margin','banking NII','RPO recognition','RoTE','capital expenditure'].includes(g.metric));const outlook=add('Growth outlook',latest?`${latest.metric}: ${latest.amountText}; ${latest.horizon||latest.relativeHorizon||'horizon not extracted'}. ${latest.comparison}.`:'No comparable numeric management guidance extracted. Historical revenue growth is not a forecast.',latest?'management expectation':'evidence gap');if(latest)outlook.append(researchSourceLink(c,latest.sourceId));
  const catalyst=d.topics?.catalysts?.[0],risk=d.topics?.risks?.[0];
  const cat=add('Catalysts / execution',catalyst?catalyst.excerpt:'No verified development extracted. Monitor new results and issuer announcements.',catalyst?.classification?.replaceAll('_',' ')||'evidence gap');if(catalyst)cat.append(researchSourceLink(c,catalyst.sourceId));
  const down=add('Downside / thesis challenge',risk?risk.excerpt:'No sourced risk passage extracted; this is not a low-risk conclusion.',risk?.classification?.replaceAll('_',' ')||'evidence gap');if(risk)down.append(researchSourceLink(c,risk.sourceId));
  for(const card of [...grid.children].slice(0,2))card.append(researchFinancialSource(c,r.fiscalEnd));
  const triggers=researchDetails(host,'Evidence that would change the thesis · transparent monitoring rules');
  triggers.append(el('p','note',fin?'Monitor issuer CET1 buffers, RoTE versus targets, banking NII guidance, expected credit losses and distributions. No corporate cash-flow test is a substitute for bank regulation.':'Reassess if cash conversion falls below 0.8×, operating margin falls more than 4pp, net debt / operating profit exceeds 4×, share count rises more than 3%, or a guidance comparison changes terms. These are screening rules requiring context, not recommendations.'));
  if(params&&!fin){const spread=Number.isFinite(r.roic)?r.roic-params.discount*100:null;triggers.append(el('p','note',`ROIC minus assumed WACC: ${spread==null?'unavailable':fmt(spread,2)+'pp'}. Positive accounting spread alone does not prove realised shareholder value creation.`));}
}
function researchR2Business(c,host){
  host.replaceChildren();const d=researchR2Data(c),ccy=c.financialCurrency||'';
  host.append(el('h3','','BUSINESS & COMPETITION'));
  const summary=c.businessSummary||'No sourced business description is available.';
  host.append(el('p','note',summary.split(/(?<=[.!?])\s/)[0]));
  const full=researchDetails(host,'Business description & provider provenance');full.append(el('p','note',summary),el('p','note',`Provider facts retrieved ${c.financialAsOf||'unknown'} · ${c.fundamentalSource||'unavailable'}. Qualitative issuer claims below are not independently verified moats.`));
  const mix=el('div','research-pair');host.append(mix);
  if(!d.revenueBreakdown?.segments&&!d.revenueBreakdown?.geography)mix.append(el('p','note','Reported segment and geographic breakdowns are unavailable; open issuer reports in source coverage.'));
  for(const [key,title] of [['segments','Reported revenue segments'],['geography','Geographic revenue exposure']]){const panel=el('section');mix.append(panel);panel.append(el('h4','',title));const b=d.revenueBreakdown?.[key];if(!b){panel.remove();continue;}
    panel.append(researchSourceLink(c,b.sourceId),el('p','note',`${b.period} · ${b.currency}. ${b.basis}`));researchTable(panel,['Reported category','Revenue'],b.rows.map(r=>[r.label,companyAmount(r.value,b.currency)]));}
  const competitors=researchDetails(host,'Principal competitors and peer relevance',true);
  if(d.reportedCompetitors?.length){for(const p of d.reportedCompetitors){const line=el('p','note',`${p.name} (${p.symbol}) · named in a collected competition passage; not a market-share ranking. `);line.append(researchSourceLink(c,p.sourceId));competitors.append(line);}}
  else competitors.append(el('p','research-gap','No principal competitor was verified by name matching in the collected issuer passages. Industry peers below are suggestions, not competitor claims.'));
  const peers=d.peerCandidates||[];
  if(peers.length){researchTable(competitors,['Suggested peer','P/E TTM','EV/EBITDA','Provider ROE'],peers.map(p=>[`${p.name} (${p.symbol})`,p.trailingPE>0?fmt(p.trailingPE,1)+'×':'—',!researchIsFinancial(c)&&p.enterpriseToEbitda>0?fmt(p.enterpriseToEbitda,1)+'×':'—',pc(p.roePct)]));competitors.append(el('p','note',peers[0].basis+'. Ratios are provider snapshots; verify reporting periods in the existing peer comparator.'));
    const button=el('button','btn','COMPARE CURRENT COMPANY WITH THESE PEERS');button.type='button';button.onclick=()=>{[c.symbol,...peers.map(p=>p.symbol)].slice(0,4).forEach((s,i)=>{const select=$('peer'+i);if(select&&[...select.options].some(o=>o.value===s)){select.value=s;state.peers[i]=s;}});renderPeers();$('peer-panel')?.scrollIntoView({behavior:'smooth',block:'start'});};competitors.append(button);}
  const advantages=researchDetails(host,'Competitive advantage evidence · issuer claims, not verified conclusions');
  for(const [key,title] of [['pricingPower','Pricing power'],['switchingCosts','Switching costs / retention'],['marketPosition','Market position'],['costStructure','Cost structure']]){const panel=researchDetails(advantages,title);researchEvidence(panel,c,d.topics?.[key],`No sufficiently specific ${title.toLowerCase()} passage extracted. Margin/ROIC trends alone do not prove an advantage.`,2);}
  const allocation=researchDetails(host,'Five-year capital allocation & value creation evidence',true),rows=d.capitalAllocation||[];
  if(!rows.length){allocation.append(el('p','research-gap','No annual allocation history has been sourced. Missing dividends, buybacks or acquisition flows are not assumed to be zero.'));return;}
  researchTable(allocation,['Fiscal year',...rows.map(r=>'FY '+r.period.slice(0,4))],[['Reinvestment: capex outflow',...rows.map(r=>companyAmount(r.capex,ccy))],['Business acquisitions / disposals (signed)',...rows.map(r=>companyAmount(r.acquisitions,ccy))],['Dividends paid',...rows.map(r=>companyAmount(r.dividends,ccy))],['Buybacks',...rows.map(r=>companyAmount(r.buybacks,ccy))],['Calculated ROIC',...rows.map(r=>pc(r.roic))],['FCF / dividends + buybacks',...rows.map(r=>Number.isFinite(r.coverage)?fmt(r.coverage,2)+'×':'—')]]);
  allocation.append(el('p','note','Missing distributions/acquisition lines remain blank. Acquisition cash flow is signed and definitions can vary; cash acquired may be netted and disposal proceeds may be included. See Financials field sources. ROIC is an accounting estimate; compare with an explicitly assumed cost of capital, not a presumed return hurdle. Returns of capital do not by themselves establish value creation.'));
  const allocationSources=researchDetails(allocation,'Period sources and acquisition definitions');for(const row of rows){allocationSources.append(researchFinancialSource(c,row.period),el('p','note',`${row.period}: ${row.acquisitionBasis}`));}
  const plot=el('div','chart');plot.id='research-allocation-roic';allocation.append(plot);chart(plot.id,[{name:'Calculated ROIC',color:BLUE,pts:rows.slice().reverse().filter(r=>Number.isFinite(r.roic)).map(r=>({date:r.period,v:r.roic}))}],{format:v=>fmt(v,2)+'%'});
}
function researchR2Outlook(c,host){
  host.replaceChildren();const d=researchR2Data(c);host.append(el('h3','','MANAGEMENT & EARNINGS INTELLIGENCE'));
  const recent=(d.sources||[]).filter(s=>s.kind==='results'||s.kind==='interim').sort((a,b)=>b.published.localeCompare(a.published)).slice(0,3);
  if(recent.length)for(const doc of recent){const row=el('p','note',`${doc.title} · published ${doc.published} · period ${doc.period||'not extracted'} · retrieved ${String(doc.retrievedAt||'unknown').slice(0,10)} `);row.append(researchSourceLink(c,doc.id));host.append(row);}
  else host.append(el('p','research-gap','No current primary results source collected. Provider news does not replace filed results.'));
  if(!d.sources?.length){host.lastElementChild?.remove();host.append(el('p','research-gap','Primary research coverage unavailable. Financial history and personal notes remain available; source failures are in the expandable coverage panel.'));const coverage=researchDetails(host,'Source coverage & failed requests');for(const text of d.gaps||[])coverage.append(el('p','note',text));return;}
  const results=researchDetails(host,'Latest reported earnings results',true);
  const reported=d.reportedResults||[];
  if(reported.length){researchTable(results,['Reported metric','Amount','Period'],reported.map(r=>[r.metric,companyAmount(r.value,r.currency||c.financialCurrency),r.period]));results.append(researchSourceLink(c,reported[0].sourceId),el('p','note','Reported first quarter column from a source table, with its stated definition. Adjusted measures are labelled; no consensus estimate is inferred.'));}
  else results.append(el('p','research-gap','No unambiguous quarterly results table was extracted. Open the dated results documents; annual financial history remains in Financials.'));
  const guidance=researchDetails(host,'Dated management expectations & extracted changes',!!d.guidance?.length);
  guidance.append(el('p','note','Latest sources appear first. Older ambitions can coexist with newer guidance; different periods, definitions and qualifications are not treated as like-for-like revisions. Open sources before relying on an expectation.'));
  if(!d.guidance?.length)guidance.append(el('p','research-gap','No unambiguous numeric management guidance extracted; neither analyst consensus nor a transcript is invented.'));
  for(const g of d.guidance||[]){const row=el('article','research-evidence');row.append(el('span','research-kind','management expectation'),el('h4','',g.metric+' · '+(g.horizon||g.relativeHorizon||'horizon not extracted')),el('p','',`${g.amountText} (${g.qualifier}; ${g.basis||'basis not separately identified'}). ${g.comparison}.`),el('p','note',g.excerpt),researchSourceLink(c,g.sourceId));if(g.previous){row.append(el('p','note',`Previous: ${g.previous.amountText} (${g.previous.qualifier}), published ${g.previous.published}. Amount/wording changes do not establish like-for-like upgrades; verify scope, qualifications and units.`),researchSourceLink(c,g.previous.sourceId));}guidance.append(row);}
  const catalysts=researchDetails(host,'Developments with potential 1–3 year relevance',!!d.topics?.catalysts?.length);
  catalysts.append(el('p','note','A reported development is not a forecast of investment returns. Source statements are classified below; timing and valuation impact are unproven unless explicitly guided.'));
  researchEvidence(catalysts,c,d.topics?.catalysts,'No specific primary-source development extracted. No catalyst is manufactured.',5);
  if(d.longTermDevelopments?.length){const longer=researchDetails(host,'Longer-term or historical developments · outside the near-term catalyst list');researchEvidence(longer,c,d.longTermDevelopments,'No longer-term evidence',4);}
  const risks=researchDetails(host,'Principal downside risks & challenging evidence',!!d.topics?.risks?.length);researchEvidence(risks,c,d.topics?.risks,'No primary risk passage extracted. Absence of extracted evidence does not mean low risk.',5);
  const monitors=researchDetails(host,'Indicators to monitor');for(const w of d.financialWarnings||[])monitors.append(el('p','note',`${w.title}: ${w.monitor} Rule: ${w.rule}`));
  if(d.news?.length){const news=researchDetails(host,'Recent company news · media evidence, not confirmed company guidance');for(const item of d.news){const a=el('a','research-source',`${item.title} · ${item.source||'publisher'} · ${item.published||'unknown date'}`);if(item.url?.startsWith('https://')){a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';news.append(a);}}}
  const transcripts=researchDetails(host,'Earnings-call access & transcripts');
  if(d.transcriptLinks?.length)for(const link of d.transcriptLinks){const a=el('a','research-source',link.title+' · issuer link; transcript text not collected');a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';transcripts.append(a);}
  else transcripts.append(el('p','research-gap','No verified freely accessible issuer transcript link was collected. Open the results source for issuer webcast materials; no transcript or management quote is synthesised.'));
  const gaps=researchDetails(host,'Source coverage & material evidence gaps');for(const text of d.gaps||[])gaps.append(el('p','research-gap',text));for(const source of d.unparsedSources||[]){const a=el('a','research-source','OPEN UNPARSED SOURCE · '+source.title);if(source.url?.startsWith('https://')){a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';gaps.append(a);}}gaps.append(el('p','note',`Research cache checked ${d.checkedAt||'not yet'}. ${d.offline?'Offline evidence; no refresh attempted.':''} Original publication/retrieval dates are retained. ${d.staleRetrieval?'Some document retrievals are more than 120 days old; check whether newer disclosures exist.':''} Independent moat verification and a full analyst thesis cannot be automated from these sources.`));
}
function researchR2Warnings(c){
  const host=$('research-warning-priority');if(!host)return;host.replaceChildren();const d=researchR2Data(c);host.append(el('h3','','FIVE PRIORITY FINANCIAL INDICATORS'));
  host.append(el('p','note','Displayed by flag, watch, unassessed, not-applicable, then within-rule status. No overall risk score; missing inputs and financial-sector exclusions remain unassessed. These are screening priorities, not guaranteed investment materiality.'));
  const warnings=d.financialWarnings||[];
  researchTable(host,['Indicator / annual period','Calculated value','Rule status'],warnings.map(w=>[`${w.title} · ${w.period||'unknown'}`,Number.isFinite(w.value)?fmt(w.value,2)+(['dilution'].includes(w.key)?'%':w.key==='margin'?'pp':'×'):'—',w.status.replaceAll('_',' ')]));
  if(!warnings.length)host.append(el('p','research-gap','Financial warning indicators have not been assessed. No low-risk conclusion is available.'));
  const rules=researchDetails(host,'Rules, missing information & ownership dates');for(const w of warnings){rules.append(el('p','note',`${w.title}: ${w.rule} ${w.monitor}`),researchFinancialSource(c,w.period));}rules.append(el('p','note','Ownership fractions below are dated provider retrievals with unknown filing/observation dates. They are not a verified live register; institutions may overlap.'));
  const rows=researchData(c).annual||[],balance=researchBalance(c);
  researchTable(rules,['Share-count source','Period','Ordinary shares'],[[balance.sharesSource||balance.source||'Latest balance (basis needs verification)',balance.sharesPeriod||balance.period||'unknown',Number.isFinite(balance.sharesOutstanding)?fmt(balance.sharesOutstanding,0):'—'],...rows.map(r=>['Annual accounts',r.fiscalEnd,Number.isFinite(r.sharesOutstanding)?fmt(r.sharesOutstanding,0):'—'])]);
}
function researchR2Render(c){researchR2Setup();researchR2Executive(c);researchR2Warnings(c);}
function researchR2Stress(c,host){
  let panel=$('research-stress-panel');if(!panel){panel=el('section','research-r2 research-stress');panel.id='research-stress-panel';host.append(panel);}panel.replaceChildren();
  panel.append(el('h3','','DOWNTURN & SECTOR STRESS TESTING'));
  if(researchIsFinancial(c)){panel.append(el('p','research-gap','Corporate FCFF recession modelling is excluded for banks and insurers. Monitor issuer NII sensitivity, ECL, regulatory CET1 buffers, liquidity and RoTE; insufficient disclosed exposures prevent an automatic capital/earnings stress result.'));return;}
  const params=researchModelSnapshot(c),r=researchData(c).annual?.[0]||{},d=researchR2Data(c),energy=/energy|oil|gas/i.test((c.sector||'')+' '+(c.industry||'')),tech=/technology|software|semiconductor/i.test((c.sector||'')+' '+(c.industry||''));
  const sector=energy?'Energy / commodity':tech?'Technology / demand and margin':'Corporate / demand and financing';
  panel.append(el('p','note',`${sector} assumption preset. This adds an explicit first-year revenue and margin contraction, higher WACC and a recovery path; 0% growth alone is not treated as recession. The validated Release 1 scenarios above remain unchanged.`));
  if(!params){panel.append(el('p','research-gap','Complete and accept the dated Release 1 valuation inputs first. Missing inputs cannot support a stress value.'));return;}
  if(!researchStressModels.has(c.symbol))researchStressModels.set(c.symbol,{revenueShockPct:energy?-25:tech?-15:-15,marginShockPp:energy?-6:tech?-5:-3,waccShockBp:200,financingShockBp:200,recoveryYears:3,extraReinvestment:0,taxPct:Number.isFinite(r.effectiveTaxRate)?r.effectiveTaxRate*100:null,commodityPct:-20,commodityBeta:null});
  const s=researchStressModels.get(c.symbol),controls=researchDetails(panel,'Edit stress assumptions',true),grid=el('div','research-inputs');controls.append(grid);const result=el('div');result.setAttribute('aria-live','polite');
  for(const [label,key] of [['First-year revenue shock (%)','revenueShockPct'],['First-year operating margin shock (percentage points)','marginShockPp'],['Stress WACC increase (basis points)','waccShockBp'],['Financing-cost increase (basis points, liquidity only)','financingShockBp'],['Recovery years (1–10)','recoveryYears'],['Extra first-year reinvestment (reporting millions)','extraReinvestment'],['Forward effective tax rate (%, assumption)','taxPct']])researchInput(grid,label,s[key],v=>{s[key]=v;paintStress();});
  controls.append(el('p','note',`Starting revenue ${companyAmount(r.revenue,c.financialCurrency)} and EBIT ${companyAmount(r.operatingProfit,c.financialCurrency)} are annual ${r.fiscalEnd||'unknown'}. Revenue is held flat as a counterfactual baseline for the incremental operating shock; base FCFF follows the selected Release 1 growth assumption. Shocks fade linearly over recovery years. Forward tax treatment is an assumption, including immediate tax relief if losses occur.`));
  panel.append(result);
  const sectorEvidence=researchDetails(panel,'Sector-specific evidence and sensitivity limits',true);
  const commodity=d.commoditySensitivities||[];
  if(energy){
    if(commodity.length)for(const item of commodity){sectorEvidence.append(el('p','note',item.basis+' · '+item.published),researchSourceLink(c,item.sourceId));researchTable(sectorEvidence,['Issuer commodity scenario','Reported asset-value effect'],[[fmt(item.downShockPct,1)+'% price outlook',`${companyAmount(item.impairmentLow,item.currency)} to ${companyAmount(item.impairmentHigh,item.currency)} impairment`],['+'+fmt(item.upShockPct,1)+'% price outlook',`${companyAmount(item.reversalLow,item.currency)} to ${companyAmount(item.reversalHigh,item.currency)} impairment reversal`]]);}
    else sectorEvidence.append(el('p','research-gap','No numeric issuer commodity sensitivity was extracted. A commodity-to-cash-flow relationship is not fabricated.'));
    sectorEvidence.append(el('p','note','Asset impairment sensitivity cannot be converted directly into FCFF or equity-value sensitivity. A price-to-cash-flow coefficient is not automatically available. An optional user assumption below is separate from the issuer scenario.'));
    const commodityControls=el('div','research-inputs');sectorEvidence.append(commodityControls);const output=el('p','note');sectorEvidence.append(output);
    function paintCommodity(){
      if(!Number.isFinite(s.commodityBeta)||!Number.isFinite(s.commodityPct)){output.textContent='Commodity-linked DCF unavailable until a verified or explicitly assumed cash-flow coefficient is entered.';return;}
      const flows=Array.from({length:params.years},(_,i)=>params.fcf*(1+params.growth)**(i+1)+s.commodityBeta*s.commodityPct/10*Math.max(0,1-i/s.recoveryYears));const v=researchPathDCF(params,flows);
      output.textContent=v?`User commodity cash-flow assumption: ${fmt(s.commodityPct,1)}% price change × ${fmt(s.commodityBeta,2)} reporting m per +10% price change, fading with recovery. Value/share ${fmt(v.price,2)} ${['GBp','GBX'].includes(c.priceCurrency)?'GBP':c.priceCurrency}. This coefficient is not issuer guidance.`:'No finite terminal valuation under these assumptions.';
    }
    researchInput(commodityControls,'Commodity-price shock (%) · assumption',s.commodityPct,v=>{s.commodityPct=v;paintCommodity();});researchInput(commodityControls,'Annual FCFF impact per +10% commodity price (reporting millions) · user assumption',s.commodityBeta,v=>{s.commodityBeta=v;paintCommodity();});paintCommodity();
  }else sectorEvidence.append(el('p','note',tech?'Technology sensitivities use revenue demand and operating-margin compression, plus incremental reinvestment. No unsourced AI demand, cloud growth, market share or capacity forecast is entered.':'Use revenue, margins, reinvestment and financing assumptions appropriate to the issuer. Exposure-specific sensitivities need disclosed data; this is not a calibrated sector forecast.'));
  function paintStress(){
    result.replaceChildren();const tax=Number.isFinite(s.taxPct)?s.taxPct/100:null;
    const v=researchDownturn(params,false,{revenue:Number.isFinite(r.revenue)?r.revenue/1e6:null,operatingProfit:Number.isFinite(r.operatingProfit)?r.operatingProfit/1e6:null,taxRate:tax,...s});
    const base=researchDCF(params),market=researchQuoteMajor(c.price,c.priceCurrency),quote=['GBp','GBX'].includes(c.priceCurrency)?'GBP':c.priceCurrency;
    if(!v){result.append(el('p','research-gap','Stress value unavailable: source revenue/EBIT/tax or scenario inputs are missing/invalid, or terminal FCFF is not positive. No terminal value is invented.'));return;}
    researchTable(result,['Calculated model','Value/share '+quote,'vs observed market','Margin of safety'],[['Release 1 base',fmt(base.price,2),market>0?pc((base.price/market-1)*100):'—',pc(researchMOS(base.price,market))],['Recession / user stress',fmt(v.price,2),market>0?pc((v.price/market-1)*100):'—',pc(researchMOS(v.price,market))]]);
    result.append(el('p','note',`Terminal dependence: ${v.enterprise>0?fmt(v.terminalPV/v.enterprise*100,1)+'%':'not meaningful'} of stressed enterprise value comes from discounted terminal value; it is highly assumption-sensitive. WACC rises from ${fmt(params.discount*100,2)}% to ${fmt((params.discount+s.waccShockBp/10000)*100,2)}%. Market date ${c.priceAsOf||'unknown'}.`));
    const path=researchDetails(result,'Year-by-year stress cash flow & financing-cost check',true);researchTable(path,['Year','Stressed revenue m','Stressed EBIT m','FCFF change m','Stressed FCFF m'],v.projection.map(p=>[String(p.year),fmt(p.revenue,2),fmt(p.ebit,2),fmt(p.delta,2),fmt(p.fcff,2)]));
    const debt=params.debt,interest=Number.isFinite(s.financingShockBp)?debt*s.financingShockBp/10000:null,existing=Number.isFinite(r.interestExpense)?r.interestExpense/1e6:null;
    const cover=existing!=null&&interest!=null&&existing+interest>0?v.projection[0].ebit/(existing+interest):null;
    path.append(el('p','note',`Liquidity-only financing cost: ${interest==null?'unavailable':fmt(interest,2)} reporting m annually if 100% of stated debt (including leases) reprices immediately. First-year EBIT / (reported interest + increment): ${cover==null?'unavailable':fmt(cover,2)+'×'}. Maturity, hedging and lease reset data are not modelled. This cost is not subtracted again from unlevered FCFF; financing stress enters valuation through WACC to avoid double counting.`));
  }paintStress();
}
