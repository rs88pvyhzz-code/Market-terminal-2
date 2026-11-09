"""Dated Shell supplemental inputs from issuer announcements and SEC QRA.

Fail closed on changed formats. Never infer outstanding shares from buyback
transaction counts or substitute weighted-average EPS shares. Cached documents
keep their real retrieval timestamp; Yahoo remains the labelled fallback.
"""
from __future__ import annotations
import datetime as dt
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

IR='https://shell.gcs-web.com'
SEC='https://www.sec.gov/Archives/edgar/data/1306965/'

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.text=[]; self.tables=[]; self.links=[]; self.table=None; self.row=None; self.cell=None; self.link=None
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='table': self.table=[]
        elif tag=='tr': self.row=[]
        elif tag in ('td','th'): self.cell=[]
        elif tag=='a': self.link=[attrs.get('href',''),[]]
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            if self.row is not None:self.row.append(' '.join(' '.join(self.cell).split()))
            self.cell=None
        elif tag=='tr' and self.row is not None:
            if self.table is not None:self.table.append(self.row)
            self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table);self.table=None
        elif tag=='a' and self.link is not None:
            self.links.append((self.link[0],' '.join(self.link[1])));self.link=None
    def handle_data(self,data):
        self.text.append(data)
        if self.cell is not None:self.cell.append(data)
        if self.link is not None:self.link[1].append(data)
    def plain(self):return ' '.join(' '.join(self.text).split())


def date(text):
    for fmt in ('%B %d, %Y','%d %B %Y','%B %d %Y'):
        try:return dt.datetime.strptime(text.strip(),fmt).date().isoformat()
        except ValueError:pass
    raise ValueError('Unrecognised issuer date')


def parse_capital(html,url,retrieved,published=None,asof=None):
    text=Document(html).plain();today=asof or dt.date.today().isoformat()
    match=re.search(r'as at\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+the Company.s capital consisted of\s+([\d,]+)\s+ordinary shares',text,re.I)
    if not match or not re.search(r'held no shares in [Tt]reasury',text):raise ValueError('No verified no-treasury ordinary-share statement')
    period=date(match[1]);shares=int(match[2].replace(',',''))
    if period>today or shares<=0:raise ValueError('Invalid ordinary-share period/count')
    if published is None:
        m=re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4}) at',text)
        published=date(m[1]) if m else None
    if published and published>today:raise ValueError('Future announcement')
    return {'sharesOutstanding':shares,'sharesPeriod':period,'sharesPublished':published,
        'sharesRetrievedAt':retrieved,'sharesSource':'Shell issuer voting-rights announcement (no treasury shares)',
        'sharesUrl':url,'shareBasis':'issued ordinary shares; no treasury; 1:1 SHEL.L; not weighted-average EPS shares'}


def parse_quarterly(html,url,retrieved,published,asof=None):
    doc=Document(html);today=asof or dt.date.today().isoformat()
    tables=[t for t in doc.tables if any('Collateral on debt-related derivatives' in ' '.join(r) for r in t)]
    if len(tables)!=1:raise ValueError('Ambiguous issuer debt reconciliation')
    rows=tables[0]
    periods=[c for row in rows for c in row if re.fullmatch(r'[A-Za-z]+ \d{1,2}, \d{4}',c)]
    if not periods:raise ValueError('Missing debt reconciliation date')
    period=date(periods[0])
    if period>today or published>today:raise ValueError('Future statement')
    def take(label):
        matches=[r for r in rows if r and r[0].startswith(label)]
        if len(matches)!=1:raise ValueError('Missing/ambiguous '+label)
        cells=[c for c in matches[0][1:] if re.fullmatch(r'\(?[\d,]+\)?',c)]
        if not cells:raise ValueError('Missing amount: '+label)
        v=cells[0];n=int(v.replace(',','').replace('(','').replace(')',''))
        return (-n if v.startswith('(') else n)*1e6
    debt=take('Total debt');cash=abs(take('Less: Cash and cash equivalents'))
    derivatives=take('Add: Debt-related derivative financial instruments')
    collateral=take('Add: Collateral on debt-related derivatives')
    net=take('Net debt')
    if abs(debt-cash+derivatives+collateral-net)>1e6:raise ValueError('Issuer debt bridge does not reconcile')
    return {'period':period,'totalDebt':debt,'cash':cash,'reportedNetDebt':net,
        'debtDerivatives':derivatives,'debtCollateral':collateral,'debtAdjustment':derivatives+collateral,
        'leaseLiabilities':take('Of which: lease liabilities'),
        'currency':'USD','source':'Shell issuer interim financial report (SEC exhibit)',
        'retrievedAt':retrieved,'published':published,'url':url}


def collect(directory=None):
    root=Path(directory or Path(__file__).parent/'.terminal_filings');root.mkdir(parents=True,exist_ok=True)
    path=root/'shell_supplemental.json';cache={}
    try:cache=json.loads(path.read_text())
    except (OSError,ValueError):pass
    now=dt.datetime.now(dt.timezone.utc);stamp=now.isoformat(timespec='seconds')
    def get(url):
        item=(cache.get('documents') or {}).get(url)
        if item:
            try:
                if (now-dt.datetime.fromisoformat(item['retrievedAt'])).total_seconds()<86400:return item['html'],item['retrievedAt']
            except (ValueError,KeyError):pass
        req=urllib.request.Request(url,headers={'User-Agent':os.environ.get('SEC_USER_AGENT','MarketTerminal/1.0 (github.com/rs88pvyhzz-code/Market-terminal-2)')})
        with urllib.request.urlopen(req,timeout=18) as response:html=response.read(12_000_000).decode('utf-8')
        cache.setdefault('documents',{})[url]={'html':html,'retrievedAt':stamp}
        return html,stamp
    balance=cache.get('balance');capital=cache.get('capital');warnings=[]
    try:
        subs=json.loads(get('https://data.sec.gov/submissions/CIK0001306965.json')[0])['filings']['recent']
        for i,form in enumerate(subs['form']):
            primary=subs['primaryDocument'][i];published=subs['filingDate'][i]
            if form!='6-K' or published>stamp[:10] or not re.search(r'(shellq[1-4]\d{4}6-k|shel-\d{8}_d\d)\.htm',primary,re.I):continue
            base=SEC+subs['accessionNumber'][i].replace('-','')+'/'
            cover=Document(get(base+primary)[0])
            links=[urljoin(base,href) for href,text in cover.links if '992' in href and ('quarterly' in href.lower() or 'exhibit' in href.lower())]
            if not links:continue
            body,retrieved=get(links[0]);candidate=parse_quarterly(body,links[0],retrieved,published)
            if not balance or candidate['period']>=balance['period']:balance=candidate
            break
    except Exception as exc:warnings.append('Shell interim source unavailable: '+str(exc)[:100])
    try:
        candidates=[]
        rss=ET.fromstring(get(IR+'/rss/news-releases.xml')[0])
        for item in rss.findall('.//item'):
            if re.search(r'voting rights',item.findtext('title') or '',re.I):
                published=parsedate_to_datetime(item.findtext('pubDate')).date().isoformat()
                candidates.append((item.findtext('link'),published))
        if capital:candidates.append((capital['sharesUrl'],capital.get('sharesPublished')))
        if not candidates:
            for page in range(3):
                listing=Document(get(IR+'/news-releases?page='+str(page))[0])
                candidates += [(urljoin(IR,href),None) for href,text in listing.links if 'voting rights' in text.lower()]
                if candidates:break
        for url,published in dict(candidates).items():
            if not url.startswith(IR+'/news-releases/'):continue
            body,retrieved=get(url);candidate=parse_capital(body,url,retrieved,published)
            if not capital or candidate['sharesPeriod']>=capital['sharesPeriod']:capital=candidate
    except Exception as exc:warnings.append('Shell ordinary-share source unavailable: '+str(exc)[:100])
    cache['balance']=balance;cache['capital']=capital
    path.write_text(json.dumps(cache,separators=(',',':')))
    return balance,capital,warnings


def apply(balance,primary,capital):
    """Keep independent balance/share dates and do not overwrite newer reporting."""
    if not balance and not primary and not capital:return None
    result=dict(balance or {})
    result.setdefault('sharesPeriod',result.get('period'))
    result.setdefault('sharesRetrievedAt',result.get('retrievedAt'))
    result.setdefault('sharesSource',result.get('source','Yahoo reported outstanding shares (issuer count unverified)'))
    if primary and primary['period']>=result.get('period',''):
        result.update(primary)
    if capital and capital['sharesPeriod']>=(result.get('sharesPeriod') or ''):
        result.update(capital)
    else:
        result.setdefault('sharesPeriod',result.get('period'))
        result.setdefault('sharesRetrievedAt',result.get('retrievedAt'))
        result.setdefault('sharesSource','Yahoo reported outstanding shares (issuer count unverified)')
    return result or None
