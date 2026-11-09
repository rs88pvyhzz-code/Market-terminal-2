"""Release 1 derived financial analysis and point-in-time multiple snapshots."""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path
import statistics


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def ratio(a, b):
    return a/b if number(a) and number(b) and b > 0 else None


def financial_sector(c):
    text = ((c.get('sector') or '')+' '+(c.get('industry') or '')).lower()
    return c.get('symbol') == 'HSBA.L' or any(s in text for s in (
        'financial services', 'bank', 'insurance', 'capital markets', 'asset management', 'credit services'))


def analyse(rows, financial=False):
    out = []
    rows = sorted(rows, key=lambda r: r['fiscalEnd'], reverse=True)[:5]
    for i, raw in enumerate(rows):
        r = dict(raw)
        prior = rows[i+1] if i+1 < len(rows) else {}
        r['fcf'] = r['operatingCashFlow']-abs(r['capex']) if all(number(r.get(k)) for k in ('operatingCashFlow', 'capex')) and not financial else None
        # EBITDA = operating profit + D&A is derived, not a company's adjusted EBITDA.
        if not financial and not number(r.get('ebitda')) and all(number(r.get(k)) for k in ('operatingProfit', 'depreciation')):
            r['ebitda'] = r['operatingProfit']+r['depreciation']
            r['ebitdaKind'] = 'calculated: operating profit + D&A'
        elif number(r.get('ebitda')): r['ebitdaKind'] = 'reported provider EBITDA'
        for key, numerator in [('grossMargin', 'grossProfit'), ('operatingMargin', 'operatingProfit'), ('ebitdaMargin', 'ebitda'), ('netMargin', 'netProfit'), ('fcfMargin', 'fcf')]:
            v = ratio(r.get(numerator), r.get('revenue'))
            r[key] = v*100 if v is not None and not (financial and key in ('ebitdaMargin', 'fcfMargin')) else None
        r['cashConversion'] = None if financial else ratio(r.get('operatingCashFlow'), r.get('netProfit'))
        r['debtToEquity'] = None if financial else ratio(r.get('totalDebt'), r.get('equity'))
        r['roe'] = None
        if all(number(x.get('equity')) for x in (r, prior)):
            v = ratio(r.get('netProfit'), (r['equity']+prior['equity'])/2)
            r['roe'] = v*100 if v is not None else None
        tax = ratio(r.get('taxExpense'), r.get('pretaxProfit'))
        tax = tax if tax is not None and 0 <= tax <= 1 else None
        r['effectiveTaxRate'] = tax
        r['roic'] = None
        if not financial and tax is not None and number(r.get('operatingProfit')) and all(number(x.get(k)) for x in (r, prior) for k in ('equity', 'totalDebt', 'cash')):
            capital = sum(x['equity']+x['totalDebt']-x['cash'] for x in (r, prior))/2
            v = ratio(r['operatingProfit']*(1-tax), capital)
            r['roic'] = v*100 if v is not None else None
        # Cash-flow working-capital contribution is signed: a cash outflow is negative.
        keys = ('operatingProfit', 'depreciation', 'capex', 'workingCapitalCashChange')
        r['nopat'] = r['operatingProfit']*(1-tax) if tax is not None and number(r.get('operatingProfit')) else None
        r['fcffProxy'] = (r['nopat']+r['depreciation']-abs(r['capex'])+r['workingCapitalCashChange']) if not financial and tax is not None and all(number(r.get(k)) for k in keys) else None
        r['ocfToFcffBridge'] = r['fcffProxy']-r['fcf'] if number(r.get('fcffProxy')) and number(r.get('fcf')) else None
        r['growth'] = {}
        # Do not call a stub/multi-year gap a one-year growth observation.
        try: annual = 330 <= (dt.date.fromisoformat(r['fiscalEnd'])-dt.date.fromisoformat(prior['fiscalEnd'])).days <= 400
        except (KeyError, ValueError): annual = False
        for key in ('revenue', 'ebitda', 'operatingProfit', 'operatingCashFlow', 'totalDebt', 'sharesOutstanding'):
            old = prior.get(key)
            if key == 'ebitda' and not number(old) and all(number(prior.get(k)) for k in ('operatingProfit', 'depreciation')):
                old = prior['operatingProfit']+prior['depreciation']
            v = ratio(r.get(key), old) if annual else None
            r['growth'][key] = (v-1)*100 if v is not None else None
        oldfcf = prior.get('operatingCashFlow')-abs(prior['capex']) if all(number(prior.get(k)) for k in ('operatingCashFlow', 'capex')) else None
        v = ratio(r.get('fcf'), oldfcf) if annual and not financial else None
        r['growth']['fcf'] = (v-1)*100 if v is not None else None
        out.append(r)
    latest = out[0] if out else {}
    oldest = out[-1] if out else {}
    cagrs = {}
    try: years = (dt.date.fromisoformat(latest['fiscalEnd'])-dt.date.fromisoformat(oldest['fiscalEnd'])).days/365.25
    except (KeyError, ValueError): years = 0
    cagr_periods = {}
    for key in ('revenue', 'ebitda', 'operatingProfit', 'operatingCashFlow', 'fcf', 'sharesOutstanding'):
        available = [r for r in out if number(r.get(key))]
        first, last = (available[0], available[-1]) if available else ({}, {})
        try: span = (dt.date.fromisoformat(first['fiscalEnd'])-dt.date.fromisoformat(last['fiscalEnd'])).days/365.25
        except (KeyError, ValueError): span = 0
        v = ratio(first.get(key), last.get(key))
        cagrs[key] = ((v**(1/span)-1)*100 if span >= .9 and v is not None and v > 0 and first.get(key, 0) > 0 else None)
        cagr_periods[key] = {'start': last.get('fiscalEnd'), 'end': first.get('fiscalEnd'), 'years': round(span, 2)}
    complete = [r for r in out[:3] if number(r.get('fcffProxy'))]
    return {'annual': out, 'cagr': cagrs, 'cagrPeriods': cagr_periods, 'cagrYears': round(years, 2),
        'normalisedFCFF': statistics.median(r['fcffProxy'] for r in complete) if complete else None,
        'normalisationPeriods': [r['fiscalEnd'] for r in complete],
        'financialSector': financial,
        'fcffMethod': 'Median of up to three available annual EBIT × (1 − effective tax rate) + D&A − |capex| + signed cash-flow working-capital change. An unadjusted FCFF proxy, not management guidance. Impairments, non-operating D&A and other noncash items may distort it.'}


def enrich(companies, profiles, directory, offline=False, asof=None):
    """Save observed valuation ratios, never backcast current multiples into history."""
    from company_profiles import _restore_published
    root = Path(directory)
    path = root/'research_valuation_cache.json'
    try: history = json.loads(path.read_text())
    except (OSError, ValueError): history = {}
    if not history and not offline: history = _restore_published('research_valuation_cache.json')
    stamp = asof or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    for c in list(companies)+list(profiles):
        c['research'] = analyse(c.get('annual') or [], financial_sector(c))
        sym = c['symbol']
        saved = history.get(sym, [])
        if not isinstance(saved, list): saved = []
        # No new observations from cached/offline profiles or synthetic demonstrations.
        checked = str(c.get('financialAsOf') or '')[:10]
        if not offline and checked == stamp[:10] and not str(c.get('fundamentalSource', '')).startswith('SYNTHETIC'):
            point = {'date': stamp[:10], 'retrievedAt': c.get('financialAsOf'), 'source': 'Yahoo Finance snapshot; provider ratio definitions',
                'trailingPE': c.get('trailingPE'), 'enterpriseToEbitda': None if financial_sector(c) else c.get('enterpriseToEbitda'), 'priceToBook': c.get('priceToBook')}
            if any(number(point[k]) for k in ('trailingPE', 'enterpriseToEbitda', 'priceToBook')):
                saved = [p for p in saved if p.get('date') != point['date']]+[point]
        saved = sorted(saved, key=lambda p: p['date'])[-3660:]
        c['valuationHistory'] = saved
        history[sym] = saved
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, separators=(',', ':'), allow_nan=False))
