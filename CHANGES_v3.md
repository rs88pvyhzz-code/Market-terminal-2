# Market Terminal: Release 3.0 (12 Nov 2026)

## Layout
- **All analytics on the Analytics tab**, grouped Markets, Company, Bonds & rates, ETFs, Watchlist. Each group shows what's selected and has a button back to where you change it.
- Moved in: company vs index, risk & momentum, RSI/moving averages, executive summary, peer comparison, accounting checks, after-tax gilt comparison, gilt ladder, US yield spread, cross-country spreads, ETF performance and risk, same-index ETF comparison, watchlist risk, cross-market conditions, research alerts.
- Overview: Key market news, Global market pulse, More market headlines (no repeats), Upcoming events. Markets: price charts and global prices. Equities: movers, constituents, screener.
- Removed as duplicates or clutter: second market-conditions panel, overview watchlist box, observed-moves panel, watchlist news references, all jump-link chip bars and sub-tab strips, every per-panel "data checks" button, "Dashboard rules".
- Company coverage panels moved to Data Quality.
- Phone tables fixed: cells no longer break into one letter per line; wide tables scroll sideways as in Terminal 1.

## Structure
- `terminal_layout.js` is the single source of truth for which panel lives on which tab. Panels are moved, never rebuilt, so no figures change. Retired panels are hidden, not deleted, so older code can't crash.
- `build_site.py` is the one build command used by all three workflows: build, verify, post-process, layout. The sequence was previously copied by hand into each workflow and had drifted.
- `build_terminal.py` assembles the front end from one ordered manifest and stops if an insertion point is missing. Before, a missing marker silently dropped a whole layer.
- CSS written for a panel's old location is twinned for its new one at build time, so moved panels keep their styling. Rule counts are identical before and after.
- `run_tests.py` and `tests/run_browser.py` discover tests automatically; workflows no longer list them one by one.
- New tests: `test_build_pipeline.py` and `tests/browser_layout.py`. The latter fails if any analytics panel appears outside Analytics or an undeclared panel drifts onto a tab.

## Bugs fixed
- The research upgrade crashed when Analytics panels weren't direct children, silently skipping its company, quality and overview setup.
- `terminal_release29.js` dragged risk and benchmark panels back into Company Research on every company render.
- Links to `#peer-panel` and `#forensic-panel` now open Analytics.
- Stale text pointing to "Markets" for news and movers.

## Deleted
`publish.yml` in the root: a dead, diverged duplicate of the real workflow. Also `apply_etf_issuer_data.py` and `etf_return_standardization.py`, which nothing referenced.

## Known limits
- The 9 CSS and 12 JS presentation layers still override each other. This release contains that debt; it doesn't remove it.
- Email alerts (`alerts.py`) are not run by any workflow. The step existed only in the deleted dead copy.
