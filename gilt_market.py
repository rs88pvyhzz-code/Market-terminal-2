"""DMO D10B purchase/sale gilt prices for the static market terminal.

Uses the official D10B export parameter and XLS/XLSX response readers.
Verifies the quotation date separately from report generation, and retains
the latest verified prices when the provider cannot be reached.

The Purchase (DMO buys / investor sells) and Sale (DMO sells / investor buys)
columns are DMO retail-service reference prices, NOT executable broker quotes.
For index-linked gilts, DMO 'clean' is REAL, while dirty includes indexation.
"""
import datetime as dt
from fractions import Fraction
import io
import json
import math
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

DMO_PAGE = 'https://www.dmo.gov.uk/data/pdfdatareport?reportCode=D10B'
EXPORT = 'https://www.dmo.gov.uk/umbraco/surface/DataExport/GetDataExport'
import os as _os
# Published-site cache location follows whichever repository runs the build.
_REPO=_os.environ.get('GITHUB_REPOSITORY','rs88pvyhzz-code/Market-terminal-2').split('/',1)
_PAGES=f'https://{_REPO[0]}.github.io/{_REPO[1]}/'
PUBLIC_LATEST = _PAGES+'dmo_latest.json'
PUBLIC_HISTORY = _PAGES+'gilt_history_cache.json'
ROOT = pathlib.Path(__file__).resolve().parent
SEED = ROOT / 'dmo_gilt_prices.xlsx'
LATEST = ROOT / '.terminal_dmo_latest.json'
HISTORY = ROOT / '.terminal_gilt_history.json'
XML = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
COUPON_FRACTIONS={'¼':.25,'½':.5,'¾':.75,'⅛':.125,'⅜':.375,'⅝':.625,'⅞':.875,'⅓':1/3,'⅔':2/3}
ALIASES={'GB00BMBL1G81':'TN28','GB00BJMHB534':'TR29','GB00BVP99566':'T29K'}


def fnum(v):
    try:
        if v is None or str(v).strip() == '': return None
        n=float(str(v).replace(',','').replace('£','').strip())
        return n if math.isfinite(n) else None
    except (ValueError,TypeError,OverflowError): return None


def coupon_from_name(name):
    part=name.split('%',1)[0].strip()
    if not part: return None
    for frac,val in COUPON_FRACTIONS.items():
        if frac in part:
            base=part.replace(frac,'').strip()
            return float(base)+val if base else val
    pieces=part.split()
    try:
        return float(pieces[0])+(float(Fraction(pieces[1])) if len(pieces)>1 else 0)
    except (ValueError,ZeroDivisionError,IndexError): return None


def _read_xlsx(raw):
    """Read DMO's small Crystal Reports XLSX using stdlib, no pip packages."""
    if len(raw)>4_000_000 or not raw.startswith(b'PK'):raise ValueError('DMO export is not a small XLSX file')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if 'xl/worksheets/sheet1.xml' not in names:raise ValueError('DMO spreadsheet sheet1 is missing')
        def safe_read(file,limit):
            info=z.getinfo(file)
            if info.file_size>limit: raise ValueError('Oversize spreadsheet XML')
            return z.read(file)
        shared=[]
        if 'xl/sharedStrings.xml' in names:
            node=ET.fromstring(safe_read('xl/sharedStrings.xml',1_500_000))
            for si in node.findall(f'{XML}si'):
                shared.append(''.join(t.text or '' for t in si.iter(f'{XML}t')))
        doc=ET.fromstring(safe_read('xl/worksheets/sheet1.xml',3_000_000))
        table=[]
        for r in doc.findall(f'.//{XML}sheetData/{XML}row'):
            cells=[None]*10
            for cell in r.findall(f'{XML}c'):
                match=re.match(r'([A-Z]+)',cell.attrib.get('r',''))
                if not match:continue
                col=0
                for ch in match.group(1):col=col*26+(ord(ch)-64)
                col-=1
                if col>=len(cells):continue
                kind=cell.attrib.get('t')
                if kind=='inlineStr':
                    rawval=''.join(x.text or '' for x in cell.iter(f'{XML}t'))
                else:
                    v=cell.find(f'{XML}v')
                    rawval=v.text if v is not None else None
                    if kind=='s' and rawval is not None:rawval=shared[int(rawval)]
                cells[col]=rawval
            table.append(cells)
        return table


def parse_dmo_xlsx(raw):
    """Parse only a validated D10B-shaped XLS/XLSX export; return [rows],date."""
    if raw.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        import xlrd
        if len(raw)>4_000_000:raise ValueError('Oversize DMO XLS')
        sheet=xlrd.open_workbook(file_contents=raw,on_demand=True).sheet_by_index(0)
        if sheet.nrows>500 or sheet.ncols>20:raise ValueError('Unexpected DMO sheet dimensions')
        table=[(sheet.row_values(i)+[None]*10)[:10] for i in range(sheet.nrows)]
    else:table=_read_xlsx(raw)
    if not table or len(table)<15:raise ValueError('DMO report has too few rows')
    top=table[0]
    if 'PURCHASE AND SALE SERVICE PRICES' not in ' '.join(str(x or '') for x in top).upper():
        raise ValueError('Not the DMO purchase and sale prices report')
    # Data Date is the report generation date, not the price quotation date.
    # D10B puts its requested trade/quotation date in the separate fourth cell.
    try:date=dt.datetime.strptime(str(top[3]).strip(),'%d %B %Y').date()
    except ValueError:raise ValueError('Source report has no verified quotation date')
    if date>dt.datetime.now(dt.timezone.utc).date():raise ValueError('Future DMO quotation date')
    header=next((i for i,r in enumerate(table[:10]) if r[0]=='ISIN Code' and 'Gilt Name'==r[1]),None)
    if header is None:raise ValueError('Expected DMO ISIN and price headers missing')
    expected=('Purchase','Sale','Clean Price','Dirty Price')
    h=' '.join(str(x or '') for x in table[header][2:6])
    if any(x.lower() not in h.lower() for x in expected):raise ValueError('DMO price columns changed')
    out=[];seen=set()
    for row in table[header+1:]:
        isin=str(row[0] or '').strip().upper()
        if not re.fullmatch(r'GB[0-9A-Z]{10}',isin) or isin in seen:continue
        name=str(row[1] or '').strip()
        vals=[fnum(row[i]) for i in [2,3,4,5]]
        if not name or any(x is None or x<=0 or x>2000 for x in vals):continue
        # A correctly labelled DMO bid cannot be above its offer (allow rounding noise).
        if vals[0]>vals[2]+0.011 or vals[1]>vals[3]+0.011:continue
        rawdate=fnum(row[7])
        if rawdate is None:continue
        maturity=dt.date(1899,12,30)+dt.timedelta(days=round(rawdate))
        if maturity<date:continue
        coupon=coupon_from_name(name)
        if coupon is None or coupon<0 or coupon>20:continue
        index_linked='index-linked' in name.lower()
        ratio=fnum(row[6]); lag=str(row[9] or '').strip() or None
        if index_linked and ratio is not None and not(.2<=ratio<=15):continue
        buy,dirty_buy,sell,dirty_sell=map(lambda x:round(x,6),vals)
        out.append({'ticker':isin,'isin':isin,'shortTicker':ALIASES.get(isin,''),'name':name,
           'maturity':maturity.isoformat(),'coupon':round(coupon,6),
           'bidClean':buy,'bidDirty':dirty_buy,'askClean':sell,'askDirty':dirty_sell,
           'price':sell,'yieldSource':None,'asOf':date.isoformat(),'quoted':True,
           'indexLinked':index_linked,'indexRatio':ratio,'indexationLag':lag,
           'source':DMO_PAGE,'quoteType':'DMO retail purchase/sale service; dated historical indicative prices, not executable'} )
        seen.add(isin)
    if len(out)<30 or sum(r['indexLinked'] for r in out)<10 or sum(not r['indexLinked'] for r in out)<30:raise ValueError('Incomplete DMO report: both conventional and index-linked coverage required')
    return sorted(out,key=lambda x:(x['maturity'],x['name'])), date


def _get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'PersonalMarketResearch/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=9) as resp:
        raw=resp.read(1_900_000)
    return json.loads(raw)


def _accept_snapshot(obj):
    if not isinstance(obj,dict):return None
    date=obj.get('asOf'); rows=obj.get('bonds')
    if not isinstance(date,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):return None
    if not isinstance(rows,list) or not 30<=len(rows)<=150:return None
    try:
        if dt.date.fromisoformat(date)>dt.datetime.now(dt.timezone.utc).date():return None
        if len({r.get('isin') for r in rows})!=len(rows):return None
        if any(not r.get('quoted') or r.get('asOf')!=date or any(fnum(r.get(k)) is None or not 0<float(r[k])<=2000 for k in ('bidClean','askClean','bidDirty','askDirty')) or r['bidClean']>r['askClean']+.011 for r in rows):return None
        if sum(bool(r.get('indexLinked')) for r in rows)<10 or sum(not r.get('indexLinked') for r in rows)<30:return None
    except (TypeError,ValueError,AttributeError):return None
    return obj


def _download_dmo_for(trade_date,diagnostics=None):
    import hashlib
    params={'reportCode':'D10B','exportFormatValue':'xls','parameters':'&Trade Date='+trade_date.strftime('%d/%m/%Y')}
    url=EXPORT+'?'+urllib.parse.urlencode(params,quote_via=urllib.parse.quote)
    event={'url':url,'requestedDate':trade_date.isoformat(),'attemptedAt':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'success':False}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'MarketTerminal/2.2 public financial research','Accept':'application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
        with urllib.request.urlopen(req,timeout=20) as response:
            event['httpStatus']=response.status;blob=response.read(4_000_001)
        rows,report_date=parse_dmo_xlsx(blob)
        if report_date!=trade_date:raise ValueError('Quotation date does not match requested trade date')
        event.update(success=True,quotationDate=report_date.isoformat(),rows=len(rows),sha256=hashlib.sha256(blob).hexdigest())
        return {'asOf':report_date.isoformat(),'bonds':rows,'retrievedAt':event['attemptedAt'],'sourceUrl':url,'sha256':event['sha256'],'origin':'official DMO download'}
    except Exception as exc:
        event.update(error=str(exc)[:200],httpStatus=getattr(exc,'code',event.get('httpStatus')))
        return None
    finally:
        if diagnostics is not None:diagnostics.append(event)


def _recent_business_days(today, count=2, holidays=None):
    result=[];cur=today
    while len(result)<count:
        if cur.weekday()<5 and cur.isoformat() not in (holidays or []):result.append(cur)
        cur-=dt.timedelta(days=1)
    return result


def collect(core,opts):
    warnings=[];candidates=[];downloaded=False;attempts=[]
    from gilt_freshness import load_calendar,assess
    try:calendar=load_calendar(offline=opts.offline)
    except Exception as exc:
        calendar={'holidays':[],'source':'https://www.gov.uk/bank-holidays.json'};warnings.append('UK holiday calendar unavailable: '+str(exc)[:100])
    # Any uploaded DMO D10B Excel file counts, whatever it is called: the newest
    # report date wins. Upload the DMO download as-is; no renaming needed.
    for book in sorted([*ROOT.glob('*.xls*'),*(ROOT/'dmo_prices').glob('*.xls*')]):
        try:
            seed_rows,day=parse_dmo_xlsx(book.read_bytes())
            candidates.append({'asOf':day.isoformat(),'bonds':seed_rows,'origin':'uploaded official DMO file','sourceFile':book.name})
        except Exception as e:
            if book==SEED:warnings.append('DMO spreadsheet could not be parsed: '+str(e)[:150])
    if LATEST.exists():
        try:
            p=_accept_snapshot(json.loads(LATEST.read_text('utf-8')))
            if p:candidates.append(p)
        except (ValueError,OSError):pass
    if not opts.offline:
        try:
            old=_accept_snapshot(_get_json(PUBLIC_LATEST))
            if old:candidates.append(old)
        except Exception:pass
        today=dt.datetime.now(dt.timezone.utc).date()
        # Try the current business day even during publication grace: an early
        # valid release should not be missed. Empty/unpublished reports fall back.
        for day in _recent_business_days(today,count=3,holidays=calendar['holidays']):
            new=_download_dmo_for(day,attempts)
            if new:
                candidates.append(new);downloaded=True;break
            if attempts and attempts[-1].get('httpStatus') in (403,429):break
    if not candidates:
        warnings.append('No verified DMO Excel prices available; prices remain blank')
        status={**assess(None,calendar=calendar),'downloadedFresh':False,'attempts':attempts,'coverage':{'total':0}}
        fp=ROOT/'.terminal_sources/dmo_verification.json';fp.parent.mkdir(parents=True,exist_ok=True);fp.write_text(json.dumps(status,indent=2))
        return [],[],warnings,0
    latest=max(candidates,key=lambda p:(p['asOf'],p.get('retrievedAt') or ''))
    rows=[dict(g) for g in latest['bonds']]
    freshness=assess(latest['asOf'],calendar=calendar)
    selected_fresh=downloaded and latest.get('origin')=='official DMO download' and any(a.get('success') and a.get('sha256')==latest.get('sha256') and a.get('quotationDate')==latest['asOf'] for a in attempts)
    diagnostics={**freshness,'downloadedFresh':selected_fresh,'networkDownloadSucceeded':downloaded,'retrievedAt':latest.get('retrievedAt'),'origin':latest.get('origin','recovered verified snapshot'),'sourceUrl':latest.get('sourceUrl',DMO_PAGE),'attempts':attempts,'coverage':{'total':len(rows),'conventional':sum(not r['indexLinked'] for r in rows),'indexLinked':sum(r['indexLinked'] for r in rows)}}
    diagnostic_path=ROOT/'.terminal_sources/dmo_verification.json';diagnostic_path.parent.mkdir(parents=True,exist_ok=True);diagnostic_path.write_text(json.dumps(diagnostics,indent=2))
    if freshness['stale']:warnings.append('DMO PRICES STALE: quotation '+latest['asOf']+'; expected '+freshness['expectedQuotationDate'])
    if not downloaded and not opts.offline:warnings.append('DMO retrieval failed; retained verified quotation '+latest['asOf'])
    LATEST.write_text(json.dumps(latest,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
    prior={}
    if not opts.offline:
        try:
            obj=_get_json(PUBLIC_HISTORY)
            if isinstance(obj,dict):prior={k:v for k,v in obj.items() if isinstance(v,list) and re.fullmatch(r'GB[0-9A-Z]{10}',k)}
        except Exception:pass
    if HISTORY.exists():
        try:
            obj=json.loads(HISTORY.read_text('utf-8'))
            if isinstance(obj,dict):
                for k,v in obj.items():
                    if isinstance(v,list) and re.fullmatch(r'GB[0-9A-Z]{10}',k):
                        old={str(x[0]):float(x[1]) for x in prior.get(k,[]) if isinstance(x,list) and len(x)==2}
                        for item in v:
                            if isinstance(item,list) and len(item)==2:old[str(item[0])]=float(item[1])
                        prior[k]=[[day,price] for day,price in sorted(old.items())][-1500:]
        except Exception:pass
    for b in rows:
        if b['quoted']:
            key=b['isin']
            pts={str(x[0]):float(x[1]) for x in prior.get(key,[]) if isinstance(x,list) and len(x)==2}
            pts[b['asOf']]=float(b['askClean'])
            prior[key]=[[day,price] for day,price in sorted(pts.items())][-1500:]
    HISTORY.write_text(json.dumps(prior,separators=(',',':')),encoding='utf-8')
    history=[{'ticker':g['ticker'],'date':d,'close':v}
             for g in rows for d,v in prior.get(g['ticker'],[])][-15000:]
    return rows,history,warnings,int(selected_fresh)

def publish(directory):
    """Persist gilt recovery independently of the equity-history publisher."""
    import shutil
    public=pathlib.Path(directory);public.mkdir(parents=True,exist_ok=True)
    for source,name in [(LATEST,'dmo_latest.json'),(HISTORY,'gilt_history_cache.json'),(ROOT/'.terminal_sources/dmo_verification.json','dmo_verification.json')]:
        if source.exists():shutil.copyfile(source,public/name)


if __name__=='__main__':
    import sys
    rows,date=parse_dmo_xlsx(pathlib.Path(sys.argv[1] if len(sys.argv)>1 else SEED).read_bytes())
    print('Verified',len(rows),'DMO gilts for',date,'; index linked',sum(r['indexLinked'] for r in rows))
    example=next(r for r in rows if r['isin']=='GB00BMBL1G81')
    print('TN28 DMO bid clean',example['bidClean'],'offer clean',example['askClean'])
