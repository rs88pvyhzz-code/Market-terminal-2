# Release 2.4 — presentation and navigation

This release changes rendering, layout and content placement only. Collectors, scheduled publication, financial models, news classifications/thresholds, source caches and verification remain unchanged. `window.MT_DATA` is read without modification. Legacy disclosure elements are converted into ordinary visible sections after every renderer, retaining child controls, source links, IDs and notes. No accordion, Show More interaction or closed details element is introduced.

## What changed

- **Overview:** exactly five sections. Seven snapshot instruments; at most three material macro/major-market developments; a four-row conditions table; at most two meaningful watchlist items; the next three significant sourced calendar releases. Routine individual share moves do not fill macro developments. Fewer supported events means fewer rows, with a concise notice. Dates remain visible. No missing figure is estimated.
- **Markets / Prices & Markets:** existing price charts and selectors, global movement list, complete index-constituent movers, cross-market conditions, and detailed research alerts. The former full five-item daily briefing and watchlist references remain here.
- **Markets / News:** full existing ranked and deduplicated feed, all subjects by default, with the six subject categories and regional filters. Every article in the selection is shown in a vertical list; sources, publication/retrieval times, archive labels, significance evidence and alternate publisher links are visible.
- **Markets / Risk & Relative Performance:** existing comparisons, risk, correlation, valuation, breadth and sector panels. The former Equities breadth/sector route redirects here. Equity screening, constituents and Company Research remain under Equities & Research. Eight main tabs and six research views remain.
- **Economics:** the complete future calendar is a chronological table with every individual release, UK/US/euro-area filters, source links, and previous/forecast/actual columns. Only explicitly sourced forecast fields are displayed. Otherwise the cell says Unavailable. Times retain their source timezone notation; unspecified times remain unavailable. Existing actual economic observations remain separately labelled by observation period and are never substituted for calendar release dates.
- **Research, bonds, ETFs and watchlist:** uniform fonts, compact table spacing, visible support/source sections, aligned year headings and numeric columns, wrapping security names and source strings. Research notes remain editable. Gilt source dates and both yield-review restrictions remain prominent and unchanged.

## Removed duplication

The redundant quote-tile snapshot is removed from the visible page; all of those instruments and figures remain in the Markets price table, with seven selected values on Overview. Identical repeated research methodology paragraphs within a research view are shown once. Long source diagnostics remain in Data Quality, directly visible rather than nested inside disclosures. No underlying payload fields are removed.

## Verification

The normal financial/ETF/research/gilt tests and actual-production-source workflow remain in place. Presentation regressions are updated to expect direct visibility and relocated panels rather than a closed accordion. `tests/browser_release24.py` checks five Overview sections, seven indicators, event limits, complete calendar columns, relocated content, eight main tabs, six research views, 3Y/5Y financial tables, no disclosure elements and no page overflow at desktop, iPad landscape and mobile widths. Screenshots are generated for Overview, Markets, Economics, Company Research and Bonds & Rates on desktop and iPad.
