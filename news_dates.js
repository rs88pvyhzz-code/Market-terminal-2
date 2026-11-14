/* Rolling publisher-time window, independent of midnight and daylight saving. */
function newsDateMatches(item,now=Date.now()){
 const raw=String(item?.published||'').trim();
 // Date-only records cannot establish publication within a 24-hour window.
 if(!/\d{2}:\d{2}/.test(raw))return false;
 const date=Date.parse(raw.replace(' UTC','Z').replace(/^(\d{4}-\d\d-\d\d) /,'$1T'));
 return Number.isFinite(date)&&date<=now&&now-date<=86400000;
}
function newsEmptyText(){return 'No news in the last 24 hours in the available feeds.';}
let newsSelectedCompany=null,newsSelectedWatch=null;
function newsDateControls(host){
 if(host)host.setAttribute('aria-label','News from the last 24 hours');
 const heading=document.querySelector('#news h2');
 if(heading)heading.textContent='MORE MARKET HEADLINES · LAST 24 HOURS';
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
// Expire stories while the page remains open, and when returning to the tab.
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshDatedNews();});
setInterval(()=>{if(!document.hidden)refreshDatedNews();},60000);
