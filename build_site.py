#!/usr/bin/env python3
"""Build the published terminal with one command.

Every workflow calls this, so the order of build, verification and
post-processing is defined once. Previously three workflows repeated the same
five-step sequence by hand and had already drifted apart.

    python build_site.py --output terminal.html --verify -- --years 10 --workers 2 ...
    python build_site.py --demo --output /tmp/research-demo.html

Everything after `--` is passed unchanged to build_terminal.py.

Stages
  1. build_terminal.py           download data, assemble template + front-end manifest
  2. verification (--verify)     hard: verify_live_research, verify_snapshot
                                 soft: verify_dmo --existing, verify_market_briefing
                                 (--strict-news makes the briefing check hard)
  3. terminal_research_upgrade   research layout, after-tax gilt comparison
  4. market_terminal_cleanup     period returns, economics, data quality
  5. layout                      news_freshness.js after the snapshot data;
                                 terminal_layout.css/js injected last, so the
                                 tab layout is the final word on placement
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAYOUT_CSS = 'terminal_layout.css'
LAYOUT_JS = 'terminal_layout.js'
LAYOUT_STYLE_ID = 'terminal-layout-styles'
LAYOUT_SCRIPT_ID = 'terminal-layout-script'
POLISH_CSS = 'terminal_polish.css'
POLISH_JS = 'terminal_polish.js'
NEWS_JS = 'news_freshness.js'
NEWS_SCRIPT_ID = 'news-freshness'


def run(label, args, required=True):
    print(f'\n== {label}', flush=True)
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    if result.returncode != 0:
        if required:
            raise SystemExit(f'{label} failed (exit {result.returncode}); the site was not built.')
        print(f'   {label} reported problems (exit {result.returncode}); continuing because it is diagnostic only.')


MAIN_SCRIPT_END = '\ninit();\n})();'

# Panels moved to the Analytics tab lose CSS written as "#old-parent .child".
# Rather than copy hundreds of rules, every such selector gets a twin scoped to
# a class (".scope-old-parent .child"), and the Analytics group containers carry
# those classes (see ANALYTICS[].scopes in terminal_layout.js).
SCOPE_TOKENS = ['#etf-tracker-panel', '#gilts', '#research-view-0', '#view-bonds', '#view-companies',
                '#view-etfs', '#view-fx', '.etf-detail', '.research-view', '.panel']
_SCOPE_RE = re.compile('(' + '|'.join(re.escape(t) for t in SCOPE_TOKENS) + r')(?![\w-])(?=[^,{]*?[\s>+~][^\s,{])')


def _split_selectors(prelude):
    parts, depth, cur = [], 0, ''
    for ch in prelude:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return parts


def _scope_aliases(selector):
    """'#gilts .row h3' -> ['.scope-gilts .row h3'].

    Only tokens used as an ancestor (followed by a combinator and more selector)
    and outside parentheses are aliased. With several tokens, one alias replaces
    all of them and one alias per token replaces just that token.
    """
    depth, spans = 0, []
    for m in _SCOPE_RE.finditer(selector):
        depth = sum(1 if c in '([' else -1 if c in ')]' else 0 for c in selector[:m.start()])
        if depth == 0:
            spans.append(m)
    def build(chosen):
        out, pos = '', 0
        for m in chosen:
            out += selector[pos:m.start()] + '.scope-' + m.group(1)[1:]
            pos = m.end()
        return (out + selector[pos:]).strip()
    variants = [build(spans)] if spans else []
    if len(spans) > 1:
        variants += [build([m]) for m in spans]
    return list(dict.fromkeys(variants))


def add_scope_aliases(css):
    result, i, n = [], 0, len(css)
    while i < n:
        j = css.find('{', i)
        if j == -1:
            result.append(css[i:])
            break
        prelude = css[i:j]
        head = prelude.lstrip('}\n\r\t ')            # '}' here closes an enclosing @-block
        if head.startswith('@'):
            result.append(css[i:j + 1])          # @media/@supports: descend into the block
            i = j + 1
            continue
        k = css.find('}', j)
        if k == -1:
            result.append(css[i:])
            break
        # Leading '}' characters close @-blocks; keep them before the selector.
        lead = len(prelude) - len(prelude.lstrip('}\n\r\t '))
        selectors = _split_selectors(prelude[lead:])
        aliases = [a for sel in selectors for a in _scope_aliases(sel)]
        if aliases:
            prelude = prelude.rstrip() + ',' + ','.join(a.strip() for a in aliases)
        result.append(prelude + css[j:k + 1])
        i = k + 1
    return ''.join(result)


def alias_all_styles(html):
    return re.sub(r'(<style[^>]*>)(.*?)(</style>)', lambda m: m.group(1) + add_scope_aliases(m.group(2)) + m.group(3),
                  html, flags=re.S)


def inject_layout(html_path):
    """Insert the layout stylesheet into <head> and the layout script inside the
    main application script, straight after init().

    The application runs inside one closure, so code outside it cannot reach
    paintWorkspace, activateWorkspace or the renderers. The layout must live in
    the same scope. Idempotent: a second run changes nothing.
    """
    html = html_path.read_text('utf-8')
    if f'/*{LAYOUT_SCRIPT_ID}*/' in html:
        print('   layout already present')
        return
    for marker, label in (('</head>', 'stylesheet'), (MAIN_SCRIPT_END, 'script')):
        if html.count(marker) != 1:
            raise SystemExit(f'Layout {label} insertion point found {html.count(marker)} times (expected 1): {marker!r}')
    # The polish layer follows the layout so it has the last word on presentation.
    css = (ROOT / LAYOUT_CSS).read_text('utf-8') + '\n' + (ROOT / POLISH_CSS).read_text('utf-8')
    js = (ROOT / LAYOUT_JS).read_text('utf-8') + '\n' + (ROOT / POLISH_JS).read_text('utf-8')
    if '</script' in js.lower() or '</style' in css.lower():
        raise SystemExit('Layout assets must not contain closing script or style tags.')
    # News freshness runs on the snapshot data before the application reads it.
    data_at = html.find('window.MT_DATA')
    data_end = html.find('</script>', data_at)
    if data_at < 0 or data_end < 0:
        raise SystemExit('Snapshot data script not found; cannot apply the news freshness rule.')
    news_js = (ROOT / NEWS_JS).read_text('utf-8')
    if '</script' in news_js.lower():
        raise SystemExit(f'{NEWS_JS} must not contain a closing script tag.')
    data_end += len('</script>')
    html = html[:data_end] + f'\n<script id="{NEWS_SCRIPT_ID}">\n{news_js}\n</script>' + html[data_end:]
    html = alias_all_styles(html)
    html = html.replace('</head>', f'<style id="{LAYOUT_STYLE_ID}">\n{css}\n</style>\n</head>')
    html = html.replace(MAIN_SCRIPT_END, f'\ninit();\n/*{LAYOUT_SCRIPT_ID}*/\n{js}\n}})();')
    html_path.write_text(html, 'utf-8')
    print(f'   layout injected into {html_path.name}')


def main():
    argv = sys.argv[1:]
    passthrough = []
    if '--' in argv:
        i = argv.index('--')
        argv, passthrough = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output', required=True, help='HTML file to write')
    p.add_argument('--demo', action='store_true', help='synthetic offline data (for tests)')
    p.add_argument('--verify', action='store_true', help='run production data verification')
    p.add_argument('--strict-news', action='store_true', help='fail the build on news provenance problems')
    a = p.parse_args(argv)
    if a.demo and a.verify:
        p.error('--verify checks real data; it cannot be combined with --demo')

    out = Path(a.output)
    html = str(out if out.is_absolute() else ROOT / out)
    build = ['build_terminal.py', '--output', html] + (['--demo'] if a.demo else []) + passthrough
    run('Download data and build terminal', build)

    if a.verify:
        run('Verify published research payload', ['verify_live_research.py', html])
        run('Check market data', ['verify_snapshot.py', html])
        run('DMO freshness diagnostics', ['verify_dmo.py', '--existing'], required=False)

    run('Research layout and after-tax gilt comparison', ['terminal_research_upgrade.py', html])
    run('Market analysis, economics and data quality', ['market_terminal_cleanup.py', '--post', '--html', html])
    print('\n== Tab layout')
    inject_layout(Path(html))

    if a.verify:
        run('News provenance and coverage', ['verify_market_briefing.py', html], required=a.strict_news)
    print(f'\nBuilt {html}')


if __name__ == '__main__':
    main()
