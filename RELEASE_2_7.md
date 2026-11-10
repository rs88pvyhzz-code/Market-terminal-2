# Release 2.7 — original ETF presentation restored

Reference: `rs88pvyhzz-code/market-terminal`, commit `ced3f6a` (the source of the working published ETF page). Base: latest Market Terminal 2 main, `37e9522`.

## Direct comparison and restored components

Inspected both repositories' `etf_panel.html`, `etf_frontend.js`, `etf_styles.css`, `etf_consolidation.py` and ETF sections of `terminal_template.html`, plus the original publication polish in `verify_snapshot.py`. The panel markup, base stylesheet and consolidation module are identical; the regression came from later rendering/style replacements rather than a missing old panel.

Restored the original final eight-column renderer from the original `terminal_template.html`/`etf_consolidation.py`: Fund/ticker, TER, P/S, fund AUM, 1Y, 3Y, 5Y, Cmp. Restored original row-click selection, checkbox controls, geographic headers and ordering, original representative-fund selection, the original six filter/search/sort controls, four compact coverage figures, original selected-fund detail/statistics layout and its existing period/basis/reference controls. The original fund/issuer/risk/tracking renderers and formulas remain in use.

Restored the original 600px table viewport and sticky headings, blue region headers, amber monospace table/section hierarchy, original table widths, cell spacing, filter grid, typography, summary spacing, selected-row colours and detail grids. CSS is scoped to the ETF panel; the eight main navigation tabs retain their current design. The ETF chart uses the original 290px SVG canvas height; only the display-height option changes, not its observations, conversion, matching or rebasing.

The restored styling comes from `etf_styles.css`, `etf_consolidation.py:COMPACT_ETF_CSS`, the ETF rules in the original `verify_snapshot.py`, and the original template's base component rules, scoped to this panel. Release 2.6's ETF replacement renderer/style block is removed. Release 2.4's ETF-specific style selectors now exclude the ETF panel, preserving their use in other audit areas. Shared terminal styles are countered with the original scoped component declarations. No global navigation or non-ETF redesign is introduced.

## Required adaptations, not another interface

The original same-index/card renderers repeated funds and allowed five additional comparisons. Those duplicate cards/all-fund lists are not restored. The existing original same-index area contains one table with no more than three distinct alternatives, keyed by exact catalogue benchmark, category and hedge label, with explicit hedge wording also kept separate. Missing variant/hedge metadata remains qualified. Selecting a benchmark in its existing selector selects a corresponding fund and updates the same detail view. No new selector, button, panel or disclosure is added.

The selected fund plus up to three matching alternatives may be charted; the original optional index/reference remains distinct. Comparison checkboxes do not silently switch the primary fund. Selecting a new fund removes incompatible comparisons. The principal table remains capped at two representatives per exact identity, including a selected fund when appropriate. The original Find Fund search runs over the entire current catalogue, so a ticker outside the shortlist can be found and selected without showing the whole catalogue as an unbounded page. The table retains its internal scroll position across rerenders.

## Data and scope preservation

All 132 current catalogue records, metadata, histories, sources and financial calculations are retained. No catalogue, issuer database, collector, cache/recovery or scheduled publication file changes. The original currently also contains 132 catalogue funds; 78 is the historical issuer-evidence subset, not the original full catalogue count. Neither the old catalogue nor its older financial observations are copied into Market Terminal 2.

The non-ETF portion of Release 2.6's presentation module is retained unchanged. Gilt and Treasury viewports, yields, source dates, calculations, Company Research, Markets, Economics and My Watchlist are outside this correction.

## Verification and screenshots

The actual original published page and actual current production payload are rendered at the same 1024×768 iPad landscape viewport using VUAG.L for both reference/detail captures. Original and restored source dates are labelled; their observations intentionally differ because the newer data is retained. Side-by-side page, table and selected-detail screenshots are generated. Pixel-comparable properties (panel font/spacing, heading font/colour, filter grid, table font/cell spacing and widths) are checked against the original rendered page, rather than only asserting that new controls exist.

The production workflow runs the new restoration test and all existing retained financial/research/news/gilt/Treasury tests. Tests cover all 132 records, two-fund caps, grouping/scrolling, selecting/changing a fund, search outside the shortlist, three genuine alternatives, chart membership and independently reconciled existing CAGR across all four currency/return bases, plus desktop/iPad/mobile layout. The old R2.6 UI-test command delegates to the replacement test, so its entry point remains usable. Financial regression tests are unchanged.

Screenshots and visual-property/source-hash records are uploaded as review artifacts. External missing issuer/AUM/benchmark evidence remains labelled; no data or claims are invented to make the reference match.

The original publication polish’s responsive detail grid (three columns at iPad landscape) is restored. The original existing US bond-reference disclosure is retained rather than forced permanently open by Release 2.5; no disclosure is added around selected-fund details or controls. Detail screenshot crops suppress only the sticky global command-bar overlay, without altering ETF content, styles or data.
