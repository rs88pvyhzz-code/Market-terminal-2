"""Layout invariants for terminal_layout.js.

1. Every market-wide analytics panel is on the Analytics tab and nowhere else;
   analysis of the selected company stays in Company Research.
2. Every panel on every other tab is declared in the layout (nothing drifts in).
3. Retired panels and jump-link bars are never visible.
4. The layout holds after changing company, research view, ETF and watchlist
   selection, at phone and desktop widths, with no page errors and no sideways
   page scroll.

Usage: python tests/browser_layout.py terminal.html
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

html = Path(sys.argv[1]).read_text()
L_RESEARCH_IDS = ['company-benchmark-block', 'company-risk-panel', 'company-advanced', 'research-executive', 'peer-panel', 'forensic-panel']
TABS = ['overview', 'fx', 'equities', 'companies', 'bonds', 'analytics', 'etfs', 'economics', 'watchlist', 'quality']

CHECK = '''() => {
  const L = window.terminalLayout, $ = id => document.getElementById(id), problems = [];
  const analyticsIds = L.ANALYTICS.flatMap(g => g.items);
  for (const id of analyticsIds) {
    const n = $(id);
    if (n && !n.closest('#view-analytics')) problems.push('analytics panel outside Analytics: ' + id);
  }
  for (const [key, ids] of Object.entries(L.TABS)) {
    const view = $('view-' + key); if (!view) { problems.push('missing view ' + key); continue; }
    for (const child of view.children) {
      if (child.classList.contains('workspace-title') || child.hidden) continue;
      if (getComputedStyle(child).display === 'none') continue;
      if (!ids.includes(child.id)) problems.push('undeclared panel on ' + key + ': ' + (child.id || child.className));
    }
  }
  for (const id of L.RETIRED_IDS) {
    const n = $(id);
    if (n && n.getClientRects().length) problems.push('retired panel visible: ' + id);
  }
  for (const sel of ['.terminal-subnav', '.r25-section-links', '#mt-bond-nav', '.t11-quality-shortcut', '.mt-quality-link'])
    document.querySelectorAll(sel).forEach(n => { if (n.getClientRects().length) problems.push('retired control visible: ' + sel); });
  for (const id of new Set([...analyticsIds, ...Object.values(L.TABS).flat()]))
    if (document.querySelectorAll('[id="' + id + '"]').length > 1) problems.push('duplicate id: ' + id);
  return problems;
}'''

with sync_playwright() as p:
    kwargs = {'executable_path': os.environ['CHROMIUM_EXECUTABLE']} if os.environ.get('CHROMIUM_EXECUTABLE') else {}
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'], **kwargs)
    for width, height in [(390, 844), (1440, 1000)]:
        page = browser.new_page(viewport={'width': width, 'height': height})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('http://localhost:8765/**', lambda r: r.fulfill(body=html, content_type='text/html'))
        page.goto('http://localhost:8765/', wait_until='domcontentloaded', timeout=120000)
        page.wait_for_timeout(400)
        assert page.evaluate('typeof window.terminalLayout') == 'object', 'layout module not loaded'

        def check(step):
            problems = page.evaluate(CHECK)
            assert not problems, (width, step, problems)

        for tab in TABS:
            page.locator('#tab-' + tab).click()
            page.wait_for_timeout(120)
            check('tab ' + tab)
            assert page.evaluate('document.body.scrollWidth<=innerWidth+1'), (width, tab, 'page scrolls sideways')

        page.locator('#tab-companies').click()
        options = page.locator('#company-pick option').evaluate_all('(o)=>o.map(x=>x.value).filter(Boolean)')
        for symbol in options[:3]:
            page.locator('#company-pick').select_option(symbol)
            page.wait_for_timeout(150)
            for i in range(page.locator('#research-nav [role=tab], #research-nav button').count()):
                page.locator('#research-tab-%d' % i).click()
                page.wait_for_timeout(60)
                check('company %s view %d' % (symbol, i))
        page.locator('#tab-analytics').click()
        page.wait_for_timeout(150)
        check('analytics after company change')
        for pid in L_RESEARCH_IDS:
            assert page.locator('#view-companies #' + pid).count() == 1, ('company panel left Company Research', pid)

        page.locator('#tab-etfs').click()
        page.wait_for_timeout(120)
        rows = page.locator('#etf-rows [data-etf-symbol]')
        if rows.count() > 2:
            rows.nth(2).click()
            page.wait_for_timeout(150)
        page.locator('#tab-analytics').click()
        page.wait_for_timeout(150)
        check('analytics after ETF change')
        assert page.locator('#view-analytics #etf-chart').count() == 1

        page.locator('#tab-watchlist').click()
        page.wait_for_timeout(120)
        wrows = page.locator('#watchlist-rows tr')
        if wrows.count() > 1:
            wrows.nth(1).click()
            page.wait_for_timeout(150)
        page.locator('#tab-analytics').click()
        page.wait_for_timeout(150)
        check('analytics after watchlist change')

        assert not errors, (width, errors)
        page.close()
    browser.close()
print('PASS layout: analytics only on Analytics, no undeclared or retired panels, stable across selections')
