# Market Terminal: Release 3.2 (12 Nov 2026)

## Economic data
- **New series, collected each build:**
  - UK: retail sales volume m/m and y/y (ONS J5EC/J5EB), core CPI (DKO8), regular pay growth (KAI9).
  - US: retail sales m/m and y/y (FRED RSAFS), core CPI (CPILFESL), core PCE (PCEPILFE), non-farm payrolls change (PAYEMS).
  - Euro area: retail sales volume m/m and y/y (Eurostat sts_trtu_m).
- Each series fails safely: a download failure blanks that card and logs a warning; the build carries on.
- **Calendar "Latest print"** now covers retail sales. US Employment Situation maps to payrolls.

## News
- **New searches:** US mega-caps (Nvidia, Apple, Microsoft and others) and leadership changes. The company search was previously fixed on four UK names.
- **CEO departures count as market-moving.** A reported CEO or chair departure is now significance evidence; speculation and "could" headlines are excluded.
- **More stories:** Key market news shows 8 (was 5); further headlines show 10 at a time (was 6).
- **Price-move alerts** (e.g. Dr Martens) carry a labelled "Find news →" link to a 3-day news search.

## Markets
- **UK yields:** Government bond yields leads with UK 5Y/10Y/20Y gilt yields (Bank of England spot) and TN28 (DMO price, Bonds & Rates yield model). All have charts.
- **Price moves by period** is grouped by asset class (indices by region, ETFs, currencies, commodities, crypto), best to worst within each group.
- **Index-duplicate ETFs removed from Price moves:** SPY, QQQ, IEUR, EWJ, EWU, INDA, EWZ, EWT. They stay in Global prices and ETF Trackers.
- TOPIX is listed with Asia-Pacific indices.

## Company Research
The overview metrics form one grid in four headed groups: Price & valuation, Size & growth, Profitability, Cash & balance sheet.

## Watchlist
- For ETFs and funds, the 52-week low sits beside the 52-week high in the key numbers.
- The "Fund fees & holdings — check issuer" placeholder is removed.
- "More financial data" hides when empty.
