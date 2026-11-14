/* Visit markers are local to this browser. They never alter market data. */
function newsVisitDate(value){
 const raw=String(value||'');
 if(!/\d{2}:\d{2}/.test(raw))return NaN;
 return Date.parse(raw.replace(' UTC','Z').replace(/^(\d{4}-\d\d-\d\d) /,'$1T'));
}
function newsVisitIsNew(published,baseline,now=Date.now()){
 const time=newsVisitDate(published);
 return Number.isFinite(baseline)&&Number.isFinite(time)&&time>baseline&&time<=now&&now-time<=86400000;
}
(function(){
 const key='terminal-news-last-visit-v1',arrival=Date.now();
 let baseline=null,available=true;
 try{const raw=localStorage.getItem(key),saved=raw==null?NaN:Number(raw);if(Number.isFinite(saved)&&saved<=arrival)baseline=saved;localStorage.setItem(key,String(arrival));}catch(e){available=false;}
 const dates=new Map();
 for(const row of [...(D.news||[]),...(D.company_news||[]).flatMap(x=>x.articles||[]),...(D.watchlist_news||[]).flatMap(x=>x.articles||[])]){
  if(row.url&&(!dates.has(row.url)||newsVisitDate(row.published)>newsVisitDate(dates.get(row.url))))dates.set(row.url,row.published);
 }
 function paint(){
  const overview=document.getElementById('view-overview');if(!overview)return;
  let controls=document.getElementById('news-visit-controls');
  if(!controls){
   controls=el('div','news-visit-controls');controls.id='news-visit-controls';
   const status=el('span');status.id='news-visit-status';controls.append(status);
   const read=el('button','btn','Mark news seen');read.type='button';read.disabled=!available;
   read.onclick=()=>{baseline=Date.now();try{localStorage.setItem(key,String(baseline));}catch(e){}paint();};controls.append(read);
   const quality=el('a','','Data diagnostics');quality.href='#quality';quality.onclick=e=>{e.preventDefault();activateWorkspace('quality',{scroll:true});};controls.append(quality);
   const heading=overview.querySelector('.workspace-title');heading?heading.after(controls):overview.prepend(controls);
  }
  const status=document.getElementById('news-visit-status');
  const text=!available?'Visit markers unavailable in this browser':baseline==null?'First visit · new markers start next visit':
   'New since '+new Date(baseline).toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})+' · this browser';
  if(status.textContent!==text)status.textContent=text;
  for(const card of document.querySelectorAll('.r24-item,.r29-news,.company-story,.watch-change-row')){
   const a=card.querySelector('a[href]'),published=a&&dates.get(a.getAttribute('href'));
   const fresh=newsVisitIsNew(published,baseline),badge=card.querySelector('.news-new');
   if(fresh&&!badge){const b=el('span','news-new','NEW');b.title='Published since your last visit on this browser';card.prepend(b);}
   else if(!fresh&&badge)badge.remove();
  }
 }
 let pending=false;
 const observer=new MutationObserver(()=>{if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;paint();});}});
 document.addEventListener('DOMContentLoaded',()=>{paint();observer.observe(document.getElementById('workspace-stage')||document.body,{childList:true,subtree:true});});
})();
