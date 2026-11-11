"""Broad ETF research catalogue and Yahoo snapshot collection.

No holdings, quantities, purchase prices or portfolio values are stored.
Metadata in etf_catalog.csv is editorial and must be checked against issuer factsheets.
Yahoo adjusted closes are unofficial total-return proxies, not certified NAV returns.
"""
import concurrent.futures
import copy
import csv
import datetime as dt
import pathlib
import re

FIELDS = ('category', 'market', 'symbol', 'name', 'benchmark', 'terPct',
          'replication', 'distribution', 'domicile', 'isin', 'hedged',
          'reference', 'note')
SYMBOL_RE = re.compile(r'^[A-Z0-9.^=_-]{1,32}$')
CATEGORIES = {'Equity', 'Bonds', 'Thematic', 'Commodity ETC'}


def read_catalog(path):
    funds, warnings, seen = [], [], set()
    source = pathlib.Path(path)
    if not source.is_file():
        return funds, ['ETF catalog missing: ' + source.name]
    with source.open(encoding='utf-8-sig', newline='') as handle:
        for line, row in enumerate(csv.DictReader(handle), 2):
            symbol = (row.get('symbol') or '').strip().upper()
            if not SYMBOL_RE.fullmatch(symbol) or symbol in seen:
                warnings.append('ETF row ' + str(line) + ': duplicate or invalid symbol')
                continue
            seen.add(symbol)
            entry = {k: (row.get(k) or '').strip() for k in FIELDS}
            if entry['category'] not in CATEGORIES:
                warnings.append(symbol + ': unknown category')
                continue
            fee = entry['terPct']
            try:
                fee = float(fee) if fee else None
                if fee is not None and not 0 <= fee <= 5:
                    raise ValueError('outside accepted range')
            except ValueError:
                warnings.append(symbol + ': fee rejected')
                fee = None
            entry['terPct'] = fee
            if entry['replication'] not in ('Physical full', 'Physical sampling',
                                            'Synthetic swap', ''):
                entry['replication'] = ''
                warnings.append(symbol + ': replication unknown')
            isin = entry['isin']
            entry['issuerFactsUrl'] = ('https://www.justetf.com/uk/etf-profile.html?isin=' + isin
                                       if re.fullmatch(r'[A-Z]{2}[A-Z0-9]{10}', isin) else '')
            # Editorial snapshot date, not live issuer validation.
            entry['factsAsOf'] = '2026-11-08' if fee is not None or entry['replication'] else ''
            entry.update(quote=None, return1Y=None, return3Y=None, return5Y=None,
                         returnBasis='', quoteStatus='Not downloaded')
            funds.append(entry)
    return funds, warnings


def compact_history(history):
    """Daily last five years; weekly earlier. No invented or interpolated prices."""
    raw = sorted((r for r in history if r.get('date') and r.get('close') and r['close'] > 0),
                 key=lambda r: r['date'])
    if not raw:
        return []
    end = dt.date.fromisoformat(raw[-1]['date'])
    out, bucket = [], None
    for r in raw:
        d = dt.date.fromisoformat(r['date'])
        if (end - d).days <= 365 * 5:
            out.append([r['date'], r['close'], r.get('adjClose')])
        else:
            week = d.isocalendar()[:2]
            if week != bucket:
                out.append([r['date'], r['close'], r.get('adjClose')])
            bucket = week
    return out


def include_completed_quote(points, quote):
    """Include a later *after-close* Yahoo quote as price only, never NAV/adjClose.

    Yahoo's regular-market quotation can update before its chart endpoint.
    Require the same ticker, a dated post-session quotation and a history bar
    no more than five calendar days behind. Intraday or unverified quotes never
    enter the series. The adjusted close stays missing, not imputed.
    """
    if not points or not quote or not quote.get('quoteAfterRegularClose'):
        return points, False
    if quote.get('source') != 'Yahoo Finance':
        return points, False
    day=quote.get('tradingDay') or (quote.get('asOf') or '')[:10]
    price=quote.get('price')
    if not isinstance(price,(int,float)) or price<=0:
        return points, False
    try:
        date=dt.date.fromisoformat(day)
        old=dt.date.fromisoformat(points[-1][0])
    except (TypeError,ValueError):
        return points, False
    if not 0 < (date-old).days <= 5:
        return points, False
    return points+[[day,price,None]],True


def _annualised_detail(points, years):
    """Use the closest actual trading date to the exact anniversary.

    The final observation is one actual dated price. Do not interpolate a
    market holiday, substitute missing FX or convert a quote into an adjusted
    close. A seven-day maximum distance makes stale endpoints unavailable.
    """
    if len(points)<2 or years not in (1,3,5):
        return None,'',None
    rows=sorted(points,key=lambda p:p[0])
    last=rows[-1]
    # If the most recent close is only a verified market quote, there is no
    # adjusted-close observation for that date: compare raw closes instead.
    idx=2 if len(last)>2 and isinstance(last[2],(int,float)) and last[2]>0 else 1
    label='Adjusted close proxy' if idx==2 else 'Price only'
    if not isinstance(last[idx],(int,float)) or last[idx]<=0:
        return None,'',None
    end=dt.date.fromisoformat(last[0])
    try:
        target=end.replace(year=end.year-years)
    except ValueError:  # 29 February -> 28 February
        target=end.replace(year=end.year-years,day=28)
    candidates=[]
    for row in rows[:-1]:
        if len(row)<=idx or not isinstance(row[idx],(int,float)) or row[idx]<=0:
            continue
        start=dt.date.fromisoformat(row[0])
        distance=abs((start-target).days)
        if distance<=7:
            candidates.append((distance,0 if start>=target else 1,start,row))
    if not candidates:
        return None,'',None
    _,_,start,first=min(candidates,key=lambda t:(t[0],t[1]))
    span=(end-start).days/365.25
    if span<years*.95 or span>years*1.07:
        return None,'',None
    value=round(100*((last[idx]/first[idx])**(1/span)-1),2)
    return value,label,{'start':start.isoformat(),'end':end.isoformat(),
                        'startPrice':first[idx],'endPrice':last[idx],
                        'basis':label}


def annualised_performance(points, years):
    """Trailing CAGR using actual closes nearest the matching anniversary."""
    value,basis,_=_annualised_detail(points,years)
    return value,basis


def attach(fund, quote, points, quote_as_history=False):
    if not quote:
        fund['quoteStatus'] = 'Unavailable'
        return
    fund['quote'] = {k: quote.get(k) for k in (
        'symbol', 'currency', 'price', 'changePct', 'asOf', 'source', 'cached',
        'adjustedAvailable','tradingDay','quoteAfterRegularClose')}
    fund['quoteStatus'] = 'Quoted' if quote.get('price') is not None else 'Unavailable'
    bases = []
    periods={}
    for years in (1, 3, 5):
        result,basis,period=_annualised_detail(points,years)
        fund['return' + str(years) + 'Y'] = result
        if basis:
            bases.append(basis)
        if period:
            periods[str(years)+'Y']=period
    fund['returnBasis'] = ', '.join(dict.fromkeys(bases))
    fund['returnPeriods']=periods
    fund['returnEndSource']='Yahoo after-close quote, price only' if quote_as_history else 'Yahoo dated historical chart'

def demo(path):
    funds, warnings = read_catalog(path)
    return {'funds': funds, 'history': [],
            'coverage': {'catalogued': len(funds), 'quoted': 0, 'withHistory': 0,
                         'unavailable': len(funds), 'failedDownloads': 0, 'demo': True},
            'warnings': warnings, 'sources': ['Editorial research catalogue; demo has no ETF quotations']}


def collect(core, opts, path, main_quotes, main_history, watch_quotes, watch_history):
    funds, warnings = read_catalog(path)
    existing = {q['symbol']: q for q in main_quotes}
    for q in watch_quotes:
        existing.setdefault(q['symbol'], q)
    known_history = {}
    for row in main_history:
        known_history.setdefault(row['symbol'], []).append(row)
    for item in watch_history:
        sym = item.get('symbol')
        if sym and sym not in known_history:
            known_history[sym] = [
                {'date': p[0], 'close': p[1], 'adjClose': p[2] if len(p) > 2 else None}
                for p in item.get('points', [])]
    todo = [f for f in funds if f['symbol'] not in existing]
    options = copy.copy(opts)
    options.years = min(10, max(1, opts.years))
    results = {}

    def one(fund):
        return core.fetch_quote(('ETF research', fund['symbol'], fund['name'], 'etf'), options)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, max(1, opts.workers))) as pool:
        tasks = {pool.submit(one, f): f['symbol'] for f in todo}
        for task in concurrent.futures.as_completed(tasks):
            sym = tasks[task]
            try:
                results[sym] = task.result()
            except Exception as exc:
                results[sym] = (None, [], None, str(exc))

    history, cached, failed = [], 0, 0
    for fund in funds:
        sym = fund['symbol']
        if sym in existing:
            quote, raw = existing[sym], known_history.get(sym, [])
        else:
            quote, raw, detail, error = results.get(sym, (None, [], None, 'Not fetched'))
            if error:
                failed += 1
                if failed <= 8:
                    warnings.append('ETF ' + sym + ': ' + str(error)[:115])
            if quote:
                cached += int(bool(quote.get('cached')))
        points = compact_history(raw)
        # Never combine a current quote with an older chart end without saying
        # which date and basis the return uses.
        quote_for_symbol=quote if quote and quote.get('symbol')==sym else None
        points,used_quote=include_completed_quote(points,quote_for_symbol)
        attach(fund, quote, points, quote_as_history=used_quote)
        if points:
            history.append({'symbol': sym, 'points': points})
    quoted = sum(f['quoteStatus'] == 'Quoted' for f in funds)
    return ({'funds': funds, 'history': history,
             'coverage': {'catalogued': len(funds), 'quoted': quoted,
                          'withHistory': len(history), 'unavailable': len(funds) - quoted,
                          'failedDownloads': failed, 'demo': False},
             'warnings': warnings,
             'sources': ['ETF metadata: editorial catalogue dated 2026-11-08; issuer factsheets for verification',
                         'Prices: Yahoo Finance unofficial historical chart download; not NAV']},
            warnings, cached)
