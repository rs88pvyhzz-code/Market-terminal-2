# v3.5 — polish layer

New files: terminal_polish.css, terminal_polish.js (injected last by build_site.py).

- ETF detail 1Y/3Y/5Y now show the same figures as the cards and table (Python return1Y/3Y/5Y). Basis stated once above the tiles.
- ETF tiles with no value (Unavailable, —, Not disclosed) are removed; sub-lines kept only where they carry a date.
- ETF metric tiles render as compact label | value rows.
- "Fund AUM" relabelled "Fund AUM (all classes)".
- "Not in main table" tag removed.
- Calendar: flat dated list; sub-line only when a real release time exists; ECB two-day meetings listed once (decision day).
- Economics actuals: empty forecast/surprise columns hidden; Source column shown once as a caption; indicator column sticky on phones.
- Stale flag beside any monthly print >80 days or quarterly print >140 days past period end.
- Explanatory notes removed (calendar subtitle, forecast-surprise text, methodology notes, ETF chart/warning notes).
- Data Quality removed from the tab bar; link at the foot of the page.
- Tests: tab clicks use dispatch_event so the hidden Data Quality tab stays testable.
