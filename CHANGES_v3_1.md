# Market Terminal: Release 3.1 (12 Nov 2026)

## News
No headline older than 3 days appears anywhere. `news_freshness.js` prunes the snapshot in the browser before any panel renders, so stories drop off at 72 hours even between builds. Issuer documents (results, filings) are evidence, not news, and are kept.

## Company Research
- Company analysis is back with the company: vs-index chart, volatility & market risk, RSI / moving averages and the executive summary sit in Overview. Peer comparison and red flags are back in their own sub-tabs.
- The "All reported snapshot metrics" section is merged into the overview tiles as one block. Day move and market capitalisation, already in the tiles, are not repeated.
- Analytics now holds market-wide analysis only.

## Look
- Every tile follows the US Treasuries presentation: one framed grid, amber label, large mono value, grey caption. This covers the gilt hold-to-maturity box, credit spreads, economics cards, company and risk tiles, and ETF stats.
- Text is about 12% larger on tablets and desktops; small text is raised on phones.
- Panels and tables are cleaner. On phones every table scrolls sideways instead of squeezing headers.
- Same palette throughout.

## Markets
Global prices is split into sections: UK, European, Americas and Asia-Pacific indices, then ETFs, currencies, government yields, commodities and crypto.

## Economic calendar
- "Latest print" shows the most recent official value of the series each release updates (e.g. UK CPI before the CPI release).
- Forecast and Actual columns are removed. Consensus forecasts are proprietary wire-service polls, and an actual cannot exist before release.
- Non-statistical items (e.g. "update on progress") show as not a tracked series.

## ETF trackers
- **ICGA.L → CNYA.L:** iShares MSCI China A; ISIN IE00BQT3WG13, TER 0.40%; BlackRock page checked 12 Nov 2026. ICGA.L returned no price data.
- **INDA.L → NDIA.L:** iShares MSCI India; ISIN IE00BZCQB185, TER 0.65%; net assets USD 4.84bn at 22 Oct 2026. INDA.L had prices only from Mar 2026.
- **EMXN.L → EMXC.L:** same Amundi fund (ISIN LU2009202107), USD line, with price history from 2019 instead of Dec 2024.
- Funds listed less than 3 or 5 years ago still show blank 3Y/5Y figures. Those numbers do not exist and are not estimated.
