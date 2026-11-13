/* Publisher-date filters use the viewer's current UK calendar day, not build time. */
const newsDateFormat=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit'});
let newsDateRange='today';
function newsDay(value){return newsDateFormat.format(new Date(value));}
function newsDateMatches(item,now=Date.now(),range=newsDateRange){
 const raw=String(item?.published||'');
 const date=Date.parse(raw.replace(' UTC','Z').replace(/^(\d{4}-\d\d-\d\d) /,'$1T'));
 if(!Number.isFinite(date)||date>now)return false;
 const day= newsDay(date),today=newsDay(now);
 const dayNumber=s=>Date.parse(s+'T12:00:00Z')/86400000;
 const age=dayNumber(today)-dayNumber(day);
 return range==='today'?age===0:range==='yesterday'?age===1:age>=0&&age<7;
}
function newsEmptyText(){return newsDateRange==='today'?'No news today in the available feeds.':newsDateRange==='yesterday'?'No news yesterday in the available feeds.':'No news in the last 7 days in the available feeds.';}
let newsSelectedCompany=null,newsSelectedWatch=null;
function newsDateControls(host){
 if(!host)return;
 const nav=el('div','pills news-date-controls');nav.setAttribute('aria-label','News publication date (UK time)');
 for(const [key,label] of [['today','Today'],['yesterday','Yesterday'],['week','7 days']]){
  const b=el('button','btn'+(newsDateRange===key?' active':''),label);b.type='button';b.setAttribute('aria-pressed',String(newsDateRange===key));
  b.onclick=()=>{newsDateRange=key;refreshDatedNews();};nav.append(b);
 }
 nav.append(el('span','mini','UK publication date · available snapshot '+(D.generatedAt||'unknown')));
 host.prepend(nav);
}
function refreshDatedNews(){
 r24Overview();renderIntelligenceNews();
 if(newsSelectedCompany)renderCompanyInsight(newsSelectedCompany);
 if(newsSelectedWatch)watchlistNews(...newsSelectedWatch);
}
const datedOverview=r24Overview;
r24Overview=function(){datedOverview();newsDateControls(document.querySelector('#r24-developments .r24-content'));};
const datedNews=renderIntelligenceNews;
renderIntelligenceNews=function(){datedNews();newsDateControls(document.getElementById('news-pills'));};
const datedCompany=renderCompanyInsight;
renderCompanyInsight=function(c){newsSelectedCompany=c;datedCompany(c);newsDateControls(document.getElementById('company-news-list'));};
const datedWatch=watchlistNews;
watchlistNews=function(w,q){newsSelectedWatch=[w,q];datedWatch(w,q);newsDateControls(document.getElementById('watchlist-news-stories'));};
// Re-evaluate on returning to the page and across UK midnight without changing data.
let newsLastDay=newsDay(Date.now());
function checkNewsDay(){const day=newsDay(Date.now());if(day!==newsLastDay){newsLastDay=day;refreshDatedNews();}}
document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkNewsDay();});
setInterval(checkNewsDay,60000);
