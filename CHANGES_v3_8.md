# v3.8 — usability

- Government yield snapshot removed from Bonds & Rates. Yield curves now opens with a curve strip: 2Y/5Y/10Y/20Y/30Y for UK (BoE), US and euro area (ECB), day change in bp, 2s10s.
- No scroll boxes inside the page: long tables run in page flow, first 20 rows then "Show all N". Selected rows always stay visible.
- ETF table on phones uses the full width; TER and P/S no longer collide.
- Search finds gilts (name, short code, ISIN) and US Treasuries (name, CUSIP) and lands on the detail; ETF results scroll to the fund.
- Chart periods: 1D (markets chart, where intraday exists), 1M, 1Y, 3Y, 5Y, MAX. Custom dates behind one DATES button.
- Formats: yield and spread changes in whole bp; returns and volatility to 2dp; gilt clean and dirty prices to 2dp, matching the gilt table.
- Tests updated for the page-flow rule; tests/expand_tables.py opens "Show all" where a test needs a row beyond the first 20.
