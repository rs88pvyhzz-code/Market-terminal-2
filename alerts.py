#!/usr/bin/env python3
"""Private email alerts, checked after every build.

Rules and mail credentials come ONLY from encrypted GitHub repository secrets,
never from files in the public repo:

  ALERT_EMAIL     the sending mailbox (ideally a dedicated account used only for this)
  ALERT_TO        optional: where alerts go (default: ALERT_EMAIL)
  ALERT_PASSWORD  an app-specific password for that mailbox
  ALERT_RULES     one rule per line:  SYMBOL, CONDITION, THRESHOLD[, note]
  ALERT_TAX_RATE  optional coupon tax % for gilt net-yield rules (default 20)
  ALERT_SMTP      optional host:port if your provider is not detected

Conditions
  price_above / price_below        last price (instrument's own units)
  day_up / day_down                daily move in % (day_down 5 = fell 5% or more)
  gilt_yield_above / _below        gross yield to maturity, % (DMO offer price)
  gilt_net_yield_above / _below    after-tax yield at ALERT_TAX_RATE, %

Examples
  TN28, gilt_net_yield_above, 4.2, short gilt cheap
  SKWD, day_down, 5
  ^FTSE, day_down, 2.5
  GBPUSD=X, price_below, 1.25

A rule emails at most once per UK day. The record of what was sent is published
as hashes only (alerts_state.json), so the public site reveals no rules.
Failures here never fail the build.
"""
from __future__ import annotations
import calendar
import datetime as dt
import hashlib
import json
import os
import pathlib
import smtplib
import ssl
import sys
import urllib.request
from email.message import EmailMessage
from zoneinfo import ZoneInfo

STATE = 'alerts_state.json'
SMTP_BY_DOMAIN = {
    'gmail.com': 'smtp.gmail.com:587', 'googlemail.com': 'smtp.gmail.com:587',
    'icloud.com': 'smtp.mail.me.com:587', 'me.com': 'smtp.mail.me.com:587', 'mac.com': 'smtp.mail.me.com:587',
    'outlook.com': 'smtp-mail.outlook.com:587', 'hotmail.com': 'smtp-mail.outlook.com:587',
    'hotmail.co.uk': 'smtp-mail.outlook.com:587', 'live.com': 'smtp-mail.outlook.com:587',
    'live.co.uk': 'smtp-mail.outlook.com:587', 'yahoo.com': 'smtp.mail.yahoo.com:587',
    'yahoo.co.uk': 'smtp.mail.yahoo.com:587',
}
CONDITIONS = {'price_above', 'price_below', 'day_up', 'day_down', 'gilt_yield_above', 'gilt_yield_below',
              'gilt_net_yield_above', 'gilt_net_yield_below'}


# ---------- gilt yield (same DMO conventions as the page; tested against it) ----------
def _bizadd(d, n):
    step = 1 if n > 0 else -1
    left = abs(n)
    while left:
        d += dt.timedelta(days=step)
        if d.weekday() < 5:
            left -= 1
    return d


def _months(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    y += d.year
    mo += 1
    return d.replace(year=y, month=mo, day=min(d.day, calendar.monthrange(y, mo)[1]))


def gilt_yield(g, tax_pct=0.0):
    """Yield to maturity (%) from the DMO offer, settling T+3 as the DMO prices do."""
    try:
        clean, dirty = float(g['askClean']), float(g['askDirty'])
        trade, maturity = dt.date.fromisoformat(g['asOf']), dt.date.fromisoformat(g['maturity'])
        coupon = float(g['coupon']) / 2
    except (KeyError, TypeError, ValueError):
        return None
    if g.get('indexLinked') or clean <= 0 or dirty <= 0:
        return None
    settle = _bizadd(trade, 3)
    if settle >= maturity:
        return None
    dates, d = [], maturity
    while d > settle:
        dates.append(d)
        d = _months(d, -6)
    dates.reverse()
    prior, nxt = d, dates[0]
    s, r = (nxt - prior).days, (nxt - settle).days
    ex_div = settle >= _bizadd(nxt, -7)
    flows = []
    for k, _ in enumerate(dates):
        c = 0.0 if (k == 0 and ex_div) else coupon
        flows.append(((r / s + k) / 2, c * (1 - tax_pct / 100) + (100 if k == len(dates) - 1 else 0)))
    pv = lambda y: sum(a / (1 + y / 200) ** (2 * t) for t, a in flows)
    lo, hi = -50.0, 150.0
    if pv(lo) < dirty or pv(hi) > dirty:
        return None
    for _ in range(90):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pv(mid) > dirty else (lo, mid)
    return (lo + hi) / 2


# ---------- data ----------
def load(html_path):
    html = pathlib.Path(html_path).read_text('utf-8')
    marker = 'window.MT_DATA = '
    i = html.index(marker) + len(marker)
    return json.loads(html[i:html.index(';</script>', i)])


def instruments(data):
    """symbol -> (name, price, day %, units, as of). Later sources fill gaps only."""
    out = {}
    def add(sym, name, price, chg, unit, asof):
        if sym and sym.upper() not in out and price is not None:
            out[sym.upper()] = (name or sym, price, chg, unit or '', asof or '')
    for q in data.get('quotes') or []:
        add(q.get('symbol'), q.get('name'), q.get('price'), q.get('changePct'), q.get('currency'), q.get('asOf'))
    for q in data.get('watchlist_quotes') or data.get('watchQuotes') or []:
        add(q.get('symbol'), q.get('name'), q.get('price'), q.get('changePct'), q.get('currency'), q.get('asOf'))
    for c in data.get('companies') or []:
        add(c.get('symbol'), c.get('name'), c.get('price'), c.get('changePct'), c.get('priceCurrency'), c.get('priceAsOf'))
    for m in data.get('movers') or []:
        for c in m.get('constituents') or []:
            add(c.get('symbol'), c.get('name'), c.get('price'), c.get('changePct') if c.get('current') else None,
                c.get('currency'), c.get('asOf'))
    return out


def gilt_index(data):
    out = {}
    for g in data.get('gilts') or []:
        for key in (g.get('shortTicker'), g.get('isin'), g.get('ticker')):
            if key:
                out[str(key).upper()] = g
    return out


def parse_rules(text):
    rules, problems = [], []
    for n, line in enumerate((text or '').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 3 or parts[1].lower() not in CONDITIONS:
            problems.append(f'line {n}: expected SYMBOL, CONDITION, THRESHOLD')
            continue
        try:
            threshold = float(parts[2])
        except ValueError:
            problems.append(f'line {n}: threshold is not a number')
            continue
        rules.append({'symbol': parts[0].upper(), 'condition': parts[1].lower(), 'threshold': threshold,
                      'note': ', '.join(parts[3:])})
    return rules, problems


def _px(v):
    return f'{v:,.2f}' if abs(v) >= 10 else f'{v:,.4f}'


def evaluate(rules, data, tax_pct):
    inst, gilts = instruments(data), gilt_index(data)
    hits, unknown = [], []
    for r in rules:
        sym, cond, x = r['symbol'], r['condition'], r['threshold']
        if cond.startswith('gilt_'):
            g = gilts.get(sym)
            if not g:
                unknown.append(sym)
                continue
            net = 'net' in cond
            y = gilt_yield(g, tax_pct if net else 0.0)
            if y is None:
                continue
            fired = y >= x if cond.endswith('above') else y <= x
            if fired:
                label = f'after-tax yield at {tax_pct:g}%' if net else 'gross yield'
                hits.append((r, f"{g.get('name')} ({sym}) {label} {y:.3f}% "
                                f"{'≥' if cond.endswith('above') else '≤'} {x:g}% · DMO offer {g.get('askClean')} "
                                f"dated {g.get('asOf')}"))
            continue
        row = inst.get(sym)
        if not row:
            unknown.append(sym)
            continue
        name, price, chg, unit, asof = row
        if cond == 'price_above' and price >= x or cond == 'price_below' and price <= x:
            hits.append((r, f"{name} ({sym}) at {_px(price)} {unit} {'≥' if cond == 'price_above' else '≤'} {x:g} · {asof}"))
        elif cond == 'day_up' and chg is not None and chg >= x:
            hits.append((r, f"{name} ({sym}) up {chg:.2f}% today (alert at +{x:g}%) · price {_px(price)} {unit}"))
        elif cond == 'day_down' and chg is not None and chg <= -abs(x):
            hits.append((r, f"{name} ({sym}) down {abs(chg):.2f}% today (alert at -{abs(x):g}%) · price {_px(price)} {unit}"))
    return hits, sorted(set(unknown))


# ---------- once-per-day state (hashes only) ----------
def _key(rule, day):
    raw = f"{rule['symbol']}|{rule['condition']}|{rule['threshold']}|{day}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def previous_state():
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if '/' not in repo:
        return []
    owner, name = repo.split('/', 1)
    try:
        req = urllib.request.Request(f'https://{owner}.github.io/{name}/{STATE}',
                                     headers={'Cache-Control': 'no-cache', 'User-Agent': 'PersonalMarketResearch/1.1'})
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read(200_000).decode('utf-8'))
        return payload.get('sent', []) if isinstance(payload, dict) else []
    except Exception:
        return []


def send(address, password, smtp, subject, body, to=None):
    host, _, port = smtp.partition(':')
    port = int(port or 587)
    msg = EmailMessage()
    msg['From'] = address
    msg['To'] = to or address
    msg['Subject'] = subject
    msg.set_content(body)
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as s:
            s.login(address, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=context)
            s.login(address, password)
            s.send_message(msg)


def main(argv):
    html = argv[1] if len(argv) > 1 else 'terminal.html'
    public = pathlib.Path(argv[2] if len(argv) > 2 else 'public')
    rules, problems = parse_rules(os.environ.get('ALERT_RULES', ''))
    if not rules:
        print('Alerts: no ALERT_RULES secret set; nothing to check.' + (' Problems: ' + '; '.join(problems) if problems else ''))
        return 0
    try:
        tax = float(os.environ.get('ALERT_TAX_RATE') or 20)
    except ValueError:
        tax = 20.0
    data = load(html)
    hits, unknown = evaluate(rules, data, tax)
    today = dt.datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    sent = [k for k in previous_state() if isinstance(k, str)]
    fresh = [(r, text) for r, text in hits if _key(r, today) not in sent]
    print(f'Alerts: {len(rules)} rules, {len(hits)} triggered, {len(fresh)} new today'
          + (f', unknown symbols: {", ".join(unknown)}' if unknown else '')
          + (f', rule problems: {"; ".join(problems)}' if problems else ''))
    address, password = os.environ.get('ALERT_EMAIL', '').strip(), os.environ.get('ALERT_PASSWORD', '').strip()
    if fresh and address and password:
        smtp = os.environ.get('ALERT_SMTP') or SMTP_BY_DOMAIN.get(address.rsplit('@', 1)[-1].lower(), '')
        if not smtp:
            print('Alerts: unknown mail provider; set the ALERT_SMTP secret (host:port).')
        else:
            lines = [f'• {text}' + (f"  [{r['note']}]" if r['note'] else '') for r, text in fresh]
            extra = []
            if unknown:
                extra.append('Not found in this build (check spelling or ticker): ' + ', '.join(unknown))
            if problems:
                extra.append('Rules ignored: ' + '; '.join(problems))
            body = ('\n'.join(lines) + '\n\n' + ('\n'.join(extra) + '\n\n' if extra else '')
                    + f"Build {data.get('generatedAt')}. Prices are delayed snapshots from free sources; "
                      'verify before acting.\n')
            subject = (f'Market alert: {len(fresh)} triggered' if len(fresh) > 1
                       else 'Market alert: ' + fresh[0][1][:90])
            try:
                send(address, password, smtp, subject, body, os.environ.get('ALERT_TO', '').strip() or None)
                sent += [_key(r, today) for r, _ in fresh]
                print('Alerts: email sent.')
            except Exception as exc:
                print('Alerts: email failed (' + type(exc).__name__ + ': ' + str(exc)[:120] + ')')
    elif fresh:
        print('Alerts: ALERT_EMAIL / ALERT_PASSWORD secrets missing; not emailed.')
    public.mkdir(parents=True, exist_ok=True)
    # Keep ~10 days of hashes; they reveal nothing about the rules.
    (public / STATE).write_text(json.dumps({'sent': sent[-400:]}), 'utf-8')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # never fail the build
        print('Alerts: skipped after error: ' + type(exc).__name__ + ': ' + str(exc)[:150])
        sys.exit(0)
