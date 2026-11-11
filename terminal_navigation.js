// Release 2.2 navigation: move existing panels; no financial calculations.
// Terminal 1 uses separate top-level Equities, Company Research and Analytics.
// Remove Terminal 2's nested, duplicate-subsection navigation.
const terminalSubViews={};
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
 const [raw,subview]=String(route||'overview').replace(/^#/,'').split(':');
 const key={'markets':'fx','equities':'equities','company':'companies','company-research':'companies',
    'companies':'companies','analytics':'analytics','research':'companies'}[raw]||raw;
 const views=['overview','fx','equities','companies','bonds','analytics','etfs','economics','watchlist','quality'];
 const direct={'peer-panel':'companies','company-events-panel':'companies','forensic-panel':'companies',
    'analytics-rolling':'analytics','market-valuations':'analytics','analytics-breadth':'analytics',
    'analytics-sectors':'analytics','score-panel':'analytics','compare':'analytics',
    'monitor':'fx','news':'fx','movers':'fx','company-news-panel':'companies',
    'equity-screener':'equities','constituents':'equities','companies':'companies'};
 if(raw==='fx'&&subview==='analytics')return {key:'analytics'};
 if(raw==='equities'&&subview==='research')return {key:'companies'};
 if(raw==='equities'&&subview==='analytics')return {key:'analytics'};
 if(raw==='fx'&&subview==='news')return {key:'fx'};
 if(direct[raw])return {key:direct[raw]};
 if(views.includes(key))return {key};
 const section=workspaceForSection[key];return section?terminalResolveRoute(section):{key:'overview'};
}
function researchArrangeOverview(){
 const host=$('research-view-0');if(!host)return;
 for(const id of ['company-price-block','company-benchmark-block','research-overview','company-risk-panel','research-executive','company-advanced','company-news-panel','company-coverage'])if($(id))host.append($(id));
}

function giltSourceStale(source){return !!source?.stale||!!(source?.freshnessDeadline&&Date.now()>Date.parse(source.freshnessDeadline));}
