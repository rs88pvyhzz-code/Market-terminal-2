// Runs inside the terminal closure and reuses its company, chart and forensic modules.
const researchViews=['Overview','Financials','Valuation','Business & Competition','Outlook & Catalysts','Red Flags & Ownership'];
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
function researchDCF({fcf,growth,discount,terminal,years,debt,cash,shares,fx,debtAdjustment=0}){
  if(![fcf,growth,discount,terminal,years,debt,cash,shares,fx,debtAdjustment].every(Number.isFinite)||fcf<=0||growth<=-1||discount<=terminal||discount<=0||terminal<=-1||shares<=0||fx<=0||debt<0||cash<0||!Number.isInteger(years)||years<1||years>20)return null;
  let pv=0,flow=fcf;const flows=[];
  for(let y=1;y<=years;y++){flow*=1+growth;const discounted=flow/(1+discount)**y;pv+=discounted;flows.push({year:y,flow,discounted});}
  const terminalPV=flow*(1+terminal)/(discount-terminal)/(1+discount)**years;
  const enterprise=pv+terminalPV,equity=enterprise-debt+cash-debtAdjustment;
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
function researchIsFinancial(c){return ['HSBA.L','HSBC','JPM','LLOY.L','BARC.L'].includes(c.symbol)||forensicIsFinancial(c);}
function researchFXValue(from,to,gbpUSD,gbpEUR){
  if(!from||!to)return null;if(from===to)return 1;
  const gbp={GBP:1,USD:Number.isFinite(gbpUSD)&&gbpUSD>0?1/gbpUSD:null,EUR:Number.isFinite(gbpEUR)&&gbpEUR>0?1/gbpEUR:null};
  return gbp[from]>0&&gbp[to]>0?gbp[from]/gbp[to]:null;
}
function researchFX(c){
  const date=(c.priceAsOf||D.generatedAt||'').slice(0,10),from=c.financialCurrency,to=['GBp','GBX'].includes(c.priceCurrency)?'GBP':c.priceCurrency;
  const series=symbol=>{const pts=histMap.get(symbol)||[];return pts.filter(p=>p.date<=date&&p.v>0&&Date.parse(date)-Date.parse(p.date)<=5*86400000).at(-1);};
  const usd=series('GBPUSD=X'),eur=series('GBPEUR=X'),value=researchFXValue(from,to,usd?.v,eur?.v);
  const needed=from===to?[]:[from,to].filter(x=>x!=='GBP');
  return {value,date:needed.length?needed.map(x=>x==='USD'?usd?.date:eur?.date).filter(Boolean).sort()[0]:date,source:from===to?'Same currency (identity)':'Yahoo observed FX via existing price history',from,to};
}
function researchBalance(c){
  const row=c.researchBalance;
  if(row&&row.currency===c.financialCurrency)return row;
  const annual=(c.annual||[]).find(r=>Number.isFinite(r.totalDebt)||Number.isFinite(r.cash))||{};
  const known=['SHEL.L','HSBA.L','MSFT'].includes(c.symbol);
  return {totalDebt:annual.totalDebt,cash:annual.cash,sharesOutstanding:known?annual.sharesOutstanding:null,period:annual.fiscalEnd,
    source:'Annual reported balances (fallback)',retrievedAt:c.financialAsOf,currency:c.financialCurrency,shareBasis:known?'ordinary quoted shares; 1:1':null};
}
function researchBalanceStale(balance,date){
  const age=(Date.parse(date)-Date.parse(balance.period))/86400000,retrieval=(Date.parse(date)-Date.parse(balance.retrievedAt))/86400000;
  const shareAge=(Date.parse(date)-Date.parse(balance.sharesPeriod||balance.period))/86400000,shareRetrieval=(Date.parse(date)-Date.parse(balance.sharesRetrievedAt||balance.retrievedAt))/86400000;
  return !Number.isFinite(age)||age<0||age>180||!Number.isFinite(retrieval)||retrieval>7||!Number.isFinite(shareAge)||shareAge<0||shareAge>180||!Number.isFinite(shareRetrieval)||shareRetrieval>7;
}
function researchData(c){return c.research||{annual:[],cagr:{},normalisedFCFF:null,normalisationPeriods:[],financialSector:researchIsFinancial(c)};}
function researchDetails(host,title,open=false){const detail=el('details','research-detail');detail.open=open;detail.append(el('summary','',title));host.append(detail);return detail;}
function researchCard(host,label,value,note){const card=el('div','research-card');card.append(el('span','mini',label),el('strong','',value),el('small','note',note));host.append(card);}
function researchTrend(value,suffix='%'){return Number.isFinite(value)?(value>0?'+':'')+fmt(value,1)+suffix:'—';}
function renderResearchOverview(c){
  const host=$('research-overview'),kpis=$('company-kpis');host.replaceChildren();const data=researchData(c),r=data.annual[0]||{},p=data.annual[1]||{},fin=researchIsFinancial(c),ccy=c.financialCurrency||'';
  const grid=el('div','research-dashboard');host.append(grid);
  researchCard(grid,'PRICE',Number.isFinite(c.price)?fmt(c.price,2)+' '+(c.priceCurrency||''):'—',pc(c.changePct)+' · '+(c.priceAsOf||'No quote'));
  const leverage=!fin&&Number.isFinite(r.totalDebt)&&Number.isFinite(r.cash)?researchRatio(r.totalDebt-r.cash,r.ebitda):null;
  researchCard(grid,'FINANCIAL STRENGTH',fin?'Sector review':leverage==null?'—':fmt(leverage,2)+'× net debt / EBITDA',fin?'Banks: review regulatory capital and liquidity in issuer reports.':leverage==null?'Requires debt, cash and positive EBITDA.':leverage<0?'Net cash (cash exceeds debt).':leverage>3?'Above 3× screening threshold; inspect maturities.':'At or below 3× screening threshold; not a credit rating.');
  const marginChange=Number.isFinite(r.operatingMargin)&&Number.isFinite(p.operatingMargin)?r.operatingMargin-p.operatingMargin:null;
  researchCard(grid,'PROFITABILITY',fin?pc(r.roe):pc(r.roic),fin?'Calculated ROE; not RoTE.':'Calculated ROIC · operating margin '+pc(r.operatingMargin)+(marginChange==null?'':' · '+researchTrend(marginChange,'pp')+' YoY'));
  researchCard(grid,'REVENUE GROWTH',pc(r.growth?.revenue),'YoY · '+(data.cagrPeriods?.revenue?.years||0)+'y CAGR '+pc(data.cagr?.revenue));
  researchCard(grid,'CASH GENERATION',fin?'Sector review':companyAmount(r.fcf,ccy),fin?'Generic corporate FCF excluded for financial companies.':'Calculated OCF − |capex| · conversion '+(Number.isFinite(r.cashConversion)?fmt(r.cashConversion,2)+'×':'—'));
  researchCard(grid,'VALUATION',c.trailingPE>0?fmt(c.trailingPE,1)+'× P/E':'—',fin?'P/B '+(c.priceToBook>0?fmt(c.priceToBook,2)+'×':'—'):'EV / EBITDA '+(c.enterpriseToEbitda>0?fmt(c.enterpriseToEbitda,1)+'×':'—')+' · observed provider ratios');
  host.append(el('p','note',`Accounts: ${r.fiscalEnd||'unavailable'} · ${ccy||'currency unknown'} · retrieved ${String(c.financialAsOf||'unknown').slice(0,10)}. Facts and calculated measures; no composite score or investment rating.`));
  const detail=researchDetails(host,'All reported snapshot metrics & source methodology');if(kpis)detail.append(kpis);
  const rules=researchDetails(host,'Dashboard rules');rules.append(el('p','note','Financial strength uses (reported debt − cash) / positive EBITDA; 3× is a visible screening threshold, not a sector rating. ROIC uses after-tax operating profit over average equity + debt − cash; ROE uses profit / average equity. Growth compares adjacent annual periods only. Cash conversion is operating cash flow / positive shareholder net profit. No missing value is treated as zero. Banks and insurers require regulatory measures not available from generic accounts.'));
}

function setupResearchViews(){
  if($('research-nav'))return;
  const root=$('companies'),nav=el('div','period-controls');nav.id='research-nav';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','Company research views');root.append(nav);
  researchViews.forEach((name,i)=>{const b=el('button','btn',name);b.id='research-tab-'+i;b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-controls','research-view-'+i);b.onclick=()=>showResearchView(i);b.onkeydown=e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?researchViews.length-1:(i+(e.key==='ArrowRight'?1:-1)+researchViews.length)%researchViews.length;showResearchView(n);$('research-tab-'+n).focus();}};nav.append(b);const v=el('section','research-view');v.id='research-view-'+i;v.setAttribute('role','tabpanel');v.setAttribute('aria-labelledby',b.id);root.append(v);});
  const move=(id,i)=>{if($(id))$('research-view-'+i).append($(id));};
  move('company-kpis',0);move('company-news-panel',0);
  const main=root.querySelector('.company-main'),income=main?.querySelector('.company-fin');if(income){const legacy=researchDetails($('research-view-1'),'Additional provider financials');legacy.dataset.legacyIncome='true';legacy.append(income);};if(main){main.id='company-price-block';$('research-view-0').append(main);}
  move('company-risk-panel',0);move('peer-panel',3);move('company-events-panel',4);move('forensic-panel',5);
  const risk=$('company-risk-panel'),benchmark=el('section','research-benchmark');benchmark.id='company-benchmark-block';
  benchmark.append($('company-benchmark-range').closest('.row'),$('company-benchmark-note'),$('company-benchmark-chart'));$('research-view-0').append(benchmark);
  const advanced=researchDetails($('research-view-0'),'Advanced Analytics · RSI and moving averages');advanced.id='company-advanced';const tech=el('div','watchlist-kpis');tech.id='company-technical-kpis';advanced.append(tech);const method=risk.querySelector(':scope > p:last-child');if(method)advanced.append(method);risk.querySelector('h3').textContent='VOLATILITY & MARKET RISK';
  // Keep the established accounting renderer, always tied to the selected company.
  $('forensic-panel').querySelector('.research-controls').hidden=true;
  $('forensic-panel').querySelector('h2').textContent='ACCOUNTING CHECKS';
  for(const [i,id] of [[0,'research-overview'],[1,'research-statements'],[2,'research-valuation'],[3,'research-business'],[4,'research-outlook'],[5,'research-ownership']]){const node=el('div');node.id=id;$('research-view-'+i).prepend(node);}
  const legacyNote=root.querySelector(':scope > p.note');if(legacyNote){const d=researchDetails($('research-view-0'),'Data coverage & methodology');d.id='company-coverage';d.append(legacyNote);}
  showResearchView(0);renderEquityResearch(ensureCompany(state.companySymbol));
}
function showResearchView(i){
  researchView=i;researchViews.forEach((_,j)=>{const b=$('research-tab-'+j);b.setAttribute('aria-selected',String(i===j));b.tabIndex=i===j?0:-1;b.classList.toggle('active',i===j);$('research-view-'+j).hidden=i!==j;});
  if(i===0||i===1)requestAnimationFrame(()=>{renderCompany();});
}
function researchTable(host,headers,rows){
  const annual=headers.length>1&&headers.slice(1).every(s=>/^FY \d{4}$/.test(s));
  const scroll=el('div','small-scroll'),t=el('table','watch research-table'+(annual?' research-table--annual':''));
  if(annual){t.style.setProperty('--research-year-count',headers.length-1);const columns=el('colgroup');headers.forEach((_,i)=>{const col=el('col');col.style.width=(i?66/(headers.length-1):34)+'%';columns.append(col);});t.append(columns);}
  const head=el('thead'),tr=el('tr');headers.forEach((s,i)=>{const th=el('th',i?'n':'',s);th.scope='col';tr.append(th);});head.append(tr);t.append(head);
  const body=el('tbody');rows.forEach(cells=>{const row=el('tr');cells.forEach((s,i)=>row.append(el('td',i?'n':'',s)));body.append(row);});t.append(body);scroll.append(t);host.append(scroll);
}
let researchFinancialYears=5;
function renderResearchStatements(c){
  const host=$('research-statements');host.replaceChildren();const data=researchData(c),all=data.annual||[],ccy=c.financialCurrency||'',fin=researchIsFinancial(c);
  host.append(el('h3','','FINANCIAL ANALYSIS'));
  const controls=el('div','period-controls research-periods');host.append(controls);
  for(const years of [1,3,5,10]){const b=el('button','btn'+(researchFinancialYears===years?' active':''),years+'Y');b.disabled=all.length<years;b.title=b.disabled?`${years} annual periods are not available`:years+' annual periods';b.onclick=()=>{researchFinancialYears=years;renderResearchStatements(c);};controls.append(b);}
  const rows=all.slice(0,researchFinancialYears);
  host.append(el('p','note',`${all.length} of 5 annual periods sourced · ${ccy||'currency unknown'} · retrieved ${String(c.financialAsOf||'unknown').slice(0,10)}. Reported inputs + calculated growth and returns. 10Y is enabled only with sufficient data.`));
  const compact=el('div','research-dashboard');host.append(compact);const L=all[0]||{};
  for(const [label,value,note] of [['Revenue',companyAmount(L.revenue,ccy),'YoY '+pc(L.growth?.revenue)],['EBITDA',fin?'Sector excluded':companyAmount(L.ebitda,ccy),L.ebitdaKind||'Unavailable'],['Operating profit',companyAmount(L.operatingProfit,ccy),'Margin '+pc(L.operatingMargin)],['FCF',fin?'Sector excluded':companyAmount(L.fcf,ccy),'Calculated OCF − |capex|']])researchCard(compact,label,value,note);
  const pct=v=>pc(v),multiple=v=>Number.isFinite(v)?fmt(v,2)+'×':'—';
  researchTable(host,['Calculated metric',...rows.map(r=>'FY '+r.fiscalYear)],
    [['Revenue growth',r=>pct(r.growth?.revenue)],['EBITDA growth',r=>fin?'—':pct(r.growth?.ebitda)],['Operating profit growth',r=>pct(r.growth?.operatingProfit)],['OCF growth',r=>fin?'—':pct(r.growth?.operatingCashFlow)],['FCF growth',r=>fin?'—':pct(r.growth?.fcf)],['Gross margin',r=>fin?'—':pct(r.grossMargin)],['Operating margin',r=>pct(r.operatingMargin)],['Net margin',r=>pct(r.netMargin)],['FCF margin',r=>fin?'—':pct(r.fcfMargin)],['Cash conversion',r=>fin?'—':multiple(r.cashConversion)],['ROIC',r=>fin?'—':pct(r.roic)],['ROE',r=>pct(r.roe)],['Debt / equity',r=>fin?'—':multiple(r.debtToEquity)],['Debt growth',r=>fin?'—':pct(r.growth?.totalDebt)],['Share-count growth',r=>pct(r.growth?.sharesOutstanding)]].map(([name,fn])=>[name,...rows.map(fn)]));
  const growth=researchDetails(host,'CAGR · calculated over sourced intervals');
  researchTable(growth,['Metric','CAGR','Period'],[['Revenue','revenue'],['EBITDA','ebitda'],['Operating profit','operatingProfit'],['Operating cash flow','operatingCashFlow'],['FCF','fcf'],['Shares outstanding','sharesOutstanding']].map(([name,k])=>[name,fin&&['ebitda','operatingCashFlow','fcf'].includes(k)?'—':pc(data.cagr?.[k]),data.cagrPeriods?.[k]?.start&&data.cagrPeriods?.[k]?.end?`${data.cagrPeriods[k].start} → ${data.cagrPeriods[k].end}`:'—']));
  growth.append(el('p','note','CAGR uses the actual interval between oldest and latest available fiscal dates and positive endpoints. Growth from a zero/negative base is not meaningful and stays blank. Margin trends are percentage-point changes; cash conversion requires positive net profit.'));
  const groupsForCharts=[
    ['research-financial-chart','REVENUE',ccy,[['Revenue','revenue',AMBER]]],
    ['research-cash-chart','OPERATING PROFIT & CASH FLOWS',ccy,[['Operating profit','operatingProfit',BLUE],['Operating cash flow','operatingCashFlow',AQUA],['FCF','fcf',UP]].filter(x=>!fin||x[1]==='operatingProfit')],
    ['research-margin-chart','PROFIT MARGINS','%',[['Operating margin','operatingMargin',AMBER],['FCF margin','fcfMargin',AQUA]].filter(x=>!fin||x[1]!=='fcfMargin')],
    ['research-return-chart',fin?'RETURN ON EQUITY':'RETURN ON INVESTED CAPITAL','%',[[fin?'ROE':'ROIC',fin?'roe':'roic',BLUE]]]
  ];
  for(const [id,title,unit,fields] of groupsForCharts){
    host.append(el('h3','',title));const legend=el('div','r25-chart-legend');
    fields.forEach(([name,key,color])=>{const label=el('span','',name);label.style.borderLeft='3px solid '+color;legend.append(label);});
    legend.append(el('span','mini',unit+' · '+(rows.at(-1)?.fiscalEnd||'—')+' → '+(rows[0]?.fiscalEnd||'—')));host.append(legend);
    const node=el('div','chart r25-financial-chart');node.id=id;host.append(node);
    chart(id,fields.map(([name,key,color])=>({name,color,pts:rows.slice().reverse().map(r=>({date:r.fiscalEnd,v:r[key]})).filter(p=>Number.isFinite(p.v))})),{height:225,format:v=>unit==='%'?fmt(v,2)+'%':companyAmount(v,ccy)});
  }
  const detail=researchDetails(host,'Detailed annual financial statements · reported inputs');
  const groups=[['Income statement',[['Revenue','revenue'],['Gross profit','grossProfit'],['EBITDA (provider or calculated)','ebitda'],['Operating profit','operatingProfit'],['Pre-tax profit','pretaxProfit'],['Tax expense','taxExpense'],['Interest expense','interestExpense'],['Shareholder net profit','netProfit']]],['Balance sheet',[['Assets','totalAssets'],['Liabilities','totalLiabilities'],['Equity','equity'],['Current assets','currentAssets'],['Current liabilities','currentLiabilities'],['Debt','totalDebt'],['Cash','cash'],['Receivables','receivables'],['Inventory','inventory'],['Goodwill','goodwill'],['Shares outstanding (millions)','sharesOutstanding']]],['Cash flow & allocation',[['Operating cash flow','operatingCashFlow'],['Capital expenditure','capex'],['Investing cash flow','investingCashFlow'],['Financing cash flow','financingCashFlow'],['D&A','depreciation'],['Working-capital cash contribution','workingCapitalCashChange'],['Dividends paid','dividendsPaid'],['Buybacks','buybacks'],['Share-based pay','shareBasedComp']]]];
  for(const [title,fields] of groups){detail.append(el('h3','',title));researchTable(detail,['Metric',...rows.map(r=>'FY '+r.fiscalYear)],fields.map(([name,key])=>[name,...rows.map(r=>key==='sharesOutstanding'?(Number.isFinite(r[key])?fmt(r[key]/1e6,2):'—'):fin&&key==='ebitda'?'—':companyAmount(r[key],ccy))]));}
  const sources=researchDetails(host,'Field-level sources, filing dates & definitions');
  sources.append(el('p','note','SEC issuer filings take precedence by matching fiscal date and currency. Later restated facts can replace earlier values; this is a latest-restated financial view, not a point-in-time backtest. Yahoo supplies unmapped fields. FCF = OCF − |capex| differs from issuer-specific FCF definitions (including Shell). EBITDA is not adjusted EBITDA. ROIC = EBIT × (1 − effective tax rate) / average (equity + debt − cash). Financial companies exclude generic corporate FCF, EBITDA leverage and ROIC.'));
  const labels={revenue:'Revenue',operatingProfit:'Operating profit',netProfit:'Net profit',totalDebt:'Debt',cash:'Cash',sharesOutstanding:'Shares',operatingCashFlow:'OCF',capex:'Capex',depreciation:'D&A',workingCapitalCashChange:'Working-capital cash contribution'};
  for(const r of rows){const period=researchDetails(sources,r.fiscalEnd+' · source register');researchTable(period,['Field','Source','Period','Filed','Retrieved'],[...new Set([...Object.keys(labels),...Object.keys(r.provenance||{})])].map(k=>{const p=r.provenance?.[k]||{};return [labels[k]||k,p.source||'Unavailable',p.period||r.fiscalEnd,p.filed||'Not supplied',String(p.retrievedAt||'Unknown').slice(0,10)];}));for(const p of Object.values(r.provenance||{})){if(p.url?.startsWith('https://www.sec.gov/')){const a=el('a','company-link','OPEN ISSUER FILING · '+(p.filed||''));a.href=p.url;a.target='_blank';a.rel='noopener noreferrer';period.append(a);break;}}}
}

function researchInput(host,label,value,onchange){const wrap=el('label','mini',label+' '),input=el('input','field');input.type='number';input.step='any';input.value=value??'';input.setAttribute('aria-label',label);input.name='research_'+state.companySymbol+'_'+(host.closest('[id]')?.id||'model')+'_'+label.toLowerCase().replace(/[^a-z0-9]+/g,'_');input.id=input.name;input.autocomplete='off';input.setAttribute('form','mt-research-form');if(!$('mt-research-form')){const form=el('form');form.id='mt-research-form';form.autocomplete='off';form.onsubmit=()=>false;document.body.append(form);}input.oninput=()=>onchange(input.value===''?null:Number(input.value));wrap.append(input);host.append(wrap);return input;}
let researchMultipleYears=5;
function renderResearchMultiples(host,c){
  const detail=researchDetails(host,'Historical valuation multiples · observed snapshots',true),history=c.valuationHistory||[];
  detail.append(el('p','note','P/E, EV/EBITDA and P/B are saved when sourced during scheduled builds. History starts at the first observed snapshot; current ratios are never copied backwards. Dates are retrieval dates, not financial periods.'));
  if(!history.length){detail.append(el('p','note','No observed multiple snapshots available yet.'));return;}
  const last=history.at(-1).date,span=(Date.parse(last)-Date.parse(history[0].date))/86400000;
  const controls=el('div','period-controls research-periods');detail.append(controls);
  for(const years of [1,3,5,10]){const b=el('button','btn',years+'Y');b.disabled=history.length<12||span<years*365.25;b.onclick=()=>{researchMultipleYears=years;renderResearchValuation(c);};controls.append(b);}
  const rows=history.filter(r=>Date.parse(last)-Date.parse(r.date)<=researchMultipleYears*365.25*86400000);
  const table=researchDetails(detail,`${rows.length} observed snapshot(s) · latest ${last}`,true);researchTable(table,['Observed','P/E TTM','EV / EBITDA','P/B'],rows.slice(-12).reverse().map(r=>[r.date,...['trailingPE','enterpriseToEbitda','priceToBook'].map(k=>k==='enterpriseToEbitda'&&researchIsFinancial(c)?'—':r[k]>0?fmt(r[k],2)+'×':'—')]));
  if(rows.length>=12&&(Date.parse(rows.at(-1).date)-Date.parse(rows[0].date))/86400000>=90){const node=el('div','chart');node.id='research-multiples-chart';detail.append(node);chart(node.id,[['P/E','trailingPE',AMBER],['EV/EBITDA','enterpriseToEbitda',BLUE],['P/B','priceToBook',AQUA]].filter(x=>!researchIsFinancial(c)||x[1]!=='enterpriseToEbitda').map(([name,k,color])=>({name,color,pts:rows.filter(r=>r[k]>0).map(r=>({date:r.date,v:r[k]}))})),{format:v=>fmt(v,2)+'×'});}
  else detail.append(el('p','note','Dated table shown until at least 12 observations span 90 days. Sparse snapshots are not a historical trend.'));
}
function renderResearchValuation(c){
  const host=$('research-valuation');host.replaceChildren();host.append(el('h3','','VALUATION · SOURCED INPUTS / CALCULATIONS / ASSUMPTIONS'));
  if(researchIsFinancial(c)){host.append(el('p','note','Standard FCFF DCF excluded for banks and insurers. Review regulatory capital, liquidity, RoTE and excess-return or dividend valuation using issuer disclosures.'));renderResearchMultiples(host,c);researchR2Stress(c,host);return;}
  const data=researchData(c),balance=researchBalance(c),fx=researchFX(c),quote=fx.to,asof=(D.generatedAt||'').slice(0,10),stale=researchBalanceStale(balance,asof);
  if(!researchModels.has(c.symbol))researchModels.set(c.symbol,{fcf:Number.isFinite(data.normalisedFCFF)?data.normalisedFCFF/1e6:null,adjustment:0,debt:Number.isFinite(balance.totalDebt)?balance.totalDebt/1e6:null,cash:Number.isFinite(balance.cash)?balance.cash/1e6:null,shares:balance.sharesOutstanding??null,fx:fx.value,years:5,terminal:2,bear:0,base:5,bull:10,discount:10,debtAdjustment:Number.isFinite(balance.debtAdjustment)?balance.debtAdjustment/1e6:0,acceptDated:false,overrides:new Set()});
  const m=researchModels.get(c.symbol);
  const provenance=researchDetails(host,`Dated sources · balance ${balance.period||'unknown'} · shares ${balance.sharesPeriod||balance.period||'unknown'}`);provenance.classList.add('research-provenance');
  const integrity=c.valuationIntegrity;
  if(integrity?.issues?.length){const warning=el('p','research-warning','VALUATION REQUIRES SOURCE REVIEW · '+(c.filingWarning?'Live primary refresh failed; values below include retained dated evidence. ':'')+'Incomplete or unverified inputs affect this valuation. Open source status before relying on model values.');host.insertBefore(warning,provenance);const status=researchDetails(provenance,'Source status · affected inputs and retrieval dates');for(const issue of integrity.issues)status.append(el('p','note',issue));const groups=new Map();for(const item of integrity.components||[]){const key=[item.period,item.source||'unavailable',item.retrievedAt||'unknown'].join(' · ');if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item);}for(const [key,items] of groups){const row=el('p','note',key+' · '+items.map(x=>x.field).join(', ')+' ');const url=items.find(x=>x.url?.startsWith('https://'))?.url;if(url){const a=el('a','research-source','OPEN COMPONENT SOURCE');a.href=url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);}status.append(row);}}
  provenance.append(el('p','note',`Reported balance: ${balance.period||'unavailable'} · ${balance.source||'unavailable'} · published ${balance.published||'not supplied'} · retrieved ${String(balance.retrievedAt||'unknown').slice(0,10)}. Shares: ${balance.shareBasis||'basis unverified; enter a verified quoted share count'}.`));
  provenance.append(el('p','note',`Ordinary shares: ${Number.isFinite(balance.sharesOutstanding)?fmt(balance.sharesOutstanding,0):'unavailable'} · as of ${balance.sharesPeriod||balance.period||'unknown'} · ${balance.sharesSource||balance.source||'unavailable'} · published ${balance.sharesPublished||'not supplied'} · retrieved ${String(balance.sharesRetrievedAt||balance.retrievedAt||'unknown').slice(0,10)}.`));
  if(Number.isFinite(balance.reportedNetDebt))provenance.append(el('p','note',`Issuer net debt: ${companyAmount(balance.reportedNetDebt,c.financialCurrency)} = gross debt − cash + debt-related derivatives/collateral (${companyAmount(balance.debtAdjustment,c.financialCurrency)}). These financing adjustments are separate from FCFF normalisation.`));
  for(const [url,label] of [[balance.url,'ISSUER DEBT RECONCILIATION'],[balance.sharesUrl,'ISSUER SHARE CAPITAL']]){if(url?.startsWith('https://')){const a=el('a','company-link',label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';provenance.append(a);}}
  provenance.append(el('p','note',`FX: ${fx.value==null?'unavailable':fmt(fx.value,6)} ${quote||'?'} per ${c.financialCurrency||'?'} · observed ${fx.date||'unknown'} · ${fx.source}. Market quotes in GBp/GBX divide by 100; statements and market capitalisation do not.`));
  if(stale){const label=el('label','note research-warning'),check=el('input');check.type='checkbox';check.checked=m.acceptDated;check.setAttribute('aria-label','Use dated balances after review');check.onchange=()=>{m.acceptDated=check.checked;paint();};label.append(check,document.createTextNode(' Balance data are old (>180 days), not recently retrieved (>7 days), or undated. Review and explicitly accept these dated inputs to use the model. They are not current balances.'));host.append(label);}
  if(Number.isFinite(balance.leaseLiabilities))provenance.append(el('p','note',`Total debt includes ${companyAmount(balance.leaseLiabilities,c.financialCurrency)} lease liabilities. Historical FCFF is not fully adjusted for new lease commitments or acquired businesses; review forward reinvestment and lease assumptions.`));
  const bridge=researchDetails(host,'Normalised FCFF calculation & limitations');
  bridge.append(el('p','note',data.fcffMethod||'No complete sourced FCFF calculation available.'));
  researchTable(bridge,['Fiscal period','EBIT','NOPAT','D&A','Capex outflow','WC cash contribution','FCFF proxy'],(data.annual||[]).slice(0,3).map(r=>[r.fiscalEnd,...['operatingProfit','nopat','depreciation','capex','workingCapitalCashChange','fcffProxy'].map(k=>Number.isFinite(r[k])?fmt((k==='capex'?-Math.abs(r[k]):r[k])/1e6,2):'—')]));
  bridge.append(el('p','note',`Reporting-currency millions. Median starting point: ${Number.isFinite(data.normalisedFCFF)?fmt(data.normalisedFCFF/1e6,2):'unavailable'} from ${(data.normalisationPeriods||[]).join(', ')||'no complete periods'}. No adjustment for impairments, disposals, noncash lease additions, acquisitions or non-operating D&A is invented. Review cash-flow classification and add documented adjustments. Missing working-capital data prevents automatic FCFF.`));
  researchTable(bridge,['Fiscal period','Operating cash flow','− |Capex|','OCF − capex FCF','OCF → operating proxy bridge','FCFF proxy'],(data.annual||[]).slice(0,3).map(r=>[r.fiscalEnd,...['operatingCashFlow','capex','fcf','ocfToFcffBridge','fcffProxy'].map(k=>Number.isFinite(r[k])?fmt((k==='capex'?-Math.abs(r[k]):r[k])/1e6,2):'—')]));
  bridge.append(el('p','note','The OCF-to-operating-proxy bridge is the calculated residual NOPAT + D&A + working-capital cash contribution − reported OCF. It reconciles the measures mathematically; it is not a separately reported adjustment. Cash taxes versus tax expense, joint ventures, noncash items and classifications need review. Historical normalisation is not a forecast of the current acquired business portfolio.'));
  const inputs=el('div','research-inputs');host.append(inputs);const output=el('div');output.setAttribute('aria-live','polite');
  const fields=[['Normalised FCFF (reporting currency, millions)','fcf'],['FCFF adjustment (reporting millions, assumption)','adjustment'],['Debt (reporting currency, millions)','debt'],['Cash (reporting currency, millions)','cash'],['Debt-related adjustment (reporting millions)','debtAdjustment'],['Shares outstanding (absolute count)','shares'],[`FX: ${quote||'quote major currency'} per ${c.financialCurrency||'reporting currency'}`,'fx'],['Forecast years (1–20)','years'],['Discount rate / WACC (%)','discount'],['Terminal growth (%)','terminal'],['Bear FCFF growth (%)','bear'],['Base FCFF growth (%)','base'],['Bull FCFF growth (%)','bull']];
  const reported=new Set(['debt','cash','shares','fx',...(Number.isFinite(balance.debtAdjustment)?['debtAdjustment']:[])]),calculated=new Set(['fcf']);
  const badges=[];
  for(const [label,key] of fields){const input=researchInput(inputs,label,m[key],v=>{m[key]=v;m.overrides.add(key);paint();});const tag=el('small','research-input-kind');input.parentElement.append(tag);badges.push([key,tag]);}
  const reset=el('button','btn','RESET TO SOURCED INPUTS');reset.type='button';reset.onclick=()=>{researchModels.delete(c.symbol);renderResearchValuation(c);};host.append(reset);
  host.append(el('p','note','Growth, WACC and terminal growth defaults are illustrative user assumptions, not forecasts. Adjustment defaults to zero (none applied). Debt/cash/shares stay dated to the balance above. Values per share use the quote major currency. Other claims and dilution require review.'),output);
  function paint(){
    researchR2Stress(c,host);researchR2Executive(c);
    for(const [key,tag] of badges)tag.textContent=m.overrides.has(key)?'User assumption / override':reported.has(key)?'Sourced · dated above':calculated.has(key)?'Calculated · FCFF bridge':'User assumption';
    output.replaceChildren();
    if(stale&&!m.acceptDated){output.append(el('p','research-warning','Valuation paused until dated balances are reviewed and accepted.'));return;}
    if(!['fcf','adjustment','debt','cash','shares','fx','debtAdjustment','years','discount','terminal','bear','base','bull'].every(k=>Number.isFinite(m[k]))||!quote||!c.financialCurrency){output.append(el('p','research-warning','Incomplete sourced inputs. Enter verified missing values as explicit user assumptions. No valuation is fabricated.'));return;}
    const params={...m,fcf:m.fcf+m.adjustment,discount:m.discount/100,terminal:m.terminal/100},base=researchDCF({...params,growth:m.base/100});
    if(!base||m.bear<=-100||m.bear>m.base||m.base>m.bull){output.append(el('p','research-warning','Invalid assumptions: adjusted FCFF, shares and FX must be positive; debt/cash non-negative; WACC > terminal growth; integer years 1–20; growth > −100%; bear ≤ base ≤ bull.'));return;}
    const market=researchQuoteMajor(c.price,c.priceCurrency);
    output.append(el('p','note',`FCFF used (reporting m): ${fmt(m.fcf,2)} starting point + ${fmt(m.adjustment,2)} user adjustment = ${fmt(params.fcf,2)}. ${m.overrides.has('fcf')?'Starting point overridden by user.':'Starting point calculated from sourced annual components.'}`));
    researchTable(output,['Scenario','FCFF growth',`Value/share ${quote}`,'vs market price'],['bear','base','bull'].map(k=>{const r=researchDCF({...params,growth:m[k]/100});return [k.toUpperCase(),pc(m[k]),r?fmt(r.price,2):'—',r&&market>0?pc((r.price/market-1)*100):'—'];}));
    output.append(el('p','note',`Observed quote: ${market==null?'unavailable':fmt(market,2)+' '+quote} · ${c.priceAsOf||'date unknown'}. Base terminal value: ${fmt(base.terminalPV/base.enterprise*100,1)}% of enterprise value. Model outputs are calculated, not investment ratings.`));
    const projected=researchDetails(output,'Projected FCFF & enterprise-to-equity bridge · assumptions');researchTable(projected,['Year','FCFF (reporting m)','Present value'],base.flows.map(r=>[String(r.year),fmt(r.flow,2),fmt(r.discounted,2)]));researchTable(projected,['Model bridge','Reporting-currency m'],[['Enterprise value',fmt(base.enterprise,2)],['Less debt',fmt(m.debt,2)],['Plus cash',fmt(m.cash,2)],['Less debt-related adjustment',fmt(m.debtAdjustment,2)],['Net financing deduction',fmt(m.debt-m.cash+m.debtAdjustment,2)],['Equity value',fmt(base.equity,2)]]);
    const implied=researchReverse(params,market);output.append(el('h3','','REVERSE DCF'),el('p','note',implied==null?'No solution in −90% to +100% growth, or market price unavailable.':`Market price implies ${fmt(implied*100,2)}% annual FCFF growth for ${m.years} years, with all other inputs fixed. An implied assumption, not a forecast.`));
    const sensitivity=researchDetails(output,'Sensitivity · value/share by WACC and terminal growth',true),gs=[m.terminal-1,m.terminal,m.terminal+1];researchTable(sensitivity,['WACC / g',...gs.map(g=>fmt(g,1)+'%')],[-2,-1,0,1,2].map(d=>[fmt(m.discount+d,1)+'%',...gs.map(g=>{const r=researchDCF({...params,growth:m.base/100,discount:(m.discount+d)/100,terminal:g/100});return r?fmt(r.price,2):'—';})]));
  }
  paint();renderResearchMultiples(host,c);
}

function researchNotes(host,c,fields){
  const notebook=researchDetails(host,'My research notes');notebook.classList.add('research-notebook');host=notebook;
  host.append(el('p','note','Research notebook · your assumptions and judgements, saved locally in this browser. Add dated report links and evidence. Empty fields mean no sourced conclusion is available. No investment rating is generated.'));
  for(const label of fields){const wrap=el('label','note',label),input=el('textarea','field');input.rows=3;input.setAttribute('aria-label',label);const key='mt-research:'+c.symbol+':'+label;try{input.value=localStorage.getItem(key)||researchNotebook.get(key)||'';}catch(_){input.value=researchNotebook.get(key)||'';}input.placeholder='No sourced assessment entered. Record evidence, source URL and date.';const status=el('span','mini');input.oninput=()=>{researchNotebook.set(key,input.value);try{localStorage.setItem(key,input.value);status.textContent='Saved locally';}catch(_){status.textContent='Browser storage unavailable: kept for this session only';}};wrap.append(input,status);host.append(wrap);}
}
function renderEquityResearch(c){
  if(!$('research-nav')||!c)return;
  renderResearchOverview(c);renderResearchStatements(c);renderResearchValuation(c);
  const business=$('research-business');researchR2Business(c,business);
  researchNotes(business,c,['Competitive advantages & supporting evidence','Competitors, market share & substitution threats','Capital allocation: reinvestment, acquisitions, dividends & buybacks']);
  const outlook=$('research-outlook');researchR2Outlook(c,outlook);
  researchNotes(outlook,c,['Growth drivers & dated catalysts','Bear / base / bull operating thesis','Investment risks, disconfirming evidence & monitoring triggers']);
  const ownership=$('research-ownership');ownership.replaceChildren();ownership.append(el('h3','','OWNERSHIP & POSITIONING · PROVIDER FACTS'));researchTable(ownership,['Measure','Reported'],[['Insider holdings',pc(Number.isFinite(c.heldPercentInsiders)?c.heldPercentInsiders*100:null)],['Institutional holdings',pc(Number.isFinite(c.heldPercentInstitutions)?c.heldPercentInstitutions*100:null)],['Short interest / float',pc(Number.isFinite(c.shortPercentOfFloat)?c.shortPercentOfFloat*100:null)]]);ownership.append(el('p','note',`Retrieved ${c.financialAsOf||'unknown'}; provider observation dates unavailable. Holdings can reflect different filing periods and overlap; this is not a current ownership register.`));
  forensicState.symbol=c.symbol;renderForensic();researchR2Render(c);researchArrangeOverview();
}
