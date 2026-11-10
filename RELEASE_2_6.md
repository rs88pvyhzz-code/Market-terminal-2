# Release 2.6 — ETF restoration and presentation cleanup

Built from latest main `d7ba5e9`. This release changes rendering and review tests, not catalogue records, sources, collectors, financial formulas, source recovery or scheduled publication.

## ETF display

One seven-column main table: fund/ticker, TER, P/S, fund-level AUM, annualised 1Y/3Y/5Y returns. Current quotations appear only in the selected fund details. Groups run Global, North America, UK, Europe, Asia-Pacific, Emerging Markets, then other markets if needed, bonds by existing government/credit/duration group order, specialist themes and commodities. Country/market and exact catalogue benchmark subheadings remain explicit.

At most two funds per benchmark/category/hedge identity are displayed. Identity keeps full benchmark strings, including net/gross, capped, equal-weight, ex-country and other variants; it does not group using a market-price proxy. Explicit hedge wording in names/markets is also kept separate. Unspecified hedge/return variants remain evidence gaps, visibly labelled; the UI does not certify missing benchmark definitions.

Shortlist priority is transparent, without an investment score: verified fund AUM first, larger comparable AUM using the existing snapshot-FX helper, lower known TER, then available return/history coverage and ticker as a stable tie-break. Unverified audit fallbacks do not count as verified AUM. Where currency conversion is unavailable, no synthetic AUM comparison is made. Missing AUM displays Unavailable; a reported zero remains zero. Source/as-of qualifications remain in selected details. Sorting changes ordering within benchmark groups, not the eligibility cap or geographic ordering.

The full 132-fund catalogue remains searchable, selectable and exportable. Search/filters run on the full catalogue before the main-table cap. A complete-catalogue selector makes every filtered fund available, including lines omitted from the default shortlist. Selecting a fund updates facts, sources, risk, tracking measures, issuer evidence, chart and alternatives. The selected fund is not automatically substituted for a preferred main-table fund, so the shortlist remains stable.

One alternatives table shows at most three other exact-label/hedge-compatible funds, deduplicated by ISIN where known. Selected-fund details are shown once; alternatives are not repeated as cards or all-fund lists. Comparison checkboxes change chart membership without changing the selected fund. Selected plus at most three alternatives can be plotted; switching to a different benchmark clears incompatible selections. The existing optional index/reference remains explicitly separate from ETF comparisons. Existing matched-date rebasing, GBP/GBp/FX, four return bases, risk and tracking mathematics are reused unchanged. Main-table returns retain their existing stored basis; alternative returns follow the explicitly selected chart basis.

Removed redundant same-market peer list, overlapping all-benchmark/cards/checked-card panels, repeated current AUM/replication/spread tiles and the generic tracking-difference placeholder. Unique dated NAV tracking, audited historical AUM/lending data, risk indicators, source links and audit warnings remain directly visible. US-domiciled bond references remain separate from UCITS fund comparisons.

## Other cleanup

Markets' short movement list excludes shares already in the detailed index mover universe and movements already in the daily briefing. Unique observations and the full mover data/analytics remain. Cross-market conditions use an aligned dated table with the same inputs/definitions. Overview watchlist news requires existing materiality evidence or an official confirmed development; full news remains in Markets and My Watchlist. News thresholds and classification are unchanged.

Company Research removes repeated share-price/P/E/EV-EBITDA snapshot tiles only when those values already appear in its summary; bank-specific exclusions and unique fields remain. Empty chart boxes become compact coverage notices retaining the missing-data message. Official gilt bid/offer display uses three decimals alongside existing three-decimal model yields; stored prices and calculations are untouched. Both accrued-interest exceptions and their ranking/ladder restrictions remain.

All substantive information remains direct. Only existing quality warnings, exceptions and technical diagnostics are disclosures; no nested disclosures or new top-level navigation.

## Verification and limitations

The PR runs all existing financial/ETF/research/gilt/news regressions, DMO freshness verification and the complete actual production collection/build. New browser checks use the supplied real payload, never substitute fixtures, and verify caps, geographic order, full catalogue selection, exact peers, selection refresh, chart membership, independently reconciled existing CAGR calculations across four bases, and desktop/iPad/mobile layouts. Existing regression suites retain Shell/Microsoft/HSBC, notes, navigation, economics, watchlist and Data Quality checks.

Screenshots of the complete ETF page, selected details, compact comparison, Markets and Company Research at desktop and iPad widths are uploaded with production verification. Demo checks are labelled separately. Existing missing issuer definitions, undated AUM and source gaps remain visible; this presentation release does not invent or repair financial data.

## Final Treasury viewport correction

Only the US Treasury securities wrapper now has a `min(60vh, 600px)` maximum height, internal vertical scrolling and sticky column headings. Search/type controls, source notes, selected-security calculations and the price chart remain outside it. Row rebuilds save and restore both scroll offsets, including on selection, manual-price changes and chart-period updates. Filtering naturally clamps the offset if the result list becomes shorter. The shared `.constituents-scroll` rule, gilt viewport, equity constituent lists and ETF layout are unchanged.

`tests/browser_treasury_scroll.py` verifies the full actual securities count, all security-type filters, CUSIP search, sticky headers after scrolling, selection/manual-price/period scroll retention, source dates and scoped styles at 1440px desktop and 1024px iPad landscape. It runs in both existing regression/production workflows; the third DMO workflow remains unchanged. Treasury screenshots are included in the production artifact.
