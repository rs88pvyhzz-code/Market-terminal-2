/* Coverage facts and explicit gaps, never a blanket reliability rating. */
function companyCoverageFacts(c,now=Date.now()){
 const raw=c?.research?.annual||c?.annual||[];
 const rows=[...new Map(raw.filter(r=>/^\d{4}-\d{2}-\d{2}$/.test(r.fiscalEnd||'')&&Date.parse(r.fiscalEnd)<=now).map(r=>[r.fiscalEnd,r])).values()].sort((a,b)=>b.fiscalEnd.localeCompare(a.fiscalEnd));
 const usable=rows.filter(r=>Number.isFinite(r.revenue)&&Number.isFinite(r.netIncome)&&Number.isFinite(r.operatingCashFlow));
 const sources=(c?.intelligence?.sources||[]).filter(s=>/^https:\/\//.test(s.url||'')&&Number.isFinite(Date.parse(s.published))&&Date.parse(s.published)<=now);
 const latest=sources.filter(s=>s.kind==='results').sort((a,b)=>b.published.localeCompare(a.published))[0];
 const gaps=[];
 if(!latest)gaps.push('No dated results document');
 else if(now-Date.parse(latest.published)>210*86400000)gaps.push('Results document over 7 months old—check for newer release');
 if(usable.length<3)gaps.push('Only '+usable.length+' usable annual periods');
 if(rows.length>usable.length)gaps.push('Some annual periods lack revenue, net income or operating cash flow');
 if(rows.some((r,i)=>i&&Date.parse(rows[i-1].fiscalEnd)-Date.parse(r.fiscalEnd)>400*86400000))gaps.push('Gaps in annual history');
 if(!sources.length)gaps.push('No linked issuer evidence in research records');
 if(rows[0]&&now-Date.parse(rows[0].fiscalEnd)>550*86400000)gaps.push('Latest annual period over 18 months old');
 return {latest,period:rows[0]?.fiscalEnd||'Unavailable',usable:usable.length,total:rows.length,sources:sources.length,gaps};
}
function renderCompanyCoverage(c){
 const host=document.getElementById('research-overview');if(!host)return;
 let box=document.getElementById('company-coverage-gaps');if(!box){box=el('div','company-coverage-gaps');box.id='company-coverage-gaps';host.prepend(box);}
 const info=companyCoverageFacts(c);box.replaceChildren(el('strong','','RESEARCH COVERAGE'));
 box.append(el('p','mini','Latest annual period: '+info.period+' · '+info.usable+'/'+info.total+' periods with revenue, net income and operating cash flow · '+info.sources+' linked research documents'));
 if(info.latest){const a=el('a','','Results document: '+info.latest.published+' · period '+(info.latest.period||'not specified'));a.href=info.latest.url;a.target='_blank';a.rel='noopener noreferrer';box.append(a);}
 box.append(el('p','note',info.gaps.length?info.gaps.join(' · '):'No gaps found by these checks. Latest-release completeness has not been independently confirmed.'));
 box.append(el('small','mini','Source listing is not independent verification. History completeness does not establish comparability; reporting bases may differ.'));
}
const priorCoverageOverview=renderResearchOverview;
renderResearchOverview=function(c){priorCoverageOverview(c);renderCompanyCoverage(c);};
