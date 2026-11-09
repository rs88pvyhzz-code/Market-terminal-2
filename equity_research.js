// Runs inside the terminal closure and reuses its company, chart and forensic modules.
const researchViews=['Overview','Financials','Valuation','Performance & Risk','Business & Competition','Outlook & Catalysts','Red Flags & Ownership'];
const researchModels=new Map();
const researchNotebook=new Map();
let researchView=0;
function researchQuoteMajor(price,currency){return Number.isFinite(price)?price/(['GBp','GBX'].includes(currency)?100:1):null;}
function researchRatio(a,b){return Number.isFinite(a)&&Number.isFinite(b)&&b!==0?a/b:null;}
function researchFCF(r){return Number.isFinite(r.operatingCashFlow)&&Number.isFinite(r.capex)?r.operatingCashFlow-Math.abs(r.capex):null;}
function researchROIC(r,p){
  if(!p||![r.operatingProfit,r.taxExpense,r.pretaxProfit,r.equity,r.totalDebt,r.cash,p.equity,p.totalDebt,p.cash].every(Number.isFinite)||r.pretaxProfit<=0)return null;
  const tax=r.taxExpense/r.pretaxProfit,capital=(r.equity+r.totalDebt-r.cash+p.equity+p.totalDebt-p.cash)/2;
  return tax>=0&&tax<=1&&capital>0?r.operatingProfit*(1-tax)/capital*100:null;
}
// FCFF and debt/cash use the same reporting currency; shares are an absolute count.
function researchDCF({fcf,growth,discount,terminal,years,debt,cash,shares,fx}){
  if(![fcf,growth,discount,terminal,years,debt,cash,shares,fx].every(Number.isFinite)||fcf<=0||growth<=-1||discount<=terminal||discount<=0||terminal<=-1||shares<=0||fx<=0||debt<0||cash<0||!Number.isInteger(years)||years<1||years>20)return null;
  let pv=0,flow=fcf;const flows=[];
  for(let y=1;y<=years;y++){flow*=1+growth;const discounted=flow/(1+discount)**y;pv+=discounted;flows.push({year:y,flow,discounted});}
  const terminalPV=flow*(1+terminal)/(discount-terminal)/(1+discount)**years;
  const enterprise=pv+terminalPV,equity=enterprise-debt+cash;
  const price=equity*1e6/shares*fx;
  if(![enterprise,equity,price,terminalPV].every(Number.isFinite))return null;
  return {enterprise,equity,price,terminalPV,flows};
}
function researchReverse(inputs,target){
  if(!Number.isFinite(target)||target<=0)return null;
  let lo=-.9,hi=1;const low=researchDCF({...inputs,growth:lo}),high=researchDCF({...inputs,growth:hi});
  if(!low||!high||target<low.price||target>high.price)return null;
  for(let i=0;i<100;i++){const mid=(lo+hi)/2;if(researchDCF({...inputs,growth:mid}).price<target)lo=mid;else hi=mid;}
  return (lo+hi)/2;
}
function setupResearchViews(){
  if($('research-nav'))return;
  const root=$('companies'),nav=el('div','period-controls');nav.id='research-nav';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','Company research views');root.append(nav);
  researchViews.forEach((name,i)=>{const b=el('button','btn',name);b.id='research-tab-'+i;b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-controls','research-view-'+i);b.onclick=()=>showResearchView(i);b.onkeydown=e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?6:(i+(e.key==='ArrowRight'?1:6))%7;showResearchView(n);$('research-tab-'+n).focus();}};nav.append(b);const v=el('section','research-view');v.id='research-view-'+i;v.setAttribute('role','tabpanel');v.setAttribute('aria-labelledby',b.id);root.append(v);});
  const move=(id,i)=>{if($(id))$('research-view-'+i).append($(id));};
  move('company-kpis',0);move('company-news-panel',0);
  const main=root.querySelector('.company-main'),income=main?.querySelector('.company-fin');if(income)$('research-view-1').append(income);if(main)$('research-view-3').append(main);
  move('company-risk-panel',3);move('peer-panel',4);move('company-events-panel',5);move('forensic-panel',6);
  // Keep the established accounting renderer, always tied to the selected company.
  $('forensic-panel').querySelector('.research-controls').hidden=true;
  $('forensic-panel').querySelector('h2').textContent='ACCOUNTING CHECKS';
  for(const [i,id] of [[1,'research-statements'],[2,'research-valuation'],[4,'research-business'],[5,'research-outlook'],[6,'research-ownership']]){const node=el('div');node.id=id;$('research-view-'+i).prepend(node);}
  showResearchView(0);renderEquityResearch(ensureCompany(state.companySymbol));
}
function showResearchView(i){
  researchView=i;researchViews.forEach((_,j)=>{const b=$('research-tab-'+j);b.setAttribute('aria-selected',String(i===j));b.tabIndex=i===j?0:-1;b.classList.toggle('active',i===j);$('research-view-'+j).hidden=i!==j;});
  if(i===1||i===3)requestAnimationFrame(()=>{renderCompany();});
}
function researchTable(host,headers,rows){const scroll=el('div','small-scroll'),t=el('table','watch');const head=el('thead'),tr=el('tr');headers.forEach(s=>tr.append(el('th','',s)));head.append(tr);t.append(head);const body=el('tbody');rows.forEach(cells=>{const row=el('tr');cells.forEach((s,i)=>row.append(el('td',i?'n':'',s)));body.append(row);});t.append(body);scroll.append(t);host.append(scroll);}
function renderResearchStatements(c){
  const host=$('research-statements');host.replaceChildren();const rows=[...(c.annual||[])].sort((a,b)=>b.fiscalEnd.localeCompare(a.fiscalEnd)).slice(0,5),ccy=c.financialCurrency||'';
  host.append(el('h3','','FIVE-YEAR FINANCIAL STATEMENTS'),el('p','note',`${rows.length} of 5 annual periods available. Missing periods and line items remain —. Reporting currency: ${ccy||'unknown'}. Retrieved: ${c.financialAsOf||'unknown'}. Source: ${c.fundamentalSource||'unavailable'}.`));
  const source=el('a','company-link','CHECK PROVIDER STATEMENTS');source.href='https://finance.yahoo.com/quote/'+encodeURIComponent(c.symbol)+'/financials/';source.target='_blank';source.rel='noopener noreferrer';host.append(source);
  const groups=[['Income statement',[['Revenue','revenue'],['Gross profit','grossProfit'],['Operating profit','operatingProfit'],['Pre-tax profit','pretaxProfit'],['Tax expense','taxExpense'],['Net profit','netProfit']]],['Balance sheet',[['Total assets','totalAssets'],['Total liabilities','totalLiabilities'],['Equity','equity'],['Current assets','currentAssets'],['Current liabilities','currentLiabilities'],['Debt','totalDebt'],['Cash','cash'],['Receivables','receivables'],['Inventory','inventory'],['Goodwill','goodwill']]],['Cash flow & capital allocation',[['Operating cash flow','operatingCashFlow'],['Capital expenditure','capex'],['Investing cash flow','investingCashFlow'],['Financing cash flow','financingCashFlow'],['Dividends paid','dividendsPaid'],['Buybacks','buybacks'],['Share-based compensation','shareBasedComp'],['FCF = operating cash flow − |capex|',researchFCF]]]];
  for(const [title,fields] of groups){host.append(el('h3','',title));researchTable(host,['Metric',...rows.map(r=>r.fiscalEnd)],fields.map(([label,key])=>[label,...rows.map(r=>companyAmount(typeof key==='function'?key(r):r[key],ccy))]));}
  const ratio=(a,b)=>{const v=researchRatio(a,b);return v==null?'—':fmt(v,2)+'×';},margin=(a,b)=>{const v=researchRatio(a,b);return v==null?'—':fmt(v*100,2)+'%';};
  const fin=forensicIsFinancial(c);
  const metrics=[['Gross margin',r=>margin(r.grossProfit,r.revenue)],['Operating margin',r=>margin(r.operatingProfit,r.revenue)],['Net margin',r=>margin(r.netProfit,r.revenue)],['FCF margin',r=>margin(researchFCF(r),r.revenue)],['Cash conversion',r=>r.netProfit>0?ratio(r.operatingCashFlow,r.netProfit):'—'],['Debt / equity',r=>!fin&&r.equity>0?ratio(r.totalDebt,r.equity):'—'],['Current ratio',r=>!fin?ratio(r.currentAssets,r.currentLiabilities):'—'],['Interest cover',r=>!fin&&r.interestExpense>0?ratio(r.operatingProfit,r.interestExpense):'—'],['Net debt / operating profit',r=>!fin&&r.operatingProfit>0&&Number.isFinite(r.totalDebt)&&Number.isFinite(r.cash)?ratio(r.totalDebt-r.cash,r.operatingProfit):'—'],['ROIC (derived)',(r,i)=>fin?'—':pc(researchROIC(r,rows[i+1]))]];
  host.append(el('h3','','MARGINS, RETURNS & DEBT RATIOS'));researchTable(host,['Metric',...rows.map(r=>r.fiscalEnd)],metrics.map(([name,fn])=>[name,...rows.map(fn)]));
  host.append(el('p','note','ROIC = operating profit × (1 − effective tax rate) / average (equity + debt − cash). Requires two periods and a valid tax rate; approximate, sector-dependent. Generic debt ratios and ROIC are suppressed for financial companies. Cash-flow classification differs under IFRS and US GAAP. FCF is a derived equity cash-flow proxy, not unlevered FCFF.'));
  const chartHost=el('div','chart');chartHost.id='research-financial-chart';host.append(el('h3','','HISTORICAL REVENUE, PROFIT & CASH FLOW'),chartHost);
  const sets=[['Revenue','revenue',AMBER],['Operating profit','operatingProfit',BLUE],['Operating cash flow','operatingCashFlow',AQUA],['FCF',researchFCF,UP]].map(([name,key,color])=>({name,color,pts:rows.slice().reverse().map(r=>({date:r.fiscalEnd,v:typeof key==='function'?key(r):r[key]})).filter(p=>Number.isFinite(p.v))}));
  chart(chartHost.id,sets,{format:v=>companyAmount(v,ccy)});
  const margins=el('div','chart');margins.id='research-margin-chart';host.append(el('h3','','HISTORICAL MARGINS & ROIC'),margins);
  chart(margins.id,[['Operating margin',AMBER,(r)=>{const x=researchRatio(r.operatingProfit,r.revenue);return x==null?null:x*100;}],['FCF margin',AQUA,(r)=>{const x=researchRatio(researchFCF(r),r.revenue);return x==null?null:x*100;}],['ROIC',BLUE,(r,i)=>fin?null:researchROIC(r,rows[i+1])]].map(([name,color,fn])=>({name,color,pts:rows.map((r,i)=>({date:r.fiscalEnd,v:fn(r,i)})).reverse().filter(p=>Number.isFinite(p.v))})),{format:v=>fmt(v,2)+'%'});
}
function researchInput(host,label,value,onchange){const wrap=el('label','mini',label+' '),input=el('input','field');input.type='number';input.step='any';input.value=value??'';input.setAttribute('aria-label',label);input.oninput=()=>onchange(input.value===''?null:Number(input.value));wrap.append(input);host.append(wrap);return input;}
function renderResearchValuation(c){
  const host=$('research-valuation');host.replaceChildren();host.append(el('h3','','DCF & REVERSE DCF · USER ASSUMPTIONS'));
  host.append(el('p','note','Unlevered free cash flow to the firm (FCFF) model. Enter a normalised FCFF after operating taxes and reinvestment, before interest. Reported operating cash flow less capex is shown in Financials but is not automatically substituted. All inputs below are modelling assumptions, not forecasts or investment ratings. Defaults for growth and discount rates are illustrative.'));
  if(forensicIsFinancial(c)){host.append(el('p','note','Generic FCFF DCF is disabled for banks and insurers; use a sector-appropriate excess-return or dividend model.'));return;}
  const latest=(c.annual||[])[0]||{},quote=['GBp','GBX'].includes(c.priceCurrency)?'GBP':c.priceCurrency;
  if(!researchModels.has(c.symbol))researchModels.set(c.symbol,{fcf:null,debt:Number.isFinite(latest.totalDebt)?latest.totalDebt/1e6:null,cash:Number.isFinite(latest.cash)?latest.cash/1e6:null,shares:latest.sharesOutstanding??null,fx:c.financialCurrency&&c.financialCurrency===quote?1:null,years:5,terminal:2,bear:0,base:5,bull:10,discount:10});
  const m=researchModels.get(c.symbol),inputs=el('div','research-inputs');host.append(inputs);
  const output=el('div');output.setAttribute('aria-live','polite');
  const definitions=[['Normalised FCFF (reporting currency, millions)','fcf'],['Debt (reporting currency, millions)','debt'],['Cash (reporting currency, millions)','cash'],['Shares outstanding (absolute count)','shares'],[`FX: ${quote||'quote major currency'} per ${c.financialCurrency||'reporting currency'}`,'fx'],['Forecast years (1–20)','years'],['Discount rate / WACC (%)','discount'],['Terminal growth (%)','terminal'],['Bear FCFF growth (%)','bear'],['Base FCFF growth (%)','base'],['Bull FCFF growth (%)','bull']];
  for(const [label,key] of definitions)researchInput(inputs,label,m[key],v=>{m[key]=v;paint();});
  host.append(el('p','note',`Debt, cash and shares initially use the latest available FY ${latest.fiscalEnd||'unknown'}; edit to reflect current balances, dilution and other claims. FX is a user assumption (1 only when currencies match). Value per share is in ${quote||'unknown quote currency'}; GBp/GBX market quotes are divided by 100. Models remain in memory per company during this session.`),output);
  function paint(){output.replaceChildren();const assumptions=['fcf','debt','cash','shares','fx','years','discount','terminal','bear','base','bull'];
    if(!assumptions.every(k=>Number.isFinite(m[k]))||!quote||!c.financialCurrency){output.append(el('p','note','Enter all model inputs and verify both currencies. Missing data cannot support a valuation.'));return;}
    const params={...m,discount:m.discount/100,terminal:m.terminal/100},base=researchDCF({...params,growth:m.base/100});
    if(!base||m.bear<=-100||m.bear>m.base||m.base>m.bull){output.append(el('p','note','Invalid assumptions: FCFF, shares and FX must be positive; debt/cash non-negative; WACC > terminal growth; integer years 1–20; growth > −100%; bear ≤ base ≤ bull.'));return;}
    const market=researchQuoteMajor(c.price,c.priceCurrency);
    researchTable(output,['Scenario (assumption)','FCFF growth','Enterprise value (reporting m)','Equity value (reporting m)',`Value/share (${quote})`,'vs market price'],['bear','base','bull'].map(key=>{const r=researchDCF({...params,growth:m[key]/100});return [key.toUpperCase(),pc(m[key]),r?fmt(r.enterprise):'—',r?fmt(r.equity):'—',r?fmt(r.price):'—',r&&market>0?pc((r.price/market-1)*100):'—'];}));
    output.append(el('p','note',`Market quote: ${market==null?'unavailable':fmt(market)+' '+quote} · ${c.priceAsOf||'date unknown'}. Base terminal value is ${fmt(base.terminalPV/base.enterprise*100,1)}% of enterprise value. Debt bridge excludes unentered minority interests, leases and other claims; adjust debt input where appropriate.`));
    output.append(el('h3','','BASE CASE CASH-FLOW PROJECTION · ASSUMPTIONS'));researchTable(output,['Year','FCFF (reporting m)','Present value (reporting m)'],base.flows.map(r=>[String(r.year),fmt(r.flow),fmt(r.discounted)]));
    const implied=researchReverse({...params,growth:0},market);output.append(el('h3','','REVERSE DCF'),el('p','note',implied==null?'Implied growth unavailable: missing market price or no solution within −90% to +100% annual growth.':`Market price implies ${fmt(implied*100)}% annual FCFF growth over ${m.years} years, holding the other base inputs fixed. This is an implied assumption, not a forecast.`));
    output.append(el('h3','','SENSITIVITY · BASE VALUE/SHARE BY WACC AND TERMINAL GROWTH'));
    const gs=[m.terminal-1,m.terminal,m.terminal+1];researchTable(output,['WACC / terminal g',...gs.map(g=>fmt(g)+'%')],[-2,-1,0,1,2].map(d=>[fmt(m.discount+d)+'%',...gs.map(g=>{const r=researchDCF({...params,growth:m.base/100,discount:(m.discount+d)/100,terminal:g/100});return r?fmt(r.price):'—';})]));
  }paint();
}
function researchNotes(host,c,fields){
  host.append(el('p','note','Research notebook · your assumptions and judgements, saved locally in this browser. Add dated report links and evidence. Empty fields mean no sourced conclusion is available. No investment rating is generated.'));
  for(const label of fields){const wrap=el('label','note',label),input=el('textarea','field');input.rows=3;input.setAttribute('aria-label',label);const key='mt-research:'+c.symbol+':'+label;try{input.value=localStorage.getItem(key)||researchNotebook.get(key)||'';}catch(_){input.value=researchNotebook.get(key)||'';}input.placeholder='No sourced assessment entered. Record evidence, source URL and date.';const status=el('span','mini');input.oninput=()=>{researchNotebook.set(key,input.value);try{localStorage.setItem(key,input.value);status.textContent='Saved locally';}catch(_){status.textContent='Browser storage unavailable: kept for this session only';}};wrap.append(input,status);host.append(wrap);}
}
function renderEquityResearch(c){
  if(!$('research-nav')||!c)return;
  renderResearchStatements(c);renderResearchValuation(c);
  const business=$('research-business');business.replaceChildren();business.append(el('h3','','BUSINESS & COMPETITION'),el('p','note',c.businessSummary||'No sourced business description available.'),el('p','note',`Provider facts retrieved ${c.financialAsOf||'unknown'} · ${c.fundamentalSource||'unavailable'}. Industry: ${c.industry||'unknown'}. Peer comparisons below use the existing comparator; choose economically comparable businesses and verify fiscal periods.`));
  researchNotes(business,c,['Competitive advantages & supporting evidence','Competitors, market share & substitution threats','Capital allocation: reinvestment, acquisitions, dividends & buybacks']);
  const outlook=$('research-outlook');outlook.replaceChildren();outlook.append(el('h3','','OUTLOOK & CATALYSTS'));researchNotes(outlook,c,['Growth drivers & dated catalysts','Bear / base / bull operating thesis','Investment risks, disconfirming evidence & monitoring triggers']);
  const ownership=$('research-ownership');ownership.replaceChildren();ownership.append(el('h3','','OWNERSHIP & POSITIONING · PROVIDER FACTS'));researchTable(ownership,['Measure','Reported'],[['Insider holdings',pc(Number.isFinite(c.heldPercentInsiders)?c.heldPercentInsiders*100:null)],['Institutional holdings',pc(Number.isFinite(c.heldPercentInstitutions)?c.heldPercentInstitutions*100:null)],['Short interest / float',pc(Number.isFinite(c.shortPercentOfFloat)?c.shortPercentOfFloat*100:null)]]);ownership.append(el('p','note',`Retrieved ${c.financialAsOf||'unknown'}; provider observation dates unavailable. Holdings can reflect different filing periods and overlap; this is not a current ownership register.`));
  forensicState.symbol=c.symbol;renderForensic();
}
