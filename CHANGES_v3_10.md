# v3.10

- UK 10Y showed 0.00% in the sovereign table: a blank Bank of England value for the latest day was read as zero. Blank values are now skipped, so the table shows the last published yield.
- Company ratios (P/E, market cap, dividend yield, etc.) blank when the provider lookup fails: the last good summary is now shown, marked "as of <date>". Selected companies outside the indices (watchlist names such as SKWD, SIE.DE) are now kept in the summary cache too.
- Analytics keeps market-wide analysis only. Gilt analysis (after-tax comparison, ladder) sits under the gilt list; US spread under US Treasuries; cross-market rates under Yield curves; ETF performance, risk and alternatives stay on ETF Trackers; watchlist risk stays on My Watchlist (What changed? still last).
- Tests updated for the moves.
