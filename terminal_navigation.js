// Release 2.2 navigation: move existing panels; no financial calculations.
const terminalSubViews={fx:[['prices','Prices & Markets',['monitor','movers']],['news','News',['news']],['analytics','Risk & Relative Performance',['analytics-rolling','market-valuations','compare','score-panel','analytics-breadth','analytics-sectors']]],equities:[['screen','Screening & Constituents',['equity-screener','constituents']],['research','Company Research',['companies','peer-panel','company-news-panel','company-events-panel','forensic-panel']]]};
let terminalNavSaved={};try{terminalNavSaved=JSON.parse(localStorage.getItem('market-terminal-navigation-v2')||'{}');}catch{}
const terminalSubSelection={fx:terminalNavSaved.fx||'prices',equities:terminalNavSaved.equities||'screen'};
function terminalBuildSubViews(view,key){
 const nav=el('nav','terminal-subnav');nav.setAttribute('aria-label',key==='equities'?'Equities and Research sections':'Markets sections');nav.setAttribute('role','tablist');view.append(nav);
 terminalSubViews[key].forEach(([name,label,ids],i)=>{const button=el('button','btn',label);button.id='sub-'+key+'-'+name;button.type='button';button.setAttribute('role','tab');button.setAttribute('aria-controls','subview-'+key+'-'+name);button.onclick=()=>activateWorkspace(key,{subview:name,scroll:false});button.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const choices=terminalSubViews[key],index=e.key==='Home'?0:e.key==='End'?choices.length-1:(i+(e.key==='ArrowRight'?1:-1)+choices.length)%choices.length;activateWorkspace(key,{subview:choices[index][0],scroll:false});$('sub-'+key+'-'+choices[index][0]).focus();};nav.append(button);
 const child=el('section','terminal-subview');child.id='subview-'+key+'-'+name;child.setAttribute('role','tabpanel');child.setAttribute('aria-labelledby',button.id);for(const id of ids){const node=$(id);if(node)child.append(node);}view.append(child);});
 terminalSetSubView(key,terminalSubSelection[key]);
}
function terminalSetSubView(key,name){
 const choices=terminalSubViews[key];if(!choices)return;
 if(!choices.some(x=>x[0]===name))name=choices[0][0];terminalSubSelection[key]=name;
 for(const [id] of choices){const chosen=id===name;const panel=$('subview-'+key+'-'+id),button=$('sub-'+key+'-'+id);if(panel)panel.hidden=!chosen;if(button){button.setAttribute('aria-selected',String(chosen));button.tabIndex=chosen?0:-1;}}
 try{localStorage.setItem('market-terminal-navigation-v2',JSON.stringify(terminalSubSelection));}catch{}
}
function terminalResolveRoute(route){
 const [key,subview]=route.split(':');
 if(key==='equities'&&subview==='analytics')return {key:'fx',subview:'analytics'};
 const researchSection={'peer-panel':3,'company-events-panel':4,'forensic-panel':5};
 if(Object.hasOwn(researchSection,key))return {key:'equities',subview:'research',researchView:researchSection[key]};
 if(key==='companies')return {key:'equities',subview:'research'};
 if(key==='analytics')return {key:'fx',subview:'analytics'};
 if(key==='markets')return {key:'fx',subview:subview||'prices'};
 if(WORKSPACES.includes(key))return {key,subview};
 const section=workspaceForSection[key];return section?terminalResolveRoute(section):{key:'overview'};
}
function researchArrangeOverview(){
 const host=$('research-view-0');if(!host)return;
 for(const id of ['company-price-block','company-benchmark-block','research-overview','company-risk-panel','research-executive','company-advanced','company-news-panel','company-coverage'])if($(id))host.append($(id));
}

function giltSourceStale(source){return !!source?.stale||!!(source?.freshnessDeadline&&Date.now()>Date.parse(source.freshnessDeadline));}
